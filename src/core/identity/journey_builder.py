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
        
        # Check if we have any valid identities
        if not identity_map:
            return journeys
        
        for identity_key, row_indices in identity_map.items():
            try:
                # Filter out invalid indices
                valid_indices = [idx for idx in row_indices if 0 <= idx < len(df)]
                
                if not valid_indices:
                    print(f"Skipping {identity_key}: no valid indices")
                    continue
                
                # Get touchpoints for this identity
                journey_df = df.iloc[valid_indices].copy()
            except Exception as e:
                print(f"Error processing identity {identity_key}: {e}")
                print(f"DF length: {len(df)}, indices: {row_indices}")
                continue
            
            # Check if we have timestamp column and data
            if 'timestamp' not in journey_df.columns or len(journey_df) == 0:
                continue
            
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
        
        for idx, row in journey_df.iterrows():
            try:
                # Handle event type conversion with fallback
                try:
                    event_type = EventType(row['event_type'].lower())
                except (ValueError, AttributeError, KeyError):
                    # Map common variations to known types
                    event_type_map = {
                        'impression': EventType.VIEW,
                        'view': EventType.VIEW,
                        'visit': EventType.VIEW,
                        'pageview': EventType.VIEW,
                        'click': EventType.CLICK,
                        'ctr': EventType.CLICK,
                        'conversion': EventType.CONVERSION,
                        'convert': EventType.CONVERSION,
                        'sale': EventType.CONVERSION,
                        'purchase': EventType.PURCHASE,
                        'buy': EventType.PURCHASE,
                        'signup': EventType.SIGNUP,
                        'register': EventType.SIGNUP,
                    }
                    event_lower = str(row.get('event_type', 'view')).lower()
                    event_type = event_type_map.get(event_lower, EventType.VIEW)
                
                # Helper function to handle NaN values
                def safe_value(val):
                    if pd.isna(val) or val == 'nan' or val == 'NaN':
                        return None
                    return val
                
                touchpoint = Touchpoint(
                    timestamp=pd.to_datetime(row['timestamp']),
                    channel=str(row['channel']),
                    event_type=event_type,
                    customer_id=safe_value(row.get('customer_id')),
                    session_id=safe_value(row.get('session_id')),
                    email=safe_value(row.get('email')),
                    campaign_id=safe_value(row.get('campaign_id')),
                    creative_id=safe_value(row.get('creative_id')),
                    cost=safe_value(row.get('cost')),
                    conversion_value=safe_value(row.get('conversion_value'))
                )
                touchpoints.append(touchpoint)
            except Exception as e:
                print(f"Error creating touchpoint at index {idx}: {e}")
                continue
        
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
