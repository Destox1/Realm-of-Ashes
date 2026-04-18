"""Async SQLite connection + init. Uses aiosqlite with WAL mode per spec §14."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv

# override=True: local .env wins over shell env vars (dev-friendly).
# In production on Railway there is no .env file, so Railway's env vars are used.
load_dotenv(override=True)

DB_PATH = os.getenv("DATABASE_PATH", "./db/roa.db")
SCHEMA_PATH = Path(__file__).parent / "db" / "schema.sql"


async def init_db() -> None:
    """Create DB file, apply schema, enable WAL mode. Idempotent."""
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(schema_sql)
        await db.commit()


@asynccontextmanager
async def get_db():
    """Context-managed connection. Row factory returns dict-like rows."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
