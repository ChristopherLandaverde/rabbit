"""Integration tests for Phase 4 production readiness features."""

import pytest
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.main import app
from src.core.security import APIKeyManager, SecurityMiddleware, InputValidator
from src.core.auth import get_current_user, require_read_permission, require_write_permission
from src.core.caching import CacheManager, AttributionCache, APICache
from src.core.monitoring import HealthChecker, MetricsCollector, AlertManager
from src.core.logging import SecurityLogger, PerformanceLogger, BusinessLogger
from src.config import get_settings


class TestPhase4SecurityIntegration:
    """Test Phase 4 security features integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
        self.api_key_manager = APIKeyManager()
        self.security_middleware = SecurityMiddleware()
        self.input_validator = InputValidator()
    
    @patch('src.core.security.redis.Redis')
    def test_security_flow_integration(self, mock_redis):
        """Test complete security flow integration."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Test API key generation
        api_key = self.api_key_manager.generate_api_key("test_user", ["read", "write"])
        assert isinstance(api_key, str)
        assert len(api_key) == 64
        
        # Test API key validation
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": True,
            "rate_limit": 1000
        }
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 5  # Under rate limit
        
        user_info = self.api_key_manager.validate_api_key(api_key)
        assert user_info["user_id"] == "test_user"
        assert user_info["permissions"] == ["read", "write"]
        
        # Test rate limiting
        rate_limit_ok = self.api_key_manager.check_rate_limit(api_key, "test_endpoint")
        assert rate_limit_ok is True
        
        # Test request validation
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.headers = {"X-API-Key": api_key}
        
        result = self.security_middleware.validate_request(mock_request)
        assert result["user_id"] == "test_user"
    
    def test_input_validation_integration(self):
        """Test input validation integration."""
        # Test file upload validation
        self.input_validator.validate_file_upload(1024, "test.csv")  # Should not raise
        
        with pytest.raises(Exception):
            self.input_validator.validate_file_upload(1024, "test.txt")  # Invalid type
        
        # Test string sanitization
        sanitized = self.input_validator.sanitize_string("  test string  ")
        assert sanitized == "test string"
        
        # Test model parameter validation
        result = self.input_validator.validate_model_parameters(
            "time_decay", half_life_days=7.0
        )
        assert result["half_life_days"] == 7.0
        
        with pytest.raises(Exception):
            self.input_validator.validate_model_parameters(
                "time_decay", half_life_days=-1.0
            )
    
    def test_security_headers_integration(self):
        """Test security headers integration."""
        mock_response = Mock()
        mock_response.headers = {}
        
        result = self.security_middleware.add_security_headers(mock_response)
        
        assert "X-Content-Type-Options" in result.headers
        assert "X-Frame-Options" in result.headers
        assert "X-XSS-Protection" in result.headers
        assert "Strict-Transport-Security" in result.headers
        assert "Referrer-Policy" in result.headers


