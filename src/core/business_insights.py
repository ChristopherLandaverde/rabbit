"""Business insights generation for actionable recommendations."""

from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


class BusinessInsightsGenerator:
    """Generates actionable business insights from attribution analysis."""
    
    def __init__(self):
        self.insight_categories = [
            'performance',
            'budget_allocation',
            'journey_optimization',
            'data_quality'
        ]
    
    def generate_performance_insights(
        self,
        attribution_results: Dict[str, float],
        channel_data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        Generate performance-based insights.
        
        Args:
            attribution_results: Attribution results by channel
            channel_data: Data grouped by channel
            
        Returns:
            List of performance insights
        """
        insights = []
        
        if not attribution_results:
            return insights
        
        # Find top and bottom performing channels
        sorted_channels = sorted(attribution_results.items(), key=lambda x: x[1], reverse=True)
        top_channel = sorted_channels[0]
        bottom_channel = sorted_channels[-1]
        
        # Top performer insight
        if top_channel[1] > 0.3:  # Significant attribution
            insights.append({
                'type': 'performance',
                'category': 'performance',
                'title': 'Top Performing Channel',
                'description': f"{top_channel[0]} is your best performing channel with {top_channel[1]:.1%} attribution",
                'impact_score': 0.9,
                'recommendation': f'Increase budget allocation to {top_channel[0]} by 20-30%',
                'priority': 'high'
            })
        
        # Underperformer insight
        if bottom_channel[1] < 0.1 and len(sorted_channels) > 2:  # Low attribution
            insights.append({
                'type': 'performance',
                'category': 'performance',
                'title': 'Underperforming Channel',
                'description': f"{bottom_channel[0]} shows low attribution at {bottom_channel[1]:.1%}",
                'impact_score': 0.7,
                'recommendation': f'Review {bottom_channel[0]} strategy or consider reallocating budget',
                'priority': 'medium'
            })
        
        # Channel balance insight
        attribution_values = list(attribution_results.values())
        if len(attribution_values) > 1:
            variance = np.var(attribution_values)
            if variance > 0.1:  # High variance
                insights.append({
                    'type': 'performance',
                    'category': 'performance',
                    'title': 'Channel Performance Imbalance',
                    'description': 'Significant variance in channel performance detected',
                    'impact_score': 0.6,
                    'recommendation': 'Balance channel investments or optimize underperforming channels',
                    'priority': 'medium'
                })
        
        return insights
    
    def generate_budget_allocation_insights(
        self,
        attribution_results: Dict[str, float],
        current_budget: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate budget allocation recommendations.
        
        Args:
            attribution_results: Attribution results by channel
            current_budget: Current budget allocation (optional)
            
        Returns:
            List of budget allocation insights
        """
        insights = []
        
        if not attribution_results:
            return insights
        
        # Calculate recommended budget allocation
        total_attribution = sum(attribution_results.values())
        if total_attribution == 0:
            return insights
        
        recommended_allocation = {
            channel: (attribution / total_attribution) * 100
            for channel, attribution in attribution_results.items()
        }
        
        # Budget optimization insight
        insights.append({
            'type': 'budget_allocation',
            'category': 'budget_allocation',
            'title': 'Optimal Budget Allocation',
            'description': 'Recommended budget distribution based on attribution performance',
            'impact_score': 0.8,
            'recommendation': f"Allocate budget as follows: {', '.join([f'{channel}: {allocation:.1f}%' for channel, allocation in recommended_allocation.items()])}",
            'priority': 'high'
        })
        
        # High ROI opportunity insight
        top_channel = max(attribution_results.items(), key=lambda x: x[1])
        if top_channel[1] > 0.4:  # Very high attribution
            insights.append({
                'type': 'budget_allocation',
                'category': 'budget_allocation',
                'title': 'High ROI Opportunity',
                'description': f"{top_channel[0]} shows exceptional performance with {top_channel[1]:.1%} attribution",
                'impact_score': 0.9,
                'recommendation': f'Consider increasing {top_channel[0]} budget by 50% to maximize ROI',
                'priority': 'high'
            })
        
        # Diversification insight
        if len(attribution_results) < 3:
            insights.append({
                'type': 'budget_allocation',
                'category': 'budget_allocation',
                'title': 'Channel Diversification Opportunity',
                'description': 'Limited channel diversity may increase risk',
                'impact_score': 0.5,
                'recommendation': 'Consider testing new channels to diversify attribution risk',
                'priority': 'low'
            })
        
        return insights
    
    def generate_journey_optimization_insights(
        self,
        journey_analysis: Dict[str, Any],
        attribution_results: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Generate journey optimization insights.
        
        Args:
            journey_analysis: Journey analysis results
            attribution_results: Attribution results by channel
            
        Returns:
            List of journey optimization insights
        """
        insights = []
        
        # Journey length insights
        if 'average_length' in journey_analysis and journey_analysis['average_length'] > 0:
            avg_length = journey_analysis['average_length']
            
            if avg_length < 2:
                insights.append({
                    'type': 'journey_optimization',
                    'category': 'journey_optimization',
                    'title': 'Short Customer Journeys',
                    'description': f'Average journey length is {avg_length:.1f} touchpoints - customers convert quickly',
                    'impact_score': 0.7,
                    'recommendation': 'Focus on immediate conversion optimization and reduce friction',
                    'priority': 'medium'
                })
            elif avg_length > 5:
                insights.append({
                    'type': 'journey_optimization',
                    'category': 'journey_optimization',
                    'title': 'Long Customer Journeys',
                    'description': f'Average journey length is {avg_length:.1f} touchpoints - customers need nurturing',
                    'impact_score': 0.8,
                    'recommendation': 'Implement nurturing campaigns and lead scoring to accelerate conversions',
                    'priority': 'high'
                })
        
        # Conversion path insights
        if 'top_paths' in journey_analysis and journey_analysis['top_paths']:
            top_path = journey_analysis['top_paths'][0]
            if top_path['percentage'] > 30:  # Dominant path
                insights.append({
                    'type': 'journey_optimization',
                    'category': 'journey_optimization',
                    'title': 'Dominant Conversion Path',
                    'description': f"One path accounts for {top_path['percentage']:.1f}% of conversions: {top_path['path']}",
                    'impact_score': 0.9,
                    'recommendation': 'Replicate this successful path in other campaigns and channels',
                    'priority': 'high'
                })
        
        # Time to conversion insights
        if 'average_time_to_conversion' in journey_analysis and journey_analysis['average_time_to_conversion'] > 0:
            avg_time = journey_analysis['average_time_to_conversion']
            
            if avg_time < 1:
                insights.append({
                    'type': 'journey_optimization',
                    'category': 'journey_optimization',
                    'title': 'Quick Conversion Cycles',
                    'description': f'Average time to conversion is {avg_time:.1f} days - very fast',
                    'impact_score': 0.6,
                    'recommendation': 'Optimize for immediate conversion and reduce decision friction',
                    'priority': 'medium'
                })
            elif avg_time > 30:
                insights.append({
                    'type': 'journey_optimization',
                    'category': 'journey_optimization',
                    'title': 'Long Conversion Cycles',
                    'description': f'Average time to conversion is {avg_time:.1f} days - long consideration period',
                    'impact_score': 0.8,
                    'recommendation': 'Implement lead nurturing and remarketing campaigns to accelerate conversions',
                    'priority': 'high'
                })
        
        return insights
    
    def generate_data_quality_insights(
        self,
        data_quality: Dict[str, float],
        sample_size: int
    ) -> List[Dict[str, Any]]:
        """
        Generate data quality improvement insights.
        
        Args:
            data_quality: Data quality metrics
            sample_size: Number of data points
            
        Returns:
            List of data quality insights
        """
        insights = []
        
        # Sample size insights
        if sample_size < 100:
            insights.append({
                'type': 'data_quality',
                'category': 'data_quality',
                'title': 'Small Sample Size',
                'description': f'Only {sample_size} data points - results may not be statistically significant',
                'impact_score': 0.8,
                'recommendation': 'Collect more data for more reliable attribution results',
                'priority': 'high'
            })
        elif sample_size > 10000:
            insights.append({
                'type': 'data_quality',
                'category': 'data_quality',
                'title': 'Large Dataset',
                'description': f'{sample_size} data points provide strong statistical foundation',
                'impact_score': 0.3,
                'recommendation': 'Excellent data volume for reliable attribution analysis',
                'priority': 'low'
            })
        
        # Data quality insights
        if 'completeness' in data_quality and data_quality['completeness'] < 0.8:
            insights.append({
                'type': 'data_quality',
                'category': 'data_quality',
                'title': 'Data Completeness Issues',
                'description': f'Data completeness is {data_quality["completeness"]:.1%} - missing values detected',
                'impact_score': 0.7,
                'recommendation': 'Improve data collection processes to reduce missing values',
                'priority': 'medium'
            })
        
        if 'consistency' in data_quality and data_quality['consistency'] < 0.8:
            insights.append({
                'type': 'data_quality',
                'category': 'data_quality',
                'title': 'Data Consistency Issues',
                'description': f'Data consistency is {data_quality["consistency"]:.1%} - format standardization needed',
                'impact_score': 0.6,
                'recommendation': 'Standardize data formats and implement data validation',
                'priority': 'medium'
            })
        
        if 'freshness' in data_quality and data_quality['freshness'] < 0.5:
            insights.append({
                'type': 'data_quality',
                'category': 'data_quality',
                'title': 'Stale Data',
                'description': f'Data freshness is {data_quality["freshness"]:.1%} - data may be outdated',
                'impact_score': 0.8,
                'recommendation': 'Use more recent data for current market conditions',
                'priority': 'high'
            })
        
        return insights
    
    def generate_comprehensive_insights(
        self,
        attribution_results: Dict[str, float],
        journey_analysis: Dict[str, Any],
        data_quality: Dict[str, float],
        sample_size: int,
        channel_data: Dict[str, pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive business insights.
        
        Args:
            attribution_results: Attribution results by channel
            journey_analysis: Journey analysis results
            data_quality: Data quality metrics
            sample_size: Number of data points
            channel_data: Data grouped by channel
            
        Returns:
            List of all business insights
        """
        all_insights = []
        
        # Generate insights from each category
        all_insights.extend(self.generate_performance_insights(attribution_results, channel_data or {}))
        all_insights.extend(self.generate_budget_allocation_insights(attribution_results))
        all_insights.extend(self.generate_journey_optimization_insights(journey_analysis, attribution_results))
        all_insights.extend(self.generate_data_quality_insights(data_quality, sample_size))
        
        # Sort by priority and impact score
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        all_insights.sort(
            key=lambda x: (priority_order.get(x.get('priority', 'low'), 1), x.get('impact_score', 0)),
            reverse=True
        )
        
        return all_insights
