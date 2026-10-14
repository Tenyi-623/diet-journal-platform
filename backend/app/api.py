import hashlib, json, uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import FileResponse
from psycopg.types.json import Jsonb
from .db import connect
from .auth import require_user, login as do_login, mobile_login as do_mobile_login, HASHER, COOKIE, token_hash, request_token
from .schemas import (
    Login,
    PasswordChange,
    Profile,
    BP,
    PlanRequest,
    SubstituteRequest,
    ChatRequest,
)
from .planner import catalog, calculate, plan_day, RULE_VERSION
from .meal_selection import animal_food
from .feedback import FEEDBACK_VERSION, explain

router = APIRouter(prefix="/api")
ROOT = Path(__file__).resolve().parents[2]


def get_profile(c, uid):
    row = c.execute(
        "SELECT version,data FROM app_profiles WHERE user_id=%s", (uid,)
    ).fetchone()
    return (
        {"version": row["version"], "profile": row["data"]}
        if row
        else {
            "version": 0,
            "profile": Profile().model_dump(exclude={"expected_version"}),
        }
    )


def valid_uuid(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError):
        raise HTTPException(422, "Invalid identifier")


def job_create(c, user, kind, data, key):
    # User row lock serializes duplicate submission and per-user queue limits.
    c.execute("SELECT id FROM app_users WHERE id=%s FOR UPDATE", (user["id"],))
    existing = c.execute(
        "SELECT id,status,input,kind FROM app_jobs WHERE user_id=%s AND idempotency_key=%s",
        (user["id"], key),
    ).fetchone()
    if existing:
        if existing["kind"] != kind or existing["input"].get(
            "request_identity"
        ) != data.get("request_identity"):
            raise HTTPException(409, "幂等键已用于另一请求")
        return {
            "job_id": str(existing["id"]),
            "status": existing["status"],
            "session_id": existing["input"].get("session_id"),
        }, False
    n = c.execute(
        "SELECT count(*) n FROM app_jobs WHERE user_id=%s AND status IN ('queued','running')",
        (user["id"],),
    ).fetchone()["n"]
    if n >= 3:
        raise HTTPException(429, "已有请求处理中，请稍后提交")
    jid = str(uuid.uuid4())
    c.execute(
        "INSERT INTO app_jobs(id,user_id,idempotency_key,kind,status,input) VALUES(%s,%s,%s,%s,'queued',%s)",
        (jid, user["id"], key, kind, Jsonb(data)),
    )
    return {
        "job_id": jid,
        "status": "queued",
        "session_id": data.get("session_id"),
    }, True


@router.post("/auth/login")
def login(body: Login, request: Request, response: Response):
    return do_login(body, request, response)


@router.post("/auth/mobile/login")
def mobile_login(body: Login, request: Request, response: Response):
    return do_mobile_login(body, request, response)


@router.post("/auth/logout")
def logout(request: Request, response: Response, user=Depends(require_user)):
    token, _ = request_token(request)
    with connect() as c:
        c.execute(
            "DELETE FROM app_sessions WHERE token_hash=%s",
            (token_hash(token),),
        )
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.post("/auth/password")
def password(body: PasswordChange, user=Depends(require_user)):
    with connect() as c:
        row = c.execute(
            "SELECT password_hash FROM app_users WHERE id=%s FOR UPDATE", (user["id"],)
        ).fetchone()
        if not HASHER.verify(body.current_password, row["password_hash"]):
            raise HTTPException(400, "当前密码不正确")
        c.execute(
            "UPDATE app_users SET password_hash=%s WHERE id=%s",
            (HASHER.hash(body.new_password), user["id"]),
        )
        c.execute("DELETE FROM app_sessions WHERE user_id=%s", (user["id"],))
    return {"ok": True, "message": "密码已修改，请重新登录"}


@router.get("/me")
def me(user=Depends(require_user)):
    return user


@router.get("/profile")
def profile(user=Depends(require_user)):
    with connect() as c:
        return get_profile(c, user["id"])


@router.patch("/profile")
def update_profile(body: Profile, user=Depends(require_user)):
    if body.allergy_status == "none" and body.allergens:
        raise HTTPException(422, "无过敏与选中症状冲突")
    if body.allergy_status == "present" and not body.allergens:
        raise HTTPException(422, "请选择过敏原")
    with connect() as c:
        c.execute("SELECT id FROM app_users WHERE id=%s FOR UPDATE", (user["id"],))
        current = get_profile(c, user["id"])
        if current["version"] != body.expected_version:
            raise HTTPException(409, "资料已更新，请刷新后再试")
        if body.dislikes:
            known = {
                r["code"]
                for r in c.execute("SELECT code FROM app_ingredients").fetchall()
            }
            if not set(body.dislikes) <= known:
                raise HTTPException(422, "未知食品")
        data = body.model_dump(exclude={"expected_version"})
        c.execute(
            """INSERT INTO app_profiles(user_id,data) VALUES(%s,%s)
            ON CONFLICT(user_id) DO UPDATE SET version=app_profiles.version+1,data=excluded.data,updated_at=now()""",
            (user["id"], Jsonb(data)),
        )
        c.execute("DELETE FROM app_home_cache WHERE user_id=%s", (user["id"],))
        return get_profile(c, user["id"])


