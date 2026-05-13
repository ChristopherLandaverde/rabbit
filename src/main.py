"""Main FastAPI application for the Multi-Touch Attribution API."""

import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time

from .config import get_settings
from .api.routes import health_router, attribution_router
from .core.security import security_middleware
from .core.logging import setup_logging, request_logger, performance_logger
from .core.monitoring import health_checker


def _v2_enabled() -> bool:
    return os.environ.get("RABBIT_V2_ENABLED", "false").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    setup_logging()
    print(f"Starting {settings.app_name} v{settings.version}")
    yield
    # Shutdown
    print("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # openapi_url=None when v2 is enabled — we publish /v2/openapi.json explicitly
    # to keep the v2 spec separate from v1 for SDK generation (A6).
    openapi_url = None if _v2_enabled() else "/openapi.json"

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Multi-Touch Attribution API for analyzing marketing touchpoint data",
        lifespan=lifespan,
        openapi_url=openapi_url,
    )
    
    # Add security middleware
    if settings.enable_api_key_auth:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.cors_origins)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # Log request start
        performance_logger.logger.info(f"Request started: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            
            # Record request metrics
            processing_time = time.time() - start_time
            health_checker.record_request(success=response.status_code < 400)
            
            # Add security headers
            response = security_middleware.add_security_headers(response)
            
            # Log request completion
            performance_logger.logger.info(
                f"Request completed: {request.method} {request.url} "
                f"in {processing_time:.3f}s with status {response.status_code}"
            )
            
            return response
            
        except Exception as e:
            # Record error
            health_checker.record_request(success=False)
            performance_logger.logger.error(f"Request failed: {request.method} {request.url} - {str(e)}")
            raise
    
    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(attribution_router, prefix="/attribution", tags=["Attribution"])

    # v2 surface — gated behind RABBIT_V2_ENABLED env flag during M0-M5 buildout
    if _v2_enabled():
        from .v2 import v2_router
        from .v2.openapi import build_v2_openapi

        app.include_router(v2_router, prefix="/v2")

        @app.get("/v2/openapi.json", include_in_schema=False)
        async def v2_openapi():
            return build_v2_openapi(app)

    return app


# Create the app instance
app = create_app()
