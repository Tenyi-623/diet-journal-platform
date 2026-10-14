"""Create a permission-restricted complete dump without exposing credentials in argv."""

import os, subprocess, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, unquote
from backend.config import settings

u = urlsplit(settings.database_url)
folder = Path("data/backups")
folder.mkdir(exist_ok=True, mode=0o700)
p = folder / ("full-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".dump")
env = {**os.environ, "PGPASSWORD": unquote(u.password or "")}
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    with os.fdopen(fd, "wb") as out:
        subprocess.run(
            [
                "pg_dump",
                "-h",
                u.hostname,
                "-p",
                str(u.port or 5432),
                "-U",
                unquote(u.username),
                "-d",
                u.path[1:],
                "-Fc",
                "--no-owner",
            ],
            env=env,
            stdout=out,
            check=True,
        )
except Exception:
    p.unlink(missing_ok=True)
    raise
meta = {
    "file": p.name,
    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    "bytes": p.stat().st_size,
    "created_utc": datetime.now(timezone.utc).isoformat(),
}
p.with_suffix(".json").write_text(json.dumps(meta, indent=2))
print(p)