class TestPhase4CachingIntegration:
    """Test Phase 4 caching features integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.cache_manager = CacheManager()
        self.attribution_cache = AttributionCache()
        self.api_cache = APICache()
    
    def test_caching_system_integration(self):
        """Test caching system integration."""
        # Test cache manager
        test_data = {"key": "value", "number": 123}
        self.cache_manager.set("test_key", test_data, 3600)
        cached_data = self.cache_manager.get("test_key")
        assert cached_data == test_data
        
        # Test attribution cache
        file_hash = "test_hash"
        model_type = "linear"
        model_params = {"param1": "value1"}
        result_data = {"attribution": "result", "confidence": 0.95}
        
        self.attribution_cache.set_attribution_result(
            file_hash, model_type, model_params, result_data
        )
        cached_result = self.attribution_cache.get_attribution_result(
            file_hash, model_type, model_params
        )
        assert cached_result == result_data
        
        # Test API cache
        methods_data = {"attribution_models": [], "linking_methods": []}
        self.api_cache.set_available_methods(methods_data)
        cached_methods = self.api_cache.get_available_methods()
        assert cached_methods == methods_data
    
    def test_cache_ttl_integration(self):
        """Test cache TTL integration."""
        # Test cache expiration
        self.cache_manager.set("ttl_test", "value", 1)  # 1 second TTL
        assert self.cache_manager.get("ttl_test") == "value"
        
        time.sleep(1.1)
        assert self.cache_manager.get("ttl_test") is None
    
    def test_cache_statistics_integration(self):
        """Test cache statistics integration."""
        # Reset stats
        self.cache_manager.cache_stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
        
        # Perform operations
        self.cache_manager.set("key1", "value1", 3600)
        self.cache_manager.get("key1")  # Hit
        self.cache_manager.get("key2")  # Miss
        self.cache_manager.delete("key1")
        
        # Check stats
        stats = self.cache_manager.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["deletes"] == 1
        assert stats["hit_rate"] == 0.5


class TestPhase4MonitoringIntegration:
    """Test Phase 4 monitoring features integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
    
    @patch('src.core.monitoring.redis.Redis')
    def test_monitoring_system_integration(self, mock_redis):
        """Test monitoring system integration."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {
            "used_memory_human": "1.2M",
            "connected_clients": 5,
            "uptime_in_seconds": 3600
        }
        
        # Test health checking
        database_health = self.health_checker.check_database_health()
        assert database_health["status"] == "healthy"
        assert database_health["type"] == "redis"
        
        # Test system health
        system_health = self.health_checker.check_system_health()
        assert "cpu_percent" in system_health
        assert "memory_percent" in system_health
        assert "disk_percent" in system_health
        
        # Test application health
        self.health_checker.record_request(success=True)
        self.health_checker.record_request(success=False)
        app_health = self.health_checker.check_application_health()
        assert app_health["request_count"] == 2
        assert app_health["error_count"] == 1
        assert app_health["error_rate"] == 0.5
        
        # Test comprehensive health
        comprehensive_health = self.health_checker.get_comprehensive_health()
        assert "status" in comprehensive_health
        assert "components" in comprehensive_health
        assert "database" in comprehensive_health["components"]
        assert "system" in comprehensive_health["components"]
        assert "application" in comprehensive_health["components"]
    
    def test_metrics_collection_integration(self):
        """Test metrics collection integration."""
        # Record metrics
        self.metrics_collector.record_metric("response_time", 1.5, {"endpoint": "/test"})
        self.metrics_collector.record_metric("response_time", 2.0, {"endpoint": "/test"})
        self.metrics_collector.record_metric("error_count", 1, {"type": "validation"})
        
        # Get metric summary
        response_time_summary = self.metrics_collector.get_metric_summary("response_time")
        assert response_time_summary["count"] == 2
        assert response_time_summary["avg"] == 1.75
        assert response_time_summary["min"] == 1.5
        assert response_time_summary["max"] == 2.0
        
        # Get all metrics
        all_metrics = self.metrics_collector.get_all_metrics()
        assert len(all_metrics) == 3
    
    def test_alert_system_integration(self):
        """Test alert system integration."""
        # Test healthy system
        healthy_data = {
            "components": {
                "application": {"error_rate": 0.01},
                "system": {"cpu_percent": 50.0, "memory_percent": 60.0},
                "database": {"status": "healthy"}
            }
        }
        
        alerts = self.alert_manager.check_alerts(healthy_data)
        assert len(alerts) == 0
        
        # Test unhealthy system
        unhealthy_data = {
            "components": {
                "application": {"error_rate": 0.1},  # High error rate
                "system": {"cpu_percent": 85.0, "memory_percent": 85.0},  # High usage
                "database": {"status": "unhealthy"}
            }
        }
        
        alerts = self.alert_manager.check_alerts(unhealthy_data)
        assert len(alerts) == 4  # All alert conditions met
        
        alert_types = [alert["type"] for alert in alerts]
        assert "error_rate_high" in alert_types
        assert "cpu_usage_high" in alert_types
        assert "memory_usage_high" in alert_types
        assert "database_unhealthy" in alert_types


class TestPhase4LoggingIntegration:
    """Test Phase 4 logging features integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.security_logger = SecurityLogger()
        self.performance_logger = PerformanceLogger()
        self.business_logger = BusinessLogger()
    
    def test_logging_system_integration(self):
        """Test logging system integration."""
        # Test security logging
        with patch.object(self.security_logger.logger, 'info') as mock_info:
            self.security_logger.log_authentication_attempt(
                "test_key", True, "192.168.1.1"
            )
            mock_info.assert_called_once()
            
            call_args = mock_info.call_args[0][0]
            assert "Authentication successful" in call_args
            assert "test_key" in call_args
            assert "192.168.1.1" in call_args
        
        # Test performance logging
        with patch.object(self.performance_logger.logger, 'info') as mock_info:
            mock_request = Mock()
            mock_request.method = "GET"
            mock_request.url = "http://test.com/api"
            mock_request.client.host = "192.168.1.1"
            mock_request.headers = {"user-agent": "test-agent"}
            
            mock_response = Mock()
            mock_response.status_code = 200
            
            user_info = {"user_id": "test_user"}
            
            self.performance_logger.log_request_metrics(
                mock_request, mock_response, 1.5, user_info
            )
            mock_info.assert_called_once()
            
            call_args = mock_info.call_args[0][0]
            assert "Request metrics" in call_args
            assert "GET" in call_args
            assert "200" in call_args
            assert "1.5" in call_args
        
        # Test business logging
        with patch.object(self.business_logger.logger, 'info') as mock_info:
            self.business_logger.log_api_usage(
                "test_user", "/attribution/analyze", "linear"
            )
            mock_info.assert_called_once()
            
            call_args = mock_info.call_args[0][0]
            assert "API usage" in call_args
            assert "test_user" in call_args
            assert "/attribution/analyze" in call_args
            assert "linear" in call_args
    
    def test_logging_event_structure_integration(self):
        """Test logging event structure integration."""
        with patch.object(self.security_logger.logger, 'info') as mock_info:
            self.security_logger.log_authentication_attempt(
                "test_key", True, "192.168.1.1"
            )
            
            call_args = mock_info.call_args[0][0]
            # Should contain JSON structure
            assert "{" in call_args
            assert "}" in call_args
            
            # Parse JSON to verify structure
            json_start = call_args.find("{")
            json_end = call_args.rfind("}") + 1
            json_str = call_args[json_start:json_end]
            
            event_data = json.loads(json_str)
            assert "event_type" in event_data
            assert "api_key" in event_data
            assert "success" in event_data
            assert "ip_address" in event_data
            assert "timestamp" in event_data


