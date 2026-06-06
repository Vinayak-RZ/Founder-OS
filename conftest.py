"""Pytest setup: isolate tests from the live brain and real credentials.

Lives at the repo root so (a) the project root is on sys.path for `from agent ...`
imports and (b) this runs before any test module imports `config` or
`memory.sql_store`. We inject dummy credentials (so config doesn't exit(1)) and
redirect the SQLite DB to a throwaway temp file. Tests never touch the real
data/founder_os.db.
"""
import os
import tempfile

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("MY_TELEGRAM_USER_ID", "123456")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")

_TEST_DB = os.path.join(tempfile.gettempdir(), "founder_os_test.db")
if os.path.exists(_TEST_DB):
    try:
        os.remove(_TEST_DB)
    except OSError:
        pass
os.environ["FOUNDER_OS_DB"] = _TEST_DB
