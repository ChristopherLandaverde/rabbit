"""Build customer journeys from resolved identities."""

from typing import List, Dict
import pandas as pd
from datetime import datetime
from ...models.touchpoint import Touchpoint, CustomerJourney
from ...models.enums import EventType


class JourneyBuilder:
    """Builds customer journeys from touchpoint data."""
    
    def __init__(self):
        self.conversion_events = {EventType.CONVERSION, EventType.PURCHASE}
    
    def build_journeys(
        self, 
        df: pd.DataFrame, 
        identity_map: Dict[str, List[int]]
    ) -> List[CustomerJourney]:
        """Build customer journeys from identity mapping."""
        journeys = []
        
        for identity_key, row_indices in identity_map.items():
            # Get touchpoints for this identity
            journey_df = df.iloc[row_indices].copy()
            
            # Sort by timestamp
            journey_df = journey_df.sort_values('timestamp')
            
            # Convert to Touchpoint objects
            touchpoints = self._create_touchpoints(journey_df)
            
            # Calculate journey metrics
            total_conversions = self._count_conversions(touchpoints)
            total_revenue = self._calculate_revenue(touchpoints)
            
            # Create journey
            journey = CustomerJourney(
                touchpoints=touchpoints,
                total_conversions=total_conversions,
                total_revenue=total_revenue,
                journey_id=identity_key
            )
            
            journeys.append(journey)
        
        return journeys
    
    def _create_touchpoints(self, journey_df: pd.DataFrame) -> List[Touchpoint]:
        """Convert DataFrame rows to Touchpoint objects."""
        touchpoints = []
        
        for _, row in journey_df.iterrows():
            touchpoint = Touchpoint(
                timestamp=pd.to_datetime(row['timestamp']),
                channel=row['channel'],
                event_type=EventType(row['event_type']),
                customer_id=row.get('customer_id'),
                session_id=row.get('session_id'),
                email=row.get('email'),
                campaign_id=row.get('campaign_id'),
                creative_id=row.get('creative_id'),
                cost=row.get('cost'),
                conversion_value=row.get('conversion_value')
            )
            touchpoints.append(touchpoint)
        
        return touchpoints
    
    def _count_conversions(self, touchpoints: List[Touchpoint]) -> int:
        """Count total conversions in a journey."""
        return sum(1 for tp in touchpoints if tp.event_type in self.conversion_events)
    
    def _calculate_revenue(self, touchpoints: List[Touchpoint]) -> float:
        """Calculate total revenue from conversions."""
        total_revenue = 0.0
        
        for tp in touchpoints:
            if tp.event_type in self.conversion_events and tp.conversion_value:
                total_revenue += tp.conversion_value
        
        return total_revenue
