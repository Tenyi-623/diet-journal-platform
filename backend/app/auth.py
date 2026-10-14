import hashlib, hmac, os, secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
from fastapi import Request, HTTPException, Response
from pwdlib import PasswordHash
from .db import connect

HASHER = PasswordHash.recommended()
DUMMY = HASHER.hash("nonexistent-user-constant-timing-password")
COOKIE = "diet_session"


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request):
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.netloc != request.headers.get("host") or parsed.scheme not in [
            "http",
            "https",
        ]:
            raise HTTPException(403, "Invalid origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Invalid origin")


def request_token(request: Request):
    """Return (token, is_bearer), rejecting malformed Authorization headers."""
    authorization = request.headers.get("authorization")
    if authorization is not None:
        scheme, separator, token = authorization.partition(" ")
        if (
            scheme.lower() != "bearer"
            or not separator
            or not token
            or token != token.strip()
            or len(token) > 100
        ):
            raise HTTPException(401, "请先登录")
        return token, True
    token = request.cookies.get(COOKIE, "")
    if not token or len(token) > 100:
        raise HTTPException(401, "请先登录")
    return token, False


def require_user(request: Request):
    token, is_bearer = request_token(request)
    with connect() as c:
        user = c.execute(
            """SELECT u.id,u.login_id,s.csrf FROM app_users u JOIN app_sessions s ON u.id=s.user_id
        WHERE s.token_hash=%s AND s.expires_at>now() AND u.enabled""",
            (token_hash(token),),
        ).fetchone()
    if not user:
        raise HTTPException(401, "登录已过期，请重新登录")
    from .rbac import access
    with connect() as c:
        user.update(access(c, user["id"]))
    if not is_bearer and request.method not in ["GET", "HEAD", "OPTIONS"]:
        check_origin(request)
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), user["csrf"]
        ):
            raise HTTPException(403, "Invalid CSRF token")
    return user


def _login(body, request: Request, response: Response, *, mobile: bool):
    if not mobile:
        check_origin(request)
    ip = request.client.host if request.client else "local"
    keys = [token_hash("ip:" + ip), token_hash("id:" + body.login_id.lower())]
    limited = False
    with connect() as c:
        for key in keys:
            row = c.execute(
                """INSERT INTO app_login_attempts(key,attempts,window_at) VALUES(%s,1,now())
                ON CONFLICT(key) DO UPDATE SET attempts=CASE WHEN app_login_attempts.window_at<now()-interval '10 minutes'
                THEN 1 ELSE app_login_attempts.attempts+1 END,window_at=CASE WHEN app_login_attempts.window_at<now()-interval '10 minutes'
                THEN now() ELSE app_login_attempts.window_at END RETURNING attempts""",
                (key,),
            ).fetchone()
            if row["attempts"] > (30 if key == keys[0] else 8):
                limited = True
    if limited:
        raise HTTPException(429, "尝试次数过多，请稍后再试")
    with connect() as c:
        user = c.execute(
            "SELECT * FROM app_users WHERE login_id=%s", (body.login_id,)
        ).fetchone()
        valid = HASHER.verify(body.password, user["password_hash"] if user else DUMMY)
        if not user or not valid or not user["enabled"]:
            raise HTTPException(401, "登录ID或密码不正确")
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        c.execute("DELETE FROM app_sessions WHERE expires_at<now()")
        expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
        c.execute(
            "INSERT INTO app_sessions(token_hash,user_id,csrf,expires_at) VALUES(%s,%s,%s,%s)",
            (
                token_hash(token),
                user["id"],
                csrf,
                expires_at,
            ),
        )
        c.execute("DELETE FROM app_login_attempts WHERE key=%s", (keys[1],))
    from .rbac import access
    with connect() as c:
        permissions = access(c, user["id"])
    if mobile:
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 43200,
            "expires_at": expires_at.isoformat(),
            "user": {"id": user["id"], "login_id": user["login_id"], **permissions},
        }
    response.set_cookie(
        COOKIE,
        token,
        max_age=43200,
        httponly=True,
        samesite="strict",
        secure=os.getenv("APP_SECURE_COOKIES") == "true",
        path="/",
    )
    return {"id": user["id"], "login_id": user["login_id"], "csrf": csrf, **permissions}


def login(body, request: Request, response: Response):
    return _login(body, request, response, mobile=False)


def mobile_login(body, request: Request, response: Response):
    return _login(body, request, response, mobile=True)
