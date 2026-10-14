"""Bounded pools keyed by DSN; web and worker have independent process-local pools."""

import os, threading
from pathlib import Path
from contextlib import contextmanager
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "app.env", override=False)
_pools = {}
_lock = threading.Lock()


@contextmanager
def connect():
    url = os.environ.get("APP_DATABASE_URL")
    if not url:
        raise RuntimeError("Run python -m backend.app.setup first")
    with _lock:
        if url not in _pools:
            _pools[url] = ConnectionPool(
                url,
                min_size=0,
                max_size=6,
                timeout=5,
                max_waiting=32,
                kwargs={"row_factory": dict_row, "connect_timeout": 5},
                open=True,
            )
        pool = _pools[url]
    with pool.connection() as connection:
        yield connection
