"""Integration tests for Phase 3 components."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.main import app
from src.core.attribution_service import AttributionService
from src.core.confidence import ConfidenceScorer
from src.core.journey_analysis import JourneyAnalyzer
from src.core.business_insights import BusinessInsightsGenerator
from src.models.enums import AttributionModelType
from src.models.validation import DataQuality


class TestPhase3Integration:
    """Integration tests for Phase 3 components working together."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def comprehensive_test_data(self):
        """Create comprehensive test data for integration testing."""
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
            timestamp = datetime.now() - timedelta(days=np.random.randint(0, 90))
            revenue = np.random.randint(0, 200) if event_type == 'conversion' else 0
            
            data.append({
                'customer_id': customer_id,
                'channel': channel,
                'event_type': event_type,
                'timestamp': timestamp,
                'revenue': revenue,
                'session_id': f'S{customer_id}',
                'email': f'user{customer_id}@test.com'
            })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def attribution_service(self):
        """Create AttributionService instance."""
        return AttributionService()
    
    @pytest.fixture
    def confidence_scorer(self):
        """Create ConfidenceScorer instance."""
        return ConfidenceScorer()
    
    @pytest.fixture
    def journey_analyzer(self):
        """Create JourneyAnalyzer instance."""
        return JourneyAnalyzer()
    
    @pytest.fixture
    def business_insights_generator(self):
        """Create BusinessInsightsGenerator instance."""
        return BusinessInsightsGenerator()
    
    def test_confidence_scoring_integration(self, comprehensive_test_data, confidence_scorer):
        """Test confidence scoring integration with real data."""
        # Test data quality assessment
        data_quality = DataQuality(
            completeness=0.95,
            consistency=0.90,
            freshness=0.85
        )
        
        # Test overall confidence calculation
        overall_confidence = confidence_scorer.calculate_overall_confidence(
            data_quality=data_quality,
            sample_size=len(comprehensive_test_data),
            model_fit_score=0.8,
            identity_resolution_confidence=0.9
        )
        
        assert 0.0 <= overall_confidence <= 1.0
        assert overall_confidence > 0.7  # Should be reasonably high with good data
        
        # Test channel confidence calculation
        email_data = comprehensive_test_data[comprehensive_test_data['channel'] == 'email']
        channel_confidence = confidence_scorer.calculate_channel_confidence(
            channel_data=email_data,
            total_conversions=len(comprehensive_test_data[comprehensive_test_data['event_type'] == 'conversion']),
            attribution_credit=0.3
        )
        
        assert 0.0 <= channel_confidence <= 1.0
        
        # Test model fit score
        attribution_results = {'email': 0.3, 'social': 0.25, 'paid_search': 0.2, 'organic': 0.15, 'direct': 0.1}
        model_fit_score = confidence_scorer.calculate_model_fit_score(
            df=comprehensive_test_data,
            attribution_model='linear',
            attribution_results=attribution_results
        )
        
        assert 0.0 <= model_fit_score <= 1.0
        assert model_fit_score > 0.5  # Should have reasonable fit
        
        # Test identity resolution confidence
        identity_confidence = confidence_scorer.calculate_identity_resolution_confidence(
            df=comprehensive_test_data,
            linking_method='customer_id'
        )
        
        assert 0.0 <= identity_confidence <= 1.0
        assert identity_confidence > 0.8  # Should be high with customer_id
        
        # Test confidence breakdown
        breakdown = confidence_scorer.generate_confidence_breakdown(
            data_quality=data_quality,
            sample_size=len(comprehensive_test_data),
            model_fit_score=model_fit_score,
            identity_resolution_confidence=identity_confidence
        )
        
        assert 'overall' in breakdown
        assert breakdown['overall'] == overall_confidence
    
    def test_journey_analysis_integration(self, comprehensive_test_data, journey_analyzer):
        """Test journey analysis integration with real data."""
        # Test journey length analysis
        length_analysis = journey_analyzer.analyze_journey_lengths(comprehensive_test_data)
        
        assert 'average_length' in length_analysis
        assert 'median_length' in length_analysis
        assert 'length_distribution' in length_analysis
        assert 'insights' in length_analysis
        
        assert length_analysis['average_length'] > 0
        assert length_analysis['median_length'] > 0
        
        # Test conversion path analysis
        path_analysis = journey_analyzer.analyze_conversion_paths(comprehensive_test_data)
        
        assert 'top_paths' in path_analysis
        assert 'conversion_rate_by_path' in path_analysis
        assert 'insights' in path_analysis
        
        assert len(path_analysis['top_paths']) > 0
        
        # Test time to conversion analysis
        time_analysis = journey_analyzer.analyze_time_to_conversion(comprehensive_test_data)
        
        assert 'average_time_to_conversion' in time_analysis
        assert 'median_time_to_conversion' in time_analysis
        assert 'time_distribution' in time_analysis
        assert 'insights' in time_analysis
        
        assert time_analysis['average_time_to_conversion'] >= 0
        
        # Test comprehensive journey insights
        attribution_results = {'email': 0.3, 'social': 0.25, 'paid_search': 0.2, 'organic': 0.15, 'direct': 0.1}
        journey_insights = journey_analyzer.generate_journey_insights(
            comprehensive_test_data, attribution_results
        )
        
        assert isinstance(journey_insights, list)
        assert len(journey_insights) > 0
        
        for insight in journey_insights:
            assert 'type' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact_score' in insight
            assert 'recommendation' in insight
    
    def test_business_insights_integration(self, comprehensive_test_data, business_insights_generator, journey_analyzer):
        """Test business insights integration with real data."""
        # Prepare data for business insights
        attribution_results = {'email': 0.35, 'social': 0.25, 'paid_search': 0.20, 'organic': 0.15, 'direct': 0.05}
        
        # Get journey analysis
        journey_analysis = {
            'average_length': 4.2,
            'top_paths': [
                {'path': 'email -> social -> paid_search', 'percentage': 25.0},
                {'path': 'organic -> email', 'percentage': 20.0}
            ],
            'average_time_to_conversion': 12.5
        }
        
        data_quality = {'completeness': 0.95, 'consistency': 0.90, 'freshness': 0.85}
        
        # Test performance insights
        performance_insights = business_insights_generator.generate_performance_insights(
            attribution_results, {}
        )
        
        assert isinstance(performance_insights, list)
        assert len(performance_insights) > 0
        
        # Test budget allocation insights
        budget_insights = business_insights_generator.generate_budget_allocation_insights(
            attribution_results
        )
        
        assert isinstance(budget_insights, list)
        assert len(budget_insights) > 0
        
        # Test journey optimization insights
        journey_opt_insights = business_insights_generator.generate_journey_optimization_insights(
            journey_analysis, attribution_results
        )
        
        assert isinstance(journey_opt_insights, list)
        
        # Test data quality insights
        quality_insights = business_insights_generator.generate_data_quality_insights(
            data_quality, len(comprehensive_test_data)
        )
        
        assert isinstance(quality_insights, list)
        
        # Test comprehensive insights
        all_insights = business_insights_generator.generate_comprehensive_insights(
            attribution_results=attribution_results,
            journey_analysis=journey_analysis,
            data_quality=data_quality,
            sample_size=len(comprehensive_test_data)
        )
        
        assert isinstance(all_insights, list)
        assert len(all_insights) > 0
        
        # Verify insight structure and prioritization
        for insight in all_insights:
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
    
    def test_attribution_service_integration(self, comprehensive_test_data, attribution_service):
        """Test AttributionService integration with Phase 3 features."""
        # Test attribution analysis with confidence scoring
        result = await attribution_service.analyze_attribution(
            comprehensive_test_data, 
            AttributionModelType.LINEAR
        )
        
        # Verify response structure includes Phase 3 features
        assert hasattr(result, 'attribution_results')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'journey_analysis')
        assert hasattr(result, 'business_insights')
        assert hasattr(result, 'metadata')
        
        # Verify confidence scoring
        confidence = result.confidence
        assert hasattr(confidence, 'overall_confidence')
        assert hasattr(confidence, 'data_quality')
        assert hasattr(confidence, 'sample_size')
        assert hasattr(confidence, 'model_fit')
        assert hasattr(confidence, 'identity_resolution')
        
        assert 0.0 <= confidence.overall_confidence <= 1.0
        
        # Verify journey analysis
        journey = result.journey_analysis
        assert hasattr(journey, 'journey_lengths')
        assert hasattr(journey, 'conversion_paths')
        assert hasattr(journey, 'time_to_conversion')
        assert hasattr(journey, 'insights')
        
        # Verify business insights
        insights = result.business_insights
        assert isinstance(insights, list)
        
        if len(insights) > 0:
            for insight in insights:
                assert hasattr(insight, 'type')
                assert hasattr(insight, 'category')
                assert hasattr(insight, 'title')
                assert hasattr(insight, 'description')
                assert hasattr(insight, 'impact_score')
                assert hasattr(insight, 'recommendation')
                assert hasattr(insight, 'priority')
    
    def test_api_endpoint_integration(self, client, comprehensive_test_data):
        """Test API endpoint integration with Phase 3 features."""
        # Convert DataFrame to CSV string
        csv_data = comprehensive_test_data.to_csv(index=False)
        
        # Test validation endpoint
        files = {"file": ("integration_test.csv", csv_data, "text/csv")}
        validation_response = client.post("/attribution/validate", files=files)
        
        assert validation_response.status_code == 200
        validation_data = validation_response.json()
        assert validation_data["valid"] is True
        
        # Test methods endpoint
        methods_response = client.get("/attribution/methods")
        assert methods_response.status_code == 200
        methods_data = methods_response.json()
        assert len(methods_data["attribution_models"]) == 5
        
        # Test analysis endpoint with Phase 3 features
        analysis_data = {"model_type": "linear"}
        analysis_response = client.post("/attribution/analyze", files=files, data=analysis_data)
        
        assert analysis_response.status_code == 200
        analysis_result = analysis_response.json()
        
        # Verify Phase 3 features in response
        assert "confidence" in analysis_result
        assert "journey_analysis" in analysis_result
        assert "business_insights" in analysis_result
        
        # Verify confidence structure
        confidence = analysis_result["confidence"]
        assert "overall_confidence" in confidence
        assert "data_quality" in confidence
        assert "sample_size" in confidence
        assert "model_fit" in confidence
        assert "identity_resolution" in confidence
        
        # Verify journey analysis structure
        journey = analysis_result["journey_analysis"]
        assert "journey_lengths" in journey
        assert "conversion_paths" in journey
        assert "time_to_conversion" in journey
        assert "insights" in journey
        
        # Verify business insights structure
        insights = analysis_result["business_insights"]
        assert isinstance(insights, list)
        
        if len(insights) > 0:
            for insight in insights:
                assert "type" in insight
                assert "category" in insight
                assert "title" in insight
                assert "description" in insight
                assert "impact_score" in insight
                assert "recommendation" in insight
                assert "priority" in insight
    
    def test_phase3_components_workflow(self, comprehensive_test_data, attribution_service, confidence_scorer, journey_analyzer, business_insights_generator):
        """Test complete Phase 3 workflow with all components."""
        # Step 1: Perform attribution analysis
        result = await attribution_service.analyze_attribution(
            comprehensive_test_data, 
            AttributionModelType.LINEAR
        )
        
        # Step 2: Extract components for further analysis
        attribution_results = result.attribution_results
        confidence = result.confidence
        journey_analysis = result.journey_analysis
        business_insights = result.business_insights
        
        # Step 3: Verify confidence scoring integration
        assert confidence.overall_confidence > 0.5  # Should have reasonable confidence
        
        # Step 4: Verify journey analysis integration
        assert journey_analysis.journey_lengths.average_length > 0
        assert len(journey_analysis.conversion_paths.top_paths) > 0
        assert journey_analysis.time_to_conversion.average_time_to_conversion >= 0
        
        # Step 5: Verify business insights integration
        assert len(business_insights) > 0
        
        # Step 6: Test component interactions
        # Journey analysis should inform business insights
        journey_insights = journey_analyzer.generate_journey_insights(
            comprehensive_test_data, attribution_results
        )
        assert len(journey_insights) > 0
        
        # Business insights should be comprehensive
        comprehensive_insights = business_insights_generator.generate_comprehensive_insights(
            attribution_results=attribution_results,
            journey_analysis={
                'average_length': journey_analysis.journey_lengths.average_length,
                'top_paths': journey_analysis.conversion_paths.top_paths,
                'average_time_to_conversion': journey_analysis.time_to_conversion.average_time_to_conversion
            },
            data_quality={
                'completeness': confidence.data_quality.completeness,
                'consistency': confidence.data_quality.consistency,
                'freshness': confidence.data_quality.freshness
            },
            sample_size=len(comprehensive_test_data)
        )
        
        assert len(comprehensive_insights) > 0
        
        # Step 7: Verify data flow between components
        # Confidence should be calculated based on data quality
        assert confidence.data_quality.completeness > 0.8
        assert confidence.data_quality.consistency > 0.8
        assert confidence.data_quality.freshness > 0.8
        
        # Journey analysis should provide meaningful insights
        assert journey_analysis.journey_lengths.insights is not None
        assert journey_analysis.conversion_paths.insights is not None
        assert journey_analysis.time_to_conversion.insights is not None
        
        # Business insights should be actionable
        for insight in comprehensive_insights:
            assert insight.impact_score > 0
            assert insight.recommendation is not None
            assert insight.priority in ['high', 'medium', 'low']
    
    def test_error_handling_integration(self, client):
        """Test error handling across Phase 3 components."""
        # Test with invalid data
        invalid_data = "invalid,csv,data\n1,2,3\n"
        files = {"file": ("invalid.csv", invalid_data, "text/csv")}
        
        # Validation should handle gracefully
        validation_response = client.post("/attribution/validate", files=files)
        assert validation_response.status_code == 200
        validation_data = validation_response.json()
        assert validation_data["valid"] is False
        
        # Analysis should handle gracefully
        analysis_data = {"model_type": "linear"}
        analysis_response = client.post("/attribution/analyze", files=files, data=analysis_data)
        assert analysis_response.status_code == 422
        
        # Test with empty data
        empty_data = "timestamp,channel,event_type\n"
        files = {"file": ("empty.csv", empty_data, "text/csv")}
        
        validation_response = client.post("/attribution/validate", files=files)
        assert validation_response.status_code == 200
        validation_data = validation_response.json()
        assert validation_data["valid"] is False
    
    def test_performance_integration(self, comprehensive_test_data, attribution_service):
        """Test performance of Phase 3 components with large dataset."""
        # Test with larger dataset
        large_data = pd.concat([comprehensive_test_data] * 2, ignore_index=True)
        
        # Should complete within reasonable time
        import time
        start_time = time.time()
        
        result = await attribution_service.analyze_attribution(
            large_data, 
            AttributionModelType.LINEAR
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within 10 seconds for this dataset size
        assert processing_time < 10.0
        
        # Verify results are still meaningful
        assert result.confidence.overall_confidence > 0.5
        assert len(result.business_insights) > 0
        assert result.journey_analysis.journey_lengths.average_length > 0
