"""Top-level v2 router. Aggregates all v2 sub-routers."""

from fastapi import APIRouter

from .routes.health import router as health_router

v2_router = APIRouter()
v2_router.include_router(health_router, tags=["v2-health"])
