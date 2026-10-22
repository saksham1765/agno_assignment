"""One shared PostgresDb for the whole app (Phase 2)."""

import os

from agno.db.postgres import PostgresDb
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_URL = "postgresql+psycopg://ai:ai@localhost:5532/ai"   # the Docker Postgres

_db = None


def get_db_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def get_db() -> PostgresDb:
    """Create the PostgresDb the first time, then always return the same one."""
    global _db
    if _db is None:
        _db = PostgresDb(db_url=get_db_url())
    return _db
