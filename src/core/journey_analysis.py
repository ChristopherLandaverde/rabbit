"""Journey analysis features for customer path insights."""

from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter


class JourneyAnalyzer:
    """Analyzes customer journeys for insights and patterns."""
    
    def __init__(self):
        self.conversion_events = ['conversion', 'purchase', 'signup', 'subscribe']
    
    def analyze_journey_lengths(self, df: pd.DataFrame, customer_id_col: str = 'customer_id') -> Dict[str, Any]:
        """
        Analyze distribution of customer journey lengths.
        
        Args:
            df: Input data with customer journeys
            customer_id_col: Column name for customer ID
            
        Returns:
            Journey length analysis results
        """
        if customer_id_col not in df.columns:
            return {
                'average_length': 0,
                'median_length': 0,
                'length_distribution': {},
                'insights': ['No customer ID column found for journey analysis']
            }
        
        # Group by customer and count touchpoints
        journey_lengths = df.groupby(customer_id_col).size()
        
        if len(journey_lengths) == 0:
            return {
                'average_length': 0,
                'median_length': 0,
                'length_distribution': {},
                'insights': ['No customer journeys found']
            }
        
        # Calculate statistics
        avg_length = journey_lengths.mean()
        median_length = journey_lengths.median()
        
        # Create length distribution
        length_distribution = {
            '1_touchpoint': len(journey_lengths[journey_lengths == 1]),
            '2_touchpoints': len(journey_lengths[journey_lengths == 2]),
            '3_5_touchpoints': len(journey_lengths[(journey_lengths >= 3) & (journey_lengths <= 5)]),
            '6_10_touchpoints': len(journey_lengths[(journey_lengths >= 6) & (journey_lengths <= 10)]),
            '11_plus_touchpoints': len(journey_lengths[journey_lengths > 10])
        }
        
        # Generate insights
        insights = []
        if avg_length < 2:
            insights.append("Most customers have very short journeys - consider improving engagement")
        elif avg_length > 5:
            insights.append("Customers have long consideration periods - focus on nurturing campaigns")
        
        if length_distribution['1_touchpoint'] > len(journey_lengths) * 0.5:
            insights.append("High percentage of single-touch conversions - strong direct response")
        
        return {
            'average_length': float(avg_length),
            'median_length': float(median_length),
            'length_distribution': length_distribution,
            'insights': insights
        }
    
    def analyze_conversion_paths(self, df: pd.DataFrame, customer_id_col: str = 'customer_id') -> Dict[str, Any]:
        """
        Analyze most common conversion paths.
        
        Args:
            df: Input data with customer journeys
            customer_id_col: Column name for customer ID
            
        Returns:
            Conversion path analysis results
        """
        if customer_id_col not in df.columns:
            return {
                'top_paths': [],
                'conversion_rate_by_path': {},
                'insights': ['No customer ID column found for path analysis']
            }
        
        # Get conversion journeys only
        # Handle conversion event matching more safely
        try:
            # Convert event_type values to lowercase strings for comparison
            event_types_str = df['event_type'].astype(str).str.lower()
            is_conversion = event_types_str.isin([e.lower() for e in self.conversion_events])
            conversion_journeys = df[is_conversion]
        except:
            # Fallback: skip this analysis if we can't determine conversions
            conversion_journeys = df.iloc[0:0]  # Empty dataframe
        
        if len(conversion_journeys) == 0:
            return {
                'top_paths': [],
                'conversion_rate_by_path': {},
                'insights': ['No conversion events found']
            }
        
        # Get unique customers who converted
        converting_customers = conversion_journeys[customer_id_col].unique()
        
        # Build paths for converting customers
        paths = []
        for customer in converting_customers:
            customer_data = df[df[customer_id_col] == customer].sort_values('timestamp')
            path = ' -> '.join(customer_data['channel'].tolist())
            paths.append(path)
        
        # Count path frequencies
        path_counts = Counter(paths)
        total_conversions = len(paths)
        
        # Get top paths
        top_paths = [
            {
                'path': path,
                'frequency': count,
                'percentage': (count / total_conversions) * 100
            }
            for path, count in path_counts.most_common(10)
        ]
        
        # Calculate conversion rates by path length
        conversion_rate_by_path = {}
        for path_info in top_paths:
            path_length = len(path_info['path'].split(' -> '))
            if path_length not in conversion_rate_by_path:
                conversion_rate_by_path[path_length] = 0
            conversion_rate_by_path[path_length] += path_info['frequency']
        
        # Generate insights
        insights = []
        if top_paths:
            most_common_path = top_paths[0]
            insights.append(f"Most common path: {most_common_path['path']} ({most_common_path['percentage']:.1f}% of conversions)")
            
            # Check for direct conversions
            direct_conversions = sum(1 for path in paths if ' -> ' not in path)
            if direct_conversions > total_conversions * 0.3:
                insights.append("High percentage of direct conversions - strong brand recognition")
        
        return {
            'top_paths': top_paths,
            'conversion_rate_by_path': conversion_rate_by_path,
            'insights': insights
        }
    
    def analyze_time_to_conversion(self, df: pd.DataFrame, customer_id_col: str = 'customer_id') -> Dict[str, Any]:
        """
        Analyze time patterns in customer journeys.
        
        Args:
            df: Input data with customer journeys
            customer_id_col: Column name for customer ID
            
        Returns:
            Time to conversion analysis results
        """
        if customer_id_col not in df.columns:
            return {
                'average_time_to_conversion': 0,
                'median_time_to_conversion': 0,
                'time_distribution': {},
                'insights': ['No customer ID column found for time analysis']
            }
        
        # Get conversion journeys
        try:
            # Convert event_type values to lowercase strings for comparison
            event_types_str = df['event_type'].astype(str).str.lower()
            is_conversion = event_types_str.isin([e.lower() for e in self.conversion_events])
            conversion_journeys = df[is_conversion]
        except:
            conversion_journeys = df.iloc[0:0]  # Empty dataframe
        
        if len(conversion_journeys) == 0:
            return {
                'average_time_to_conversion': 0,
                'median_time_to_conversion': 0,
                'time_distribution': {},
                'insights': ['No conversion events found']
            }
        
        # Calculate time to conversion for each customer
        time_to_conversion = []
        for customer in conversion_journeys[customer_id_col].unique():
            customer_data = df[df[customer_id_col] == customer].sort_values('timestamp')
            
            # Check if we have data for this customer
            if len(customer_data) == 0:
                continue
            
            # Find first touchpoint and conversion
            first_touch = customer_data.iloc[0]['timestamp']
            
            # Find conversion events in this customer's journey
            customer_conversions = customer_data[customer_data['event_type'].astype(str).str.lower().isin([e.lower() for e in self.conversion_events])]
            if len(customer_conversions) == 0:
                continue
                
            conversion_touch = customer_conversions.iloc[0]['timestamp']
            
            # Calculate days between first touch and conversion
            days_diff = (conversion_touch - first_touch).days
            time_to_conversion.append(days_diff)
        
        if not time_to_conversion:
            return {
                'average_time_to_conversion': 0,
                'median_time_to_conversion': 0,
                'time_distribution': {},
                'insights': ['No valid time calculations found']
            }
        
        # Calculate statistics
        avg_time = np.mean(time_to_conversion)
        median_time = np.median(time_to_conversion)
        
        # Create time distribution
        time_distribution = {
            'same_day': len([t for t in time_to_conversion if t == 0]),
            '1_7_days': len([t for t in time_to_conversion if 1 <= t <= 7]),
            '8_30_days': len([t for t in time_to_conversion if 8 <= t <= 30]),
            '31_90_days': len([t for t in time_to_conversion if 31 <= t <= 90]),
            '90_plus_days': len([t for t in time_to_conversion if t > 90])
        }
        
        # Generate insights
        insights = []
        if avg_time < 1:
            insights.append("Very quick conversions - customers make fast decisions")
        elif avg_time > 30:
            insights.append("Long consideration periods - focus on nurturing campaigns")
        
        if time_distribution['same_day'] > len(time_to_conversion) * 0.5:
            insights.append("High percentage of same-day conversions - strong immediate impact")
        
        return {
            'average_time_to_conversion': float(avg_time),
            'median_time_to_conversion': float(median_time),
            'time_distribution': time_distribution,
            'insights': insights
        }
    
    def generate_journey_insights(
        self,
        df: pd.DataFrame,
        attribution_results: Dict[str, float],
        customer_id_col: str = 'customer_id'
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive journey insights.
        
        Args:
            df: Input data
            attribution_results: Attribution results by channel
            customer_id_col: Column name for customer ID
            
        Returns:
            List of journey insights
        """
        insights = []
        
        # Analyze journey lengths
        length_analysis = self.analyze_journey_lengths(df, customer_id_col)
        if length_analysis['average_length'] > 0:
            insights.append({
                'type': 'journey_length',
                'title': 'Customer Journey Length Analysis',
                'description': f"Average journey length: {length_analysis['average_length']:.1f} touchpoints",
                'impact_score': 0.7,
                'recommendation': 'Optimize touchpoint sequence based on journey length patterns'
            })
        
        # Analyze conversion paths
        path_analysis = self.analyze_conversion_paths(df, customer_id_col)
        if path_analysis['top_paths']:
            top_path = path_analysis['top_paths'][0]
            insights.append({
                'type': 'conversion_path',
                'title': 'Most Effective Conversion Path',
                'description': f"Top path: {top_path['path']} ({top_path['percentage']:.1f}% of conversions)",
                'impact_score': 0.8,
                'recommendation': 'Replicate successful path patterns in future campaigns'
            })
        
        # Analyze time to conversion
        time_analysis = self.analyze_time_to_conversion(df, customer_id_col)
        if time_analysis['average_time_to_conversion'] > 0:
            insights.append({
                'type': 'conversion_timing',
                'title': 'Conversion Timing Analysis',
                'description': f"Average time to conversion: {time_analysis['average_time_to_conversion']:.1f} days",
                'impact_score': 0.6,
                'recommendation': 'Adjust campaign timing based on conversion patterns'
            })
        
        # Channel performance insights
        if attribution_results:
            top_channel = max(attribution_results.items(), key=lambda x: x[1])
            insights.append({
                'type': 'channel_performance',
                'title': 'Top Performing Channel',
                'description': f"Best performing channel: {top_channel[0]} ({top_channel[1]:.1%} attribution)",
                'impact_score': 0.9,
                'recommendation': f'Increase investment in {top_channel[0]} channel'
            })
        
        return insights
