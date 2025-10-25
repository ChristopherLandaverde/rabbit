"""Tests for monitoring and health check system."""

import pytest
import time
import psutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.core.monitoring import (
    HealthChecker, MetricsCollector, AlertManager,
    health_checker, metrics_collector, alert_manager
)
from src.config import get_settings


class TestHealthChecker:
    """Test HealthChecker functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.health_checker = HealthChecker()
    
    @patch('src.core.monitoring.redis.Redis')
    def test_health_checker_initialization(self, mock_redis):
        """Test HealthChecker initialization."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        checker = HealthChecker()
        assert checker.redis_client is not None
        assert checker.start_time > 0
        assert checker.request_count == 0
        assert checker.error_count == 0
    
    @patch('src.core.monitoring.redis.Redis')
    def test_check_database_health_healthy(self, mock_redis):
        """Test database health check when Redis is healthy."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Mock Redis info
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {
            "used_memory_human": "1.2M",
            "connected_clients": 5,
            "uptime_in_seconds": 3600
        }
        
        checker = HealthChecker()
        result = checker.check_database_health()
        
        assert result["status"] == "healthy"
        assert result["type"] == "redis"
        assert "response_time" in result
        assert result["memory_usage"] == "1.2M"
        assert result["connected_clients"] == 5
        assert result["uptime"] == 3600
    
    @patch('src.core.monitoring.redis.Redis')
    def test_check_database_health_unhealthy(self, mock_redis):
        """Test database health check when Redis is unhealthy."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.ping.side_effect = Exception("Connection failed")
        
        checker = HealthChecker()
        result = checker.check_database_health()
        
        assert result["status"] == "unhealthy"
        assert result["type"] == "redis"
        assert "error" in result
        assert "Connection failed" in result["error"]
    
    def test_check_database_health_no_redis(self):
        """Test database health check when Redis is not configured."""
        with patch.object(self.health_checker, 'redis_client', None):
            result = self.health_checker.check_database_health()
            
            assert result["status"] == "unavailable"
            assert result["type"] == "redis"
            assert "Redis client not configured" in result["message"]
    
    @patch('src.core.monitoring.psutil.cpu_percent')
    @patch('src.core.monitoring.psutil.virtual_memory')
    @patch('src.core.monitoring.psutil.disk_usage')
    @patch('src.core.monitoring.psutil.Process')
    def test_check_system_health_healthy(self, mock_process, mock_disk, mock_memory, mock_cpu):
        """Test system health check when system is healthy."""
        # Mock system metrics
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=60.0, available=8 * 1024**3)  # 8GB available
        mock_disk.return_value = Mock(percent=70.0, free=50 * 1024**3)  # 50GB free
        mock_process.return_value.memory_info.return_value.rss = 100 * 1024**2  # 100MB
        
        result = self.health_checker.check_system_health()
        
        assert result["status"] == "healthy"
        assert result["cpu_percent"] == 50.0
        assert result["memory_percent"] == 60.0
        assert result["memory_available_gb"] == 8.0
        assert result["disk_percent"] == 70.0
        assert result["disk_free_gb"] == 50.0
        assert result["process_memory_mb"] == 100.0
    
    @patch('src.core.monitoring.psutil.cpu_percent')
    @patch('src.core.monitoring.psutil.virtual_memory')
    @patch('src.core.monitoring.psutil.disk_usage')
    @patch('src.core.monitoring.psutil.Process')
    def test_check_system_health_warning(self, mock_process, mock_disk, mock_memory, mock_cpu):
        """Test system health check when system resources are high."""
        # Mock high resource usage
        mock_cpu.return_value = 85.0
        mock_memory.return_value = Mock(percent=85.0, available=2 * 1024**3)  # 2GB available
        mock_disk.return_value = Mock(percent=70.0, free=50 * 1024**3)  # 50GB free
        mock_process.return_value.memory_info.return_value.rss = 100 * 1024**2  # 100MB
        
        result = self.health_checker.check_system_health()
        
        assert result["status"] == "warning"
        assert result["cpu_percent"] == 85.0
        assert result["memory_percent"] == 85.0
    
    @patch('src.core.monitoring.psutil.cpu_percent')
    def test_check_system_health_exception(self, mock_cpu):
        """Test system health check when exception occurs."""
        mock_cpu.side_effect = Exception("System error")
        
        result = self.health_checker.check_system_health()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "System error" in result["error"]
    
    @patch('src.core.monitoring.cache_manager')
    def test_check_application_health_healthy(self, mock_cache_manager):
        """Test application health check when application is healthy."""
        # Mock cache stats
        mock_cache_manager.get_stats.return_value = {
            "hit_rate": 0.8,
            "total_requests": 1000
        }
        
        # Set up health checker state
        self.health_checker.request_count = 100
        self.health_checker.error_count = 2  # 2% error rate
        
        result = self.health_checker.check_application_health()
        
        assert result["status"] == "healthy"
        assert result["request_count"] == 100
        assert result["error_count"] == 2
        assert result["error_rate"] == 0.02
        assert result["cache_hit_rate"] == 0.8
        assert result["cache_total_requests"] == 1000
    
    @patch('src.core.monitoring.cache_manager')
    def test_check_application_health_warning(self, mock_cache_manager):
        """Test application health check when error rate is high."""
        # Mock cache stats
        mock_cache_manager.get_stats.return_value = {
            "hit_rate": 0.5,
            "total_requests": 100
        }
        
        # Set up health checker state with high error rate
        self.health_checker.request_count = 100
        self.health_checker.error_count = 10  # 10% error rate
        
        result = self.health_checker.check_application_health()
        
        assert result["status"] == "warning"
        assert result["error_rate"] == 0.1
    
    def test_get_comprehensive_health(self):
        """Test comprehensive health status aggregation."""
        # Mock individual health checks
        with patch.object(self.health_checker, 'check_database_health') as mock_db:
            with patch.object(self.health_checker, 'check_system_health') as mock_sys:
                with patch.object(self.health_checker, 'check_application_health') as mock_app:
                    # Mock all healthy
                    mock_db.return_value = {"status": "healthy"}
                    mock_sys.return_value = {"status": "healthy"}
                    mock_app.return_value = {"status": "healthy"}
                    
                    result = self.health_checker.get_comprehensive_health()
                    
                    assert result["status"] == "healthy"
                    assert "components" in result
                    assert "database" in result["components"]
                    assert "system" in result["components"]
                    assert "application" in result["components"]
    
    def test_get_comprehensive_health_unhealthy(self):
        """Test comprehensive health status with unhealthy components."""
        # Mock individual health checks
        with patch.object(self.health_checker, 'check_database_health') as mock_db:
            with patch.object(self.health_checker, 'check_system_health') as mock_sys:
                with patch.object(self.health_checker, 'check_application_health') as mock_app:
                    # Mock one unhealthy component
                    mock_db.return_value = {"status": "unhealthy"}
                    mock_sys.return_value = {"status": "healthy"}
                    mock_app.return_value = {"status": "healthy"}
                    
                    result = self.health_checker.get_comprehensive_health()
                    
                    assert result["status"] == "unhealthy"
    
    def test_get_comprehensive_health_warning(self):
        """Test comprehensive health status with warning components."""
        # Mock individual health checks
        with patch.object(self.health_checker, 'check_database_health') as mock_db:
            with patch.object(self.health_checker, 'check_system_health') as mock_sys:
                with patch.object(self.health_checker, 'check_application_health') as mock_app:
                    # Mock one warning component
                    mock_db.return_value = {"status": "healthy"}
                    mock_sys.return_value = {"status": "warning"}
                    mock_app.return_value = {"status": "healthy"}
                    
                    result = self.health_checker.get_comprehensive_health()
                    
                    assert result["status"] == "warning"
    
    def test_record_request(self):
        """Test request recording for metrics."""
        initial_count = self.health_checker.request_count
        initial_errors = self.health_checker.error_count
        
        # Record successful request
        self.health_checker.record_request(success=True)
        assert self.health_checker.request_count == initial_count + 1
        assert self.health_checker.error_count == initial_errors
        
        # Record failed request
        self.health_checker.record_request(success=False)
        assert self.health_checker.request_count == initial_count + 2
        assert self.health_checker.error_count == initial_errors + 1
    
    @patch('src.core.monitoring.cache_manager')
    def test_get_metrics(self, mock_cache_manager):
        """Test metrics collection."""
        # Mock cache stats
        mock_cache_manager.get_stats.return_value = {
            "hit_rate": 0.8,
            "total_requests": 1000
        }
        
        # Set up health checker state
        self.health_checker.request_count = 100
        self.health_checker.error_count = 5
        
        metrics = self.health_checker.get_metrics()
        
        assert "uptime_seconds" in metrics
        assert metrics["request_count"] == 100
        assert metrics["error_count"] == 5
        assert metrics["error_rate"] == 0.05
        assert "requests_per_minute" in metrics
        assert "cache_stats" in metrics


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.metrics_collector = MetricsCollector()
    
    def test_record_metric(self):
        """Test metric recording."""
        self.metrics_collector.record_metric("test_metric", 100.0, {"tag1": "value1"})
        
        assert len(self.metrics_collector.metrics_history) == 1
        metric = self.metrics_collector.metrics_history[0]
        assert metric["name"] == "test_metric"
        assert metric["value"] == 100.0
        assert metric["tags"] == {"tag1": "value1"}
        assert "timestamp" in metric
    
    def test_record_metric_without_tags(self):
        """Test metric recording without tags."""
        self.metrics_collector.record_metric("test_metric", 50.0)
        
        assert len(self.metrics_collector.metrics_history) == 1
        metric = self.metrics_collector.metrics_history[0]
        assert metric["tags"] == {}
    
    def test_get_metric_summary(self):
        """Test metric summary generation."""
        # Record some metrics
        self.metrics_collector.record_metric("test_metric", 100.0)
        self.metrics_collector.record_metric("test_metric", 200.0)
        self.metrics_collector.record_metric("test_metric", 150.0)
        
        summary = self.metrics_collector.get_metric_summary("test_metric")
        
        assert summary["count"] == 3
        assert summary["avg"] == 150.0
        assert summary["min"] == 100.0
        assert summary["max"] == 200.0
        assert summary["latest"] == 150.0
    
    def test_get_metric_summary_no_metrics(self):
        """Test metric summary with no metrics."""
        summary = self.metrics_collector.get_metric_summary("nonexistent_metric")
        
        assert summary["count"] == 0
        assert summary["avg"] == 0
        assert summary["min"] == 0
        assert summary["max"] == 0
    
    def test_get_metric_summary_time_window(self):
        """Test metric summary with time window filtering."""
        # Record metrics with different timestamps
        self.metrics_collector.record_metric("test_metric", 100.0)
        time.sleep(0.1)  # Small delay to ensure different timestamps
        self.metrics_collector.record_metric("test_metric", 200.0)
        
        # Get summary for recent metrics only
        summary = self.metrics_collector.get_metric_summary("test_metric", time_window_minutes=1)
        
        assert summary["count"] == 2
        assert summary["avg"] == 150.0
    
    def test_get_all_metrics(self):
        """Test getting all recorded metrics."""
        # Record some metrics
        self.metrics_collector.record_metric("metric1", 100.0)
        self.metrics_collector.record_metric("metric2", 200.0)
        
        all_metrics = self.metrics_collector.get_all_metrics()
        
        assert len(all_metrics) == 2
        assert all_metrics[0]["name"] == "metric1"
        assert all_metrics[1]["name"] == "metric2"
    
    def test_metrics_history_limit(self):
        """Test metrics history size limit."""
        # Record more metrics than the limit
        for i in range(self.metrics_collector.max_history_size + 10):
            self.metrics_collector.record_metric("test_metric", float(i))
        
        # Should be limited to max_history_size
        assert len(self.metrics_collector.metrics_history) == self.metrics_collector.max_history_size
        
        # Should contain the most recent metrics
        latest_metric = self.metrics_collector.metrics_history[-1]
        assert latest_metric["value"] == float(self.metrics_collector.max_history_size + 9)


