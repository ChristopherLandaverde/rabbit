"""Performance and load tests for Phase 4 production readiness features."""

import pytest
import time
import asyncio
import concurrent.futures
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import statistics

from src.core.security import APIKeyManager, SecurityMiddleware, InputValidator
from src.core.auth import get_current_user, require_read_permission, require_write_permission
from src.core.caching import CacheManager, AttributionCache, APICache
from src.core.monitoring import HealthChecker, MetricsCollector, AlertManager
from src.core.logging import SecurityLogger, PerformanceLogger, BusinessLogger
from src.config import get_settings


class TestPhase4SecurityPerformance:
    """Test Phase 4 security features performance."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.api_key_manager = APIKeyManager()
        self.security_middleware = SecurityMiddleware()
        self.input_validator = InputValidator()
    
    @patch('src.core.security.redis.Redis')
    def test_api_key_generation_performance(self, mock_redis):
        """Test API key generation performance."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.setex.return_value = True
        
        # Test single key generation performance
        start_time = time.time()
        api_key = self.api_key_manager.generate_api_key("test_user", ["read", "write"])
        end_time = time.time()
        
        assert isinstance(api_key, str)
        assert len(api_key) == 64
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test multiple key generation performance
        start_time = time.time()
        for i in range(100):
            self.api_key_manager.generate_api_key(f"user_{i}", ["read", "write"])
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 100 keys
    
    @patch('src.core.security.redis.Redis')
    def test_api_key_validation_performance(self, mock_redis):
        """Test API key validation performance."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": True,
            "rate_limit": 1000
        }
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.setex.return_value = True
        
        # Test single validation performance
        start_time = time.time()
        user_info = self.api_key_manager.validate_api_key("test_key")
        end_time = time.time()
        
        assert user_info["user_id"] == "test_user"
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test multiple validation performance
        start_time = time.time()
        for i in range(100):
            self.api_key_manager.validate_api_key("test_key")
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 100 validations
    
    @patch('src.core.security.redis.Redis')
    def test_rate_limiting_performance(self, mock_redis):
        """Test rate limiting performance."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        key_metadata = {"rate_limit": 1000}
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 5  # Under limit
        mock_redis_client.zadd.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.zremrangebyscore.return_value = 0
        
        # Test single rate limit check performance
        start_time = time.time()
        rate_limit_ok = self.api_key_manager.check_rate_limit("test_key", "test_endpoint")
        end_time = time.time()
        
        assert rate_limit_ok is True
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test multiple rate limit checks performance
        start_time = time.time()
        for i in range(100):
            self.api_key_manager.check_rate_limit("test_key", f"endpoint_{i}")
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 100 checks
    
    def test_input_validation_performance(self):
        """Test input validation performance."""
        # Test file upload validation performance
        start_time = time.time()
        for i in range(1000):
            self.input_validator.validate_file_upload(1024, "test.csv")
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 validations
        
        # Test string sanitization performance
        start_time = time.time()
        for i in range(1000):
            self.input_validator.sanitize_string(f"test string {i}")
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 sanitizations
        
        # Test model parameter validation performance
        start_time = time.time()
        for i in range(1000):
            self.input_validator.validate_model_parameters(
                "time_decay", half_life_days=7.0
            )
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 validations


