"""Durable single-worker queue. Lease expiry retries once, guarded publishing, cancellation."""

import asyncio, logging, uuid, hashlib
from pathlib import Path
import httpx
from psycopg.types.json import Jsonb
from .db import connect
from .planner import plan_day, catalog
from .chat import classify, answer_question
from .plan_explanation import enrich_plan
from .feedback import explain, failure_result
from .qa_policy import allergy_conflict
from .budget import resolve_budget
from .food_requirements import requested_foods

logger = logging.getLogger(__name__)
BUILD_HASH = hashlib.sha256(
    b"".join(
        Path(__file__).with_name(n).read_bytes()
        for n in ["worker.py", "chat.py", "qa_policy.py", "feedback.py", "budget.py", "food_requirements.py", "planner.py", "meal_selection.py", "plan_explanation.py"]
    )
).hexdigest()


def claim():
    with connect() as c:
        expired = c.execute(
            "SELECT id,input FROM app_jobs WHERE status='running' AND lease_until<now() AND attempts>=2 FOR UPDATE"
        ).fetchall()
        for job in expired:
            result = explain("processing_interrupted", job["input"].get("profile", {}).get("language", "zh"))
            c.execute(
                "UPDATE app_jobs SET status='failed',result=%s,updated_at=now(),lease_until=NULL WHERE id=%s",
                (Jsonb(result), job["id"]),
            )
            # Persist the explanation atomically, so reopening chat still shows it.
            if job["input"].get("session_id"):
                c.execute(
                    "INSERT INTO app_chat_messages(session_id,role,content,data) VALUES(%s,'assistant',%s,%s)",
                    (job["input"]["session_id"], result["message"], Jsonb(result)),
                )
        row = c.execute("""SELECT * FROM app_jobs WHERE status='queued' OR (status='running' AND lease_until<now() AND attempts<2)
             ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1""").fetchone()
        if not row:
            return None
        c.execute(
            "UPDATE app_jobs SET status='running',attempts=attempts+1,lease_until=now()+interval '10 minutes',updated_at=now() WHERE id=%s",
            (row["id"],),
        )
        return row


async def execute(job):
    data = job["input"]
    profile = data["profile"]
    lang = profile.get("language", "zh")
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5)) as client:
        if job["kind"] == "chat":
            ingredients, _ = await asyncio.to_thread(catalog)
            intent = await classify(
                client,
                data["message"],
                data.get("history", []),
                {k: v["name"] for k, v in ingredients.items()},
            )
            if intent.domain == "off_topic":
                return explain("outside_diet_scope", lang)
            if intent.domain == "unclear":
                return explain("unclear_question", lang)
            if intent.requested_allergens:
                conflicts = set(intent.requested_allergens) & set(profile.get("allergens", []))
                if conflicts:
                    return allergy_conflict(conflicts, lang)
            if intent.intent == "qa":
                return await answer_question(
                    client, data["message"], intent.japanese_query, lang,
                    profile=profile,
                    new_profile_facts=intent.new_health_or_allergy or intent.needs_profile_update,
                    requested_allergens=intent.requested_allergens or None,
                )
            if (
                intent.new_health_or_allergy
                or intent.needs_profile_update
                or intent.intent == "profile"
            ):
                return explain("profile_update_required", lang)
            if intent.intent == "replace":
                if not data.get("previous_plan") or not intent.meal:
                    return explain("replacement_context_missing", lang)
                replacement = {"plan": data["previous_plan"], "meal": intent.meal}
            else:
                replacement = None
            profile = dict(profile)
            profile["dislikes"] = list(
                set(profile.get("dislikes", []) + intent.exclude_food_codes)
            )
            upper, lower = resolve_budget(intent.budget, intent.budget_min, data.get("previous_plan"))
            requirements = requested_foods(data["message"], intent.requested_allergens)
            if not requirements and not intent.exclude_food_codes:
                requirements = (data.get("previous_plan") or {}).get("food_requirements", [])
            result = await asyncio.to_thread(
                plan_day, profile, upper, replacement, budget_min=lower, food_requirements=requirements,
            )
        elif job["kind"] == "substitute":
            result = await asyncio.to_thread(
                plan_day,
                profile,
                data.get("budget"),
                {"plan": data["previous_plan"], "meal": data["meal"]},
                budget_min=data.get("budget_min"),
                food_requirements=data["previous_plan"].get("food_requirements", []),
            )
        else:
            result = await asyncio.to_thread(plan_day, profile, data.get("budget"), budget_min=data.get("budget_min"))
        if result["status"] == "ready":
            if result.get("budget_min_jpy") is not None:
                low, high = result["budget_min_jpy"], result["budget_jpy"]
                cost = result["totals"]["cost_jpy"]
                result["message"] = {
                    "zh": f"已按您要求的每日 ¥{low}–¥{high} 预算区间筛选三餐，测算总费用为 ¥{cost:.2f}，同时满足预算下限和上限。营养与费用明细见下方。",
                    "en": f"Selected three meals within your daily ¥{low}–¥{high} range. Estimated total cost is ¥{cost:.2f}, meeting both bounds. Nutrition and cost details follow.",
                    "ja": f"一日 ¥{low}–¥{high} の予算範囲で三食を選びました。仮定費用の合計は ¥{cost:.2f} で、下限・上限の両方を満たします。栄養量と費用の明細は以下をご覧ください。",
                }[lang]
            else:
                result["message"] = {
                    "zh": "已按确认的目标、过敏限制和预算筛选三餐。营养与费用由食品数据库计算，详见菜单明细。",
                    "en": "Three meals meet the confirmed demonstration targets, allergy constraints and budget. See calculated nutrition and cost below.",
                    "ja": "確認されたデモ目標、アレルギー条件と予算で三食を選びました。栄養量と費用の計算明細をご確認ください。",
                }[lang]
            await enrich_plan(client, result)
        return result


