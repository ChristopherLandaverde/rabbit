"""Main FastAPI application for the Multi-Touch Attribution API."""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time
from urllib.parse import urlsplit
from redis.asyncio import Redis
from fastapi.responses import JSONResponse

from .config import get_settings
from .api.routes import health_router, attribution_router
from .core.security import security_middleware
from .core.logging import setup_logging, request_logger, performance_logger
from .core.monitoring import health_checker
from .db.session import engine
from .v2.router import v2_router
from .v2.auth.errors import ApiProblem, problem_content
from .v2.auth.admin import admin_router
from .v2.auth.service import authenticate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    setup_logging()
    app.state.db_engine = engine
    app.state.redis = Redis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
        password=settings.redis_password,
        decode_responses=True,
    )
    print(f"Starting {settings.app_name} v{settings.version}")
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()
    print("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Multi-Touch Attribution API for analyzing marketing touchpoint data",
        lifespan=lifespan,
        openapi_url=None,
    )

    @app.exception_handler(ApiProblem)
    async def api_problem_handler(request: Request, exc: ApiProblem):
        return JSONResponse(
            status_code=exc.status,
            media_type="application/problem+json",
            content=problem_content(exc.status, exc.code, exc.title, exc.detail, exc.fix_hint, exc.doc_url),
        )
    
    # Add security middleware
    if settings.enable_api_key_auth:
        allowed_hosts = {
            "localhost",
            "127.0.0.1",
            *(urlsplit(origin).hostname for origin in settings.cors_origins if urlsplit(origin).hostname),
        }
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted(allowed_hosts))
    
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
        path = request.url.path
        if settings.rabbit_v2_enabled and path.startswith("/v2/") and path != "/v2/health":
            is_admin = path.startswith("/v2/admin/keys")
            if not is_admin:
                _, auth_error = await authenticate(request)
                if auth_error:
                    return auth_error
        
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
    if settings.rabbit_v2_enabled:
        app.include_router(v2_router, prefix="/v2")
        app.include_router(admin_router, prefix="/v2")
    
    return app


# Create the app instance
app = create_app()