@router.get("/income-bands")
def income(user=Depends(require_user)):
    with connect() as c:
        return {
            "bands": c.execute(
                "SELECT * FROM app_income_policies ORDER BY lower_jpy"
            ).fetchall()
        }


@router.get("/foods")
def foods(q: str = Query(default="", max_length=100), user=Depends(require_user)):
    with connect() as c:
        rows = c.execute(
            "SELECT code,name,allergens,data FROM app_ingredients WHERE name::text ILIKE %s ORDER BY code LIMIT 50",
            ("%" + q + "%",),
        ).fetchall()
        return {"foods": rows, "scope": "reviewed_demo_subset"}


@router.get("/foods/{code}")
def food_detail(code: str, user=Depends(require_user)):
    with connect() as c:
        row = c.execute(
            "SELECT dataset_id FROM app_ingredients WHERE code=%s", (code,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "食品不在演示子集中")
        f = c.execute(
            "SELECT * FROM foods WHERE dataset_id=%s AND code=%s",
            (row["dataset_id"], code),
        ).fetchone()
        vals = c.execute(
            "SELECT * FROM food_values WHERE dataset_id=%s AND food_code=%s ORDER BY nutrient_code",
            (row["dataset_id"], code),
        ).fetchall()
        return {"food": f, "values": vals}


@router.get("/recipes")
def recipes(user=Depends(require_user)):
    ingredients, rows = catalog()
    return {"recipes": [calculate(r, ingredients) for r in rows]}


@router.get("/recipes/{rid}")
def recipe(rid: str, user=Depends(require_user)):
    ingredients, rows = catalog()
    row = next((r for r in rows if r["id"] == rid), None)
    if not row:
        raise HTTPException(404, "食谱不存在")
    return calculate(row, ingredients)


@router.get("/recipe-images/{rid}")
def image(rid: str, lang: Literal["zh", "en", "ja"] = "zh", user=Depends(require_user)):
    import re

    if not re.fullmatch(r"(?:[bld][1-7]|r178-[bld][0-9]{3}|nuts-b[0-9]{3})", rid):
        raise HTTPException(404)
    path = ROOT / "frontend/public/recipe-art" / f"{rid}.svg"
    translated = path.with_name(f"{rid}.{lang}.svg")
    if lang != "zh" and translated.is_file():
        path = translated
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(
        path,
        media_type="image/svg+xml",
        headers={"Cache-Control": "private,max-age=3600"},
    )


@router.get("/home/today")
def home(user=Depends(require_user)):
    with connect() as c:
        p = get_profile(c, user["id"])
        ingredients, rows = catalog(c)
        policies = c.execute("SELECT * FROM app_income_policies ORDER BY id").fetchall()
        version_data = [(r["id"], r["version"], r["ingredients"]) for r in rows]
        key = hashlib.sha256(
            json.dumps(
                [
                    datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat(),
                    p,
                    version_data,
                    [
                        (k, str(v["price_per_100g"]), v["data"], v["nutrients"])
                        for k, v in ingredients.items()
                    ],
                    policies,
                    RULE_VERSION,
                    FEEDBACK_VERSION,
                ],
                default=str,
                sort_keys=True,
            ).encode()
        ).hexdigest()
        old = c.execute(
            "SELECT result FROM app_home_cache WHERE user_id=%s AND cache_key=%s",
            (user["id"], key),
        ).fetchone()
        if old:
            return old["result"]
    result = plan_day(p["profile"])
    if result["status"] == "ready":
        result["personalized"] = True
    else:
        examples = []
        # Unsupported health profiles get no implied suitable food cards.
        if result["status"] != "unsupported":
            for r in sorted(rows, key=lambda r: (r["id"][1:], r["meal"])):
                m = calculate(r, ingredients)
                if set(m["allergens"]) & set(p["profile"].get("allergens", [])):
                    continue
                if any(
                    x["code"] in p["profile"].get("dislikes", [])
                    for x in m["ingredients"]
                ):
                    continue
                if p["profile"].get("diet") == "vegetarian" and any(
                    animal_food(x["code"]) for x in m["ingredients"]
                ):
                    continue
                if m["minutes"] > p["profile"].get("cooking_minutes", 45):
                    continue
                examples.append(m)
                if len(examples) == 6:
                    break
        result.update(
            {
                "personalized": False,
                "examples": examples,
                "note": "食谱示例，完善信息后生成个人推荐。图片为示意图；不能据此判断适合个人。",
            }
        )
    result["date"] = datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    with connect() as c:
        c.execute(
            "INSERT INTO app_home_cache(user_id,cache_key,result) VALUES(%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET cache_key=excluded.cache_key,result=excluded.result,updated_at=now()",
            (user["id"], key, Jsonb(result)),
        )
    return result


@router.get("/blood-pressure")
def bp_list(user=Depends(require_user)):
    with connect() as c:
        return {
            "records": c.execute(
                "SELECT id,systolic,diastolic,measured_at FROM app_bp WHERE user_id=%s ORDER BY measured_at DESC LIMIT 100",
                (user["id"],),
            ).fetchall()
        }


@router.post("/blood-pressure")
def bp_add(body: BP, user=Depends(require_user)):
    if (
        body.systolic <= body.diastolic
        or not body.measured_at.tzinfo
        or body.measured_at > datetime.now(timezone.utc)
    ):
        raise HTTPException(422, "请核对血压与测量时间")
    with connect() as c:
        row = c.execute(
            "INSERT INTO app_bp(user_id,systolic,diastolic,measured_at) VALUES(%s,%s,%s,%s) RETURNING id",
            (user["id"], body.systolic, body.diastolic, body.measured_at),
        ).fetchone()
    return {**row, "note": "仅记录，不根据单次测量诊断或修改治疗。"}


@router.post("/recommendation-jobs", status_code=202)
def create_plan(body: PlanRequest, user=Depends(require_user)):
    with connect() as c:
        p = get_profile(c, user["id"])
        if body.language:
            p["profile"]["language"] = body.language
        result, _ = job_create(
            c,
            user,
            "plan",
            {
                "profile": p["profile"],
                "profile_version": p["version"],
                "budget": body.budget,
                "budget_min": body.budget_min,
                "request_identity": {
                    "budget": body.budget, "language": body.language,
                    **({"budget_min": body.budget_min} if body.budget_min is not None else {}),
                },
            },
            body.idempotency_key,
        )
        return result


@router.get("/recommendation-jobs/{jid}")
def get_job(jid: str, user=Depends(require_user)):
    with connect() as c:
        row = c.execute(
            "SELECT id,status,result,created_at,updated_at FROM app_jobs WHERE id=%s AND user_id=%s",
            (valid_uuid(jid), user["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, "任务不存在")
    return row


@router.post("/recommendation-jobs/{jid}/cancel")
def cancel(jid: str, user=Depends(require_user)):
    with connect() as c:
        row = c.execute(
            "SELECT input FROM app_jobs WHERE id=%s AND user_id=%s AND status IN ('queued','running') FOR UPDATE",
            (valid_uuid(jid), user["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(409, "任务不存在或已结束")
        result = explain("user_cancelled", row["input"].get("profile", {}).get("language", "zh"))
        c.execute(
            "UPDATE app_jobs SET status='cancelled',result=%s,updated_at=now(),lease_until=NULL WHERE id=%s",
            (Jsonb(result), valid_uuid(jid)),
        )
        if row["input"].get("session_id"):
            c.execute(
                "INSERT INTO app_chat_messages(session_id,role,content,data) VALUES(%s,'assistant',%s,%s)",
                (row["input"]["session_id"], result["message"], Jsonb(result)),
            )
    return {"ok": True, "result": result}


@router.get("/recommendations")
def history(user=Depends(require_user)):
    with connect() as c:
        return {
            "recommendations": c.execute(
                "SELECT id,created_at,data FROM app_recommendations WHERE user_id=%s ORDER BY created_at DESC LIMIT 30",
                (user["id"],),
            ).fetchall()
        }


@router.get("/recommendations/{rid}")
def recommendation(rid: str, user=Depends(require_user)):
    with connect() as c:
        row = c.execute(
            "SELECT id,created_at,data FROM app_recommendations WHERE id=%s AND user_id=%s",
            (valid_uuid(rid), user["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, "方案不存在")
    return row


@router.post("/recommendations/{rid}/substitutions", status_code=202)
def substitute(rid: str, body: SubstituteRequest, user=Depends(require_user)):
    with connect() as c:
        old = c.execute(
            "SELECT data FROM app_recommendations WHERE id=%s AND user_id=%s",
            (valid_uuid(rid), user["id"]),
        ).fetchone()
        if not old:
            raise HTTPException(404, "方案不存在")
        p = get_profile(c, user["id"])
        if body.language:
            p["profile"]["language"] = body.language
        result, _ = job_create(
            c,
            user,
            "substitute",
            {
                "profile": p["profile"],
                "profile_version": p["version"],
                "previous_plan": old["data"],
                "meal": body.meal,
                "budget": body.budget
                if body.budget is not None
                else old["data"]["budget_jpy"],
                "budget_min": body.budget_min if body.budget is not None else old["data"].get("budget_min_jpy"),
                "request_identity": {
                    "recommendation": rid,
                    "meal": body.meal,
                    "budget": body.budget,
                    **({"budget_min": body.budget_min} if body.budget_min is not None else {}),
                    "language": body.language,
                },
            },
            body.idempotency_key,
        )
        return result


@router.post("/diet-chat/messages", status_code=202)
def chat(body: ChatRequest, user=Depends(require_user)):
    if not body.message.strip():
        raise HTTPException(422, "请输入内容")
    with connect() as c:
        c.execute("SELECT id FROM app_users WHERE id=%s FOR UPDATE", (user["id"],))
        existing = c.execute(
            "SELECT id,status,input FROM app_jobs WHERE user_id=%s AND idempotency_key=%s",
            (user["id"], body.idempotency_key),
        ).fetchone()
        identity = {
            "message": body.message,
            "session_id": body.session_id,
            "language": body.language,
        }
        if existing:
            if existing["input"].get("request_identity") != identity:
                raise HTTPException(409, "幂等键已被使用")
            return {
                "job_id": str(existing["id"]),
                "status": existing["status"],
                "session_id": existing["input"].get("session_id"),
            }
        sid = valid_uuid(body.session_id) if body.session_id else str(uuid.uuid4())
        if body.session_id:
            if not c.execute(
                "SELECT 1 FROM app_chat_sessions WHERE id=%s AND user_id=%s",
                (sid, user["id"]),
            ).fetchone():
                raise HTTPException(404, "会话不存在")
            if c.execute(
                "SELECT 1 FROM app_jobs WHERE user_id=%s AND input->>'session_id'=%s AND status IN ('queued','running')",
                (user["id"], sid),
            ).fetchone():
                raise HTTPException(409, "请等待当前回复完成")
        else:
            c.execute(
                "INSERT INTO app_chat_sessions(id,user_id) VALUES(%s,%s)",
                (sid, user["id"]),
            )
        messages = c.execute(
            "SELECT role,content,data FROM app_chat_messages WHERE session_id=%s ORDER BY id DESC LIMIT 8",
            (sid,),
        ).fetchall()[::-1]
        previous = next(
            (m["data"] for m in reversed(messages) if m["data"].get("meals")), None
        )
        p = get_profile(c, user["id"])
        if body.language:
            p["profile"]["language"] = body.language
        result, new = job_create(
            c,
            user,
            "chat",
            {
                "profile": p["profile"],
                "profile_version": p["version"],
                "session_id": sid,
                "message": body.message,
                "history": [
                    {"role": m["role"], "content": m["content"][:800]} for m in messages
                ],
                "previous_plan": previous,
                "request_identity": identity,
            },
            body.idempotency_key,
        )
        if new:
            c.execute(
                "INSERT INTO app_chat_messages(session_id,role,content) VALUES(%s,'user',%s)",
                (sid, body.message),
            )
        return result


@router.get("/diet-chat/sessions")
def chat_sessions(user=Depends(require_user)):
    with connect() as c:
        return {
            "sessions": c.execute(
                "SELECT id,created_at FROM app_chat_sessions WHERE user_id=%s ORDER BY created_at DESC LIMIT 30",
                (user["id"],),
            ).fetchall()
        }


@router.get("/diet-chat/sessions/{sid}")
def chat_history(sid: str, user=Depends(require_user)):
    with connect() as c:
        if not c.execute(
            "SELECT 1 FROM app_chat_sessions WHERE id=%s AND user_id=%s",
            (valid_uuid(sid), user["id"]),
        ).fetchone():
            raise HTTPException(404)
        return {
            "messages": c.execute(
                "SELECT role,content,data,created_at FROM app_chat_messages WHERE session_id=%s ORDER BY id",
                (sid,),
            ).fetchall(),
            "active_job": c.execute(
                "SELECT id AS job_id,status FROM app_jobs WHERE user_id=%s AND input->>'session_id'=%s AND status IN ('queued','running') ORDER BY created_at LIMIT 1",
                (user["id"], sid),
            ).fetchone(),
        }


@router.get("/evidence/{cid}")
def evidence(cid: int, user=Depends(require_user)):
    with connect() as c:
        row = c.execute(
            """SELECT ch.content,ch.pdf_page,p.printed_page,d.title,d.warning,d.id document_id FROM kb_chunks ch
         JOIN kb_pages p ON p.document_id=ch.document_id AND p.pdf_page=ch.pdf_page
         JOIN kb_documents d ON d.id=ch.document_id WHERE ch.id=%s AND d.status='ready' AND d.enabled AND p.status='eligible' """,
            (cid,),
        ).fetchone()
    if not row:
        raise HTTPException(404)
    return row
