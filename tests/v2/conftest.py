"""Service fixtures for v2 integration tests."""

import os
import asyncio

import pytest
from docker.errors import DockerException
from fastapi import APIRouter, Depends, Response
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from testcontainers.postgres import PostgresContainer

from src.config import get_settings
from src.core.logging import performance_logger
from src.db import models  # noqa: F401
from src.db.base import Base
from src.db.session import get_session
from src.main import create_app


class MemoryRedis:
    def __init__(self):
        self.events = {}
        self.fail = False

    async def zremrangebyscore(self, key, minimum, maximum):
        self._check()
        self.events[key] = [event for event in self.events.get(key, []) if event[0] > float(maximum)]

    async def zadd(self, key, mapping):
        self._check()
        self.events.setdefault(key, []).extend((float(score), member) for member, score in mapping.items())

    async def zcard(self, key):
        self._check()
        return len(self.events.get(key, []))

    async def expire(self, key, seconds):
        self._check()
        return True

    async def zrange(self, key, start, stop, withscores=False):
        self._check()
        values = sorted(self.events.get(key, []))
        subset = values[start:stop + 1 if stop != -1 else None]
        return [(member, score) for score, member in subset] if withscores else [member for _, member in subset]

    async def aclose(self):
        return None

    def _check(self):
        if self.fail:
            raise ConnectionError("Redis unavailable")


@pytest.fixture
def client(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rabbit_v2_enabled", True)
    monkeypatch.setattr(performance_logger.logger, "info", lambda *args, **kwargs: None)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_KEY", "bootstrap-secret")
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(prepare())

    async def override_session():
        async with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state.test_session_factory = factory
    app.state.api_session_factory = factory
    checks = APIRouter()

    from src.v2.auth.dependencies import require_api_key, require_scope

    @checks.get("/auth-check")
    async def auth_check(key=Depends(require_api_key)):
        return {"livemode": key.livemode, "is_test": key.is_test}

    @checks.post("/scope-check", dependencies=[Depends(require_scope("datasets:write"))])
    async def scope_check(response: Response):
        return {"ok": True}

    app.include_router(checks, prefix="/v2")
    with TestClient(app, base_url="http://localhost") as test_client:
        app.state.redis = MemoryRedis()
        yield test_client
    asyncio.run(engine.dispose())


def bootstrap(client, name="integration", scopes=None, mode="live", rate_limit=60):
    response = client.post(
        "/v2/admin/keys",
        headers={"X-Admin-Bootstrap-Key": "bootstrap-secret"},
        json={"name": name, "scopes": scopes or ["datasets:write"], "mode": mode,
              "rate_limit_per_minute": rate_limit},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def make_key():
    return bootstrap


@pytest.fixture(scope="session")
def postgres_container():
    """Start an isolated PostgreSQL 16 container, skipping without Docker."""
    if os.getenv("DATABASE_URL"):
        # CI provides its PostgreSQL service as DATABASE_URL.
        yield None
        return
    container = PostgresContainer("postgres:16-alpine")
    try:
        container.start()
    except (DockerException, OSError) as error:
        pytest.skip(f"Docker is unavailable for PostgreSQL test container: {error}")
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def postgres_url(postgres_container):
    """Return the asyncpg URL needed by the async migration environment."""
    if postgres_container is None:
        return os.environ["DATABASE_URL"]
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="session")
def redis_service():
    """Use the configured Redis service or skip if it is unavailable."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    client = Redis(
        host=host,
        port=port,
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD") or None,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        client.ping()
    except Exception:
        pytest.skip("needs Redis")
    finally:
        client.close()
    yield (host, port)
