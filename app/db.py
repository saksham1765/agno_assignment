"""Shared PostgresDb helpers (primary + optional separate trace DB)."""

import os

from agno.db.postgres import PostgresDb
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_URL = "postgresql+psycopg://ai:ai@localhost:5532/ai"   # the Docker Postgres

_db = None
_trace_db = None


def get_db_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def get_trace_db_url() -> str | None:
    """When set, traces go to a different Postgres than the primary app DB."""
    url = os.getenv("TRACE_DATABASE_URL", "").strip()
    return url or None


def get_db() -> PostgresDb:
    """Create the primary PostgresDb the first time, then always return the same one."""
    global _db
    if _db is None:
        _db = PostgresDb(db_url=get_db_url(), id="valura-primary")
    return _db


def get_trace_db() -> PostgresDb:
    """Trace/spans DB. Falls back to the primary DB when TRACE_DATABASE_URL is unset."""
    global _trace_db
    if _trace_db is None:
        url = get_trace_db_url()
        if url:
            _trace_db = PostgresDb(db_url=url, id="valura-traces")
        else:
            _trace_db = get_db()
    return _trace_db