def publish(job, result):
    if result["status"] != "out_of_scope":
        result["profile_version"] = job["input"].get("profile_version")
        result["implementation_sha256"] = BUILD_HASH
    with connect() as c:
        current = c.execute(
            "SELECT status FROM app_jobs WHERE id=%s FOR UPDATE", (job["id"],)
        ).fetchone()
        if not current or current["status"] != "running":
            return
        if result.get("meals"):
            rid = str(uuid.uuid4())
            result["recommendation_id"] = rid
            c.execute(
                "INSERT INTO app_recommendations(id,user_id,job_id,data) VALUES(%s,%s,%s,%s) ON CONFLICT(job_id) DO NOTHING",
                (rid, job["user_id"], job["id"], Jsonb(result)),
            )
        c.execute(
            "UPDATE app_jobs SET status=%s,result=%s,updated_at=now(),lease_until=NULL WHERE id=%s",
            (result["status"], Jsonb(result), job["id"]),
        )
        if job["input"].get("session_id"):
            c.execute(
                "INSERT INTO app_chat_messages(session_id,role,content,data) VALUES(%s,'assistant',%s,%s)",
                (
                    job["input"]["session_id"],
                    result.get("message", result.get("note", "")),
                    Jsonb(result),
                ),
            )


async def run():
    with connect() as c:
        # Session advisory lock ensures one model worker even if started twice.
        if not c.execute("SELECT pg_try_advisory_lock(510120)").fetchone()[
            "pg_try_advisory_lock"
        ]:
            raise RuntimeError("A diet worker is already running")
        c.commit()
        while True:
            job = await asyncio.to_thread(claim)
            if not job:
                from .kb_import import claim_upload, process_upload
                upload = await asyncio.to_thread(claim_upload)
                if upload:
                    await process_upload(upload)
                    continue
                await asyncio.sleep(1)
                continue
            try:
                result = await asyncio.wait_for(execute(job), timeout=500)
            except Exception as exc:
                logger.exception("Diet worker job failed: %s", job["id"])
                result = failure_result(exc, job["input"]["profile"].get("language", "zh"))
            await asyncio.to_thread(publish, job, result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
