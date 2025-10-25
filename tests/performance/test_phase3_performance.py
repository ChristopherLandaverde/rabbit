"""Performance tests for Phase 3 features."""

import pytest
import pandas as pd
import numpy as np
import time
import psutil
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import asyncio
from unittest.mock import patch

from src.main import app
from src.core.attribution_service import AttributionService
from src.core.confidence import ConfidenceScorer
from src.core.journey_analysis import JourneyAnalyzer
from src.core.business_insights import BusinessInsightsGenerator
from src.models.enums import AttributionModelType
from src.models.validation import DataQuality


class TestPhase3Performance:
    """Performance tests for Phase 3 components."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def large_dataset(self):
        """Create large dataset for performance testing."""
        np.random.seed(42)
        n_customers = 1000
        n_touchpoints = 10000
        
        customer_ids = [f'C{i:04d}' for i in range(n_customers)]
        channels = ['email', 'social', 'paid_search', 'organic', 'direct', 'affiliate', 'display', 'video']
        event_types = ['touchpoint', 'conversion']
        
        data = []
        for i in range(n_touchpoints):
            customer_id = np.random.choice(customer_ids)
            channel = np.random.choice(channels)
            event_type = np.random.choice(event_types, p=[0.9, 0.1])  # 90% touchpoints, 10% conversions
            timestamp = datetime.now() - timedelta(days=np.random.randint(0, 180))
            revenue = np.random.randint(0, 500) if event_type == 'conversion' else 0
            
            data.append({
                'customer_id': customer_id,
                'channel': channel,
                'event_type': event_type,
                'timestamp': timestamp,
                'revenue': revenue,
                'session_id': f'S{customer_id}_{i}',
                'email': f'user{customer_id}@test.com',
                'campaign': f'campaign_{np.random.randint(1, 20)}'
            })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def very_large_dataset(self):
        """Create very large dataset for stress testing."""
        np.random.seed(42)
        n_customers = 5000
        n_touchpoints = 50000
        
        customer_ids = [f'C{i:05d}' for i in range(n_customers)]
        channels = ['email', 'social', 'paid_search', 'organic', 'direct', 'affiliate', 'display', 'video', 'mobile', 'retargeting']
        event_types = ['touchpoint', 'conversion']
        
        data = []
        for i in range(n_touchpoints):
            customer_id = np.random.choice(customer_ids)
            channel = np.random.choice(channels)
            event_type = np.random.choice(event_types, p=[0.92, 0.08])  # 92% touchpoints, 8% conversions
            timestamp = datetime.now() - timedelta(days=np.random.randint(0, 365))
            revenue = np.random.randint(0, 1000) if event_type == 'conversion' else 0
            
            data.append({
                'customer_id': customer_id,
                'channel': channel,
                'event_type': event_type,
                'timestamp': timestamp,
                'revenue': revenue,
                'session_id': f'S{customer_id}_{i}',
                'email': f'user{customer_id}@test.com'
            })
        
        return pd.DataFrame(data)
    
    def test_confidence_scoring_performance(self, large_dataset):
        """Test performance of confidence scoring with large dataset."""
        confidence_scorer = ConfidenceScorer()
        
        # Test data quality assessment performance
        start_time = time.time()
        data_quality = DataQuality(
            completeness=0.95,
            consistency=0.90,
            freshness=0.85
        )
        end_time = time.time()
        data_quality_time = end_time - start_time
        
        assert data_quality_time < 0.1  # Should be very fast
        
        # Test overall confidence calculation performance
        start_time = time.time()
        overall_confidence = confidence_scorer.calculate_overall_confidence(
            data_quality=data_quality,
            sample_size=len(large_dataset),
            model_fit_score=0.8,
            identity_resolution_confidence=0.9
        )
        end_time = time.time()
        overall_confidence_time = end_time - start_time
        
        assert overall_confidence_time < 0.1  # Should be very fast
        assert 0.0 <= overall_confidence <= 1.0
        
        # Test channel confidence calculation performance
        start_time = time.time()
        email_data = large_dataset[large_dataset['channel'] == 'email']
        channel_confidence = confidence_scorer.calculate_channel_confidence(
            channel_data=email_data,
            total_conversions=len(large_dataset[large_dataset['event_type'] == 'conversion']),
            attribution_credit=0.3
        )
        end_time = time.time()
        channel_confidence_time = end_time - start_time
        
        assert channel_confidence_time < 0.5  # Should be fast even with large channel data
        assert 0.0 <= channel_confidence <= 1.0
        
        # Test model fit score calculation performance
        start_time = time.time()
        attribution_results = {channel: np.random.random() for channel in large_dataset['channel'].unique()}
        # Normalize attribution results
        total = sum(attribution_results.values())
        attribution_results = {k: v/total for k, v in attribution_results.items()}
        
        model_fit_score = confidence_scorer.calculate_model_fit_score(
            df=large_dataset,
            attribution_model='linear',
            attribution_results=attribution_results
        )
        end_time = time.time()
        model_fit_time = end_time - start_time
        
        assert model_fit_time < 1.0  # Should be reasonable for large dataset
        assert 0.0 <= model_fit_score <= 1.0
        
        # Test identity resolution confidence performance
        start_time = time.time()
        identity_confidence = confidence_scorer.calculate_identity_resolution_confidence(
            df=large_dataset,
            linking_method='customer_id'
        )
        end_time = time.time()
        identity_confidence_time = end_time - start_time
        
        assert identity_confidence_time < 0.5  # Should be fast
        assert 0.0 <= identity_confidence <= 1.0
        
        # Test confidence breakdown performance
        start_time = time.time()
        breakdown = confidence_scorer.generate_confidence_breakdown(
            data_quality=data_quality,
            sample_size=len(large_dataset),
            model_fit_score=model_fit_score,
            identity_resolution_confidence=identity_confidence
        )
        end_time = time.time()
        breakdown_time = end_time - start_time
        
        assert breakdown_time < 0.1  # Should be very fast
        assert 'overall' in breakdown
    
    def test_journey_analysis_performance(self, large_dataset):
        """Test performance of journey analysis with large dataset."""
        journey_analyzer = JourneyAnalyzer()
        
        # Test journey length analysis performance
        start_time = time.time()
        length_analysis = journey_analyzer.analyze_journey_lengths(large_dataset)
        end_time = time.time()
        length_analysis_time = end_time - start_time
        
        assert length_analysis_time < 2.0  # Should be reasonable for large dataset
        assert 'average_length' in length_analysis
        assert length_analysis['average_length'] > 0
        
        # Test conversion path analysis performance
        start_time = time.time()
        path_analysis = journey_analyzer.analyze_conversion_paths(large_dataset)
        end_time = time.time()
        path_analysis_time = end_time - start_time
        
        assert path_analysis_time < 3.0  # Should be reasonable for large dataset
        assert 'top_paths' in path_analysis
        assert len(path_analysis['top_paths']) > 0
        
        # Test time to conversion analysis performance
        start_time = time.time()
        time_analysis = journey_analyzer.analyze_time_to_conversion(large_dataset)
        end_time = time.time()
        time_analysis_time = end_time - start_time
        
        assert time_analysis_time < 2.0  # Should be reasonable for large dataset
        assert 'average_time_to_conversion' in time_analysis
        assert time_analysis['average_time_to_conversion'] >= 0
        
        # Test comprehensive journey insights performance
        start_time = time.time()
        attribution_results = {channel: np.random.random() for channel in large_dataset['channel'].unique()}
        total = sum(attribution_results.values())
        attribution_results = {k: v/total for k, v in attribution_results.items()}
        
        journey_insights = journey_analyzer.generate_journey_insights(
            large_dataset, attribution_results
        )
        end_time = time.time()
        insights_time = end_time - start_time
        
        assert insights_time < 3.0  # Should be reasonable for large dataset
        assert isinstance(journey_insights, list)
        assert len(journey_insights) > 0
    
    def test_business_insights_performance(self, large_dataset):
        """Test performance of business insights generation with large dataset."""
        business_insights_generator = BusinessInsightsGenerator()
        
        # Prepare data for business insights
        attribution_results = {channel: np.random.random() for channel in large_dataset['channel'].unique()}
        total = sum(attribution_results.values())
        attribution_results = {k: v/total for k, v in attribution_results.items()}
        
        journey_analysis = {
            'average_length': 4.2,
            'top_paths': [
                {'path': 'email -> social -> paid_search', 'percentage': 25.0},
                {'path': 'organic -> email', 'percentage': 20.0}
            ],
            'average_time_to_conversion': 12.5
        }
        
        data_quality = {'completeness': 0.95, 'consistency': 0.90, 'freshness': 0.85}
        
        # Test performance insights generation
        start_time = time.time()
        performance_insights = business_insights_generator.generate_performance_insights(
            attribution_results, {}
        )
        end_time = time.time()
        performance_time = end_time - start_time
        
        assert performance_time < 0.5  # Should be fast
        assert isinstance(performance_insights, list)
        
        # Test budget allocation insights generation
        start_time = time.time()
        budget_insights = business_insights_generator.generate_budget_allocation_insights(
            attribution_results
        )
        end_time = time.time()
        budget_time = end_time - start_time
        
        assert budget_time < 0.5  # Should be fast
        assert isinstance(budget_insights, list)
        
        # Test journey optimization insights generation
        start_time = time.time()
        journey_opt_insights = business_insights_generator.generate_journey_optimization_insights(
            journey_analysis, attribution_results
        )
        end_time = time.time()
        journey_opt_time = end_time - start_time
        
        assert journey_opt_time < 0.5  # Should be fast
        assert isinstance(journey_opt_insights, list)
        
        # Test data quality insights generation
        start_time = time.time()
        quality_insights = business_insights_generator.generate_data_quality_insights(
            data_quality, len(large_dataset)
        )
        end_time = time.time()
        quality_time = end_time - start_time
        
        assert quality_time < 0.5  # Should be fast
        assert isinstance(quality_insights, list)
        
        # Test comprehensive insights generation
        start_time = time.time()
        comprehensive_insights = business_insights_generator.generate_comprehensive_insights(
            attribution_results=attribution_results,
            journey_analysis=journey_analysis,
            data_quality=data_quality,
            sample_size=len(large_dataset)
        )
        end_time = time.time()
        comprehensive_time = end_time - start_time
        
        assert comprehensive_time < 1.0  # Should be reasonable
        assert isinstance(comprehensive_insights, list)
        assert len(comprehensive_insights) > 0
    
    def test_attribution_service_performance(self, large_dataset):
        """Test performance of AttributionService with Phase 3 features."""
        attribution_service = AttributionService()
        
        # Test attribution analysis performance
        start_time = time.time()
        result = await attribution_service.analyze_attribution(
            large_dataset, 
            AttributionModelType.LINEAR
        )
        end_time = time.time()
        analysis_time = end_time - start_time
        
        assert analysis_time < 10.0  # Should complete within 10 seconds
        assert hasattr(result, 'attribution_results')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'journey_analysis')
        assert hasattr(result, 'business_insights')
        
        # Verify confidence scoring performance
        confidence = result.confidence
        assert 0.0 <= confidence.overall_confidence <= 1.0
        
        # Verify journey analysis performance
        journey = result.journey_analysis
        assert journey.journey_lengths.average_length > 0
        
        # Verify business insights performance
        insights = result.business_insights
        assert isinstance(insights, list)
    
    def test_api_endpoint_performance(self, client, large_dataset):
        """Test performance of API endpoints with large dataset."""
        # Convert DataFrame to CSV string
        csv_data = large_dataset.to_csv(index=False)
        
        # Test validation endpoint performance
        files = {"file": ("large_test.csv", csv_data, "text/csv")}
        
        start_time = time.time()
        validation_response = client.post("/attribution/validate", files=files)
        end_time = time.time()
        validation_time = end_time - start_time
        
        assert validation_response.status_code == 200
        assert validation_time < 5.0  # Should complete within 5 seconds
        
        # Test methods endpoint performance
        start_time = time.time()
        methods_response = client.get("/attribution/methods")
        end_time = time.time()
        methods_time = end_time - start_time
        
        assert methods_response.status_code == 200
        assert methods_time < 1.0  # Should be very fast
        
        # Test analysis endpoint performance
        analysis_data = {"model_type": "linear"}
        
        start_time = time.time()
        analysis_response = client.post("/attribution/analyze", files=files, data=analysis_data)
        end_time = time.time()
        analysis_time = end_time - start_time
        
        assert analysis_response.status_code == 200
        assert analysis_time < 15.0  # Should complete within 15 seconds
        
        # Verify response includes Phase 3 features
        analysis_result = analysis_response.json()
        assert "confidence" in analysis_result
        assert "journey_analysis" in analysis_result
        assert "business_insights" in analysis_result
    
    def test_memory_usage_performance(self, very_large_dataset):
        """Test memory usage with very large dataset."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Test confidence scoring memory usage
        confidence_scorer = ConfidenceScorer()
        data_quality = DataQuality(completeness=0.95, consistency=0.90, freshness=0.85)
        
        confidence_memory = process.memory_info().rss / 1024 / 1024  # MB
        confidence_memory_increase = confidence_memory - initial_memory
        
        assert confidence_memory_increase < 100  # Should not use more than 100MB additional memory
        
        # Test journey analysis memory usage
        journey_analyzer = JourneyAnalyzer()
        length_analysis = journey_analyzer.analyze_journey_lengths(very_large_dataset)
        
        journey_memory = process.memory_info().rss / 1024 / 1024  # MB
        journey_memory_increase = journey_memory - initial_memory
        
        assert journey_memory_increase < 200  # Should not use more than 200MB additional memory
        
        # Test business insights memory usage
        business_insights_generator = BusinessInsightsGenerator()
        attribution_results = {channel: 0.2 for channel in very_large_dataset['channel'].unique()}
        
        comprehensive_insights = business_insights_generator.generate_comprehensive_insights(
            attribution_results=attribution_results,
            journey_analysis={'average_length': 4.0, 'top_paths': [], 'average_time_to_conversion': 10.0},
            data_quality={'completeness': 0.95, 'consistency': 0.90, 'freshness': 0.85},
            sample_size=len(very_large_dataset)
        )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        assert total_memory_increase < 500  # Should not use more than 500MB additional memory
    
    def test_concurrent_performance(self, large_dataset):
        """Test performance under concurrent load."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def run_analysis():
            try:
                attribution_service = AttributionService()
                result = await attribution_service.analyze_attribution(
                    large_dataset, 
                    AttributionModelType.LINEAR
                )
                results_queue.put(result)
            except Exception as e:
                errors_queue.put(e)
        
        # Run multiple analyses concurrently
        threads = []
        num_concurrent = 3
        
        start_time = time.time()
        
        for i in range(num_concurrent):
            thread = threading.Thread(target=run_analysis)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time even with concurrent load
        assert total_time < 30.0  # Should complete within 30 seconds
        
        # Check that we got results without errors
        assert results_queue.qsize() == num_concurrent
        assert errors_queue.qsize() == 0
        
        # Verify results are valid
        while not results_queue.empty():
            result = results_queue.get()
            assert hasattr(result, 'attribution_results')
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'journey_analysis')
            assert hasattr(result, 'business_insights')
    
    def test_scalability_performance(self):
        """Test scalability with different dataset sizes."""
        dataset_sizes = [100, 1000, 5000, 10000]
        processing_times = []
        
        for size in dataset_sizes:
            # Create dataset of specific size
            np.random.seed(42)
            n_customers = size // 10
            customer_ids = [f'C{i:04d}' for i in range(n_customers)]
            channels = ['email', 'social', 'paid', 'organic', 'direct']
            
            data = []
            for i in range(size):
                customer_id = np.random.choice(customer_ids)
                channel = np.random.choice(channels)
                event_type = np.random.choice(['touchpoint', 'conversion'], p=[0.9, 0.1])
                timestamp = datetime.now() - timedelta(days=np.random.randint(0, 30))
                
                data.append({
                    'customer_id': customer_id,
                    'channel': channel,
                    'event_type': event_type,
                    'timestamp': timestamp
                })
            
            df = pd.DataFrame(data)
            
            # Test processing time
            start_time = time.time()
            
            confidence_scorer = ConfidenceScorer()
            data_quality = DataQuality(completeness=0.95, consistency=0.90, freshness=0.85)
            confidence = confidence_scorer.calculate_overall_confidence(
                data_quality, len(df), 0.8, 0.9
            )
            
            journey_analyzer = JourneyAnalyzer()
            length_analysis = journey_analyzer.analyze_journey_lengths(df)
            
            end_time = time.time()
            processing_time = end_time - start_time
            processing_times.append(processing_time)
        
        # Verify that processing time scales reasonably
        # Should not increase exponentially with dataset size
        for i in range(1, len(processing_times)):
            time_ratio = processing_times[i] / processing_times[i-1]
            size_ratio = dataset_sizes[i] / dataset_sizes[i-1]
            
            # Processing time should not increase more than 2x the size increase
            assert time_ratio < size_ratio * 2
    
    def test_phase3_component_benchmarks(self, large_dataset):
        """Test performance benchmarks for Phase 3 components."""
        benchmarks = {}
        
        # Benchmark confidence scoring
        start_time = time.time()
        confidence_scorer = ConfidenceScorer()
        data_quality = DataQuality(completeness=0.95, consistency=0.90, freshness=0.85)
        confidence = confidence_scorer.calculate_overall_confidence(
            data_quality, len(large_dataset), 0.8, 0.9
        )
        benchmarks['confidence_scoring'] = time.time() - start_time
        
        # Benchmark journey analysis
        start_time = time.time()
        journey_analyzer = JourneyAnalyzer()
        length_analysis = journey_analyzer.analyze_journey_lengths(large_dataset)
        path_analysis = journey_analyzer.analyze_conversion_paths(large_dataset)
        time_analysis = journey_analyzer.analyze_time_to_conversion(large_dataset)
        benchmarks['journey_analysis'] = time.time() - start_time
        
        # Benchmark business insights
        start_time = time.time()
        business_insights_generator = BusinessInsightsGenerator()
        attribution_results = {channel: 0.2 for channel in large_dataset['channel'].unique()}
        comprehensive_insights = business_insights_generator.generate_comprehensive_insights(
            attribution_results=attribution_results,
            journey_analysis={'average_length': 4.0, 'top_paths': [], 'average_time_to_conversion': 10.0},
            data_quality={'completeness': 0.95, 'consistency': 0.90, 'freshness': 0.85},
            sample_size=len(large_dataset)
        )
        benchmarks['business_insights'] = time.time() - start_time
        
        # Verify benchmarks meet performance requirements
        assert benchmarks['confidence_scoring'] < 1.0  # Should be under 1 second
        assert benchmarks['journey_analysis'] < 5.0  # Should be under 5 seconds
        assert benchmarks['business_insights'] < 2.0  # Should be under 2 seconds
        
        # Print benchmarks for monitoring
        print(f"Performance Benchmarks for {len(large_dataset)} records:")
        for component, time_taken in benchmarks.items():
            print(f"  {component}: {time_taken:.2f}s")
