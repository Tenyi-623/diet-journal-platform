"""Authenticated local diet demonstration service; serve compiled React from the same origin."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import httpx, psycopg
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .app.api import router
from .app.admin import router as admin_router, media_router
from .app.auth import require_user
from .app.db import connect
from .knowledge_api import router as knowledge_router

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app):
    app.state.http_client = httpx.AsyncClient(timeout=settings.timeout_seconds)
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="食日记 · Diet Journal",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(router)
app.include_router(admin_router)
app.include_router(media_router)
app.include_router(knowledge_router, dependencies=[Depends(require_user)])


@app.middleware("http")
async def security(request: Request, call_next):
    # Bound bodies for JSON-only business endpoints; chunked oversized bodies are bounded too.
    if request.method in ["POST", "PATCH", "PUT"]:
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"detail": "JSON required"}, status_code=415)
        import re
        import asyncio
        upload_permission = (
            "knowledge.manage" if request.url.path == "/api/admin/knowledge/uploads"
            else "recipes.manage" if re.fullmatch(r"/api/admin/recipes/[^/]+/image", request.url.path)
            else None
        )
        limit = 20000
        if upload_permission:
            try:
                upload_user = await asyncio.to_thread(require_user, request)
                if upload_permission not in upload_user["permissions"]:
                    raise HTTPException(403, "没有上传权限")
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            limit = 18 * 1024 * 1024 if upload_permission == "knowledge.manage" else 6 * 1024 * 1024
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > limit:
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(psycopg.Error)
async def db_error(request, exc):
    logger.error("Database request failed: %s", type(exc).__name__)
    return JSONResponse({"detail": "数据库暂不可用，请稍后重试"}, status_code=503)


@app.get("/api/health")
def health():
    return {"status": "alive"}


@app.get("/api/readiness")
async def ready(request: Request, user=Depends(require_user)):
    with connect() as c:
        db = c.execute("SELECT count(*) n FROM app_migrations").fetchone()["n"]
        counts = c.execute(
            "SELECT (SELECT count(*) FROM app_users) users,(SELECT count(*) FROM app_recipes) recipes"
        ).fetchone()
    try:
        r = await request.app.state.http_client.get(
            settings.ollama_base_url + "/api/tags", timeout=5
        )
        r.raise_for_status()
        models = {m["name"] for m in r.json()["models"]}
        model_ok = settings.llm_model in models and settings.embedding_model in models
    except (httpx.HTTPError, KeyError):
        model_ok = False
    return {
        "database": bool(db),
        "models_configured": model_ok,
        **counts,
        "note": "Model listing is not an inference benchmark.",
    }


@app.get("/api/openapi.json")
def schema(user=Depends(require_user)):
    return app.openapi()


@app.post("/api/chat")
def old_chat(user=Depends(require_user)):
    raise HTTPException(410, "请使用受控饮食聊天 /api/diet-chat/messages")


@app.post("/api/embed")
def old_embed(user=Depends(require_user)):
    raise HTTPException(410, "Embedding仅供后端内部调用")


@app.get("/docs", include_in_schema=False)
def console(request: Request):
    try:
        require_user(request)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    return FileResponse(ROOT / "backend/static/api-console.html")


@app.get("/api/console.js", include_in_schema=False)
def console_script(user=Depends(require_user)):
    return FileResponse(
        ROOT / "backend/static/console.js", media_type="application/javascript"
    )


DIST = ROOT / "frontend/dist"
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def web(path: str, request: Request):
    if path.startswith("api/") or path in ["register", "signup"]:
        raise HTTPException(404)
    if path not in ["", "login"]:
        try:
            require_user(request)
        except HTTPException:
            return RedirectResponse("/login", status_code=303)
    if not (DIST / "index.html").exists():
        return JSONResponse(
            {"detail": "Frontend not built. Run scripts/build_frontend.sh."},
            status_code=503,
        )
    return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-store"})
