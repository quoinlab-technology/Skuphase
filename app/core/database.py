"""Database connection and session management."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from app.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool,  # For serverless environments - doesn't support pool_size
)

# Create session factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all models
Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database connectivity and verify migration state.

    Migration-first policy:
    - Schema changes must be applied via Alembic, not create_all().
    """
    async with engine.begin() as conn:
        try:
            # Keep stack lightweight: enable pgvector in Postgres when allowed.
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            # Some managed DB roles may not have extension permissions.
            logger.warning(f"Could not initialize pgvector extension: {str(e)}")

        # Verify Alembic has been applied.
        try:
            result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            version = result.scalar_one_or_none()
            if not version:
                raise RuntimeError("Alembic version table exists but has no revision.")
            logger.info(f"Database migration revision: {version}")
        except Exception as e:
            raise RuntimeError(
                "Database is not migrated. Run `alembic -c alembic.ini upgrade head` before starting the app."
            ) from e


async def close_db():
    """Close database connection."""
    await engine.dispose()
