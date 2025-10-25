"""Comprehensive logging system for the Multi-Touch Attribution API."""

import logging
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import Request, Response
from fastapi.logger import logger as fastapi_logger
import structlog
from contextlib import asynccontextmanager

from ..config import get_settings


class SecurityLogger:
    """Specialized logger for security events."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("security")
        self.logger.setLevel(getattr(logging, self.settings.log_level))
        
        # Create file handler for security logs
        if self.settings.enable_security_logging:
            handler = logging.FileHandler("logs/security.log")
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
    
    def log_authentication_attempt(self, api_key: str, success: bool, ip_address: str):
        """Log authentication attempts."""
        event = {
            "event_type": "authentication_attempt",
            "api_key": api_key[:8] + "..." if api_key else None,
            "success": success,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            self.logger.info(f"Authentication successful: {json.dumps(event)}")
        else:
            self.logger.warning(f"Authentication failed: {json.dumps(event)}")
    
    def log_rate_limit_exceeded(self, api_key: str, endpoint: str, ip_address: str):
        """Log rate limit violations."""
        event = {
            "event_type": "rate_limit_exceeded",
            "api_key": api_key[:8] + "..." if api_key else None,
            "endpoint": endpoint,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(f"Rate limit exceeded: {json.dumps(event)}")
    
    def log_file_upload(self, api_key: str, filename: str, file_size: int, success: bool):
        """Log file upload events."""
        event = {
            "event_type": "file_upload",
            "api_key": api_key[:8] + "..." if api_key else None,
            "filename": filename,
            "file_size": file_size,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            self.logger.info(f"File upload successful: {json.dumps(event)}")
        else:
            self.logger.error(f"File upload failed: {json.dumps(event)}")
    
    def log_attribution_analysis(self, api_key: str, model_type: str, file_size: int, 
                                processing_time: float, success: bool):
        """Log attribution analysis events."""
        event = {
            "event_type": "attribution_analysis",
            "api_key": api_key[:8] + "..." if api_key else None,
            "model_type": model_type,
            "file_size": file_size,
            "processing_time": processing_time,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            self.logger.info(f"Attribution analysis completed: {json.dumps(event)}")
        else:
            self.logger.error(f"Attribution analysis failed: {json.dumps(event)}")


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("performance")
        self.logger.setLevel(getattr(logging, self.settings.log_level))
        
        # Create file handler for performance logs
        handler = logging.FileHandler("logs/performance.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log_request_metrics(self, request: Request, response: Response, 
                           processing_time: float, user_info: Dict[str, Any]):
        """Log request performance metrics."""
        event = {
            "event_type": "request_metrics",
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "processing_time": processing_time,
            "user_id": user_info.get("user_id"),
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"Request metrics: {json.dumps(event)}")
    
    def log_file_processing_metrics(self, filename: str, file_size: int, 
                                  processing_time: float, memory_usage: float):
        """Log file processing performance metrics."""
        event = {
            "event_type": "file_processing_metrics",
            "filename": filename,
            "file_size": file_size,
            "processing_time": processing_time,
            "memory_usage": memory_usage,
            "throughput_mb_per_sec": file_size / processing_time if processing_time > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"File processing metrics: {json.dumps(event)}")
    
    def log_attribution_processing_metrics(self, model_type: str, data_size: int,
                                         processing_time: float, confidence_score: float):
        """Log attribution processing performance metrics."""
        event = {
            "event_type": "attribution_processing_metrics",
            "model_type": model_type,
            "data_size": data_size,
            "processing_time": processing_time,
            "confidence_score": confidence_score,
            "records_per_second": data_size / processing_time if processing_time > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"Attribution processing metrics: {json.dumps(event)}")


class BusinessLogger:
    """Logger for business metrics and insights."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("business")
        self.logger.setLevel(getattr(logging, self.settings.log_level))
        
        # Create file handler for business logs
        handler = logging.FileHandler("logs/business.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log_api_usage(self, user_id: str, endpoint: str, model_type: str = None):
        """Log API usage for business metrics."""
        event = {
            "event_type": "api_usage",
            "user_id": user_id,
            "endpoint": endpoint,
            "model_type": model_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"API usage: {json.dumps(event)}")
    
    def log_attribution_insights(self, user_id: str, model_type: str, 
                               total_conversions: int, top_channels: list):
        """Log attribution analysis insights."""
        event = {
            "event_type": "attribution_insights",
            "user_id": user_id,
            "model_type": model_type,
            "total_conversions": total_conversions,
            "top_channels": top_channels,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"Attribution insights: {json.dumps(event)}")


class RequestLogger:
    """Middleware for logging all requests and responses."""
    
    def __init__(self):
        self.security_logger = SecurityLogger()
        self.performance_logger = PerformanceLogger()
        self.business_logger = BusinessLogger()
    
    @asynccontextmanager
    async def log_request(self, request: Request, user_info: Dict[str, Any] = None):
        """Context manager for logging request lifecycle."""
        start_time = time.time()
        
        try:
            # Log request start
            self.performance_logger.logger.info(f"Request started: {request.method} {request.url}")
            
            yield
            
        except Exception as e:
            # Log request error
            self.performance_logger.logger.error(f"Request failed: {request.method} {request.url} - {str(e)}")
            raise
            
        finally:
            # Log request completion
            processing_time = time.time() - start_time
            if user_info:
                self.performance_logger.logger.info(
                    f"Request completed: {request.method} {request.url} "
                    f"in {processing_time:.3f}s for user {user_info.get('user_id')}"
                )


# Global logger instances
security_logger = SecurityLogger()
performance_logger = PerformanceLogger()
business_logger = BusinessLogger()
request_logger = RequestLogger()


def setup_logging():
    """Setup comprehensive logging configuration."""
    settings = get_settings()
    
    # Configure structlog for structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/application.log")
        ]
    )
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