class TestPhase4EndToEndIntegration:
    """Test Phase 4 end-to-end integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @patch('src.core.security.redis.Redis')
    def test_complete_phase4_workflow(self, mock_redis):
        """Test complete Phase 4 workflow integration."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Mock Redis responses
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": True,
            "rate_limit": 1000
        }
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 5  # Under rate limit
        mock_redis_client.setex.return_value = True
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {
            "used_memory_human": "1.2M",
            "connected_clients": 5,
            "uptime_in_seconds": 3600
        }
        
        # Test complete workflow
        # 1. Generate API key
        api_key_manager = APIKeyManager()
        api_key = api_key_manager.generate_api_key("test_user", ["read", "write"])
        assert isinstance(api_key, str)
        
        # 2. Validate API key
        user_info = api_key_manager.validate_api_key(api_key)
        assert user_info["user_id"] == "test_user"
        
        # 3. Check rate limiting
        rate_limit_ok = api_key_manager.check_rate_limit(api_key, "test_endpoint")
        assert rate_limit_ok is True
        
        # 4. Test caching
        cache_manager = CacheManager()
        test_data = {"result": "cached"}
        cache_manager.set("test_key", test_data, 3600)
        cached_data = cache_manager.get("test_key")
        assert cached_data == test_data
        
        # 5. Test monitoring
        health_checker = HealthChecker()
        health_checker.record_request(success=True)
        health_checker.record_request(success=False)
        
        metrics = health_checker.get_metrics()
        assert metrics["request_count"] == 2
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == 0.5
        
        # 6. Test logging
        security_logger = SecurityLogger()
        with patch.object(security_logger.logger, 'info') as mock_info:
            security_logger.log_authentication_attempt(api_key, True, "192.168.1.1")
            mock_info.assert_called_once()
        
        # 7. Test health checking
        database_health = health_checker.check_database_health()
        assert database_health["status"] == "healthy"
        
        system_health = health_checker.check_system_health()
        assert "cpu_percent" in system_health
        
        application_health = health_checker.check_application_health()
        assert application_health["request_count"] == 2
        
        comprehensive_health = health_checker.get_comprehensive_health()
        assert "status" in comprehensive_health
        assert "components" in comprehensive_health
    
    def test_phase4_error_handling_integration(self):
        """Test Phase 4 error handling integration."""
        # Test security error handling
        with pytest.raises(Exception):
            APIKeyManager().validate_api_key("invalid_key")
        
        # Test caching error handling
        cache_manager = CacheManager()
        with patch.object(cache_manager, 'redis_client', None):
            # Should work with memory fallback
            cache_manager.set("test_key", "test_value", 3600)
            assert cache_manager.get("test_key") == "test_value"
        
        # Test monitoring error handling
        health_checker = HealthChecker()
        with patch.object(health_checker, 'redis_client', None):
            database_health = health_checker.check_database_health()
            assert database_health["status"] == "unavailable"
        
        # Test logging error handling
        security_logger = SecurityLogger()
        with patch.object(security_logger.logger, 'info') as mock_info:
            security_logger.log_authentication_attempt("test_key", True, "192.168.1.1")
            mock_info.assert_called_once()
    
    def test_phase4_performance_integration(self):
        """Test Phase 4 performance integration."""
        # Test caching performance
        cache_manager = CacheManager()
        
        # Test cache hit performance
        cache_manager.set("perf_test", "value", 3600)
        start_time = time.time()
        cached_data = cache_manager.get("perf_test")
        end_time = time.time()
        
        assert cached_data == "value"
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test cache miss performance
        start_time = time.time()
        cached_data = cache_manager.get("non_existent_key")
        end_time = time.time()
        
        assert cached_data is None
        assert (end_time - start_time) < 0.1  # Should be fast
        
        # Test metrics collection performance
        metrics_collector = MetricsCollector()
        
        start_time = time.time()
        for i in range(100):
            metrics_collector.record_metric("test_metric", float(i))
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Should be fast
        
        # Test health checking performance
        health_checker = HealthChecker()
        
        start_time = time.time()
        health_checker.record_request(success=True)
        health_checker.record_request(success=False)
        metrics = health_checker.get_metrics()
        end_time = time.time()
        
        assert metrics["request_count"] == 2
        assert (end_time - start_time) < 0.1  # Should be fast
    
    def test_phase4_scalability_integration(self):
        """Test Phase 4 scalability integration."""
        # Test cache scalability
        cache_manager = CacheManager()
        
        # Test multiple cache operations
        for i in range(1000):
            cache_manager.set(f"key_{i}", f"value_{i}", 3600)
        
        # Test cache retrieval
        for i in range(1000):
            cached_data = cache_manager.get(f"key_{i}")
            assert cached_data == f"value_{i}"
        
        # Test metrics scalability
        metrics_collector = MetricsCollector()
        
        # Test multiple metrics
        for i in range(1000):
            metrics_collector.record_metric("test_metric", float(i))
        
        # Test metric summary
        summary = metrics_collector.get_metric_summary("test_metric")
        assert summary["count"] == 1000
        assert summary["avg"] == 499.5  # Average of 0-999
        
        # Test health checker scalability
        health_checker = HealthChecker()
        
        # Test multiple requests
        for i in range(1000):
            health_checker.record_request(success=(i % 10 != 0))  # 90% success rate
        
        metrics = health_checker.get_metrics()
        assert metrics["request_count"] == 1000
        assert metrics["error_count"] == 100
        assert metrics["error_rate"] == 0.1
