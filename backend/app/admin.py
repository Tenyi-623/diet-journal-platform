"""Permission-checked administration; immutable uploaded media and audited changes."""

import base64
import binascii
import hashlib
import io
import os
from pathlib import Path
import secrets
import uuid
import warnings
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, field_validator
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .auth import HASHER, require_user
from .db import connect
from .rbac import access, audit, require_permission
from .schemas import Strict
from .planner import calculate, catalog

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "data/uploads/recipes"
PDFS = ROOT / "data/uploads/knowledge"
router = APIRouter(prefix="/api/admin")
media_router = APIRouter(prefix="/api")
users_permission = require_permission("users.manage")
recipes_permission = require_permission("recipes.manage")
knowledge_permission = require_permission("knowledge.manage")


class UserCreate(Strict):
    login_id: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str | None = Field(default=None, min_length=12, max_length=128)
    roles: list[str] = Field(
        default_factory=lambda: ["user"], min_length=1, max_length=5
    )


class UserUpdate(Strict):
    enabled: bool
    roles: list[str] = Field(min_length=1, max_length=5)


def validate_roles(c, roles, actor):
    known = {r["id"] for r in c.execute("SELECT id FROM app_roles").fetchall()}
    if not set(roles) <= known:
        raise HTTPException(422, "未知角色")
    if set(roles) != {"user"} and "roles.manage" not in actor["permissions"]:
        raise HTTPException(403, "不能分配管理角色")


