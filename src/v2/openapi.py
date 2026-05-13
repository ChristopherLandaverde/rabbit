"""Custom OpenAPI generator scoped to v2 routes only.

Why: FastAPI's default /openapi.json merges all routers. v2 should publish a
standalone spec at /v2/openapi.json so SDK generators don't see legacy v1.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def build_v2_openapi(app: FastAPI) -> dict[str, Any]:
    """Return an OpenAPI 3.x dict containing only routes prefixed with /v2."""
    full_spec = get_openapi(
        title="Rabbit Attribution API",
        version="2.0.0",
        description="Multi-touch attribution API for developers building marketing tools.",
        routes=[r for r in app.routes if getattr(r, "path", "").startswith("/v2")],
    )
    full_spec["servers"] = [{"url": "/", "description": "current host"}]
    return full_spec