class TestPhase4CachingPerformance:
    """Test Phase 4 caching features performance."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.cache_manager = CacheManager()
        self.attribution_cache = AttributionCache()
        self.api_cache = APICache()
    
    def test_cache_operations_performance(self):
        """Test cache operations performance."""
        # Test cache set performance
        start_time = time.time()
        for i in range(1000):
            self.cache_manager.set(f"key_{i}", f"value_{i}", 3600)
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 sets
        
        # Test cache get performance
        start_time = time.time()
        for i in range(1000):
            cached_data = self.cache_manager.get(f"key_{i}")
            assert cached_data == f"value_{i}"
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 gets
        
        # Test cache delete performance
        start_time = time.time()
        for i in range(1000):
            self.cache_manager.delete(f"key_{i}")
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 deletes
    
    def test_attribution_cache_performance(self):
        """Test attribution cache performance."""
        # Test attribution result caching performance
        start_time = time.time()
        for i in range(1000):
            file_hash = f"hash_{i}"
            model_type = "linear"
            model_params = {"param": f"value_{i}"}
            result_data = {"attribution": f"result_{i}", "confidence": 0.95}
            
            self.attribution_cache.set_attribution_result(
                file_hash, model_type, model_params, result_data
            )
        end_time = time.time()
        
        assert (end_time - start_time) < 2.0  # Should be fast for 1000 sets
        
        # Test attribution result retrieval performance
        start_time = time.time()
        for i in range(1000):
            file_hash = f"hash_{i}"
            model_type = "linear"
            model_params = {"param": f"value_{i}"}
            
            cached_result = self.attribution_cache.get_attribution_result(
                file_hash, model_type, model_params
            )
            assert cached_result["attribution"] == f"result_{i}"
        end_time = time.time()
        
        assert (end_time - start_time) < 2.0  # Should be fast for 1000 gets
    
    def test_api_cache_performance(self):
        """Test API cache performance."""
        # Test available methods caching performance
        start_time = time.time()
        for i in range(1000):
            methods_data = {"attribution_models": [], "linking_methods": []}
            self.api_cache.set_available_methods(methods_data)
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 sets
        
        # Test available methods retrieval performance
        start_time = time.time()
        for i in range(1000):
            cached_methods = self.api_cache.get_available_methods()
            assert cached_methods is not None
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 gets
    
    def test_cache_hit_rate_performance(self):
        """Test cache hit rate performance."""
        # Test cache hit rate calculation
        self.cache_manager.cache_stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
        
        # Perform operations
        for i in range(1000):
            self.cache_manager.set(f"key_{i}", f"value_{i}", 3600)
            self.cache_manager.get(f"key_{i}")  # Hit
            self.cache_manager.get(f"miss_{i}")  # Miss
        
        # Test stats calculation performance
        start_time = time.time()
        stats = self.cache_manager.get_stats()
        end_time = time.time()
        
        assert stats["hits"] == 1000
        assert stats["misses"] == 1000
        assert stats["hit_rate"] == 0.5
        assert (end_time - start_time) < 0.1  # Should be fast


class TestPhase4MonitoringPerformance:
    """Test Phase 4 monitoring features performance."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
    
    @patch('src.core.monitoring.redis.Redis')
    def test_health_checking_performance(self, mock_redis):
        """Test health checking performance."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {
            "used_memory_human": "1.2M",
            "connected_clients": 5,
            "uptime_in_seconds": 3600
        }
        
        # Test database health check performance
        start_time = time.time()
        database_health = self.health_checker.check_database_health()
        end_time = time.time()
        
        assert database_health["status"] == "healthy"
        assert (end_time - start_time) < 0.5  # Should be fast
        
        # Test system health check performance
        start_time = time.time()
        system_health = self.health_checker.check_system_health()
        end_time = time.time()
        
        assert "cpu_percent" in system_health
        assert (end_time - start_time) < 0.5  # Should be fast
        
        # Test application health check performance
        start_time = time.time()
        application_health = self.health_checker.check_application_health()
        end_time = time.time()
        
        assert "request_count" in application_health
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test comprehensive health check performance
        start_time = time.time()
        comprehensive_health = self.health_checker.get_comprehensive_health()
        end_time = time.time()
        
        assert "status" in comprehensive_health
        assert (end_time - start_time) < 1.0  # Should be fast
    
    def test_metrics_collection_performance(self):
        """Test metrics collection performance."""
        # Test metric recording performance
        start_time = time.time()
        for i in range(10000):
            self.metrics_collector.record_metric("test_metric", float(i))
        end_time = time.time()
        
        assert (end_time - start_time) < 2.0  # Should be fast for 10000 metrics
        
        # Test metric summary performance
        start_time = time.time()
        summary = self.metrics_collector.get_metric_summary("test_metric")
        end_time = time.time()
        
        assert summary["count"] == 10000
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test all metrics retrieval performance
        start_time = time.time()
        all_metrics = self.metrics_collector.get_all_metrics()
        end_time = time.time()
        
        assert len(all_metrics) == 10000
        assert (end_time - start_time) < 0.5  # Should be fast
    
    def test_alert_system_performance(self):
        """Test alert system performance."""
        # Test alert checking performance
        health_data = {
            "components": {
                "application": {"error_rate": 0.1},
                "system": {"cpu_percent": 85.0, "memory_percent": 85.0},
                "database": {"status": "unhealthy"}
            }
        }
        
        start_time = time.time()
        alerts = self.alert_manager.check_alerts(health_data)
        end_time = time.time()
        
        assert len(alerts) == 4
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test multiple alert checks performance
        start_time = time.time()
        for i in range(1000):
            self.alert_manager.check_alerts(health_data)
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 1000 checks
    
    def test_request_recording_performance(self):
        """Test request recording performance."""
        # Test request recording performance
        start_time = time.time()
        for i in range(10000):
            self.health_checker.record_request(success=(i % 10 != 0))
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast for 10000 requests
        
        # Test metrics retrieval performance
        start_time = time.time()
        metrics = self.health_checker.get_metrics()
        end_time = time.time()
        
        assert metrics["request_count"] == 10000
        assert (end_time - start_time) < 0.1  # Should be fast


class TestPhase4LoggingPerformance:
    """Test Phase 4 logging features performance."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.security_logger = SecurityLogger()
        self.performance_logger = PerformanceLogger()
        self.business_logger = BusinessLogger()
    
    def test_security_logging_performance(self):
        """Test security logging performance."""
        with patch.object(self.security_logger.logger, 'info') as mock_info:
            # Test authentication logging performance
            start_time = time.time()
            for i in range(1000):
                self.security_logger.log_authentication_attempt(
                    f"key_{i}", True, f"192.168.1.{i % 255}"
                )
            end_time = time.time()
            
            assert (end_time - start_time) < 1.0  # Should be fast for 1000 logs
            
            # Test rate limit logging performance
            start_time = time.time()
            for i in range(1000):
                self.security_logger.log_rate_limit_exceeded(
                    f"key_{i}", f"GET:/endpoint_{i}", f"192.168.1.{i % 255}"
                )
            end_time = time.time()
            
            assert (end_time - start_time) < 1.0  # Should be fast for 1000 logs
    
    def test_performance_logging_performance(self):
        """Test performance logging performance."""
        with patch.object(self.performance_logger.logger, 'info') as mock_info:
            # Test request metrics logging performance
            start_time = time.time()
            for i in range(1000):
                mock_request = Mock()
                mock_request.method = "GET"
                mock_request.url = f"http://test.com/api/{i}"
                mock_request.client.host = f"192.168.1.{i % 255}"
                mock_request.headers = {"user-agent": f"test-agent-{i}"}
                
                mock_response = Mock()
                mock_response.status_code = 200
                
                user_info = {"user_id": f"user_{i}"}
                
                self.performance_logger.log_request_metrics(
                    mock_request, mock_response, 1.5, user_info
                )
            end_time = time.time()
            
            assert (end_time - start_time) < 2.0  # Should be fast for 1000 logs
    
    def test_business_logging_performance(self):
        """Test business logging performance."""
        with patch.object(self.business_logger.logger, 'info') as mock_info:
            # Test API usage logging performance
            start_time = time.time()
            for i in range(1000):
                self.business_logger.log_api_usage(
                    f"user_{i}", f"/endpoint_{i}", f"model_{i % 5}"
                )
            end_time = time.time()
            
            assert (end_time - start_time) < 1.0  # Should be fast for 1000 logs
            
            # Test attribution insights logging performance
            start_time = time.time()
            for i in range(1000):
                self.business_logger.log_attribution_insights(
                    f"user_{i}", f"model_{i % 5}", i, [f"channel_{j}" for j in range(3)]
                )
            end_time = time.time()
            
            assert (end_time - start_time) < 1.0  # Should be fast for 1000 logs