def user_row(c, uid):
    row = c.execute(
        "SELECT id,login_id,enabled,created_at FROM app_users WHERE id=%s", (uid,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "账号不存在")
    return {**row, **access(c, uid)}


@router.get("/roles")
def roles(user=Depends(users_permission)):
    with connect() as c:
        rows = c.execute(
            """SELECT r.id,r.name,COALESCE(array_agg(p.permission_id)
            FILTER(WHERE p.permission_id IS NOT NULL),'{}') permissions
            FROM app_roles r LEFT JOIN app_role_permissions p ON r.id=p.role_id
            GROUP BY r.id ORDER BY r.id"""
        ).fetchall()
    return {"roles": rows, "can_assign_roles": "roles.manage" in user["permissions"]}


@router.get("/users")
def users(
    q: str = Query("", max_length=80),
    offset: int = Query(0, ge=0),
    user=Depends(users_permission),
):
    with connect() as c:
        rows = c.execute(
            "SELECT id FROM app_users WHERE login_id ILIKE %s ORDER BY id LIMIT 50 OFFSET %s",
            ("%" + q + "%", offset),
        ).fetchall()
        total = c.execute(
            "SELECT count(*) n FROM app_users WHERE login_id ILIKE %s", ("%" + q + "%",)
        ).fetchone()["n"]
        return {"users": [user_row(c, r["id"]) for r in rows], "total": total}


@router.post("/users", status_code=201)
def create_user(body: UserCreate, user=Depends(users_permission)):
    password = body.password or secrets.token_urlsafe(18)
    try:
        with connect() as c:
            c.execute("SELECT pg_advisory_xact_lock(510121)")
            validate_roles(c, body.roles, user)
            uid = c.execute(
                "INSERT INTO app_users(login_id,password_hash) VALUES(%s,%s) RETURNING id",
                (body.login_id, HASHER.hash(password)),
            ).fetchone()["id"]
            for role in set(body.roles):
                c.execute("INSERT INTO app_user_roles VALUES(%s,%s)", (uid, role))
            audit(c, user, "user.create", uid, {"roles": body.roles})
            return {"user": user_row(c, uid), "initial_password": password}
    except UniqueViolation:
        raise HTTPException(409, "登录ID已存在")


def protect_account(c, uid, actor):
    row = user_row(c, uid)
    if (
        "roles.manage" in row["permissions"]
        and "roles.manage" not in actor["permissions"]
    ):
        raise HTTPException(403, "不能管理管理员账号")
    return row


@router.patch("/users/{uid}")
def update_user(uid: int, body: UserUpdate, user=Depends(users_permission)):
    with connect() as c:
        c.execute("SELECT pg_advisory_xact_lock(510121)")
        old = protect_account(c, uid, user)
        validate_roles(c, body.roles, user)
        if uid == user["id"] and (
            not body.enabled or set(body.roles) != set(old["roles"])
        ):
            raise HTTPException(409, "不能禁用自己或修改自己的角色")
        if (
            old["enabled"]
            and "admin" in old["roles"]
            and (not body.enabled or "admin" not in body.roles)
        ):
            remaining = c.execute(
                """SELECT count(*) n FROM app_users u JOIN app_user_roles r ON r.user_id=u.id
                WHERE u.enabled AND r.role_id='admin' AND u.id<>%s""",
                (uid,),
            ).fetchone()["n"]
            if not remaining:
                raise HTTPException(409, "必须保留至少一个启用的管理员")
        changed = old["enabled"] != body.enabled or set(old["roles"]) != set(body.roles)
        c.execute("UPDATE app_users SET enabled=%s WHERE id=%s", (body.enabled, uid))
        c.execute("DELETE FROM app_user_roles WHERE user_id=%s", (uid,))
        for role in set(body.roles):
            c.execute("INSERT INTO app_user_roles VALUES(%s,%s)", (uid, role))
        if changed:
            c.execute("DELETE FROM app_sessions WHERE user_id=%s", (uid,))
        audit(c, user, "user.update", uid, body.model_dump())
        return user_row(c, uid)


@router.post("/users/{uid}/reset-password")
def reset_password(uid: int, user=Depends(users_permission)):
    with connect() as c:
        c.execute("SELECT pg_advisory_xact_lock(510121)")
        protect_account(c, uid, user)
        if uid == user["id"]:
            raise HTTPException(409, "请使用用户信息中的修改密码功能")
        password = secrets.token_urlsafe(18)
        c.execute(
            "UPDATE app_users SET password_hash=%s WHERE id=%s",
            (HASHER.hash(password), uid),
        )
        c.execute("DELETE FROM app_sessions WHERE user_id=%s", (uid,))
        audit(c, user, "user.reset_password", uid)
        return {"initial_password": password}


class Text3(Strict):
    zh: str = Field(min_length=1, max_length=2000)
    en: str = Field(min_length=1, max_length=2000)
    ja: str = Field(min_length=1, max_length=2000)


class RecipeEdit(Strict):
    expected_version: str | None = Field(default=None, max_length=80)
    name: Text3
    meal: Literal["breakfast", "lunch", "dinner"]
    ingredients: dict[str, float] = Field(min_length=1, max_length=19)
    minutes: int = Field(ge=1, le=240)
    instructions: Text3
    enabled: bool = True

    @field_validator("ingredients")
    @classmethod
    def weights(cls, values):
        import math

        if any(
            len(k) != 5 or not k.isdigit() or not math.isfinite(v) or not 0 < v <= 2000
            for k, v in values.items()
        ):
            raise ValueError("配料需使用食品编号，重量须在0至2000g之间")
        if sum(values.values()) > 4000:
            raise ValueError("单份总重量不能超过4000g")
        return values


@router.get("/recipes")
def recipes(user=Depends(recipes_permission)):
    with connect() as c:
        return {
            "recipes": c.execute(
                "SELECT * FROM app_recipes ORDER BY meal,id"
            ).fetchall(),
            "ingredients": c.execute(
                "SELECT code,name FROM app_ingredients ORDER BY code"
            ).fetchall(),
        }


def save_recipe(body, rid, actor, create=False):
    with connect() as c:
        old = (
            None
            if create
            else c.execute(
                "SELECT * FROM app_recipes WHERE id=%s FOR UPDATE", (rid,)
            ).fetchone()
        )
        if not create and not old:
            raise HTTPException(404, "菜谱不存在")
        if old and old["version"] != body.expected_version:
            raise HTTPException(409, "菜谱已被修改，请刷新")
        ingredients, _ = catalog(c)
        if not set(body.ingredients) <= ingredients.keys():
            raise HTTPException(422, "只能使用已有结构化营养数据的配料")
        if any(len(v) > 100 for v in body.name.model_dump().values()):
            raise HTTPException(422, "菜谱名称过长")
        data = {
            **(old["data"] if old else {}),
            "minutes": body.minutes,
            "instructions": body.instructions.model_dump(),
            "scales": old["data"]["scales"] if old else [0.8, 1, 1.2, 1.4],
            "image": old["data"]["image"] if old else "/api/recipe-images/b1",
        }
        row = {
            "id": rid,
            "version": str(uuid.uuid4()),
            "meal": body.meal,
            "name": body.name.model_dump(),
            "ingredients": body.ingredients,
            "data": data,
            "enabled": body.enabled,
        }
        # Validate numeric availability with the same calculator used by recommendations.
        calculate(row, ingredients)
        if create:
            c.execute(
                """INSERT INTO app_recipes(id,version,meal,name,ingredients,data,enabled)
                       VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (
                    rid,
                    row["version"],
                    body.meal,
                    Jsonb(row["name"]),
                    Jsonb(body.ingredients),
                    Jsonb(data),
                    body.enabled,
                ),
            )
        else:
            c.execute(
                """UPDATE app_recipes SET version=%s,meal=%s,name=%s,ingredients=%s,data=%s,enabled=%s
                       WHERE id=%s""",
                (
                    row["version"],
                    body.meal,
                    Jsonb(row["name"]),
                    Jsonb(body.ingredients),
                    Jsonb(data),
                    body.enabled,
                    rid,
                ),
            )
        c.execute("DELETE FROM app_home_cache")
        audit(
            c,
            actor,
            "recipe.create" if create else "recipe.update",
            rid,
            {"version": row["version"]},
        )
        return row


@router.post("/recipes", status_code=201)
def create_recipe(body: RecipeEdit, user=Depends(recipes_permission)):
    return save_recipe(body, "recipe-" + uuid.uuid4().hex[:16], user, True)


@router.patch("/recipes/{rid}")
def update_recipe(rid: str, body: RecipeEdit, user=Depends(recipes_permission)):
    return save_recipe(body, rid, user)


class Upload(Strict):
    filename: str = Field(min_length=1, max_length=160)
    content_base64: str = Field(min_length=1, max_length=24_000_000)


class ImageUpload(Upload):
    expected_version: str = Field(min_length=1, max_length=80)


def decode_upload(value, limit):
    if len(value) > (limit * 4 // 3 + 8):
        raise HTTPException(413, "文件过大")
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, "文件编码无效")
    if not data or len(data) > limit:
        raise HTTPException(413, "文件为空或过大")
    return data


def image_bytes(raw):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if (
                    image.format not in {"PNG", "JPEG", "WEBP"}
                    or image.width * image.height > 20_000_000
                ):
                    raise HTTPException(
                        422, "仅支持PNG、JPEG、WebP，像素总数不能超过2000万"
                    )
                image.load()
                clean = ImageOps.exif_transpose(image).convert("RGB")
                clean.thumbnail((1600, 1600))
                out = io.BytesIO()
                clean.save(out, format="WEBP", quality=88)
                return out.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise HTTPException(422, "图片文件损坏或尺寸过大")


@router.post("/recipes/{rid}/image")
def upload_image(rid: str, body: ImageUpload, user=Depends(recipes_permission)):
    payload = image_bytes(decode_upload(body.content_base64, 4 * 1024 * 1024))
    digest = hashlib.sha256(payload).hexdigest()
    MEDIA.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = MEDIA / (digest + ".webp")
    with connect() as c:
        row = c.execute(
            "SELECT * FROM app_recipes WHERE id=%s FOR UPDATE", (rid,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "菜谱不存在")
        if row["version"] != body.expected_version:
            raise HTTPException(409, "菜谱已被修改，请刷新")
        if not path.exists():
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
        row["data"]["image"] = f"/api/recipe-media/{digest}.webp"
        row["version"] = str(uuid.uuid4())
        c.execute(
            "UPDATE app_recipes SET data=%s,version=%s WHERE id=%s",
            (Jsonb(row["data"]), row["version"], rid),
        )
        c.execute("DELETE FROM app_home_cache")
        audit(c, user, "recipe.image", rid, {"sha256": digest})
        return row


@media_router.get("/recipe-media/{filename}")
def media(filename: str, user=Depends(require_user)):
    import re

    if not re.fullmatch(r"[a-f0-9]{64}\.webp", filename):
        raise HTTPException(404)
    path = MEDIA / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": "private,max-age=31536000,immutable"},
    )


class KnowledgeMetadata(Strict):
    title: str = Field(min_length=1, max_length=240)
    publisher: str = Field(min_length=1, max_length=200)
    edition: str = Field(min_length=1, max_length=100)
    source_kind: Literal[
        "guideline_commentary",
        "guideline_chapter",
        "food_composition_reference",
        "historical_guideline",
        "dietary_reference_intakes",
        "reference",
    ]
    warning: str = Field(
        default="管理员上传资料，尚未完成逐页人工审核。", max_length=1500
    )


class KnowledgeEdit(KnowledgeMetadata):
    enabled: bool


class KnowledgeUpload(Upload, KnowledgeMetadata):
    pass


@router.get("/knowledge")
def knowledge(user=Depends(knowledge_permission)):
    with connect() as c:
        return {
            "documents": c.execute(
                """SELECT d.id,d.title,d.publisher,d.edition,d.source_kind,d.warning,d.page_count,d.status,d.enabled,
            d.filename,(SELECT count(*) FROM kb_chunks ch WHERE ch.document_id=d.id) chunks,
            (SELECT count(*) FROM kb_pages p WHERE p.document_id=d.id AND p.status='quarantined') quarantined_pages
            FROM kb_documents d ORDER BY d.id DESC"""
            ).fetchall(),
            "uploads": c.execute(
                """SELECT id,metadata,status,document_id,error,created_at,updated_at
            FROM app_kb_uploads ORDER BY created_at DESC LIMIT 30"""
            ).fetchall(),
        }


@router.patch("/knowledge/{did}")
def update_document(did: int, body: KnowledgeEdit, user=Depends(knowledge_permission)):
    with connect() as c:
        row = c.execute(
            "SELECT status FROM kb_documents WHERE id=%s FOR UPDATE", (did,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "文档不存在")
        if body.enabled and row["status"] != "ready":
            raise HTTPException(409, "仅完整导入且通过提取检查的文档可以启用")
        c.execute(
            """UPDATE kb_documents SET title=%s,publisher=%s,edition=%s,source_kind=%s,warning=%s,enabled=%s WHERE id=%s""",
            (
                body.title,
                body.publisher,
                body.edition,
                body.source_kind,
                body.warning,
                body.enabled,
                did,
            ),
        )
        audit(c, user, "knowledge.update", did, {"enabled": body.enabled})
    return {"ok": True}


@router.get("/knowledge/{did}/pages")
def document_pages(
    did: int, page: int = Query(1, ge=1), user=Depends(knowledge_permission)
):
    with connect() as c:
        row = c.execute(
            "SELECT pdf_page,printed_page,content,status,reason FROM kb_pages WHERE document_id=%s AND pdf_page=%s",
            (did, page),
        ).fetchone()
        if not row:
            raise HTTPException(404, "页面不存在")
        return row


@router.post("/knowledge/uploads", status_code=202)
def upload_document(body: KnowledgeUpload, user=Depends(knowledge_permission)):
    raw = decode_upload(body.content_base64, 12 * 1024 * 1024)
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(422, "请上传PDF文件")
    digest = hashlib.sha256(raw).hexdigest()
    uid = str(uuid.uuid4())
    metadata = body.model_dump(exclude={"content_base64"})
    PDFS.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = PDFS / (digest + ".pdf")
    try:
        with connect() as c:
            c.execute("SELECT pg_advisory_xact_lock(510122)")
            if c.execute(
                "SELECT 1 FROM kb_documents WHERE sha256=%s", (digest,)
            ).fetchone():
                raise HTTPException(409, "该PDF已在知识库中")
            if (
                c.execute(
                    "SELECT count(*) n FROM app_kb_uploads WHERE status IN ('queued','processing')"
                ).fetchone()["n"]
                >= 5
            ):
                raise HTTPException(429, "已有文档等待导入，请稍后上传")
            if not path.exists():
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(raw)
            c.execute(
                "INSERT INTO app_kb_uploads(id,created_by,metadata,sha256,file_path) VALUES(%s,%s,%s,%s,%s)",
                (uid, user["id"], Jsonb(metadata), digest, str(path)),
            )
            audit(c, user, "knowledge.upload", uid, {"sha256": digest})
        return {"upload_id": uid, "status": "queued"}
    except UniqueViolation:
        raise HTTPException(409, "此文件已上传，请查看导入记录")


@router.post("/knowledge/uploads/{uid}/retry")
def retry_upload(uid: uuid.UUID, user=Depends(knowledge_permission)):
    with connect() as c:
        row = c.execute(
            """UPDATE app_kb_uploads SET status='queued',error=NULL,attempts=0,lease_until=NULL,updated_at=now()
            WHERE id=%s AND status='failed' RETURNING id""",
            (uid,),
        ).fetchone()
        if not row:
            raise HTTPException(409, "只有失败的导入任务可以重试")
        audit(c, user, "knowledge.retry", uid)
    return {"ok": True}
