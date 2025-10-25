"""Confidence scoring system for attribution results."""

from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime
import numpy as np
from ..models.validation import DataQuality


class ConfidenceScorer:
    """Calculates confidence scores for attribution results."""
    
    def __init__(self):
        self.weights = {
            'data_quality': 0.4,
            'sample_size': 0.3,
            'model_fit': 0.2,
            'identity_resolution': 0.1
        }
    
    def calculate_overall_confidence(
        self,
        data_quality: DataQuality,
        sample_size: int,
        model_fit_score: float,
        identity_resolution_confidence: float
    ) -> float:
        """
        Calculate overall confidence score for attribution results.
        
        Args:
            data_quality: Data quality metrics
            sample_size: Number of data points
            model_fit_score: Statistical fit quality (0-1)
            identity_resolution_confidence: Identity linking confidence (0-1)
            
        Returns:
            Overall confidence score (0-1)
        """
        # Data quality component
        data_quality_score = (
            data_quality.completeness * 0.4 +
            data_quality.consistency * 0.3 +
            data_quality.freshness * 0.3
        )
        
        # Sample size component (logarithmic scale)
        sample_size_score = min(1.0, np.log10(max(1, sample_size)) / 3.0)  # 0-1 scale, peaks at 1000+ samples
        
        # Model fit component (already 0-1)
        model_fit_component = model_fit_score
        
        # Identity resolution component (already 0-1)
        identity_component = identity_resolution_confidence
        
        # Weighted combination
        overall_confidence = (
            data_quality_score * self.weights['data_quality'] +
            sample_size_score * self.weights['sample_size'] +
            model_fit_component * self.weights['model_fit'] +
            identity_component * self.weights['identity_resolution']
        )
        
        return min(1.0, max(0.0, overall_confidence))
    
    def calculate_channel_confidence(
        self,
        channel_data: pd.DataFrame,
        total_conversions: int,
        attribution_credit: float
    ) -> float:
        """
        Calculate confidence score for a specific channel's attribution.
        
        Args:
            channel_data: Data for the specific channel
            total_conversions: Total conversions in the dataset
            attribution_credit: Credit assigned to this channel
            
        Returns:
            Channel-specific confidence score (0-1)
        """
        if total_conversions == 0:
            return 0.0
        
        # Base confidence from sample size
        channel_touchpoints = len(channel_data)
        sample_confidence = min(1.0, channel_touchpoints / 100.0)  # Peaks at 100+ touchpoints
        
        # Conversion rate confidence
        channel_conversions = len(channel_data[channel_data['event_type'] == 'conversion'])
        conversion_rate = channel_conversions / channel_touchpoints if channel_touchpoints > 0 else 0
        conversion_confidence = min(1.0, conversion_rate * 10)  # Scale conversion rate
        
        # Attribution credit confidence (higher credit = higher confidence if supported by data)
        credit_confidence = min(1.0, attribution_credit * 2)  # Scale attribution credit
        
        # Weighted combination
        channel_confidence = (
            sample_confidence * 0.4 +
            conversion_confidence * 0.4 +
            credit_confidence * 0.2
        )
        
        return min(1.0, max(0.0, channel_confidence))
    
    def calculate_model_fit_score(
        self,
        df: pd.DataFrame,
        attribution_model: str,
        attribution_results: Dict[str, float]
    ) -> float:
        """
        Calculate statistical fit score for the attribution model.
        
        Args:
            df: Input data
            attribution_model: Name of the attribution model used
            attribution_results: Attribution results by channel
            
        Returns:
            Model fit score (0-1)
        """
        if len(df) == 0:
            return 0.0
        
        # Base fit score from model appropriateness
        model_scores = {
            'linear': 0.8,  # Generally good fit
            'first_touch': 0.7,  # Good for awareness campaigns
            'last_touch': 0.7,  # Good for conversion optimization
            'time_decay': 0.9,  # Excellent for time-sensitive data
            'position_based': 0.85  # Good for complex journeys
        }
        
        base_score = model_scores.get(attribution_model, 0.5)
        
        # Adjust based on data characteristics
        journey_lengths = df.groupby('customer_id').size() if 'customer_id' in df.columns else [len(df)]
        avg_journey_length = np.mean(journey_lengths)
        
        # Longer journeys favor certain models
        if attribution_model == 'linear' and avg_journey_length > 3:
            base_score += 0.1
        elif attribution_model == 'time_decay' and avg_journey_length > 2:
            base_score += 0.1
        elif attribution_model == 'position_based' and avg_journey_length > 4:
            base_score += 0.1
        
        # Check for data quality indicators
        if 'timestamp' in df.columns:
            time_span = (pd.to_datetime(df['timestamp']).max() - pd.to_datetime(df['timestamp']).min()).days
            if time_span > 30:  # Good time span for attribution
                base_score += 0.05
        
        return min(1.0, base_score)
    
    def calculate_identity_resolution_confidence(
        self,
        df: pd.DataFrame,
        linking_method: str
    ) -> float:
        """
        Calculate confidence in identity resolution.
        
        Args:
            df: Input data
            linking_method: Method used for identity linking
            
        Returns:
            Identity resolution confidence (0-1)
        """
        method_scores = {
            'customer_id': 0.95,  # Highest confidence
            'session_email': 0.85,  # High confidence
            'email_only': 0.70,  # Medium confidence
            'aggregate': 0.50,  # Lower confidence
            'auto': 0.80  # Depends on available data
        }
        
        base_score = method_scores.get(linking_method, 0.50)
        
        # Adjust based on data availability
        if linking_method == 'customer_id' and 'customer_id' in df.columns:
            # Check for completeness of customer_id
            customer_id_completeness = df['customer_id'].notna().mean()
            base_score *= customer_id_completeness
        elif linking_method == 'session_email' and 'session_id' in df.columns and 'email' in df.columns:
            # Check for completeness of both fields
            session_completeness = df['session_id'].notna().mean()
            email_completeness = df['email'].notna().mean()
            base_score *= (session_completeness + email_completeness) / 2
        elif linking_method == 'email_only' and 'email' in df.columns:
            # Check for email completeness
            email_completeness = df['email'].notna().mean()
            base_score *= email_completeness
        
        return min(1.0, max(0.0, base_score))
    
    def generate_confidence_breakdown(
        self,
        data_quality: DataQuality,
        sample_size: int,
        model_fit_score: float,
        identity_resolution_confidence: float
    ) -> Dict[str, float]:
        """
        Generate detailed confidence breakdown.
        
        Returns:
            Dictionary with confidence components
        """
        data_quality_score = (
            data_quality.completeness * 0.4 +
            data_quality.consistency * 0.3 +
            data_quality.freshness * 0.3
        )
        
        sample_size_score = min(1.0, np.log10(max(1, sample_size)) / 3.0)
        
        return {
            'data_quality': data_quality_score,
            'sample_size': sample_size_score,
            'model_fit': model_fit_score,
            'identity_resolution': identity_resolution_confidence,
            'overall': self.calculate_overall_confidence(
                data_quality, sample_size, model_fit_score, identity_resolution_confidence
            )
        }