"""Main FastAPI application for the Multi-Touch Attribution API."""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time
from datetime import datetime, timezone
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
from .v2.auth.errors import ApiProblem, problem_content, problem
from .v2.auth.admin import admin_router
from .v2.auth.signup import signup_router
from .v2.datasets import router as datasets_router
from .v2.analyses import router as analyses_router
from .v2.sample_dataset import router as sample_dataset_router
from .v2.auth.service import authenticate
from .v2.auth.limits import check_request_limit
from .db.models import AuditLog
from .db.session import async_session_factory
from ulid import ULID


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
        key = None
        limit_headers = {}
        if settings.rabbit_v2_enabled and path.startswith("/v2/") and path not in {"/v2/health", "/v2/sample-dataset"}:
            is_admin = path.startswith("/v2/admin/keys")
            is_signup = path == "/v2/keys/signup"
            if not (is_admin or is_signup):
                key, auth_error = await authenticate(request)
                if auth_error:
                    return auth_error
                request.state.request_id = request.headers.get("X-Request-ID") or str(ULID())
                if key.is_test:
                    limit_headers = {
                        "X-RateLimit-Limit": "unlimited",
                        "X-RateLimit-Remaining": "unlimited",
                        "X-RateLimit-Reset": "0",
                    }
                else:
                    limit_headers, retry_after = await check_request_limit(request, key)
                    if retry_after is not None:
                        response = problem(
                            429, "rate_limited", "Rate limit exceeded",
                            "This API key has exceeded its per-minute request limit.",
                            "Wait for the rate-limit window to reset or request a higher limit.",
                            "https://docs.rabbit.example/rate-limits",
                        )
                        response.headers.update(limit_headers)
                        response.headers["Retry-After"] = str(retry_after)
                        return response
        
        # Log request start
        performance_logger.logger.info(f"Request started: {request.method} {request.url}")
        
        try:
            response = await call_next(request)

            if key is not None:
                response.headers.update(limit_headers)
                if request.method in {"POST", "PUT", "DELETE"}:
                    try:
                        parts = request.url.path.strip("/").split("/")
                        resource_type = parts[1] if len(parts) > 1 else None
                        resource_id = parts[2] if len(parts) > 2 else None
                        session_factory = getattr(app.state, "api_session_factory", async_session_factory)
                        async with session_factory() as session:
                            session.add(AuditLog(
                                id=str(ULID()), key_id=key.id, action=request.method,
                                resource_type=resource_type, resource_id=resource_id,
                                request_id=getattr(request.state, "request_id", None),
                                ip=request.client.host if request.client else None,
                                user_agent=request.headers.get("User-Agent"),
                                created_at=datetime.now(timezone.utc),
                            ))
                            await session.commit()
                    except Exception as exc:
                        performance_logger.logger.warning(f"Could not write v2 audit log: {exc}")

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
        app.include_router(signup_router, prefix="/v2")
        app.include_router(admin_router, prefix="/v2")
        app.include_router(datasets_router, prefix="/v2")
        app.include_router(analyses_router, prefix="/v2")
        app.include_router(sample_dataset_router, prefix="/v2")
    
    return app


# Create the app instance
app = create_app()
