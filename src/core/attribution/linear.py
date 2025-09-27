"""Linear attribution model implementation."""

from typing import Dict
from .base import AttributionModel
from ...models.touchpoint import CustomerJourney


class LinearAttributionModel(AttributionModel):
    """Linear attribution model - equal credit to all touchpoints."""
    
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        """
        Calculate linear attribution - equal credit distribution.
        
        Args:
            journey: Customer journey containing touchpoints
            
        Returns:
            Dictionary mapping channel names to attribution credit
        """
        if not journey.touchpoints:
            return {}
        
        # Equal credit distribution
        credit_per_touchpoint = 1.0 / len(journey.touchpoints)
        attribution = {}
        
        for touchpoint in journey.touchpoints:
            if touchpoint.channel in attribution:
                attribution[touchpoint.channel] += credit_per_touchpoint
            else:
                attribution[touchpoint.channel] = credit_per_touchpoint
        
        return attribution
