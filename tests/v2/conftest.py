"""Opt-in Postgres and Redis containers for v2 integration tests."""

import pytest
from docker.errors import DockerException
from testcontainers.core.container import DockerContainer
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container():
    """Start an isolated PostgreSQL 16 container, skipping without Docker."""
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
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="session")
def redis_container():
    """Start an isolated Redis 7 container, skipping without Docker."""
    container = DockerContainer("redis:7-alpine").with_exposed_ports(6379)
    try:
        container.start()
    except (DockerException, OSError) as error:
        pytest.skip(f"Docker is unavailable for Redis test container: {error}")
    try:
        yield container
    finally:
        container.stop()
