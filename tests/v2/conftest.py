"""Service fixtures for v2 integration tests."""

import os

import pytest
from docker.errors import DockerException
from redis import Redis
from testcontainers.community.postgres import PostgresContainer


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
