"""Pydantic models for the Multi-Touch Attribution API."""

from .attribution import (
    AttributionResponse,
    AttributionResults,
    ChannelAttribution,
    BusinessInsight,
    AnalysisMetadata,
)
from .touchpoint import Touchpoint, CustomerJourney
from .validation import ValidationError
from .enums import AttributionModelType, LinkingMethod, EventType

__all__ = [
    "AttributionResponse",
    "AttributionResults", 
    "ChannelAttribution",
    "BusinessInsight",
    "AnalysisMetadata",
    "Touchpoint",
    "CustomerJourney",
    "ValidationError",
    "AttributionModelType",
    "LinkingMethod",
    "EventType",
]
