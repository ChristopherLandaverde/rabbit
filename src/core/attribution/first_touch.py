"""First touch attribution model implementation."""

from typing import Dict
from .base import AttributionModel
from ...models.touchpoint import CustomerJourney


class FirstTouchAttributionModel(AttributionModel):
    """First touch attribution model - all credit to first touchpoint."""
    
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        """
        Calculate first touch attribution.
        
        Args:
            journey: Customer journey containing touchpoints
            
        Returns:
            Dictionary mapping channel names to attribution credit
        """
        if not journey.touchpoints:
            return {}
        
        # All credit to first touchpoint
        first_touchpoint = journey.touchpoints[0]
        return {first_touchpoint.channel: 1.0}