class TestAlertManager:
    """Test AlertManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.alert_manager = AlertManager()
    
    def test_check_alerts_no_alerts(self):
        """Test alert checking with no alert conditions."""
        health_data = {
            "components": {
                "application": {"error_rate": 0.01},
                "system": {"cpu_percent": 50.0, "memory_percent": 60.0},
                "database": {"status": "healthy"}
            }
        }
        
        alerts = self.alert_manager.check_alerts(health_data)
        assert len(alerts) == 0
    
    def test_check_alerts_high_error_rate(self):
        """Test alert checking with high error rate."""
        health_data = {
            "components": {
                "application": {"error_rate": 0.1},  # 10% error rate
                "system": {"cpu_percent": 50.0, "memory_percent": 60.0},
                "database": {"status": "healthy"}
            }
        }
        
        alerts = self.alert_manager.check_alerts(health_data)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "error_rate_high"
        assert alerts[0]["severity"] == "warning"
        assert "Error rate is 10.0%" in alerts[0]["message"]
    
    def test_check_alerts_high_cpu_usage(self):
        """Test alert checking with high CPU usage."""
        health_data = {
            "components": {
                "application": {"error_rate": 0.01},
                "system": {"cpu_percent": 85.0, "memory_percent": 60.0},
                "database": {"status": "healthy"}
            }
        }
        
        alerts = self.alert_manager.check_alerts(health_data)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "cpu_usage_high"
        assert alerts[0]["severity"] == "warning"
        assert "CPU usage is 85.0%" in alerts[0]["message"]
    
    def test_check_alerts_high_memory_usage(self):
        """Test alert checking with high memory usage."""
        health_data = {
            "components": {
                "application": {"error_rate": 0.01},
                "system": {"cpu_percent": 50.0, "memory_percent": 85.0},
                "database": {"status": "healthy"}
            }
        }
        
        alerts = self.alert_manager.check_alerts(health_data)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "memory_usage_high"
        assert alerts[0]["severity"] == "warning"
        assert "Memory usage is 85.0%" in alerts[0]["message"]
    
    def test_check_alerts_database_unhealthy(self):
        """Test alert checking with unhealthy database."""
        health_data = {
            "components": {
                "application": {"error_rate": 0.01},
                "system": {"cpu_percent": 50.0, "memory_percent": 60.0},
                "database": {"status": "unhealthy"}
            }
        }
        
        alerts = self.alert_manager.check_alerts(health_data)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "database_unhealthy"
        assert alerts[0]["severity"] == "critical"
        assert "Database is unhealthy" in alerts[0]["message"]
    
    def test_check_alerts_multiple_alerts(self):
        """Test alert checking with multiple alert conditions."""
        health_data = {
            "components": {
                "application": {"error_rate": 0.1},  # High error rate
                "system": {"cpu_percent": 85.0, "memory_percent": 85.0},  # High CPU and memory
                "database": {"status": "unhealthy"}  # Unhealthy database
            }
        }
        
        alerts = self.alert_manager.check_alerts(health_data)
        assert len(alerts) == 4  # All four alert conditions
        
        alert_types = [alert["type"] for alert in alerts]
        assert "error_rate_high" in alert_types
        assert "cpu_usage_high" in alert_types
        assert "memory_usage_high" in alert_types
        assert "database_unhealthy" in alert_types
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        # Add some alerts
        self.alert_manager.alerts = [
            {"type": "test_alert", "active": True},
            {"type": "inactive_alert", "active": False}
        ]
        
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0]["type"] == "test_alert"


class TestMonitoringIntegration:
    """Integration tests for monitoring system."""
    
    def test_global_monitoring_instances(self):
        """Test that global monitoring instances are properly configured."""
        assert health_checker is not None
        assert metrics_collector is not None
        assert alert_manager is not None
        
        # Test that instances have required methods
        assert hasattr(health_checker, 'check_database_health')
        assert hasattr(health_checker, 'check_system_health')
        assert hasattr(health_checker, 'get_comprehensive_health')
        assert hasattr(metrics_collector, 'record_metric')
        assert hasattr(metrics_collector, 'get_metric_summary')
        assert hasattr(alert_manager, 'check_alerts')
        assert hasattr(alert_manager, 'get_active_alerts')
    
    def test_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        # Record some metrics
        metrics_collector.record_metric("response_time", 1.5, {"endpoint": "/test"})
        metrics_collector.record_metric("response_time", 2.0, {"endpoint": "/test"})
        
        # Get metric summary
        summary = metrics_collector.get_metric_summary("response_time")
        assert summary["count"] == 2
        assert summary["avg"] == 1.75
        
        # Record request for health metrics
        health_checker.record_request(success=True)
        health_checker.record_request(success=False)
        
        # Get health metrics
        metrics = health_checker.get_metrics()
        assert metrics["request_count"] == 2
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == 0.5
    
    def test_alert_thresholds_configuration(self):
        """Test alert threshold configuration."""
        assert alert_manager.alert_thresholds["error_rate"] == 0.05
        assert alert_manager.alert_thresholds["cpu_usage"] == 80
        assert alert_manager.alert_thresholds["memory_usage"] == 80
        assert alert_manager.alert_thresholds["disk_usage"] == 90
        assert alert_manager.alert_thresholds["response_time"] == 5.0
    
    def test_health_checker_redis_fallback(self):
        """Test health checker fallback when Redis is unavailable."""
        with patch('src.core.monitoring.redis.Redis', side_effect=Exception("Redis unavailable")):
            checker = HealthChecker()
            assert checker.redis_client is None
            
            # Should handle gracefully
            result = checker.check_database_health()
            assert result["status"] == "unavailable"
    
    def test_metrics_collector_time_filtering(self):
        """Test metrics collector time window filtering."""
        # Record metrics at different times
        metrics_collector.record_metric("test_metric", 100.0)
        time.sleep(0.1)
        metrics_collector.record_metric("test_metric", 200.0)
        
        # Get summary for recent metrics
        summary = metrics_collector.get_metric_summary("test_metric", time_window_minutes=1)
        assert summary["count"] == 2
        
        # Get summary for very old metrics (should be empty)
        summary_old = metrics_collector.get_metric_summary("test_metric", time_window_minutes=0)
        assert summary_old["count"] == 0
