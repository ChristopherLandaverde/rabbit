"""Touchpoint and journey models."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .enums import EventType


class Touchpoint(BaseModel):
    """Individual marketing touchpoint."""
    timestamp: datetime = Field(..., description="When the touchpoint occurred")
    channel: str = Field(..., description="Marketing channel (e.g., email, social, paid_search)")
    event_type: EventType = Field(..., description="Type of marketing event")
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    email: Optional[str] = Field(None, description="Customer email")
    campaign_id: Optional[str] = Field(None, description="Campaign identifier")
    creative_id: Optional[str] = Field(None, description="Creative/ad identifier")
    cost: Optional[float] = Field(None, ge=0.0, description="Cost associated with touchpoint")
    conversion_value: Optional[float] = Field(None, ge=0.0, description="Conversion value")


class CustomerJourney(BaseModel):
    """Complete customer journey with touchpoints."""
    touchpoints: List[Touchpoint] = Field(..., description="List of touchpoints in chronological order")
    total_conversions: int = Field(..., ge=0, description="Total conversions in journey")
    total_revenue: float = Field(..., ge=0.0, description="Total revenue from journey")
    journey_id: str = Field(..., description="Unique journey identifier")
    
    @property
    def has_conversion(self) -> bool:
        """Check if journey contains any conversions."""
        return any(tp.event_type in [EventType.CONVERSION, EventType.PURCHASE] for tp in self.touchpoints)
