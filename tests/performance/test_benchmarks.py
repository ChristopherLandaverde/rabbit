"""Performance benchmarks for the Multi-Touch Attribution API."""

import pytest
import time
import pandas as pd
from tests.fixtures.data import large_dataset
from tests.fixtures.app import client, sample_csv_file
from src.core.attribution_service import AttributionService
from src.models.enums import AttributionModelType


@pytest.mark.performance
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_linear_attribution_performance(self, large_dataset):
        """Benchmark linear attribution model performance."""
        service = AttributionService()
        
        start_time = time.time()
        result = service.analyze_attribution(
            large_dataset, 
            AttributionModelType.LINEAR
        )
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process 10,000 rows in under 30 seconds
        assert processing_time < 30.0, f"Processing took {processing_time:.2f} seconds, expected < 30 seconds"
        
        # Verify result structure
        assert result.results.total_conversions >= 0
        assert len(result.results.channel_attributions) > 0
    
    def test_time_decay_attribution_performance(self, large_dataset):
        """Benchmark time decay attribution model performance."""
        service = AttributionService()
        
        start_time = time.time()
        result = service.analyze_attribution(
            large_dataset, 
            AttributionModelType.TIME_DECAY
        )
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process 10,000 rows in under 45 seconds (time decay is more complex)
        assert processing_time < 45.0, f"Processing took {processing_time:.2f} seconds, expected < 45 seconds"
    
    def test_api_endpoint_performance(self, client, sample_csv_file):
        """Benchmark API endpoint response time."""
        start_time = time.time()
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", sample_csv_file, "text/csv")},
            data={"model_type": "linear"}
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # API should respond in under 5 seconds
        assert response_time < 5.0, f"API response took {response_time:.2f} seconds, expected < 5 seconds"
        assert response.status_code == 200
    
    def test_concurrent_requests_performance(self, client, sample_csv_file):
        """Test performance with concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            start_time = time.time()
            response = client.post(
                "/attribution/analyze",
                files={"file": ("test.csv", sample_csv_file, "text/csv")},
                data={"model_type": "linear"}
            )
            end_time = time.time()
            
            results.put({
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        # Make 5 concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        response_times = []
        while not results.empty():
            result = results.get()
            assert result['status_code'] == 200
            response_times.append(result['response_time'])
        
        # All requests should complete successfully
        assert len(response_times) == 5
        
        # Average response time should still be reasonable
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 10.0, f"Average concurrent response time: {avg_response_time:.2f}s"
    
    def test_memory_usage_with_large_dataset(self, large_dataset):
        """Test memory usage with large dataset."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        service = AttributionService()
        result = service.analyze_attribution(
            large_dataset, 
            AttributionModelType.LINEAR
        )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be less than 1GB
        assert memory_increase < 1024, f"Memory increased by {memory_increase:.2f}MB, expected < 1024MB"
        
        # Verify result is still correct
        assert result.results.total_conversions >= 0


@pytest.mark.performance
class TestScalabilityBenchmarks:
    """Scalability benchmark tests."""
    
    @pytest.mark.parametrize("dataset_size", [100, 1000, 5000])
    def test_dataset_size_scalability(self, dataset_size):
        """Test performance scaling with different dataset sizes."""
        import random
        from datetime import datetime, timedelta
        
        # Generate dataset of specified size
        channels = ['email', 'social', 'paid_search', 'organic']
        event_types = ['view', 'click', 'conversion']
        
        data = []
        base_time = datetime(2024, 1, 1)
        
        for i in range(dataset_size):
            customer_id = f"cust_{i % (dataset_size // 10)}"  # 10% unique customers
            data.append({
                'timestamp': base_time + timedelta(hours=i),
                'channel': random.choice(channels),
                'event_type': random.choice(event_types),
                'customer_id': customer_id,
                'session_id': f"sess_{i}",
                'email': f"user{i % (dataset_size // 10)}@example.com",
                'conversion_value': random.choice([None, None, None, random.uniform(10, 500)])
            })
        
        df = pd.DataFrame(data)
        
        service = AttributionService()
        start_time = time.time()
        
        result = service.analyze_attribution(
            df, 
            AttributionModelType.LINEAR
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Processing time should scale roughly linearly
        expected_max_time = dataset_size / 1000 * 3  # 3 seconds per 1000 rows
        assert processing_time < expected_max_time, f"Processing {dataset_size} rows took {processing_time:.2f}s, expected < {expected_max_time:.2f}s"
        
        # Result should be valid
        assert result.results.total_conversions >= 0
    
    def test_attribution_model_performance_comparison(self, large_dataset):
        """Compare performance of different attribution models."""
        service = AttributionService()
        models = [
            AttributionModelType.LINEAR,
            AttributionModelType.FIRST_TOUCH,
            AttributionModelType.LAST_TOUCH,
            AttributionModelType.TIME_DECAY,
            AttributionModelType.POSITION_BASED
        ]
        
        model_times = {}
        
        for model_type in models:
            start_time = time.time()
            result = service.analyze_attribution(large_dataset, model_type)
            end_time = time.time()
            
            processing_time = end_time - start_time
            model_times[model_type] = processing_time
            
            # All models should complete successfully
            assert result.results.total_conversions >= 0
        
        # Linear and simple models should be fastest
        assert model_times[AttributionModelType.LINEAR] < model_times[AttributionModelType.TIME_DECAY]
        assert model_times[AttributionModelType.FIRST_TOUCH] < model_times[AttributionModelType.TIME_DECAY]
        assert model_times[AttributionModelType.LAST_TOUCH] < model_times[AttributionModelType.TIME_DECAY]


@pytest.mark.performance
class TestMemoryEfficiency:
    """Memory efficiency tests."""
    
    def test_memory_cleanup_after_processing(self):
        """Test that memory is properly cleaned up after processing."""
        import gc
        import psutil
        import os
        
        # Create a large dataset
        large_data = []
        for i in range(5000):
            large_data.append({
                'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
                'channel': f'channel_{i % 5}',
                'event_type': 'click',
                'customer_id': f'cust_{i % 100}'
            })
        
        df = pd.DataFrame(large_data)
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process the data
        service = AttributionService()
        result = service.analyze_attribution(df, AttributionModelType.LINEAR)
        
        # Clear references and force garbage collection
        del df, result, service
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should return close to initial levels
        assert memory_increase < 100, f"Memory leak detected: {memory_increase:.2f}MB increase"