class TestPhase4LoadTesting:
    """Test Phase 4 load testing scenarios."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.cache_manager = CacheManager()
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
    
    def test_concurrent_cache_operations(self):
        """Test concurrent cache operations."""
        def cache_operation(operation_id):
            """Perform cache operations for a specific operation ID."""
            start_time = time.time()
            
            # Perform cache operations
            for i in range(100):
                key = f"concurrent_key_{operation_id}_{i}"
                value = f"concurrent_value_{operation_id}_{i}"
                
                self.cache_manager.set(key, value, 3600)
                cached_value = self.cache_manager.get(key)
                assert cached_value == value
                
                self.cache_manager.delete(key)
            
            end_time = time.time()
            return end_time - start_time
        
        # Test concurrent operations
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(cache_operation, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        # Verify all operations completed successfully
        assert len(results) == 10
        assert all(result < 5.0 for result in results)  # Each operation should be fast
        assert (end_time - start_time) < 10.0  # Total time should be reasonable
    
    def test_concurrent_health_checking(self):
        """Test concurrent health checking."""
        def health_check_operation(operation_id):
            """Perform health check operations for a specific operation ID."""
            start_time = time.time()
            
            # Perform health check operations
            for i in range(100):
                self.health_checker.record_request(success=(i % 10 != 0))
                
                if i % 10 == 0:
                    metrics = self.health_checker.get_metrics()
                    assert "request_count" in metrics
                    assert "error_count" in metrics
                    assert "error_rate" in metrics
            
            end_time = time.time()
            return end_time - start_time
        
        # Test concurrent operations
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(health_check_operation, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        # Verify all operations completed successfully
        assert len(results) == 10
        assert all(result < 5.0 for result in results)  # Each operation should be fast
        assert (end_time - start_time) < 10.0  # Total time should be reasonable
    
    def test_concurrent_metrics_collection(self):
        """Test concurrent metrics collection."""
        def metrics_operation(operation_id):
            """Perform metrics collection operations for a specific operation ID."""
            start_time = time.time()
            
            # Perform metrics operations
            for i in range(1000):
                self.metrics_collector.record_metric(
                    f"metric_{operation_id}", float(i), {"tag": f"value_{i}"}
                )
                
                if i % 100 == 0:
                    summary = self.metrics_collector.get_metric_summary(f"metric_{operation_id}")
                    assert "count" in summary
                    assert "avg" in summary
            
            end_time = time.time()
            return end_time - start_time
        
        # Test concurrent operations
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(metrics_operation, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        # Verify all operations completed successfully
        assert len(results) == 5
        assert all(result < 10.0 for result in results)  # Each operation should be fast
        assert (end_time - start_time) < 15.0  # Total time should be reasonable
    
    def test_memory_usage_under_load(self):
        """Test memory usage under load."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform load operations
        for i in range(10000):
            self.cache_manager.set(f"load_key_{i}", f"load_value_{i}", 3600)
            self.health_checker.record_request(success=(i % 10 != 0))
            self.metrics_collector.record_metric("load_metric", float(i))
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100.0, f"Memory increase too high: {memory_increase}MB"
    
    def test_response_time_consistency(self):
        """Test response time consistency under load."""
        # Test cache operations response time consistency
        cache_times = []
        for i in range(1000):
            start_time = time.time()
            self.cache_manager.set(f"consistency_key_{i}", f"consistency_value_{i}", 3600)
            end_time = time.time()
            cache_times.append(end_time - start_time)
        
        # Calculate statistics
        mean_time = statistics.mean(cache_times)
        std_time = statistics.stdev(cache_times)
        max_time = max(cache_times)
        
        # Response times should be consistent
        assert mean_time < 0.01  # Mean should be fast
        assert std_time < 0.01  # Standard deviation should be low
        assert max_time < 0.1  # Maximum should be reasonable
        
        # Test health checking response time consistency
        health_times = []
        for i in range(1000):
            start_time = time.time()
            self.health_checker.record_request(success=True)
            end_time = time.time()
            health_times.append(end_time - start_time)
        
        # Calculate statistics
        mean_time = statistics.mean(health_times)
        std_time = statistics.stdev(health_times)
        max_time = max(health_times)
        
        # Response times should be consistent
        assert mean_time < 0.001  # Mean should be very fast
        assert std_time < 0.001  # Standard deviation should be very low
        assert max_time < 0.01  # Maximum should be reasonable


