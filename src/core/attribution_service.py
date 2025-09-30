"""Main attribution service that orchestrates the attribution process."""

import time
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

from ..models.attribution import (
    AttributionResponse,
    AttributionResults,
    ChannelAttribution,
    AnalysisMetadata,
    BusinessInsight
)
from ..models.touchpoint import CustomerJourney
from ..models.enums import AttributionModelType, LinkingMethod
from .attribution.factory import AttributionModelFactory
from .attribution.base import AttributionModel
from .identity.resolver import IdentityResolver, select_linking_method
from .identity.journey_builder import JourneyBuilder
from .validation.validators import DataQuality, validate_required_columns, validate_data_types, validate_data_quality
from .confidence import ConfidenceCalculator


class AttributionService:
    """Main service for performing attribution analysis."""
    
    def __init__(self):
        self.journey_builder = JourneyBuilder()
        self.confidence_calculator = ConfidenceCalculator()
    
    async def analyze_attribution(
        self,
        df: pd.DataFrame,
        model_type: AttributionModelType,
        **model_kwargs
    ) -> AttributionResponse:
        """
        Perform complete attribution analysis.
        
        Args:
            df: DataFrame containing touchpoint data
            model_type: Attribution model to use
            **model_kwargs: Additional parameters for the attribution model
            
        Returns:
            Complete attribution analysis response
        """
        start_time = time.time()
        
        # Step 1: Validate data
        validation_errors = self._validate_data(df)
        if validation_errors:
            raise ValueError(f"Data validation failed: {validation_errors}")
        
        # Step 2: Assess data quality
        data_quality = validate_data_quality(df)
        
        # Step 3: Select linking method and resolve identities
        linking_method = select_linking_method(df)
        resolver = IdentityResolver(linking_method)
        identity_map = resolver.resolve_identities(df)
        
        # Step 4: Build customer journeys
        journeys = self.journey_builder.build_journeys(df, identity_map)
        
        # Step 5: Calculate attribution
        attribution_model = AttributionModelFactory.create_model(model_type, **model_kwargs)
        channel_attributions = self._calculate_attribution(journeys, attribution_model)
        
        # Step 6: Calculate confidence scores
        linking_accuracy = self.confidence_calculator.calculate_linking_accuracy(
            journeys, linking_method
        )
        overall_confidence = self.confidence_calculator.calculate_confidence(
            data_quality, linking_accuracy, len(journeys), len(df)
        )
        
        # Step 7: Build results
        processing_time = int((time.time() - start_time) * 1000)
        
        results = self._build_attribution_results(
            channel_attributions, journeys, overall_confidence
        )
        
        metadata = self._build_metadata(
            model_type, df, journeys, linking_method, processing_time
        )
        
        insights = self._generate_business_insights(results, data_quality)
        
        return AttributionResponse(
            results=results,
            metadata=metadata,
            insights=insights
        )
    
    def _validate_data(self, df: pd.DataFrame) -> List[str]:
        """Validate input data and return list of error messages."""
        errors = []
        
        # Check required columns
        validation_errors = validate_required_columns(df)
        if validation_errors:
            errors.extend([f"Missing column: {e.field}" for e in validation_errors])
        
        # Check data types
        type_errors = validate_data_types(df)
        if type_errors:
            errors.extend([f"Invalid data type in {e.field}: {e.message}" for e in type_errors])
        
        return errors
    
    def _calculate_attribution(
        self, 
        journeys: List[CustomerJourney], 
        model: AttributionModel
    ) -> Dict[str, ChannelAttribution]:
        """Calculate attribution using the specified model."""
        # Only analyze journeys with conversions
        converting_journeys = [j for j in journeys if j.has_conversion]
        
        if not converting_journeys:
            return {}
        
        # Calculate aggregate attribution
        channel_credits = model.calculate_journey_attribution(converting_journeys)
        
        # Build ChannelAttribution objects
        channel_attributions = {}
        total_conversions = sum(j.total_conversions for j in converting_journeys)
        total_revenue = sum(j.total_revenue for j in converting_journeys)
        
        for channel, credit in channel_credits.items():
            # Calculate metrics for this channel
            channel_conversions = int(credit * total_conversions)
            channel_revenue = credit * total_revenue
            
            # Calculate channel-specific confidence
            channel_touchpoints = sum(
                len([tp for tp in j.touchpoints if tp.channel == channel])
                for j in converting_journeys
            )
            
            channel_confidence = self.confidence_calculator.calculate_channel_confidence(
                channel, channel_touchpoints, len(converting_journeys), None
            )
            
            channel_attributions[channel] = ChannelAttribution(
                credit=credit,
                conversions=channel_conversions,
                revenue=channel_revenue,
                confidence=channel_confidence
            )
        
        return channel_attributions
    
    def _build_attribution_results(
        self,
        channel_attributions: Dict[str, ChannelAttribution],
        journeys: List[CustomerJourney],
        overall_confidence: float
    ) -> AttributionResults:
        """Build the attribution results object."""
        converting_journeys = [j for j in journeys if j.has_conversion]
        
        total_conversions = sum(j.total_conversions for j in converting_journeys)
        total_revenue = sum(j.total_revenue for j in converting_journeys)
        
        return AttributionResults(
            total_conversions=total_conversions,
            total_revenue=total_revenue,
            channel_attributions=channel_attributions,
            overall_confidence=overall_confidence
        )
    
    def _build_metadata(
        self,
        model_type: AttributionModelType,
        df: pd.DataFrame,
        journeys: List[CustomerJourney],
        linking_method: LinkingMethod,
        processing_time_ms: int
    ) -> AnalysisMetadata:
        """Build the analysis metadata object."""
        time_range_start = df['timestamp'].min() if 'timestamp' in df.columns else datetime.now()
        time_range_end = df['timestamp'].max() if 'timestamp' in df.columns else datetime.now()
        
        return AnalysisMetadata(
            model_used=str(model_type),
            data_points_analyzed=len(df),
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            linking_method=str(linking_method),
            processing_time_ms=processing_time_ms
        )
    
    def _generate_business_insights(
        self,
        results: AttributionResults,
        data_quality: DataQuality
    ) -> List[BusinessInsight]:
        """Generate business insights from attribution results."""
        insights = []
        
        if not results.channel_attributions:
            return insights
        
        # Find top performing channel
        top_channel = max(
            results.channel_attributions.items(),
            key=lambda x: x[1].credit
        )
        
        insights.append(BusinessInsight(
            insight_type="performance",
            title="Top Performing Channel",
            description=f"{top_channel[0]} is your top performing channel with {top_channel[1].credit:.1%} attribution credit.",
            impact_score=top_channel[1].confidence,
            recommendation=f"Consider increasing investment in {top_channel[0]} to maximize ROI."
        ))
        
        # Data quality insight
        if data_quality.completeness < 0.8:
            insights.append(BusinessInsight(
                insight_type="data_quality",
                title="Data Completeness Issue",
                description=f"Data completeness is {data_quality.completeness:.1%}, below the recommended 80%.",
                impact_score=1.0 - data_quality.completeness,
                recommendation="Improve data collection processes to capture more complete customer journey data."
            ))
        
        return insights
