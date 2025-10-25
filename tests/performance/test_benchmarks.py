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


@pytest.mark.performance
@pytest.mark.slow
class TestAdvancedPerformanceBenchmarks:
    """Advanced performance benchmark tests."""
    
    def test_very_large_dataset_performance(self):
        """Test performance with very large dataset (100k rows)."""
        import random
        from datetime import datetime, timedelta
        
        # Generate 100k row dataset
        channels = ['email', 'social', 'paid_search', 'organic', 'display', 'affiliate']
        event_types = ['view', 'click', 'conversion']
        
        data = []
        base_time = datetime(2024, 1, 1)
        
        print("Generating 100k row dataset...")
        for i in range(100000):
            if i % 10000 == 0:
                print(f"Generated {i} rows...")
            data.append({
                'timestamp': base_time + timedelta(hours=i % 8760),  # Spread over a year
                'channel': random.choice(channels),
                'event_type': random.choice(event_types),
                'customer_id': f'cust_{i % 10000}',  # 10k unique customers
                'session_id': f'sess_{i}',
                'email': f'user{i % 10000}@example.com',
                'conversion_value': random.choice([None, None, None, None, random.uniform(10, 1000)])
            })
        
        df = pd.DataFrame(data)
        print(f"Generated dataset with {len(df)} rows")
        
        service = AttributionService()
        start_time = time.time()
        
        result = service.analyze_attribution(df, AttributionModelType.LINEAR)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 100k rows in under 5 minutes
        assert processing_time < 300, f"Processing 100k rows took {processing_time:.2f} seconds, expected < 300 seconds"
        
        # Verify result
        assert result.results.total_conversions >= 0
        assert len(result.results.channel_attributions) > 0
    
    def test_attribution_model_memory_efficiency(self):
        """Test memory efficiency across different attribution models."""
        import psutil
        import os
        
        # Create medium-sized dataset
        data = []
        for i in range(10000):
            data.append({
                'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
                'channel': f'channel_{i % 10}',
                'event_type': 'click' if i % 10 != 0 else 'conversion',
                'customer_id': f'cust_{i % 1000}',
                'conversion_value': random.uniform(10, 500) if i % 10 == 0 else None
            })
        
        df = pd.DataFrame(data)
        service = AttributionService()
        
        models = [
            AttributionModelType.LINEAR,
            AttributionModelType.TIME_DECAY,
            AttributionModelType.POSITION_BASED
        ]
        
        memory_usage = {}
        
        for model_type in models:
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            result = service.analyze_attribution(df, model_type)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_usage[model_type] = final_memory - initial_memory
            
            # Clean up
            del result
        
        # All models should use reasonable memory
        for model_type, memory in memory_usage.items():
            assert memory < 500, f"{model_type} used {memory:.2f}MB, expected < 500MB"
    
    def test_concurrent_processing_performance(self):
        """Test performance with concurrent processing."""
        import threading
        import queue
        
        # Create multiple datasets
        datasets = []
        for i in range(5):
            data = []
            for j in range(2000):  # 2k rows each
                data.append({
                    'timestamp': f'2024-01-01 10:{j % 60:02d}:00',
                    'channel': f'channel_{j % 5}',
                    'event_type': 'click' if j % 10 != 0 else 'conversion',
                    'customer_id': f'cust_{j % 200}',
                    'conversion_value': random.uniform(10, 500) if j % 10 == 0 else None
                })
            datasets.append(pd.DataFrame(data))
        
        results_queue = queue.Queue()
        
        def process_dataset(dataset, dataset_id):
            service = AttributionService()
            start_time = time.time()
            
            result = service.analyze_attribution(dataset, AttributionModelType.LINEAR)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            results_queue.put({
                'dataset_id': dataset_id,
                'processing_time': processing_time,
                'conversions': result.results.total_conversions
            })
        
        # Process datasets concurrently
        threads = []
        start_time = time.time()
        
        for i, dataset in enumerate(datasets):
            thread = threading.Thread(target=process_dataset, args=(dataset, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # All datasets should be processed
        assert len(results) == 5
        
        # Total time should be reasonable (concurrent processing)
        assert total_time < 60, f"Concurrent processing took {total_time:.2f}s, expected < 60s"
        
        # Individual processing times should be reasonable
        for result in results:
            assert result['processing_time'] < 30, f"Dataset {result['dataset_id']} took {result['processing_time']:.2f}s"
            assert result['conversions'] >= 0
    
    def test_data_quality_impact_on_performance(self):
        """Test how data quality affects processing performance."""
        import random
        
        # Create datasets with different quality levels
        quality_scenarios = {
            'high_quality': 0.95,  # 95% valid data
            'medium_quality': 0.80,  # 80% valid data
            'low_quality': 0.60   # 60% valid data
        }
        
        performance_results = {}
        
        for quality_name, quality_ratio in quality_scenarios.items():
            data = []
            for i in range(5000):
                # Add invalid data based on quality ratio
                if random.random() > quality_ratio:
                    # Add invalid data
                    if random.random() < 0.5:
                        # Missing required field
                        data.append({
                            'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
                            'channel': f'channel_{i % 5}',
                            'event_type': 'click',
                            # Missing customer_id
                        })
                    else:
                        # Invalid data type
                        data.append({
                            'timestamp': 'invalid_timestamp',
                            'channel': f'channel_{i % 5}',
                            'event_type': 'click',
                            'customer_id': f'cust_{i % 100}'
                        })
                else:
                    # Valid data
                    data.append({
                        'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
                        'channel': f'channel_{i % 5}',
                        'event_type': 'click' if i % 10 != 0 else 'conversion',
                        'customer_id': f'cust_{i % 100}',
                        'conversion_value': random.uniform(10, 500) if i % 10 == 0 else None
                    })
            
            df = pd.DataFrame(data)
            service = AttributionService()
            
            start_time = time.time()
            try:
                result = service.analyze_attribution(df, AttributionModelType.LINEAR)
                end_time = time.time()
                processing_time = end_time - start_time
                success = True
            except Exception as e:
                processing_time = time.time() - start_time
                success = False
                result = None
            
            performance_results[quality_name] = {
                'processing_time': processing_time,
                'success': success,
                'conversions': result.results.total_conversions if result else 0
            }
        
        # High quality should be fastest
        assert performance_results['high_quality']['processing_time'] < performance_results['low_quality']['processing_time']
        
        # High quality should succeed
        assert performance_results['high_quality']['success'] is True
    
    def test_attribution_accuracy_benchmark(self):
        """Benchmark attribution accuracy with known ground truth."""
        # Create dataset with known attribution patterns
        data = []
        
        # Customer 1: Linear journey with 3 touchpoints
        data.extend([
            {'timestamp': '2024-01-01 10:00:00', 'channel': 'email', 'event_type': 'click', 'customer_id': 'cust_001'},
            {'timestamp': '2024-01-01 11:00:00', 'channel': 'social', 'event_type': 'view', 'customer_id': 'cust_001'},
            {'timestamp': '2024-01-01 12:00:00', 'channel': 'paid_search', 'event_type': 'conversion', 'customer_id': 'cust_001', 'conversion_value': 100.0}
        ])
        
        # Customer 2: First touch only
        data.extend([
            {'timestamp': '2024-01-02 10:00:00', 'channel': 'organic', 'event_type': 'conversion', 'customer_id': 'cust_002', 'conversion_value': 50.0}
        ])
        
        # Customer 3: Last touch only
        data.extend([
            {'timestamp': '2024-01-03 10:00:00', 'channel': 'email', 'event_type': 'click', 'customer_id': 'cust_003'},
            {'timestamp': '2024-01-03 11:00:00', 'channel': 'display', 'event_type': 'conversion', 'customer_id': 'cust_003', 'conversion_value': 75.0}
        ])
        
        df = pd.DataFrame(data)
        service = AttributionService()
        
        # Test different models
        models = [
            AttributionModelType.LINEAR,
            AttributionModelType.FIRST_TOUCH,
            AttributionModelType.LAST_TOUCH
        ]
        
        results = {}
        for model_type in models:
            start_time = time.time()
            result = service.analyze_attribution(df, model_type)
            end_time = time.time()
            
            results[model_type] = {
                'processing_time': end_time - start_time,
                'attributions': result.results.channel_attributions,
                'total_conversions': result.results.total_conversions,
                'total_revenue': result.results.total_revenue
            }
        
        # Verify results make sense
        for model_type, result in results.items():
            assert result['total_conversions'] == 3
            assert result['total_revenue'] == 225.0  # 100 + 50 + 75
            
            # Processing should be fast for small dataset
            assert result['processing_time'] < 1.0, f"{model_type} took {result['processing_time']:.3f}s"
            
            # Check attribution logic
            attributions = result['attributions']
            if model_type == AttributionModelType.LINEAR:
                # cust_001: email=1/3, social=1/3, paid_search=1/3
                # cust_002: organic=1
                # cust_003: email=1/2, display=1/2
                assert len(attributions) >= 4  # email, social, paid_search, organic, display
            elif model_type == AttributionModelType.FIRST_TOUCH:
                # Only first touchpoints get credit
                assert 'email' in attributions or 'organic' in attributions
            elif model_type == AttributionModelType.LAST_TOUCH:
                # Only last touchpoints get credit
                assert 'paid_search' in attributions or 'organic' in attributions or 'display' in attributions


@pytest.mark.performance
class TestResourceUtilization:
    """Test resource utilization patterns."""
    
    def test_cpu_utilization_during_processing(self):
        """Test CPU utilization during processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Create a dataset that will require significant processing
        data = []
        for i in range(20000):  # 20k rows
            data.append({
                'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
                'channel': f'channel_{i % 20}',  # 20 different channels
                'event_type': 'click' if i % 10 != 0 else 'conversion',
                'customer_id': f'cust_{i % 2000}',  # 2k unique customers
                'conversion_value': random.uniform(10, 1000) if i % 10 == 0 else None
            })
        
        df = pd.DataFrame(data)
        service = AttributionService()
        
        # Monitor CPU usage
        cpu_samples = []
        
        def monitor_cpu():
            while True:
                cpu_samples.append(process.cpu_percent())
                time.sleep(0.1)
        
        import threading
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        start_time = time.time()
        result = service.analyze_attribution(df, AttributionModelType.TIME_DECAY)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete in reasonable time
        assert processing_time < 60, f"Processing took {processing_time:.2f}s, expected < 60s"
        
        # CPU utilization should be reasonable (not 100% sustained)
        if cpu_samples:
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            max_cpu = max(cpu_samples)
            
            # Average CPU should be reasonable
            assert avg_cpu < 90, f"Average CPU usage: {avg_cpu:.1f}%, expected < 90%"
            
            # Max CPU can be high but not sustained
            assert max_cpu < 100, f"Max CPU usage: {max_cpu:.1f}%, expected < 100%"
    
    def test_memory_growth_pattern(self):
        """Test memory growth pattern during processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Create progressively larger datasets
        dataset_sizes = [1000, 5000, 10000, 20000]
        memory_usage = []
        
        for size in dataset_sizes:
            data = []
            for i in range(size):
                data.append({
                    'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
                    'channel': f'channel_{i % 10}',
                    'event_type': 'click' if i % 10 != 0 else 'conversion',
                    'customer_id': f'cust_{i % (size // 10)}',
                    'conversion_value': random.uniform(10, 500) if i % 10 == 0 else None
                })
            
            df = pd.DataFrame(data)
            service = AttributionService()
            
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            result = service.analyze_attribution(df, AttributionModelType.LINEAR)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_usage.append(final_memory - initial_memory)
            
            # Clean up
            del df, result, service
            import gc
            gc.collect()
        
        # Memory usage should scale reasonably with dataset size
        for i in range(1, len(memory_usage)):
            size_ratio = dataset_sizes[i] / dataset_sizes[i-1]
            memory_ratio = memory_usage[i] / memory_usage[i-1] if memory_usage[i-1] > 0 else 1
            
            # Memory should not grow faster than dataset size
            assert memory_ratio <= size_ratio * 1.5, f"Memory growth too high: {memory_ratio:.2f}x for {size_ratio:.2f}x dataset size"
    
    def test_processing_time_consistency(self):
        """Test that processing time is consistent across runs."""
        # Create a standard dataset
        data = []
        for i in range(5000):
            data.append({
                'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
                'channel': f'channel_{i % 5}',
                'event_type': 'click' if i % 10 != 0 else 'conversion',
                'customer_id': f'cust_{i % 500}',
                'conversion_value': random.uniform(10, 500) if i % 10 == 0 else None
            })
        
        df = pd.DataFrame(data)
        service = AttributionService()
        
        # Run multiple times
        processing_times = []
        for _ in range(5):
            start_time = time.time()
            result = service.analyze_attribution(df, AttributionModelType.LINEAR)
            end_time = time.time()
            processing_times.append(end_time - start_time)
        
        # Processing times should be consistent (within 50% variance)
        avg_time = sum(processing_times) / len(processing_times)
        max_variance = max(abs(t - avg_time) for t in processing_times)
        
        assert max_variance < avg_time * 0.5, f"Processing time variance too high: {max_variance:.3f}s (avg: {avg_time:.3f}s)"
        
        # All runs should complete successfully
        assert all(t < 30 for t in processing_times), f"Some runs took too long: {processing_times}"
