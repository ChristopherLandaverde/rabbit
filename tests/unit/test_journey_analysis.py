"""Tests for journey analysis features."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.journey_analysis import JourneyAnalyzer


class TestJourneyAnalyzer:
    """Test cases for JourneyAnalyzer class."""
    
    @pytest.fixture
    def journey_analyzer(self):
        """Create JourneyAnalyzer instance for testing."""
        return JourneyAnalyzer()
    
    @pytest.fixture
    def sample_journey_data(self):
        """Create sample journey data for testing."""
        return pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C1', 'C2', 'C2', 'C3', 'C3', 'C3', 'C3'],
            'channel': ['email', 'social', 'paid', 'email', 'organic', 'direct', 'email', 'social', 'paid'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion', 'touchpoint', 'conversion', 'touchpoint', 'touchpoint', 'touchpoint', 'conversion'],
            'timestamp': [
                datetime.now() - timedelta(days=5),
                datetime.now() - timedelta(days=3),
                datetime.now() - timedelta(days=1),
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=1),
                datetime.now() - timedelta(days=4),
                datetime.now() - timedelta(days=3),
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=1)
            ]
        })
    
    @pytest.fixture
    def single_touchpoint_data(self):
        """Create data with single touchpoints per customer."""
        return pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'channel': ['email', 'social', 'direct'],
            'event_type': ['conversion', 'conversion', 'conversion'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
    
    @pytest.fixture
    def long_journey_data(self):
        """Create data with long customer journeys."""
        # Create data with consistent array lengths
        customer_ids = ['C1'] * 8 + ['C2'] * 6
        channels = ['email', 'social', 'paid', 'organic', 'direct', 'email', 'social', 'paid'] + ['email', 'social', 'paid', 'organic', 'direct', 'email']
        event_types = ['touchpoint'] * 13 + ['conversion'] + ['touchpoint'] * 5 + ['conversion']
        timestamps = [datetime.now() - timedelta(days=i) for i in range(14)]
        
        # Ensure all arrays have same length
        channels = channels[:14]
        event_types = event_types[:14]
        
        return pd.DataFrame({
            'customer_id': customer_ids,
            'channel': channels,
            'event_type': event_types,
            'timestamp': timestamps
        })
    
    def test_analyze_journey_lengths_basic(self, journey_analyzer, sample_journey_data):
        """Test basic journey length analysis."""
        result = journey_analyzer.analyze_journey_lengths(sample_journey_data)
        
        assert isinstance(result, dict)
        assert 'average_length' in result
        assert 'median_length' in result
        assert 'length_distribution' in result
        assert 'insights' in result
        
        assert result['average_length'] > 0
        assert result['median_length'] > 0
        assert isinstance(result['length_distribution'], dict)
        assert isinstance(result['insights'], list)
    
    def test_analyze_journey_lengths_single_touchpoints(self, journey_analyzer, single_touchpoint_data):
        """Test journey length analysis with single touchpoints."""
        result = journey_analyzer.analyze_journey_lengths(single_touchpoint_data)
        
        assert result['average_length'] == 1.0
        assert result['median_length'] == 1.0
        assert result['length_distribution']['1_touchpoint'] == 3
        assert result['length_distribution']['2_touchpoints'] == 0
    
    def test_analyze_journey_lengths_long_journeys(self, journey_analyzer, long_journey_data):
        """Test journey length analysis with long journeys."""
        result = journey_analyzer.analyze_journey_lengths(long_journey_data)
        
        assert result['average_length'] > 5  # Should be long journeys
        assert result['median_length'] > 5
        # With 14 total touchpoints across 2 customers, we should have journeys of 8 and 6 touchpoints
        assert result['length_distribution']['6_10_touchpoints'] > 0
    
    def test_analyze_journey_lengths_no_customer_id(self, journey_analyzer):
        """Test journey length analysis without customer ID column."""
        data_without_customer_id = pd.DataFrame({
            'channel': ['email', 'social', 'paid'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        result = journey_analyzer.analyze_journey_lengths(data_without_customer_id)
        
        assert result['average_length'] == 0
        assert result['median_length'] == 0
        assert 'No customer ID column found' in result['insights'][0]
    
    def test_analyze_journey_lengths_empty_data(self, journey_analyzer):
        """Test journey length analysis with empty data."""
        empty_data = pd.DataFrame(columns=['customer_id', 'channel', 'event_type', 'timestamp'])
        
        result = journey_analyzer.analyze_journey_lengths(empty_data)
        
        assert result['average_length'] == 0
        assert result['median_length'] == 0
        assert 'No customer journeys found' in result['insights'][0]
    
    def test_analyze_conversion_paths_basic(self, journey_analyzer, sample_journey_data):
        """Test basic conversion path analysis."""
        result = journey_analyzer.analyze_conversion_paths(sample_journey_data)
        
        assert isinstance(result, dict)
        assert 'top_paths' in result
        assert 'conversion_rate_by_path' in result
        assert 'insights' in result
        
        assert isinstance(result['top_paths'], list)
        assert isinstance(result['conversion_rate_by_path'], dict)
        assert isinstance(result['insights'], list)
    
    def test_analyze_conversion_paths_no_conversions(self, journey_analyzer):
        """Test conversion path analysis with no conversion events."""
        data_without_conversions = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'channel': ['email', 'social', 'paid'],
            'event_type': ['touchpoint', 'touchpoint', 'touchpoint'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        result = journey_analyzer.analyze_conversion_paths(data_without_conversions)
        
        assert result['top_paths'] == []
        assert result['conversion_rate_by_path'] == {}
        assert 'No conversion events found' in result['insights'][0]
    
    def test_analyze_conversion_paths_no_customer_id(self, journey_analyzer):
        """Test conversion path analysis without customer ID column."""
        data_without_customer_id = pd.DataFrame({
            'channel': ['email', 'social', 'paid'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        result = journey_analyzer.analyze_conversion_paths(data_without_customer_id)
        
        assert result['top_paths'] == []
        assert result['conversion_rate_by_path'] == {}
        assert 'No customer ID column found' in result['insights'][0]
    
    def test_analyze_conversion_paths_direct_conversions(self, journey_analyzer):
        """Test conversion path analysis with direct conversions."""
        direct_conversion_data = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'channel': ['email', 'social', 'direct'],
            'event_type': ['conversion', 'conversion', 'conversion'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        result = journey_analyzer.analyze_conversion_paths(direct_conversion_data)
        
        assert len(result['top_paths']) > 0
        # Should have direct paths (no arrows)
        direct_paths = [path for path in result['top_paths'] if ' -> ' not in path['path']]
        assert len(direct_paths) > 0
    
    def test_analyze_time_to_conversion_basic(self, journey_analyzer, sample_journey_data):
        """Test basic time to conversion analysis."""
        result = journey_analyzer.analyze_time_to_conversion(sample_journey_data)
        
        assert isinstance(result, dict)
        assert 'average_time_to_conversion' in result
        assert 'median_time_to_conversion' in result
        assert 'time_distribution' in result
        assert 'insights' in result
        
        assert result['average_time_to_conversion'] >= 0
        assert result['median_time_to_conversion'] >= 0
        assert isinstance(result['time_distribution'], dict)
        assert isinstance(result['insights'], list)
    
    def test_analyze_time_to_conversion_no_conversions(self, journey_analyzer):
        """Test time to conversion analysis with no conversion events."""
        data_without_conversions = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'channel': ['email', 'social', 'paid'],
            'event_type': ['touchpoint', 'touchpoint', 'touchpoint'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        result = journey_analyzer.analyze_time_to_conversion(data_without_conversions)
        
        assert result['average_time_to_conversion'] == 0
        assert result['median_time_to_conversion'] == 0
        assert 'No conversion events found' in result['insights'][0]
    
    def test_analyze_time_to_conversion_no_customer_id(self, journey_analyzer):
        """Test time to conversion analysis without customer ID column."""
        data_without_customer_id = pd.DataFrame({
            'channel': ['email', 'social', 'paid'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        result = journey_analyzer.analyze_time_to_conversion(data_without_customer_id)
        
        assert result['average_time_to_conversion'] == 0
        assert result['median_time_to_conversion'] == 0
        assert 'No customer ID column found' in result['insights'][0]
    
    def test_analyze_time_to_conversion_same_day(self, journey_analyzer):
        """Test time to conversion analysis with same-day conversions."""
        same_day_data = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C2', 'C2'],
            'channel': ['email', 'direct', 'social', 'paid'],
            'event_type': ['touchpoint', 'conversion', 'touchpoint', 'conversion'],
            'timestamp': [
                datetime.now() - timedelta(hours=2),
                datetime.now(),
                datetime.now() - timedelta(hours=1),
                datetime.now()
            ]
        })
        
        result = journey_analyzer.analyze_time_to_conversion(same_day_data)
        
        assert result['average_time_to_conversion'] == 0.0  # Same day
        assert result['time_distribution']['same_day'] == 2
    
    def test_generate_journey_insights_basic(self, journey_analyzer, sample_journey_data):
        """Test basic journey insights generation."""
        attribution_results = {'email': 0.4, 'social': 0.3, 'paid': 0.3}
        
        insights = journey_analyzer.generate_journey_insights(
            sample_journey_data, attribution_results
        )
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        for insight in insights:
            assert 'type' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
            
            assert 0.0 <= insight['impact_score'] <= 1.0
    
    def test_generate_journey_insights_empty_attribution(self, journey_analyzer, sample_journey_data):
        """Test journey insights generation with empty attribution results."""
        insights = journey_analyzer.generate_journey_insights(
            sample_journey_data, {}
        )
        
        assert isinstance(insights, list)
        # Should still generate some insights even without attribution results
    
    def test_generate_journey_insights_no_customer_id(self, journey_analyzer):
        """Test journey insights generation without customer ID column."""
        data_without_customer_id = pd.DataFrame({
            'channel': ['email', 'social', 'paid'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        attribution_results = {'email': 0.4, 'social': 0.3, 'paid': 0.3}
        
        insights = journey_analyzer.generate_journey_insights(
            data_without_customer_id, attribution_results
        )
        
        assert isinstance(insights, list)
        # Should still generate some insights
    
    def test_journey_analyzer_conversion_events(self, journey_analyzer):
        """Test that conversion events are properly configured."""
        expected_events = ['conversion', 'purchase', 'signup', 'subscribe']
        assert journey_analyzer.conversion_events == expected_events
    
    def test_analyze_journey_lengths_insights_generation(self, journey_analyzer):
        """Test that journey length analysis generates appropriate insights."""
        # Create data that should trigger specific insights
        short_journey_data = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'channel': ['email', 'social', 'direct'],
            'event_type': ['conversion', 'conversion', 'conversion'],
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        result = journey_analyzer.analyze_journey_lengths(short_journey_data)
        
        # Should generate insights about short journeys
        insights = result['insights']
        assert any('short journeys' in insight.lower() or 'direct response' in insight.lower() 
                  for insight in insights)
    
    def test_analyze_conversion_paths_path_analysis(self, journey_analyzer):
        """Test that conversion path analysis correctly identifies paths."""
        # Create data with clear conversion paths
        path_data = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C2', 'C2', 'C3'],
            'channel': ['email', 'social', 'email', 'paid', 'direct'],
            'event_type': ['touchpoint', 'conversion', 'touchpoint', 'conversion', 'conversion'],
            'timestamp': [
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=1),
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=1),
                datetime.now()
            ]
        })
        
        result = journey_analyzer.analyze_conversion_paths(path_data)
        
        assert len(result['top_paths']) > 0
        # Should have paths with arrows
        path_strings = [path['path'] for path in result['top_paths']]
        assert any(' -> ' in path for path in path_strings)
    
    def test_analyze_time_to_conversion_insights(self, journey_analyzer):
        """Test that time to conversion analysis generates appropriate insights."""
        # Create data with quick conversions
        quick_conversion_data = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C2', 'C2'],
            'channel': ['email', 'direct', 'social', 'paid'],
            'event_type': ['touchpoint', 'conversion', 'touchpoint', 'conversion'],
            'timestamp': [
                datetime.now() - timedelta(hours=1),
                datetime.now(),
                datetime.now() - timedelta(hours=2),
                datetime.now()
            ]
        })
        
        result = journey_analyzer.analyze_time_to_conversion(quick_conversion_data)
        
        # Should generate insights about quick conversions
        insights = result['insights']
        assert any('quick' in insight.lower() or 'fast' in insight.lower() 
                  for insight in insights)
    
    def test_journey_analyzer_with_real_world_scenario(self, journey_analyzer):
        """Test journey analyzer with realistic e-commerce scenario."""
        # Create realistic e-commerce data
        np.random.seed(42)
        n_customers = 100
        n_touchpoints = 500
        
        customer_ids = [f'C{i:03d}' for i in range(n_customers)]
        channels = ['email', 'social', 'paid_search', 'organic', 'direct', 'affiliate']
        event_types = ['touchpoint', 'conversion']
        
        data = []
        for i in range(n_touchpoints):
            customer_id = np.random.choice(customer_ids)
            channel = np.random.choice(channels)
            event_type = np.random.choice(event_types, p=[0.85, 0.15])  # 85% touchpoints, 15% conversions
            timestamp = datetime.now() - timedelta(days=np.random.randint(0, 30))
            
            data.append({
                'customer_id': customer_id,
                'channel': channel,
                'event_type': event_type,
                'timestamp': timestamp
            })
        
        df = pd.DataFrame(data)
        
        # Test journey length analysis
        length_result = journey_analyzer.analyze_journey_lengths(df)
        assert length_result['average_length'] > 0
        assert length_result['median_length'] > 0
        
        # Test conversion path analysis
        path_result = journey_analyzer.analyze_conversion_paths(df)
        assert isinstance(path_result['top_paths'], list)
        
        # Test time to conversion analysis
        time_result = journey_analyzer.analyze_time_to_conversion(df)
        assert time_result['average_time_to_conversion'] >= 0
        
        # Test comprehensive insights
        attribution_results = {channel: np.random.random() for channel in channels}
        # Normalize attribution results
        total = sum(attribution_results.values())
        attribution_results = {k: v/total for k, v in attribution_results.items()}
        
        insights = journey_analyzer.generate_journey_insights(df, attribution_results)
        assert len(insights) > 0
        
        for insight in insights:
            assert 'type' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
