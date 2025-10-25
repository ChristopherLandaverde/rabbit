"""Main FastAPI application for the Multi-Touch Attribution API."""

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
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Multi-Touch Attribution API for analyzing marketing touchpoint data",
        lifespan=lifespan
    )
    
    # Add security middleware
    if settings.enable_api_key_auth:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    
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
    
    return app


# Create the app instance
app = create_app()
