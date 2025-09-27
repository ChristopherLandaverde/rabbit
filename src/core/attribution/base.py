"""Base attribution model abstract class."""

from abc import ABC, abstractmethod
from typing import Dict
from ...models.touchpoint import CustomerJourney


class AttributionModel(ABC):
    """Abstract base class for attribution models."""
    
    @abstractmethod
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        """
        Calculate attribution credit for each channel in a customer journey.
        
        Args:
            journey: Customer journey containing touchpoints
            
        Returns:
            Dictionary mapping channel names to attribution credit
        """
        pass
    
    def calculate_journey_attribution(self, journeys: list[CustomerJourney]) -> Dict[str, float]:
        """
        Calculate aggregate attribution across multiple journeys.
        
        Args:
            journeys: List of customer journeys
            
        Returns:
            Dictionary mapping channel names to total attribution credit
        """
        total_attribution = {}
        
        for journey in journeys:
            journey_attribution = self.calculate_attribution(journey)
            
            for channel, credit in journey_attribution.items():
                if channel in total_attribution:
                    total_attribution[channel] += credit
                else:
                    total_attribution[channel] = credit
        
        return total_attribution
