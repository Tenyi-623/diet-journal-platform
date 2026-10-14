"""Offline schema migrations and idempotent 50-account provisioning. Never prints credentials."""

import csv, hashlib, os, secrets
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote
import psycopg
from psycopg import sql
from pwdlib import PasswordHash
from backend.config import settings

ROOT = Path(__file__).resolve().parents[2]


def migrate(url):
    with psycopg.connect(url) as c:
        c.execute("SELECT pg_advisory_xact_lock(51011)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS app_migrations(name text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz DEFAULT now())"
        )
        for path in sorted((ROOT / "backend/migrations").glob("*.sql")):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            old = c.execute(
                "SELECT sha256 FROM app_migrations WHERE name=%s", (path.name,)
            ).fetchone()
            if old:
                if old[0] != digest:
                    raise RuntimeError("Applied migration changed: " + path.name)
                continue
            c.execute(path.read_text())
            c.execute(
                "INSERT INTO app_migrations(name,sha256) VALUES(%s,%s)",
                (path.name, digest),
            )


def setup():
    migrate(settings.database_url)
    credentials = []
    hasher = PasswordHash.recommended()
    with psycopg.connect(settings.database_url) as c:
        c.execute("SELECT pg_advisory_xact_lock(51011)")
        for i in range(1, 51):
            if c.execute("SELECT 1 FROM app_users WHERE id=%s", (i,)).fetchone():
                continue
            password = secrets.token_urlsafe(12)
            login = f"diet{i:03d}"
            c.execute(
                "INSERT INTO app_users(id,login_id,password_hash) VALUES(%s,%s,%s)",
                (i, login, hasher.hash(password)),
            )
            credentials.append((login, password))
        env_path = ROOT / "backend/app.env"
        if not env_path.exists():
            role = "diet_web"
            password = secrets.token_urlsafe(32)
            if c.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                raise RuntimeError(
                    "Existing diet_web role without app.env; recover credentials explicitly"
                )
            c.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)
                )
            )
            u = urlsplit(settings.database_url)
            appurl = urlunsplit(
                (
                    u.scheme,
                    f"{role}:{quote(password)}@{u.hostname}:{u.port}",
                    u.path,
                    "",
                    "",
                )
            )
            fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(f"APP_DATABASE_URL={appurl}\nAPP_SECURE_COOKIES=false\n")
        c.execute("GRANT USAGE ON SCHEMA public TO diet_web")
        for (table,) in c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        ).fetchall():
            perms = (
                "SELECT,INSERT,UPDATE,DELETE"
                if table.startswith("app_")
                and table
                not in [
                    "app_migrations",
                    "app_income_policies",
                    "app_ingredients",
                    "app_roles",
                    "app_permissions",
                    "app_role_permissions",
                    "app_admin_audit",
                ]
                or table in ["kb_documents", "kb_pages", "kb_chunks", "kb_collections"]
                else "SELECT"
            )
            c.execute(
                sql.SQL("GRANT " + perms + " ON {} TO diet_web").format(
                    sql.Identifier(table)
                )
            )
        c.execute("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO diet_web")
        c.execute("GRANT INSERT ON app_admin_audit TO diet_web")
        c.execute("REVOKE UPDATE,DELETE ON app_admin_audit FROM diet_web")
    if credentials:
        path = ROOT / "data/private/local-accounts.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["login_id", "initial_password"])
            writer.writerows(credentials)
    print(
        f"Migrations complete; {len(credentials)} accounts created; credentials saved under data/private (0600)."
    )


if __name__ == "__main__":
    setup()
