"""Smoke tests for the v2 router, migration, and service fixtures."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from src.config import get_settings
from src.core.logging import performance_logger
from src.main import create_app

ROOT = Path(__file__).resolve().parents[2]


def test_v2_health_and_openapi_are_scoped(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rabbit_v2_enabled", True)
    monkeypatch.setattr(performance_logger.logger, "info", lambda *args, **kwargs: None)
    with TestClient(create_app(), base_url="http://localhost") as client:
        response = client.get("/v2/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "2.0.0"}
        assert client.get("/openapi.json").status_code == 404

        schema = client.get("/v2/openapi.json")
        assert schema.status_code == 401
        assert schema.json()["code"] == "missing_api_key"


def test_v2_routes_are_hidden_when_disabled(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rabbit_v2_enabled", False)
    monkeypatch.setattr(performance_logger.logger, "info", lambda *args, **kwargs: None)
    with TestClient(create_app(), base_url="http://localhost") as client:
        assert client.get("/v2/health").status_code == 404
        assert client.get("/v2/openapi.json").status_code == 404


def test_sqlite_migration_creates_foundation_tables(tmp_path):
    database = tmp_path / "rabbit-v2.sqlite"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {
        "api_keys",
        "datasets",
        "analyses",
        "webhooks",
        "webhook_deliveries",
        "audit_log",
    } <= tables


def test_postgres_container_migration(postgres_url):
    environment = os.environ.copy()
    environment["DATABASE_URL"] = postgres_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )


def test_redis_service(redis_service):
    host, port = redis_service
    client = Redis(host=host, port=port)
    try:
        assert client.ping() is True
    finally:
        client.close()
