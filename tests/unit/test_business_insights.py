"""Tests for business insights generation."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.business_insights import BusinessInsightsGenerator


class TestBusinessInsightsGenerator:
    """Test cases for BusinessInsightsGenerator class."""
    
    @pytest.fixture
    def insights_generator(self):
        """Create BusinessInsightsGenerator instance for testing."""
        return BusinessInsightsGenerator()
    
    @pytest.fixture
    def sample_attribution_results(self):
        """Create sample attribution results for testing."""
        return {
            'email': 0.4,
            'social': 0.3,
            'paid': 0.2,
            'organic': 0.1
        }
    
    @pytest.fixture
    def sample_channel_data(self):
        """Create sample channel data for testing."""
        return {
            'email': pd.DataFrame({
                'customer_id': ['C1', 'C2', 'C3'],
                'channel': ['email', 'email', 'email'],
                'event_type': ['touchpoint', 'touchpoint', 'conversion'],
                'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
            }),
            'social': pd.DataFrame({
                'customer_id': ['C1', 'C2'],
                'channel': ['social', 'social'],
                'event_type': ['touchpoint', 'conversion'],
                'timestamp': [datetime.now() - timedelta(days=i) for i in range(2)]
            })
        }
    
    @pytest.fixture
    def sample_journey_analysis(self):
        """Create sample journey analysis results."""
        return {
            'average_length': 3.5,
            'median_length': 3.0,
            'length_distribution': {
                '1_touchpoint': 10,
                '2_touchpoints': 20,
                '3_5_touchpoints': 30,
                '6_10_touchpoints': 15,
                '11_plus_touchpoints': 5
            },
            'top_paths': [
                {
                    'path': 'email -> social -> paid',
                    'frequency': 15,
                    'percentage': 30.0
                },
                {
                    'path': 'direct',
                    'frequency': 10,
                    'percentage': 20.0
                }
            ],
            'average_time_to_conversion': 7.5,
            'time_distribution': {
                'same_day': 5,
                '1_7_days': 20,
                '8_30_days': 15,
                '31_90_days': 8,
                '90_plus_days': 2
            }
        }
    
    @pytest.fixture
    def sample_data_quality(self):
        """Create sample data quality metrics."""
        return {
            'completeness': 0.95,
            'consistency': 0.90,
            'freshness': 0.85
        }
    
    def test_generate_performance_insights_basic(self, insights_generator, sample_attribution_results, sample_channel_data):
        """Test basic performance insights generation."""
        insights = insights_generator.generate_performance_insights(
            sample_attribution_results, sample_channel_data
        )
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        for insight in insights:
            assert 'type' in insight
            assert 'category' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
            assert 'priority' in insight
            
            assert insight['type'] == 'performance'
            assert insight['category'] == 'performance'
            assert 0.0 <= insight['impact_score'] <= 1.0
            assert insight['priority'] in ['high', 'medium', 'low']
    
    def test_generate_performance_insights_empty_attribution(self, insights_generator, sample_channel_data):
        """Test performance insights generation with empty attribution results."""
        insights = insights_generator.generate_performance_insights({}, sample_channel_data)
        
        assert isinstance(insights, list)
        assert len(insights) == 0
    
    def test_generate_performance_insights_high_performer(self, insights_generator, sample_channel_data):
        """Test performance insights generation with high performing channel."""
        high_performer_results = {
            'email': 0.6,  # High attribution
            'social': 0.2,
            'paid': 0.1,
            'organic': 0.1
        }
        
        insights = insights_generator.generate_performance_insights(
            high_performer_results, sample_channel_data
        )
        
        # Should generate high performer insight
        high_performer_insights = [i for i in insights if 'Top Performing Channel' in i['title']]
        assert len(high_performer_insights) > 0
        assert high_performer_insights[0]['priority'] == 'high'
    
    def test_generate_performance_insights_underperformer(self, insights_generator, sample_channel_data):
        """Test performance insights generation with underperforming channel."""
        underperformer_results = {
            'email': 0.4,
            'social': 0.3,
            'paid': 0.2,
            'organic': 0.05  # Low attribution
        }
        
        insights = insights_generator.generate_performance_insights(
            underperformer_results, sample_channel_data
        )
        
        # Should generate underperformer insight
        underperformer_insights = [i for i in insights if 'Underperforming Channel' in i['title']]
        assert len(underperformer_insights) > 0
        assert underperformer_insights[0]['priority'] == 'medium'
    
    def test_generate_performance_insights_imbalanced(self, insights_generator, sample_channel_data):
        """Test performance insights generation with imbalanced performance."""
        imbalanced_results = {
            'email': 0.8,  # Very high
            'social': 0.1,
            'paid': 0.05,
            'organic': 0.05
        }
        
        insights = insights_generator.generate_performance_insights(
            imbalanced_results, sample_channel_data
        )
        
        # Should generate imbalance insight
        imbalance_insights = [i for i in insights if 'imbalance' in i['title'].lower()]
        assert len(imbalance_insights) > 0
    
    def test_generate_budget_allocation_insights_basic(self, insights_generator, sample_attribution_results):
        """Test basic budget allocation insights generation."""
        insights = insights_generator.generate_budget_allocation_insights(sample_attribution_results)
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        for insight in insights:
            assert 'type' in insight
            assert 'category' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
            assert 'priority' in insight
            
            assert insight['type'] == 'budget_allocation'
            assert insight['category'] == 'budget_allocation'
            assert 0.0 <= insight['impact_score'] <= 1.0
            assert insight['priority'] in ['high', 'medium', 'low']
    
    def test_generate_budget_allocation_insights_empty_attribution(self, insights_generator):
        """Test budget allocation insights generation with empty attribution results."""
        insights = insights_generator.generate_budget_allocation_insights({})
        
        assert isinstance(insights, list)
        assert len(insights) == 0
    
    def test_generate_budget_allocation_insights_zero_total(self, insights_generator):
        """Test budget allocation insights generation with zero total attribution."""
        zero_results = {'email': 0.0, 'social': 0.0}
        
        insights = insights_generator.generate_budget_allocation_insights(zero_results)
        
        assert isinstance(insights, list)
        assert len(insights) == 0
    
    def test_generate_budget_allocation_insights_high_roi(self, insights_generator):
        """Test budget allocation insights generation with high ROI opportunity."""
        high_roi_results = {
            'email': 0.5,  # Very high attribution
            'social': 0.3,
            'paid': 0.2
        }
        
        insights = insights_generator.generate_budget_allocation_insights(high_roi_results)
        
        # Should generate high ROI insight
        roi_insights = [i for i in insights if 'High ROI Opportunity' in i['title']]
        assert len(roi_insights) > 0
        assert roi_insights[0]['priority'] == 'high'
    
    def test_generate_budget_allocation_insights_diversification(self, insights_generator):
        """Test budget allocation insights generation with limited diversification."""
        limited_diversity_results = {
            'email': 0.6,
            'social': 0.4
        }
        
        insights = insights_generator.generate_budget_allocation_insights(limited_diversity_results)
        
        # Should generate diversification insight
        diversification_insights = [i for i in insights if 'diversification' in i['title'].lower()]
        assert len(diversification_insights) > 0
        assert diversification_insights[0]['priority'] == 'low'
    
    def test_generate_journey_optimization_insights_basic(self, insights_generator, sample_attribution_results):
        """Test basic journey optimization insights generation."""
        # Use journey analysis data that will generate insights
        journey_analysis_with_insights = {
            'average_length': 6.0,  # Long journeys to trigger insights
            'top_paths': [
                {
                    'path': 'email -> social -> paid',
                    'frequency': 15,
                    'percentage': 35.0  # Dominant path to trigger insights
                }
            ],
            'average_time_to_conversion': 45.0  # Long conversion time to trigger insights
        }
        
        insights = insights_generator.generate_journey_optimization_insights(
            journey_analysis_with_insights, sample_attribution_results
        )
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        for insight in insights:
            assert 'type' in insight
            assert 'category' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
            assert 'priority' in insight
            
            assert insight['type'] == 'journey_optimization'
            assert insight['category'] == 'journey_optimization'
            assert 0.0 <= insight['impact_score'] <= 1.0
            assert insight['priority'] in ['high', 'medium', 'low']
    
    def test_generate_journey_optimization_insights_short_journeys(self, insights_generator, sample_attribution_results):
        """Test journey optimization insights generation with short journeys."""
        short_journey_analysis = {
            'average_length': 1.5,  # Short journeys
            'top_paths': [{'path': 'direct', 'percentage': 60.0}],
            'average_time_to_conversion': 0.5
        }
        
        insights = insights_generator.generate_journey_optimization_insights(
            short_journey_analysis, sample_attribution_results
        )
        
        # Should generate short journey insight
        short_journey_insights = [i for i in insights if 'short' in i['title'].lower()]
        assert len(short_journey_insights) > 0
    
    def test_generate_journey_optimization_insights_long_journeys(self, insights_generator, sample_attribution_results):
        """Test journey optimization insights generation with long journeys."""
        long_journey_analysis = {
            'average_length': 8.0,  # Long journeys
            'top_paths': [{'path': 'email -> social -> paid -> organic', 'percentage': 40.0}],
            'average_time_to_conversion': 45.0
        }
        
        insights = insights_generator.generate_journey_optimization_insights(
            long_journey_analysis, sample_attribution_results
        )
        
        # Should generate long journey insight
        long_journey_insights = [i for i in insights if 'long' in i['title'].lower()]
        assert len(long_journey_insights) > 0
    
    def test_generate_journey_optimization_insights_dominant_path(self, insights_generator, sample_attribution_results):
        """Test journey optimization insights generation with dominant conversion path."""
        dominant_path_analysis = {
            'average_length': 3.0,
            'top_paths': [{'path': 'email -> social -> paid', 'percentage': 65.0}],  # Dominant path
            'average_time_to_conversion': 5.0
        }
        
        insights = insights_generator.generate_journey_optimization_insights(
            dominant_path_analysis, sample_attribution_results
        )
        
        # Should generate dominant path insight
        dominant_path_insights = [i for i in insights if 'dominant' in i['title'].lower()]
        assert len(dominant_path_insights) > 0
        assert dominant_path_insights[0]['priority'] == 'high'
    
    def test_generate_journey_optimization_insights_quick_conversions(self, insights_generator, sample_attribution_results):
        """Test journey optimization insights generation with quick conversions."""
        quick_conversion_analysis = {
            'average_length': 2.0,
            'top_paths': [{'path': 'direct', 'percentage': 50.0}],
            'average_time_to_conversion': 0.5  # Very quick
        }
        
        insights = insights_generator.generate_journey_optimization_insights(
            quick_conversion_analysis, sample_attribution_results
        )
        
        # Should generate quick conversion insight
        quick_conversion_insights = [i for i in insights if 'quick' in i['title'].lower()]
        assert len(quick_conversion_insights) > 0
    
    def test_generate_journey_optimization_insights_long_conversions(self, insights_generator, sample_attribution_results):
        """Test journey optimization insights generation with long conversion cycles."""
        long_conversion_analysis = {
            'average_length': 4.0,
            'top_paths': [{'path': 'email -> social -> paid -> organic', 'percentage': 30.0}],
            'average_time_to_conversion': 45.0  # Long conversion cycle
        }
        
        insights = insights_generator.generate_journey_optimization_insights(
            long_conversion_analysis, sample_attribution_results
        )
        
        # Should generate long conversion cycle insight
        long_conversion_insights = [i for i in insights if 'long' in i['title'].lower() and 'cycle' in i['title'].lower()]
        assert len(long_conversion_insights) > 0
    
    def test_generate_data_quality_insights_basic(self, insights_generator, sample_data_quality):
        """Test basic data quality insights generation."""
        insights = insights_generator.generate_data_quality_insights(sample_data_quality, 1000)
        
        assert isinstance(insights, list)
        # Should generate some insights for good data quality
        
        for insight in insights:
            assert 'type' in insight
            assert 'category' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
            assert 'priority' in insight
            
            assert insight['type'] == 'data_quality'
            assert insight['category'] == 'data_quality'
            assert 0.0 <= insight['impact_score'] <= 1.0
            assert insight['priority'] in ['high', 'medium', 'low']
    
    def test_generate_data_quality_insights_small_sample(self, insights_generator, sample_data_quality):
        """Test data quality insights generation with small sample size."""
        insights = insights_generator.generate_data_quality_insights(sample_data_quality, 50)
        
        # Should generate small sample size insight
        small_sample_insights = [i for i in insights if 'small sample' in i['title'].lower()]
        assert len(small_sample_insights) > 0
        assert small_sample_insights[0]['priority'] == 'high'
    
    def test_generate_data_quality_insights_large_sample(self, insights_generator, sample_data_quality):
        """Test data quality insights generation with large sample size."""
        insights = insights_generator.generate_data_quality_insights(sample_data_quality, 15000)
        
        # Should generate large dataset insight
        large_dataset_insights = [i for i in insights if 'large dataset' in i['title'].lower()]
        assert len(large_dataset_insights) > 0
        assert large_dataset_insights[0]['priority'] == 'low'
    
    def test_generate_data_quality_insights_poor_completeness(self, insights_generator):
        """Test data quality insights generation with poor data completeness."""
        poor_quality = {
            'completeness': 0.6,  # Poor completeness
            'consistency': 0.9,
            'freshness': 0.8
        }
        
        insights = insights_generator.generate_data_quality_insights(poor_quality, 1000)
        
        # Should generate completeness insight
        completeness_insights = [i for i in insights if 'completeness' in i['title'].lower()]
        assert len(completeness_insights) > 0
        assert completeness_insights[0]['priority'] == 'medium'
    
    def test_generate_data_quality_insights_poor_consistency(self, insights_generator):
        """Test data quality insights generation with poor data consistency."""
        poor_quality = {
            'completeness': 0.9,
            'consistency': 0.6,  # Poor consistency
            'freshness': 0.8
        }
        
        insights = insights_generator.generate_data_quality_insights(poor_quality, 1000)
        
        # Should generate consistency insight
        consistency_insights = [i for i in insights if 'consistency' in i['title'].lower()]
        assert len(consistency_insights) > 0
        assert consistency_insights[0]['priority'] == 'medium'
    
    def test_generate_data_quality_insights_stale_data(self, insights_generator):
        """Test data quality insights generation with stale data."""
        stale_quality = {
            'completeness': 0.9,
            'consistency': 0.9,
            'freshness': 0.3  # Stale data
        }
        
        insights = insights_generator.generate_data_quality_insights(stale_quality, 1000)
        
        # Should generate stale data insight
        stale_data_insights = [i for i in insights if 'stale' in i['title'].lower()]
        assert len(stale_data_insights) > 0
        assert stale_data_insights[0]['priority'] == 'high'
    
    def test_generate_comprehensive_insights_basic(self, insights_generator, sample_attribution_results, sample_journey_analysis, sample_data_quality, sample_channel_data):
        """Test comprehensive insights generation."""
        insights = insights_generator.generate_comprehensive_insights(
            attribution_results=sample_attribution_results,
            journey_analysis=sample_journey_analysis,
            data_quality=sample_data_quality,
            sample_size=1000,
            channel_data=sample_channel_data
        )
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Should have insights from all categories
        categories = set(insight['category'] for insight in insights)
        expected_categories = {'performance', 'budget_allocation', 'journey_optimization', 'data_quality'}
        assert categories.intersection(expected_categories)
        
        # Should be sorted by priority and impact score
        for i in range(len(insights) - 1):
            current = insights[i]
            next_insight = insights[i + 1]
            
            # Higher priority should come first
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            current_priority = priority_order.get(current.get('priority', 'low'), 1)
            next_priority = priority_order.get(next_insight.get('priority', 'low'), 1)
            
            if current_priority > next_priority:
                continue  # Higher priority comes first
            elif current_priority == next_priority:
                # Same priority, higher impact score should come first
                assert current.get('impact_score', 0) >= next_insight.get('impact_score', 0)
    
    def test_generate_comprehensive_insights_empty_data(self, insights_generator):
        """Test comprehensive insights generation with empty data."""
        insights = insights_generator.generate_comprehensive_insights(
            attribution_results={},
            journey_analysis={},
            data_quality={},
            sample_size=0
        )
        
        assert isinstance(insights, list)
        # Should still generate some insights even with empty data
    
    def test_insights_generator_categories(self, insights_generator):
        """Test that insight categories are properly configured."""
        expected_categories = ['performance', 'budget_allocation', 'journey_optimization', 'data_quality']
        assert insights_generator.insight_categories == expected_categories
    
    def test_generate_insights_with_real_world_scenario(self, insights_generator):
        """Test insights generation with realistic e-commerce scenario."""
        # Create realistic attribution results
        attribution_results = {
            'email': 0.35,
            'social': 0.25,
            'paid_search': 0.20,
            'organic': 0.15,
            'affiliate': 0.05
        }
        
        # Create realistic journey analysis
        journey_analysis = {
            'average_length': 4.2,
            'median_length': 3.0,
            'length_distribution': {
                '1_touchpoint': 15,
                '2_touchpoints': 25,
                '3_5_touchpoints': 35,
                '6_10_touchpoints': 20,
                '11_plus_touchpoints': 5
            },
            'top_paths': [
                {'path': 'email -> social -> paid_search', 'frequency': 45, 'percentage': 22.5},
                {'path': 'organic -> email', 'frequency': 30, 'percentage': 15.0},
                {'path': 'direct', 'frequency': 25, 'percentage': 12.5}
            ],
            'average_time_to_conversion': 12.5,
            'time_distribution': {
                'same_day': 20,
                '1_7_days': 35,
                '8_30_days': 30,
                '31_90_days': 12,
                '90_plus_days': 3
            }
        }
        
        # Create realistic data quality
        data_quality = {
            'completeness': 0.92,
            'consistency': 0.88,
            'freshness': 0.95
        }
        
        # Generate comprehensive insights
        insights = insights_generator.generate_comprehensive_insights(
            attribution_results=attribution_results,
            journey_analysis=journey_analysis,
            data_quality=data_quality,
            sample_size=5000
        )
        
        assert len(insights) > 0
        
        # Verify insight structure
        for insight in insights:
            assert 'type' in insight
            assert 'category' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
            assert 'priority' in insight
            
            assert 0.0 <= insight['impact_score'] <= 1.0
            assert insight['priority'] in ['high', 'medium', 'low']
            assert insight['category'] in ['performance', 'budget_allocation', 'journey_optimization', 'data_quality']
        
        # Should have insights from multiple categories
        categories = set(insight['category'] for insight in insights)
        assert len(categories) > 1
