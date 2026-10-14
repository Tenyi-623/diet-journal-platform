"""Create the explicitly requested independent administrator; never print its password."""

import csv
import os
import secrets
from pathlib import Path

import psycopg
from pwdlib import PasswordHash
from backend.config import settings


def main():
    path = Path(__file__).resolve().parents[1] / "data/private/admin-account.csv"
    with psycopg.connect(settings.database_url) as c:
        c.execute("SELECT pg_advisory_xact_lock(510121)")
        if c.execute("SELECT 1 FROM app_users WHERE login_id='admin'").fetchone():
            print("admin already exists; credentials and roles unchanged.")
            return
        password = secrets.token_urlsafe(20)
        uid = c.execute(
            "INSERT INTO app_users(login_id,password_hash) VALUES('admin',%s) RETURNING id",
            (PasswordHash.recommended().hash(password),),
        ).fetchone()[0]
        c.execute("INSERT INTO app_user_roles VALUES(%s,'admin')", (uid,))
        c.execute(
            "INSERT INTO app_admin_audit(actor_id,action,target) VALUES(%s,'admin.bootstrap',%s)",
            (uid, str(uid)),
        )
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["login_id", "initial_password"])
            writer.writerow(["admin", password])
    print(
        "Created admin. Initial credentials saved to data/private/admin-account.csv (0600)."
    )


if __name__ == "__main__":
    main()
