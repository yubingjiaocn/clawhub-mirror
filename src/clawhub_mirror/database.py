"""SQLAlchemy async database setup for ClawHub Mirror.

Provides engine creation, session management, and table initialization
using async SQLAlchemy with aiosqlite.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from clawhub_mirror.config import Settings

# Module-level state set by init_db()
engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> AsyncEngine:
    """Initialize the async engine and session factory from application settings.

    Must be called once at application startup before any database access.

    Args:
        settings: Application settings containing database_url.

    Returns:
        The created async engine.
    """
    global engine, session_factory  # noqa: PLW0603

    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The session is automatically closed when the request completes.

    Yields:
        An active AsyncSession.

    Raises:
        RuntimeError: If init_db() has not been called.
    """
    if session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all ORM-mapped tables in the database.

    Uses the metadata from the declarative base defined in models.py.

    Raises:
        RuntimeError: If init_db() has not been called.
    """
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    from clawhub_mirror.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Aliases used by routers and tests
get_session = get_db

async def close_db() -> None:
    """Close the database connection pool."""
    global engine, session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        session_factory = None

async def init_db_async(settings: "Settings") -> None:
    """Async-compatible wrapper for init_db."""
    init_db(settings)
    await create_tables()
