"""Async engine + sessionmaker. Reads DATABASE_URL from env."""

import os
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _database_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://rabbit:rabbit_dev@localhost:5432/rabbit",
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency."""
    async with async_session_maker() as session:
        yield session
