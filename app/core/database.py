"""Async SQLAlchemy engine/session management and startup DB verification."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


settings = None


def _get_engine():
    global settings
    if settings is None:
        from app.config.settings import get_settings

        settings = get_settings()

    connect_args = {}
    db_url_lower = settings.database_url.lower()
    # Supabase Transaction Pooler (port 6543) or PgBouncer mode requires
    # disabling asyncpg prepared statement caching to prevent runtime errors.
    if ":6543" in db_url_lower or "pooler" in db_url_lower or "pgbouncer" in db_url_lower:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0

    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=1800,
        connect_args=connect_args,
    )


engine = None
async_session_maker = None


def _ensure_engine():
    global engine, async_session_maker
    if engine is None:
        engine = _get_engine()
        async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine


def get_async_session_maker() -> async_sessionmaker:
    """Return the process-wide async session factory."""
    _ensure_engine()
    assert async_session_maker is not None
    return async_session_maker


async def get_db_session():
    """
    Dependency that provides a transactional database session.
    Ensures the session is closed after request completion.
    """
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Startup verification gate.

    The app refuses to start against an unmigrated or unreachable database.
    Schema creation happens exclusively through Alembic migrations — this
    function never creates or alters tables.
    """
    _ensure_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        logger.info("Database migration state verified")
    except Exception as e:
        logger.error(f"Database not initialized. Run 'python init_db.py' first. Error: {e}")
        raise RuntimeError(f"Database not initialized: {e}") from e
