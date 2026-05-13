"""v2 API package. Mounted under /v2 when RABBIT_V2_ENABLED=true."""

from .router import v2_router

__all__ = ["v2_router"]
