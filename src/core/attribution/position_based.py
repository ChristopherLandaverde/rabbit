"""Position-based attribution model implementation."""

from typing import Dict
from .base import AttributionModel
from ...models.touchpoint import CustomerJourney


class PositionBasedAttributionModel(AttributionModel):
    """Position-based attribution model - weighted credit by position."""
    
    def __init__(self, first_touch_weight: float = 0.4, last_touch_weight: float = 0.4):
        """
        Initialize position-based model.
        
        Args:
            first_touch_weight: Weight for first touchpoint (default 40%)
            last_touch_weight: Weight for last touchpoint (default 40%)
        """
        self.first_touch_weight = first_touch_weight
        self.last_touch_weight = last_touch_weight
        self.middle_touch_weight = 1.0 - first_touch_weight - last_touch_weight
    
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        """
        Calculate position-based attribution.
        
        Args:
            journey: Customer journey containing touchpoints
            
        Returns:
            Dictionary mapping channel names to attribution credit
        """
        if not journey.touchpoints:
            return {}
        
        attribution = {}
        num_touchpoints = len(journey.touchpoints)
        
        if num_touchpoints == 1:
            # Single touchpoint gets all credit
            attribution[journey.touchpoints[0].channel] = 1.0
        elif num_touchpoints == 2:
            # With 2 touchpoints, first and last split evenly
            # Each gets first_touch_weight + (middle_touch_weight / 2)
            credit_per_position = self.first_touch_weight + (self.middle_touch_weight / 2)
            attribution[journey.touchpoints[0].channel] = credit_per_position
            attribution[journey.touchpoints[1].channel] = credit_per_position
        else:
            # First touchpoint
            first_channel = journey.touchpoints[0].channel
            attribution[first_channel] = self.first_touch_weight
            
            # Last touchpoint
            last_channel = journey.touchpoints[-1].channel
            if last_channel in attribution:
                attribution[last_channel] += self.last_touch_weight
            else:
                attribution[last_channel] = self.last_touch_weight
            
            # Middle touchpoints (if any)
            if num_touchpoints > 2:
                middle_credit = self.middle_touch_weight / (num_touchpoints - 2)
                for touchpoint in journey.touchpoints[1:-1]:
                    if touchpoint.channel in attribution:
                        attribution[touchpoint.channel] += middle_credit
                    else:
                        attribution[touchpoint.channel] = middle_credit
        
        return attribution
