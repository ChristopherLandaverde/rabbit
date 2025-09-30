"""Time decay attribution model implementation."""

from typing import Dict
from .base import AttributionModel
from ...models.touchpoint import CustomerJourney


class TimeDecayAttributionModel(AttributionModel):
    """Time decay attribution model - more credit to recent touchpoints."""
    
    def __init__(self, half_life_days: float = 7.0):
        """
        Initialize time decay model.
        
        Args:
            half_life_days: Half-life for exponential decay in days
        """
        self.half_life_days = half_life_days
    
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        """
        Calculate time decay attribution.
        
        Args:
            journey: Customer journey containing touchpoints
            
        Returns:
            Dictionary mapping channel names to attribution credit
        """
        if not journey.touchpoints:
            return {}
        
        # Find conversion time (latest touchpoint)
        conversion_time = max(tp.timestamp for tp in journey.touchpoints)
        total_weight = 0.0
        weights = {}
        
        # Calculate weights for each touchpoint
        for i, touchpoint in enumerate(journey.touchpoints):
            days_before_conversion = (conversion_time - touchpoint.timestamp).days
            weight = 2 ** (-days_before_conversion / self.half_life_days)
            weights[i] = weight
            total_weight += weight
        
        # Calculate attribution
        attribution = {}
        for i, touchpoint in enumerate(journey.touchpoints):
            weight = weights[i]
            credit = weight / total_weight
            if touchpoint.channel in attribution:
                attribution[touchpoint.channel] += credit
            else:
                attribution[touchpoint.channel] = credit
        
        return attribution
