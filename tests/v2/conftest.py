"""Shared v2 test fixtures.

For M0, we exercise the v2 surface with RABBIT_V2_ENABLED=true but without a live
Postgres connection (the health endpoint doesn't touch the DB). Real DB-backed
tests in M2+ will use testcontainers — wired in a later slice.
"""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def v2_client(monkeypatch):
    """A TestClient with v2 enabled."""
    monkeypatch.setenv("RABBIT_V2_ENABLED", "true")

    # Force re-import so create_app() sees the flag
    import importlib
    import src.main as main_module
    importlib.reload(main_module)

    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
def v1_only_client(monkeypatch):
    """A TestClient with v2 disabled (regression coverage for v1)."""
    monkeypatch.setenv("RABBIT_V2_ENABLED", "false")

    import importlib
    import src.main as main_module
    importlib.reload(main_module)

    with TestClient(main_module.app) as client:
        yield client
