"""Routes for the initial Rabbit v2 API surface."""

from fastapi import APIRouter, Request
from fastapi.openapi.utils import get_openapi

v2_router = APIRouter()


@v2_router.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Return v2 API status without requiring authentication."""
    return {"status": "ok", "version": "2.0.0"}


@v2_router.get("/openapi.json", include_in_schema=False)
async def v2_openapi(request: Request) -> dict:
    """Generate an OpenAPI document containing only v2 routes."""
    routes = [
        route
        for route in request.app.routes
        if getattr(route, "path", "").startswith("/v2/")
        and getattr(route, "include_in_schema", True)
    ]
    return get_openapi(title="Rabbit API", version="2.0.0", routes=routes)
