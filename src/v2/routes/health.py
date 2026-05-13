"""v2 health endpoint. No auth required."""

from fastapi import APIRouter
from pydantic import BaseModel

V2_VERSION = "2.0.0"

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def v2_health() -> HealthResponse:
    return HealthResponse(status="ok", version=V2_VERSION)
