"""Tests for confidence scoring system."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.confidence import ConfidenceScorer
from src.models.validation import DataQuality


class TestConfidenceScorer:
    """Test cases for ConfidenceScorer class."""
    
    @pytest.fixture
    def confidence_scorer(self):
        """Create ConfidenceScorer instance for testing."""
        return ConfidenceScorer()
    
    @pytest.fixture
    def sample_data_quality(self):
        """Create sample data quality metrics."""
        return DataQuality(
            completeness=0.95,
            consistency=0.90,
            freshness=0.85
        )
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C2', 'C2', 'C3'],
            'channel': ['email', 'social', 'email', 'paid', 'organic'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion', 'touchpoint', 'conversion'],
            'timestamp': [
                datetime.now() - timedelta(days=5),
                datetime.now() - timedelta(days=3),
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=1),
                datetime.now()
            ]
        })
    
    def test_calculate_overall_confidence_high_quality(self, confidence_scorer, sample_data_quality):
        """Test overall confidence calculation with high quality data."""
        confidence = confidence_scorer.calculate_overall_confidence(
            data_quality=sample_data_quality,
            sample_size=1000,
            model_fit_score=0.9,
            identity_resolution_confidence=0.95
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # Should be high confidence
    
    def test_calculate_overall_confidence_low_quality(self, confidence_scorer):
        """Test overall confidence calculation with low quality data."""
        low_quality = DataQuality(
            completeness=0.5,
            consistency=0.4,
            freshness=0.3
        )
        
        confidence = confidence_scorer.calculate_overall_confidence(
            data_quality=low_quality,
            sample_size=10,
            model_fit_score=0.3,
            identity_resolution_confidence=0.4
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.5  # Should be low confidence
    
    def test_calculate_overall_confidence_edge_cases(self, confidence_scorer, sample_data_quality):
        """Test overall confidence calculation with edge cases."""
        # Zero sample size
        confidence = confidence_scorer.calculate_overall_confidence(
            data_quality=sample_data_quality,
            sample_size=0,
            model_fit_score=0.9,
            identity_resolution_confidence=0.95
        )
        assert 0.0 <= confidence <= 1.0
        
        # Perfect scores
        confidence = confidence_scorer.calculate_overall_confidence(
            data_quality=sample_data_quality,
            sample_size=10000,
            model_fit_score=1.0,
            identity_resolution_confidence=1.0
        )
        assert confidence <= 1.0
    
    def test_calculate_channel_confidence_high_performance(self, confidence_scorer, sample_dataframe):
        """Test channel confidence calculation with high performance data."""
        channel_data = sample_dataframe[sample_dataframe['channel'] == 'email']
        confidence = confidence_scorer.calculate_channel_confidence(
            channel_data=channel_data,
            total_conversions=100,
            attribution_credit=0.4
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.0
    
    def test_calculate_channel_confidence_no_conversions(self, confidence_scorer, sample_dataframe):
        """Test channel confidence calculation with no conversions."""
        channel_data = sample_dataframe[sample_dataframe['channel'] == 'email']
        confidence = confidence_scorer.calculate_channel_confidence(
            channel_data=channel_data,
            total_conversions=0,
            attribution_credit=0.0
        )
        
        assert confidence == 0.0
    
    def test_calculate_channel_confidence_empty_data(self, confidence_scorer):
        """Test channel confidence calculation with empty data."""
        empty_df = pd.DataFrame(columns=['channel', 'event_type'])
        confidence = confidence_scorer.calculate_channel_confidence(
            channel_data=empty_df,
            total_conversions=100,
            attribution_credit=0.4
        )
        
        assert 0.0 <= confidence <= 1.0
    
    def test_calculate_model_fit_score_different_models(self, confidence_scorer, sample_dataframe):
        """Test model fit score calculation for different attribution models."""
        attribution_results = {'email': 0.4, 'social': 0.3, 'paid': 0.3}
        
        # Test different models
        models = ['linear', 'first_touch', 'last_touch', 'time_decay', 'position_based']
        
        for model in models:
            fit_score = confidence_scorer.calculate_model_fit_score(
                df=sample_dataframe,
                attribution_model=model,
                attribution_results=attribution_results
            )
            
            assert 0.0 <= fit_score <= 1.0
            assert fit_score > 0.0  # Should have some fit
    
    def test_calculate_model_fit_score_empty_data(self, confidence_scorer):
        """Test model fit score calculation with empty data."""
        empty_df = pd.DataFrame()
        attribution_results = {}
        
        fit_score = confidence_scorer.calculate_model_fit_score(
            df=empty_df,
            attribution_model='linear',
            attribution_results=attribution_results
        )
        
        assert fit_score == 0.0
    
    def test_calculate_model_fit_score_long_journeys(self, confidence_scorer):
        """Test model fit score calculation with long customer journeys."""
        # Create data with long journeys - ensure all arrays have same length
        customer_ids = ['C1'] * 10 + ['C2'] * 8
        channels = ['email', 'social', 'paid', 'organic'] * 4 + ['email', 'social'] * 4
        event_types = ['touchpoint'] * 18
        timestamps = [datetime.now() - timedelta(days=i) for i in range(18)]
        
        # Fix channels array to match length
        channels = channels[:18]
        
        # Verify all arrays have same length
        assert len(customer_ids) == len(channels) == len(event_types) == len(timestamps) == 18
        
        long_journey_data = pd.DataFrame({
            'customer_id': customer_ids,
            'channel': channels,
            'event_type': event_types,
            'timestamp': timestamps
        })
        
        attribution_results = {'email': 0.4, 'social': 0.3, 'paid': 0.2, 'organic': 0.1}
        
        fit_score = confidence_scorer.calculate_model_fit_score(
            df=long_journey_data,
            attribution_model='linear',
            attribution_results=attribution_results
        )
        
        assert 0.0 <= fit_score <= 1.0
        # Linear model should perform well with long journeys
        assert fit_score > 0.7
    
    def test_calculate_identity_resolution_confidence_different_methods(self, confidence_scorer, sample_dataframe):
        """Test identity resolution confidence for different linking methods."""
        methods = ['customer_id', 'session_email', 'email_only', 'aggregate', 'auto']
        
        for method in methods:
            confidence = confidence_scorer.calculate_identity_resolution_confidence(
                df=sample_dataframe,
                linking_method=method
            )
            
            assert 0.0 <= confidence <= 1.0
            assert confidence > 0.0
    
    def test_calculate_identity_resolution_confidence_customer_id(self, confidence_scorer):
        """Test identity resolution confidence with customer_id method."""
        df_with_customer_id = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3', None, 'C4'],  # Some missing values
            'channel': ['email', 'social', 'paid', 'organic', 'email'],
            'event_type': ['touchpoint'] * 5,
            'timestamp': [datetime.now()] * 5
        })
        
        confidence = confidence_scorer.calculate_identity_resolution_confidence(
            df=df_with_customer_id,
            linking_method='customer_id'
        )
        
        assert 0.0 <= confidence <= 1.0
        # Should be reasonably high but not perfect due to missing values
        assert confidence > 0.7
    
    def test_calculate_identity_resolution_confidence_session_email(self, confidence_scorer):
        """Test identity resolution confidence with session_email method."""
        df_with_session_email = pd.DataFrame({
            'session_id': ['S1', 'S2', 'S3', None, 'S4'],
            'email': ['user1@test.com', 'user2@test.com', None, 'user4@test.com', 'user5@test.com'],
            'channel': ['email', 'social', 'paid', 'organic', 'email'],
            'event_type': ['touchpoint'] * 5,
            'timestamp': [datetime.now()] * 5
        })
        
        confidence = confidence_scorer.calculate_identity_resolution_confidence(
            df=df_with_session_email,
            linking_method='session_email'
        )
        
        assert 0.0 <= confidence <= 1.0
        # Should be good but not perfect due to missing values
        assert confidence > 0.6
    
    def test_calculate_identity_resolution_confidence_email_only(self, confidence_scorer):
        """Test identity resolution confidence with email_only method."""
        df_with_email = pd.DataFrame({
            'email': ['user1@test.com', 'user2@test.com', None, 'user4@test.com', 'user5@test.com'],
            'channel': ['email', 'social', 'paid', 'organic', 'email'],
            'event_type': ['touchpoint'] * 5,
            'timestamp': [datetime.now()] * 5
        })
        
        confidence = confidence_scorer.calculate_identity_resolution_confidence(
            df=df_with_email,
            linking_method='email_only'
        )
        
        assert 0.0 <= confidence <= 1.0
        # Should be moderate due to missing values
        assert confidence > 0.5
    
    def test_generate_confidence_breakdown(self, confidence_scorer, sample_data_quality):
        """Test confidence breakdown generation."""
        breakdown = confidence_scorer.generate_confidence_breakdown(
            data_quality=sample_data_quality,
            sample_size=1000,
            model_fit_score=0.9,
            identity_resolution_confidence=0.95
        )
        
        assert isinstance(breakdown, dict)
        assert 'data_quality' in breakdown
        assert 'sample_size' in breakdown
        assert 'model_fit' in breakdown
        assert 'identity_resolution' in breakdown
        assert 'overall' in breakdown
        
        # All values should be between 0 and 1
        for key, value in breakdown.items():
            assert 0.0 <= value <= 1.0
        
        # Overall should match the calculated confidence
        expected_overall = confidence_scorer.calculate_overall_confidence(
            sample_data_quality, 1000, 0.9, 0.95
        )
        assert abs(breakdown['overall'] - expected_overall) < 0.001
    
    def test_confidence_scorer_weights(self, confidence_scorer):
        """Test that confidence scorer weights are properly configured."""
        expected_weights = {
            'data_quality': 0.4,
            'sample_size': 0.3,
            'model_fit': 0.2,
            'identity_resolution': 0.1
        }
        
        assert confidence_scorer.weights == expected_weights
        assert abs(sum(confidence_scorer.weights.values()) - 1.0) < 0.001
    
    def test_confidence_scorer_with_real_world_data(self, confidence_scorer):
        """Test confidence scorer with realistic data scenarios."""
        # Create realistic data
        np.random.seed(42)
        n_customers = 1000
        n_touchpoints = 5000
        
        customer_ids = [f'C{i:04d}' for i in range(n_customers)]
        channels = ['email', 'social', 'paid', 'organic', 'direct']
        event_types = ['touchpoint', 'conversion']
        
        data = []
        for i in range(n_touchpoints):
            customer_id = np.random.choice(customer_ids)
            channel = np.random.choice(channels)
            event_type = np.random.choice(event_types, p=[0.9, 0.1])  # 90% touchpoints, 10% conversions
            timestamp = datetime.now() - timedelta(days=np.random.randint(0, 90))
            
            data.append({
                'customer_id': customer_id,
                'channel': channel,
                'event_type': event_type,
                'timestamp': timestamp
            })
        
        df = pd.DataFrame(data)
        
        # Test with realistic parameters
        data_quality = DataQuality(
            completeness=0.95,
            consistency=0.90,
            freshness=0.85
        )
        
        confidence = confidence_scorer.calculate_overall_confidence(
            data_quality=data_quality,
            sample_size=len(df),
            model_fit_score=0.8,
            identity_resolution_confidence=0.9
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be reasonably high with good data
        
        # Test channel confidence
        email_data = df[df['channel'] == 'email']
        channel_confidence = confidence_scorer.calculate_channel_confidence(
            channel_data=email_data,
            total_conversions=len(df[df['event_type'] == 'conversion']),
            attribution_credit=0.3
        )
        
        assert 0.0 <= channel_confidence <= 1.0
