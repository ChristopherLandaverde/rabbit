"""Async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import get_settings


def make_engine(database_url: str | None = None):
    """Create an async engine, optionally for a test database."""
    return create_async_engine(database_url or get_settings().database_url, pool_pre_ping=True)


engine = make_engine()
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    """Yield a session for FastAPI dependencies and background work."""
    async with async_session_factory() as session:
        yield session
