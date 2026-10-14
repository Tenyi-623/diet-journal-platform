"""Restore one complete backup into a newly created isolated verification DB."""

import os, subprocess, json, time
from pathlib import Path
from urllib.parse import urlsplit, unquote, urlunsplit
import psycopg
from psycopg import sql
from backend.config import settings

u = urlsplit(settings.database_url)
backup = sorted(Path("data/backups").glob("full-*.dump"))[-1]
name = "diet_verify_" + str(int(time.time()))
env = {**os.environ, "PGPASSWORD": unquote(u.password or "")}
with psycopg.connect(settings.database_url, autocommit=True) as c:
    c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
subprocess.run(
    [
        "pg_restore",
        "-h",
        u.hostname,
        "-p",
        str(u.port),
        "-U",
        unquote(u.username),
        "-d",
        name,
        "--no-owner",
        str(backup),
    ],
    env=env,
    check=True,
)
query = "SELECT (SELECT count(*) FROM foods),(SELECT count(*) FROM food_values),(SELECT count(*) FROM kb_chunks),(SELECT count(*) FROM app_users),(SELECT count(*) FROM app_recipes)"
with psycopg.connect(settings.database_url) as c:
    expected = c.execute(query).fetchone()
with psycopg.connect(urlunsplit((u.scheme, u.netloc, "/" + name, u.query, ""))) as c:
    actual = c.execute(query).fetchone()
assert expected == actual, (expected, actual)
Path("docs/evaluation/restore.json").write_text(
    json.dumps(
        {
            "backup": backup.name,
            "verification_database": name,
            "tables": ["foods", "food_values", "kb_chunks", "app_users", "app_recipes"],
            "expected": expected,
            "restored": actual,
            "pass": True,
        },
        indent=2,
    )
)
print(
    "Full restore verified:",
    dict(zip(["foods", "food_values", "kb_chunks", "users", "recipes"], actual)),
)
