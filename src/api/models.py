"""API-specific models."""

from datetime import datetime
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    timestamp: str
