"""Confidence scoring for attribution results."""

from typing import Dict, List
from ..models.touchpoint import CustomerJourney
from .validation.validators import DataQuality


class ConfidenceCalculator:
    """Calculates confidence scores for attribution results."""
    
    def calculate_confidence(
        self, 
        data_quality: DataQuality, 
        linking_accuracy: float,
        journey_count: int,
        total_touchpoints: int
    ) -> float:
        """
        Calculate overall confidence score.
        
        Args:
            data_quality: Data quality metrics
            linking_accuracy: Accuracy of identity linking (0.0 to 1.0)
            journey_count: Number of customer journeys
            total_touchpoints: Total number of touchpoints
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Combine data quality metrics
        quality_score = (
            data_quality.completeness * 0.4 +
            data_quality.consistency * 0.3 +
            data_quality.freshness * 0.3
        )
        
        # Calculate volume factor (more data = higher confidence)
        volume_factor = min(1.0, (journey_count / 100) + (total_touchpoints / 1000))
        
        # Weight with linking accuracy and volume
        confidence = (
            quality_score * 0.5 +
            linking_accuracy * 0.3 +
            volume_factor * 0.2
        )
        
        return min(1.0, max(0.0, confidence))
    
    def calculate_channel_confidence(
        self,
        channel: str,
        channel_touchpoints: int,
        total_touchpoints: int,
        data_quality: DataQuality
    ) -> float:
        """
        Calculate confidence score for a specific channel.
        
        Args:
            channel: Channel name
            channel_touchpoints: Number of touchpoints for this channel
            total_touchpoints: Total number of touchpoints
            data_quality: Overall data quality
            
        Returns:
            Channel-specific confidence score
        """
        # Base confidence from data quality
        base_confidence = (
            data_quality.completeness * 0.6 +
            data_quality.consistency * 0.4
        )
        
        # Volume factor for this channel
        channel_volume_factor = min(1.0, channel_touchpoints / 10)
        
        # Calculate final confidence
        confidence = base_confidence * (0.7 + 0.3 * channel_volume_factor)
        
        return min(1.0, max(0.0, confidence))
    
    def calculate_linking_accuracy(
        self, 
        journeys: List[CustomerJourney], 
        linking_method: str
    ) -> float:
        """
        Estimate linking accuracy based on journey characteristics.
        
        Args:
            journeys: List of customer journeys
            linking_method: Method used for linking
            
        Returns:
            Estimated linking accuracy (0.0 to 1.0)
        """
        if not journeys:
            return 0.0
        
        # Base accuracy by linking method
        method_accuracy = {
            'customer_id': 0.95,
            'session_email': 0.85,
            'email_only': 0.75,
            'aggregate': 0.5
        }
        
        base_accuracy = method_accuracy.get(linking_method, 0.5)
        
        # Adjust based on journey characteristics
        avg_journey_length = sum(len(j.touchpoints) for j in journeys) / len(journeys)
        
        # Longer journeys suggest better identity resolution
        length_factor = min(1.0, avg_journey_length / 5)
        
        # Calculate final accuracy
        accuracy = base_accuracy * (0.8 + 0.2 * length_factor)
        
        return min(1.0, max(0.0, accuracy))
