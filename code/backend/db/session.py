"""
Async SQLAlchemy session management for AlphaMind.

The engine is created once at import time from the ``DATABASE_URL`` environment
variable (or the SQLite fallback).  A ``get_db`` FastAPI dependency yields an
``AsyncSession`` that is automatically closed after each request.

Production: set  DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
Development: falls back to   sqlite+aiosqlite:///./alphamind.db
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./alphamind.db",
)

# connect_args only needed for SQLite (disables same-thread check)
_connect_args: dict = (
    {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}
)

engine = create_async_engine(
    _DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency - yields a single DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all tables (used in lifespan / tests; production uses Alembic)."""
    import db.models  # noqa: F401 - side-effect: registers all model classes
    from db.base import Base  # noqa: F401 - ensures models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