class TestPhase4ScalabilityLimits:
    """Test Phase 4 scalability limits."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.cache_manager = CacheManager()
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
    
    def test_cache_capacity_limits(self):
        """Test cache capacity limits."""
        # Test cache with large number of keys
        start_time = time.time()
        for i in range(100000):
            self.cache_manager.set(f"capacity_key_{i}", f"capacity_value_{i}", 3600)
        end_time = time.time()
        
        # Should be able to handle 100k keys
        assert (end_time - start_time) < 30.0  # Should be reasonable time
        
        # Test retrieval of random keys
        start_time = time.time()
        for i in range(1000):
            random_key = f"capacity_key_{i * 100}"
            cached_value = self.cache_manager.get(random_key)
            assert cached_value == f"capacity_value_{i * 100}"
        end_time = time.time()
        
        # Should be able to retrieve keys quickly
        assert (end_time - start_time) < 1.0  # Should be fast
    
    def test_metrics_collection_limits(self):
        """Test metrics collection limits."""
        # Test metrics collection with large number of metrics
        start_time = time.time()
        for i in range(100000):
            self.metrics_collector.record_metric("limit_metric", float(i))
        end_time = time.time()
        
        # Should be able to handle 100k metrics
        assert (end_time - start_time) < 30.0  # Should be reasonable time
        
        # Test metric summary with large dataset
        start_time = time.time()
        summary = self.metrics_collector.get_metric_summary("limit_metric")
        end_time = time.time()
        
        # Should be able to calculate summary quickly
        assert summary["count"] == 100000
        assert (end_time - start_time) < 1.0  # Should be fast
    
    def test_health_checker_limits(self):
        """Test health checker limits."""
        # Test health checker with large number of requests
        start_time = time.time()
        for i in range(100000):
            self.health_checker.record_request(success=(i % 10 != 0))
        end_time = time.time()
        
        # Should be able to handle 100k requests
        assert (end_time - start_time) < 10.0  # Should be reasonable time
        
        # Test metrics retrieval with large dataset
        start_time = time.time()
        metrics = self.health_checker.get_metrics()
        end_time = time.time()
        
        # Should be able to retrieve metrics quickly
        assert metrics["request_count"] == 100000
        assert (end_time - start_time) < 0.1  # Should be fast
    
    def test_concurrent_load_limits(self):
        """Test concurrent load limits."""
        def load_operation(operation_id):
            """Perform load operations for a specific operation ID."""
            for i in range(1000):
                self.cache_manager.set(f"load_key_{operation_id}_{i}", f"load_value_{operation_id}_{i}", 3600)
                self.health_checker.record_request(success=(i % 10 != 0))
                self.metrics_collector.record_metric(f"load_metric_{operation_id}", float(i))
        
        # Test concurrent operations with high load
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(load_operation, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        # Should be able to handle concurrent load
        assert len(results) == 20
        assert (end_time - start_time) < 60.0  # Total time should be reasonable
