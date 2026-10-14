"""Run app integration checks only against the previously restored isolated database."""

import os, unittest
from urllib.parse import urlsplit, urlunsplit
from backend.config import settings

u = urlsplit(settings.database_url)
os.environ["DIET_TEST_DATABASE_URL"] = urlunsplit(
    (u.scheme, u.netloc, "/diet_restore_check", u.query, "")
)
suite = unittest.defaultTestLoader.discover("backend/tests")
r = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not r.wasSuccessful())
