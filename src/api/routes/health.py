"""Health check endpoint."""

from datetime import datetime
from fastapi import APIRouter, Depends
from ..models import HealthResponse
from ...core.monitoring import health_checker, metrics_collector
from ...core.caching import api_cache
from ...core.auth import get_current_user
from ...config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    settings = get_settings()
    
    # Check if we have cached health status
    cached_status = api_cache.get_health_status()
    if cached_status:
        return HealthResponse(**cached_status)
    
    # Get comprehensive health status
    health_data = health_checker.get_comprehensive_health()
    
    # Cache health status for 1 minute
    api_cache.set_health_status(health_data, ttl_seconds=60)
    
    return HealthResponse(
        status=health_data["status"],
        version=health_data["version"],
        timestamp=health_data["timestamp"]
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    return health_checker.get_comprehensive_health()


@router.get("/health/metrics")
async def health_metrics():
    """Get application metrics."""
    return health_checker.get_metrics()


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    health_data = health_checker.get_comprehensive_health()
    
    if health_data["status"] in ["healthy", "warning"]:
        return {"status": "ready"}
    else:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "reason": health_data["status"]}
        )


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
