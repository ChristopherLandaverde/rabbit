"""Attribution-related Pydantic models."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ChannelAttribution(BaseModel):
    """Attribution credit for a specific channel."""
    credit: float = Field(..., ge=0.0, le=1.0, description="Attribution credit (0.0 to 1.0)")
    conversions: int = Field(..., ge=0, description="Number of conversions attributed")
    revenue: float = Field(..., ge=0.0, description="Revenue attributed to this channel")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for attribution")


class AttributionResults(BaseModel):
    """Results of attribution analysis."""
    total_conversions: int = Field(..., ge=0, description="Total number of conversions")
    total_revenue: float = Field(..., ge=0.0, description="Total revenue analyzed")
    channel_attributions: Dict[str, ChannelAttribution] = Field(
        ..., description="Attribution results by channel"
    )
    overall_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence score"
    )


class BusinessInsight(BaseModel):
    """Business insight generated from attribution analysis."""
    insight_type: str = Field(..., description="Type of insight")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Detailed insight description")
    impact_score: float = Field(..., ge=0.0, le=1.0, description="Impact score")
    recommendation: Optional[str] = Field(None, description="Actionable recommendation")


class AnalysisMetadata(BaseModel):
    """Metadata about the attribution analysis."""
    model_config = {"protected_namespaces": ()}
    
    model_used: str = Field(..., description="Attribution model used")
    data_points_analyzed: int = Field(..., ge=0, description="Number of data points")
    time_range_start: datetime = Field(..., description="Analysis start time")
    time_range_end: datetime = Field(..., description="Analysis end time")
    linking_method: str = Field(..., description="Method used for identity linking")
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds")


class AttributionResponse(BaseModel):
    """Complete attribution analysis response."""
    results: AttributionResults = Field(..., description="Attribution analysis results")
    metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    insights: Optional[List[BusinessInsight]] = Field(
        None, description="Business insights generated"
    )


class SchemaDetection(BaseModel):
    """Schema detection results."""
    detected_columns: Dict[str, str] = Field(..., description="Detected column names and types")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Schema detection confidence")
    required_columns_present: bool = Field(..., description="Whether all required columns are present")


class DataQualityMetrics(BaseModel):
    """Data quality assessment metrics."""
    completeness: float = Field(..., ge=0.0, le=1.0, description="Data completeness score")
    consistency: float = Field(..., ge=0.0, le=1.0, description="Data consistency score")
    freshness: float = Field(..., ge=0.0, le=1.0, description="Data freshness score")
    overall_quality: float = Field(..., ge=0.0, le=1.0, description="Overall data quality score")


class ValidationResponse(BaseModel):
    """Data validation response."""
    valid: bool = Field(..., description="Whether the data is valid for analysis")
    schema_detection: SchemaDetection = Field(..., description="Schema detection results")
    data_quality: DataQualityMetrics = Field(..., description="Data quality metrics")
    errors: List[Dict[str, Any]] = Field(..., description="Validation errors found")
    recommendations: List[str] = Field(..., description="Recommendations for data improvement")
    warnings: List[str] = Field(..., description="Non-critical warnings")
