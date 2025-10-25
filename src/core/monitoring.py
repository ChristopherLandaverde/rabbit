"""Monitoring and health check system for the API."""

import time
import psutil
import redis
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from ..config import get_settings
from .caching import cache_manager
from .logging import performance_logger, business_logger


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = self._get_redis_client()
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_health_check = time.time()
    
    def _get_redis_client(self) -> redis.Redis:
        """Get Redis client for health checks."""
        try:
            return redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        except Exception:
            return None
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            if self.redis_client:
                # Test Redis connection
                start_time = time.time()
                self.redis_client.ping()
                response_time = time.time() - start_time
                
                # Get Redis info
                info = self.redis_client.info()
                
                return {
                    "status": "healthy",
                    "type": "redis",
                    "response_time": response_time,
                    "memory_usage": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "uptime": info.get("uptime_in_seconds"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "unavailable",
                    "type": "redis",
                    "message": "Redis client not configured",
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "type": "redis",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check system resource usage and performance."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free = disk.free / (1024**3)  # GB
            
            # Process info
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024**2)  # MB
            
            return {
                "status": "healthy" if cpu_percent < 80 and memory_percent < 80 else "warning",
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory_available,
                "disk_percent": disk_percent,
                "disk_free_gb": disk_free,
                "process_memory_mb": process_memory,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def check_application_health(self) -> Dict[str, Any]:
        """Check application-specific health metrics."""
        try:
            uptime = time.time() - self.start_time
            
            # Calculate error rate
            error_rate = self.error_count / max(self.request_count, 1)
            
            # Get cache statistics
            cache_stats = cache_manager.get_stats()
            
            return {
                "status": "healthy" if error_rate < 0.05 else "warning",
                "uptime_seconds": uptime,
                "request_count": self.request_count,
                "error_count": self.error_count,
                "error_rate": error_rate,
                "cache_hit_rate": cache_stats.get("hit_rate", 0),
                "cache_total_requests": cache_stats.get("total_requests", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        database_health = self.check_database_health()
        system_health = self.check_system_health()
        application_health = self.check_application_health()
        
        # Determine overall status
        statuses = [
            database_health.get("status"),
            system_health.get("status"),
            application_health.get("status")
        ]
        
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": self.settings.version,
            "components": {
                "database": database_health,
                "system": system_health,
                "application": application_health
            }
        }
    
    def record_request(self, success: bool = True):
        """Record a request for health metrics."""
        self.request_count += 1
        if not success:
            self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get application metrics for monitoring."""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "requests_per_minute": self.request_count / (uptime / 60) if uptime > 0 else 0,
            "cache_stats": cache_manager.get_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }


class MetricsCollector:
    """Collects and aggregates metrics for monitoring."""
    
    def __init__(self):
        self.metrics_history = []
        self.max_history_size = 1000
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value."""
        metric = {
            "name": metric_name,
            "value": value,
            "tags": tags or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.metrics_history.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def get_metric_summary(self, metric_name: str, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        recent_metrics = [
            m for m in self.metrics_history
            if m["name"] == metric_name and 
            datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
        
        if not recent_metrics:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        values = [m["value"] for m in recent_metrics]
        
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else 0
        }
    
    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Get all recorded metrics."""
        return self.metrics_history.copy()


class AlertManager:
    """Manages alerts and notifications for monitoring."""
    
    def __init__(self):
        self.alerts = []
        self.alert_thresholds = {
            "error_rate": 0.05,  # 5%
            "cpu_usage": 80,      # 80%
            "memory_usage": 80,   # 80%
            "disk_usage": 90,     # 90%
            "response_time": 5.0  # 5 seconds
        }
    
    def check_alerts(self, health_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        
        # Check error rate
        error_rate = health_data.get("components", {}).get("application", {}).get("error_rate", 0)
        if error_rate > self.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "error_rate_high",
                "severity": "warning",
                "message": f"Error rate is {error_rate:.1%}, above threshold of {self.alert_thresholds['error_rate']:.1%}",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check system resources
        system_health = health_data.get("components", {}).get("system", {})
        cpu_percent = system_health.get("cpu_percent", 0)
        if cpu_percent > self.alert_thresholds["cpu_usage"]:
            alerts.append({
                "type": "cpu_usage_high",
                "severity": "warning",
                "message": f"CPU usage is {cpu_percent:.1f}%, above threshold of {self.alert_thresholds['cpu_usage']}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        memory_percent = system_health.get("memory_percent", 0)
        if memory_percent > self.alert_thresholds["memory_usage"]:
            alerts.append({
                "type": "memory_usage_high",
                "severity": "warning",
                "message": f"Memory usage is {memory_percent:.1f}%, above threshold of {self.alert_thresholds['memory_usage']}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check database health
        database_health = health_data.get("components", {}).get("database", {})
        if database_health.get("status") == "unhealthy":
            alerts.append({
                "type": "database_unhealthy",
                "severity": "critical",
                "message": "Database is unhealthy",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return alerts
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        return [alert for alert in self.alerts if alert.get("active", True)]


# Global monitoring instances
health_checker = HealthChecker()
metrics_collector = MetricsCollector()
alert_manager = AlertManager()
