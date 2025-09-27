"""Last touch attribution model implementation."""

from typing import Dict
from .base import AttributionModel
from ...models.touchpoint import CustomerJourney


class LastTouchAttributionModel(AttributionModel):
    """Last touch attribution model - all credit to last touchpoint."""
    
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        """
        Calculate last touch attribution.
        
        Args:
            journey: Customer journey containing touchpoints
            
        Returns:
            Dictionary mapping channel names to attribution credit
        """
        if not journey.touchpoints:
            return {}
        
        # All credit to last touchpoint
        last_touchpoint = journey.touchpoints[-1]
        return {last_touchpoint.channel: 1.0}
