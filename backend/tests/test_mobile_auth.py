import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request, Response

from backend.app import auth
from backend.app.schemas import Login


def request_with(method="POST", headers=()):
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": "/api/profile",
            "raw_path": b"/api/profile",
            "query_string": b"",
            "headers": [(b"host", b"diet.example"), *headers],
            "client": ("192.0.2.10", 50000),
            "server": ("diet.example", 443),
        }
    )


class FakeConnection:
    def __init__(self, user=None):
        self.user = user or {"id": 7, "login_id": "diet007", "csrf": "web-csrf"}
        self.statements = []
        self.next_row = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if "INSERT INTO app_login_attempts" in sql:
            self.next_row = {"attempts": 1}
        elif "SELECT * FROM app_users" in sql:
            self.next_row = {
                "id": 7,
                "login_id": "diet007",
                "password_hash": "hashed-password",
                "enabled": True,
            }
        elif "SELECT u.id,u.login_id,s.csrf" in sql:
            self.next_row = self.user
        else:
            self.next_row = None
        return self

    def fetchone(self):
        return self.next_row


class MobileAuthenticationTests(unittest.TestCase):
    def test_bearer_session_authenticates_unsafe_requests_without_cookie_csrf(self):
        request = request_with(headers=[(b"authorization", b"Bearer mobile-token")])
        db = FakeConnection()
        with patch("backend.app.auth.connect", return_value=db), patch(
            "backend.app.rbac.access", return_value={"roles": ["user"], "permissions": []}
        ):
            user = auth.require_user(request)
        self.assertEqual(user["id"], 7)
        self.assertEqual(db.statements[0][1], (auth.token_hash("mobile-token"),))

    def test_cookie_session_keeps_csrf_requirement(self):
        request = request_with(
            headers=[
                (b"cookie", b"diet_session=web-token"),
                (b"origin", b"https://diet.example"),
                (b"x-csrf-token", b"wrong"),
            ]
        )
        with patch("backend.app.auth.connect", return_value=FakeConnection()), patch(
            "backend.app.rbac.access", return_value={"roles": ["user"], "permissions": []}
        ):
            with self.assertRaises(HTTPException) as raised:
                auth.require_user(request)
        self.assertEqual(raised.exception.status_code, 403)

    def test_mobile_login_returns_bearer_token_without_setting_cookie(self):
        db = FakeConnection()
        request = request_with(
            headers=[(b"content-type", b"application/json")]
        )
        response = Response()
        with patch("backend.app.auth.connect", return_value=db), patch(
            "backend.app.auth.HASHER.verify", return_value=True
        ), patch(
            "backend.app.rbac.access", return_value={"roles": ["user"], "permissions": []}
        ):
            result = auth.mobile_login(
                Login(login_id="diet007", password="secret"), request, response
            )
        self.assertEqual(result["token_type"], "Bearer")
        self.assertEqual(result["expires_in"], 43200)
        self.assertEqual(result["user"]["id"], 7)
        self.assertTrue(result["access_token"])
        self.assertNotIn("set-cookie", response.headers)
        self.assertIn(
            auth.token_hash(result["access_token"]),
            [params[0] for sql, params in db.statements if "INSERT INTO app_sessions" in sql],
        )

    def test_malformed_authorization_does_not_fall_back_to_cookie(self):
        request = request_with(
            headers=[
                (b"authorization", b"Basic abc"),
                (b"cookie", b"diet_session=valid-web-token"),
            ]
        )
        with self.assertRaises(HTTPException) as raised:
            auth.require_user(request)
        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
