"""Local administrator operations; no account creation or public management endpoint."""

import argparse, csv, os, secrets
from pathlib import Path
import psycopg
from pwdlib import PasswordHash
from backend.config import settings

p = argparse.ArgumentParser()
p.add_argument("action", choices=["disable", "enable", "reset-password"])
p.add_argument("login_id")
a = p.parse_args()
with psycopg.connect(settings.database_url) as c:
    row = c.execute(
        "SELECT id FROM app_users WHERE login_id=%s FOR UPDATE", (a.login_id,)
    ).fetchone()
    if not row:
        raise SystemExit("Unknown account")
    if a.action == "reset-password":
        password = secrets.token_urlsafe(16)
        c.execute(
            "UPDATE app_users SET password_hash=%s WHERE id=%s",
            (PasswordHash.recommended().hash(password), row[0]),
        )
        path = Path("data/private/password-resets.csv")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            csv.writer(f).writerow([a.login_id, password])
        print("New password saved to data/private/password-resets.csv (0600)")
    else:
        c.execute(
            "UPDATE app_users SET enabled=%s WHERE id=%s",
            (a.action == "enable", row[0]),
        )
    c.execute("DELETE FROM app_sessions WHERE user_id=%s", (row[0],))
print("Account updated; previous sessions revoked.")
