"""
Async database engine and session management.

`check_db_connection()` is used by the /ready endpoint: it must actually
round-trip to the database (not just check that an engine object exists) so
that /ready genuinely reflects whether this instance can serve traffic.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency: yields a DB session scoped to a single request."""
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_connection() -> bool:
    """
    Lightweight liveness probe against the real database connection.
    Returns True if the DB answered a trivial query, False otherwise.
    Never raises — callers (the /ready endpoint) turn a False into a 503.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def init_models():
    """Create tables on startup. Fine for SQLite/dev; use Alembic in prod."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine():
    """Close all pooled connections cleanly during graceful shutdown."""
    await engine.dispose()
