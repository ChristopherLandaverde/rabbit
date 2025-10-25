"""Tests for comprehensive logging system."""

import pytest
import json
import logging
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from fastapi import Request, Response

from src.core.logging import (
    SecurityLogger, PerformanceLogger, BusinessLogger, RequestLogger,
    security_logger, performance_logger, business_logger, request_logger,
    setup_logging
)
from src.config import get_settings


class TestSecurityLogger:
    """Test SecurityLogger functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.security_logger = SecurityLogger()
    
    @patch('src.core.logging.logging.FileHandler')
    @patch('src.core.logging.get_settings')
    def test_security_logger_initialization(self, mock_get_settings, mock_file_handler):
        """Test SecurityLogger initialization."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        mock_settings.enable_security_logging = True
        mock_get_settings.return_value = mock_settings
        
        # Mock file handler
        mock_handler = Mock()
        mock_file_handler.return_value = mock_handler
        
        logger = SecurityLogger()
        
        assert logger.logger is not None
        assert logger.logger.name == "security"
        mock_file_handler.assert_called_once_with("logs/security.log")
    
    @patch('src.core.logging.get_settings')
    def test_security_logger_initialization_disabled(self, mock_get_settings):
        """Test SecurityLogger initialization when logging is disabled."""
        # Mock settings with logging disabled
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        mock_settings.enable_security_logging = False
        mock_get_settings.return_value = mock_settings
        
        logger = SecurityLogger()
        
        assert logger.logger is not None
        assert len(logger.logger.handlers) == 0  # No file handler added
    
    def test_log_authentication_attempt_success(self):
        """Test logging successful authentication attempt."""
        with patch.object(self.security_logger.logger, 'info') as mock_info:
            self.security_logger.log_authentication_attempt(
                "test_api_key", True, "192.168.1.1"
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "Authentication successful" in call_args
            assert "test_api_key" in call_args
            assert "192.168.1.1" in call_args
    
    def test_log_authentication_attempt_failure(self):
        """Test logging failed authentication attempt."""
        with patch.object(self.security_logger.logger, 'warning') as mock_warning:
            self.security_logger.log_authentication_attempt(
                "invalid_key", False, "192.168.1.1"
            )
            
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0][0]
            assert "Authentication failed" in call_args
            assert "invalid_key" in call_args
            assert "192.168.1.1" in call_args
    
    def test_log_rate_limit_exceeded(self):
        """Test logging rate limit exceeded event."""
        with patch.object(self.security_logger.logger, 'warning') as mock_warning:
            self.security_logger.log_rate_limit_exceeded(
                "test_api_key", "GET:/test", "192.168.1.1"
            )
            
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0][0]
            assert "Rate limit exceeded" in call_args
            assert "test_api_key" in call_args
            assert "GET:/test" in call_args
            assert "192.168.1.1" in call_args
    
    def test_log_file_upload_success(self):
        """Test logging successful file upload."""
        with patch.object(self.security_logger.logger, 'info') as mock_info:
            self.security_logger.log_file_upload(
                "test_api_key", "test.csv", 1024, True
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "File upload successful" in call_args
            assert "test.csv" in call_args
            assert "1024" in call_args
    
    def test_log_file_upload_failure(self):
        """Test logging failed file upload."""
        with patch.object(self.security_logger.logger, 'error') as mock_error:
            self.security_logger.log_file_upload(
                "test_api_key", "test.csv", 1024, False
            )
            
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "File upload failed" in call_args
            assert "test.csv" in call_args
            assert "1024" in call_args
    
    def test_log_attribution_analysis_success(self):
        """Test logging successful attribution analysis."""
        with patch.object(self.security_logger.logger, 'info') as mock_info:
            self.security_logger.log_attribution_analysis(
                "test_api_key", "linear", 1024, 2.5, True
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "Attribution analysis completed" in call_args
            assert "linear" in call_args
            assert "1024" in call_args
            assert "2.5" in call_args
    
    def test_log_attribution_analysis_failure(self):
        """Test logging failed attribution analysis."""
        with patch.object(self.security_logger.logger, 'error') as mock_error:
            self.security_logger.log_attribution_analysis(
                "test_api_key", "linear", 1024, 2.5, False
            )
            
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "Attribution analysis failed" in call_args
            assert "linear" in call_args
            assert "1024" in call_args
            assert "2.5" in call_args


class TestPerformanceLogger:
    """Test PerformanceLogger functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.performance_logger = PerformanceLogger()
    
    @patch('src.core.logging.logging.FileHandler')
    @patch('src.core.logging.get_settings')
    def test_performance_logger_initialization(self, mock_get_settings, mock_file_handler):
        """Test PerformanceLogger initialization."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings
        
        # Mock file handler
        mock_handler = Mock()
        mock_file_handler.return_value = mock_handler
        
        logger = PerformanceLogger()
        
        assert logger.logger is not None
        assert logger.logger.name == "performance"
        mock_file_handler.assert_called_once_with("logs/performance.log")
    
    def test_log_request_metrics(self):
        """Test logging request performance metrics."""
        with patch.object(self.performance_logger.logger, 'info') as mock_info:
            # Mock request and response
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
            assert "http://test.com/api" in call_args
            assert "200" in call_args
            assert "1.5" in call_args
            assert "test_user" in call_args
    
    def test_log_file_processing_metrics(self):
        """Test logging file processing performance metrics."""
        with patch.object(self.performance_logger.logger, 'info') as mock_info:
            self.performance_logger.log_file_processing_metrics(
                "test.csv", 1024, 2.0, 50.0
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "File processing metrics" in call_args
            assert "test.csv" in call_args
            assert "1024" in call_args
            assert "2.0" in call_args
            assert "50.0" in call_args
            assert "512.0" in call_args  # throughput_mb_per_sec
    
    def test_log_attribution_processing_metrics(self):
        """Test logging attribution processing performance metrics."""
        with patch.object(self.performance_logger.logger, 'info') as mock_info:
            self.performance_logger.log_attribution_processing_metrics(
                "linear", 1000, 1.5, 0.95
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "Attribution processing metrics" in call_args
            assert "linear" in call_args
            assert "1000" in call_args
            assert "1.5" in call_args
            assert "0.95" in call_args
            assert "666.67" in call_args  # records_per_second


class TestBusinessLogger:
    """Test BusinessLogger functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.business_logger = BusinessLogger()
    
    @patch('src.core.logging.logging.FileHandler')
    @patch('src.core.logging.get_settings')
    def test_business_logger_initialization(self, mock_get_settings, mock_file_handler):
        """Test BusinessLogger initialization."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings
        
        # Mock file handler
        mock_handler = Mock()
        mock_file_handler.return_value = mock_handler
        
        logger = BusinessLogger()
        
        assert logger.logger is not None
        assert logger.logger.name == "business"
        mock_file_handler.assert_called_once_with("logs/business.log")
    
    def test_log_api_usage(self):
        """Test logging API usage."""
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
    
    def test_log_api_usage_without_model(self):
        """Test logging API usage without model type."""
        with patch.object(self.business_logger.logger, 'info') as mock_info:
            self.business_logger.log_api_usage(
                "test_user", "/attribution/methods"
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "API usage" in call_args
            assert "test_user" in call_args
            assert "/attribution/methods" in call_args
    
    def test_log_attribution_insights(self):
        """Test logging attribution insights."""
        with patch.object(self.business_logger.logger, 'info') as mock_info:
            self.business_logger.log_attribution_insights(
                "test_user", "linear", 100, ["email", "social", "paid_search"]
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "Attribution insights" in call_args
            assert "test_user" in call_args
            assert "linear" in call_args
            assert "100" in call_args
            assert "email" in call_args
            assert "social" in call_args
            assert "paid_search" in call_args


class TestRequestLogger:
    """Test RequestLogger functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.request_logger = RequestLogger()
    
    def test_request_logger_initialization(self):
        """Test RequestLogger initialization."""
        assert self.request_logger.security_logger is not None
        assert self.request_logger.performance_logger is not None
        assert self.request_logger.business_logger is not None
    
    @pytest.mark.asyncio
    async def test_log_request_success(self):
        """Test successful request logging."""
        # Mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com/api"
        
        user_info = {"user_id": "test_user"}
        
        with patch.object(self.request_logger.performance_logger.logger, 'info') as mock_info:
            async with self.request_logger.log_request(mock_request, user_info):
                # Simulate request processing
                pass
            
            # Should log request start and completion
            assert mock_info.call_count == 2
            start_call = mock_info.call_args_list[0][0][0]
            completion_call = mock_info.call_args_list[1][0][0]
            
            assert "Request started" in start_call
            assert "Request completed" in completion_call
            assert "test_user" in completion_call
    
    @pytest.mark.asyncio
    async def test_log_request_error(self):
        """Test request logging with error."""
        # Mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com/api"
        
        user_info = {"user_id": "test_user"}
        
        with patch.object(self.request_logger.performance_logger.logger, 'info') as mock_info:
            with patch.object(self.request_logger.performance_logger.logger, 'error') as mock_error:
                with pytest.raises(Exception):
                    async with self.request_logger.log_request(mock_request, user_info):
                        raise Exception("Test error")
                
                # Should log request start and error
                assert mock_info.call_count == 1
                assert mock_error.call_count == 1
                
                start_call = mock_info.call_args_list[0][0][0]
                error_call = mock_error.call_args_list[0][0][0]
                
                assert "Request started" in start_call
                assert "Request failed" in error_call
                assert "Test error" in error_call
    
    @pytest.mark.asyncio
    async def test_log_request_without_user_info(self):
        """Test request logging without user info."""
        # Mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com/api"
        
        with patch.object(self.request_logger.performance_logger.logger, 'info') as mock_info:
            async with self.request_logger.log_request(mock_request):
                # Simulate request processing
                pass
            
            # Should log request start and completion
            assert mock_info.call_count == 2
            completion_call = mock_info.call_args_list[1][0][0]
            assert "Request completed" in completion_call


class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    def test_global_logger_instances(self):
        """Test that global logger instances are properly configured."""
        assert security_logger is not None
        assert performance_logger is not None
        assert business_logger is not None
        assert request_logger is not None
        
        # Test that instances have required methods
        assert hasattr(security_logger, 'log_authentication_attempt')
        assert hasattr(security_logger, 'log_rate_limit_exceeded')
        assert hasattr(performance_logger, 'log_request_metrics')
        assert hasattr(performance_logger, 'log_file_processing_metrics')
        assert hasattr(business_logger, 'log_api_usage')
        assert hasattr(business_logger, 'log_attribution_insights')
        assert hasattr(request_logger, 'log_request')
    
    @patch('src.core.logging.logging.basicConfig')
    @patch('src.core.logging.logging.FileHandler')
    @patch('src.core.logging.structlog.configure')
    @patch('src.core.logging.get_settings')
    @patch('os.makedirs')
    def test_setup_logging(self, mock_makedirs, mock_get_settings, mock_structlog, mock_file_handler, mock_basic_config):
        """Test logging setup configuration."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings
        
        # Mock file handler
        mock_handler = Mock()
        mock_file_handler.return_value = mock_handler
        
        # Test setup
        setup_logging()
        
        # Verify structlog configuration
        mock_structlog.assert_called_once()
        
        # Verify basic config
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == logging.INFO
        assert 'logs/application.log' in str(call_args[1]['handlers'])
        
        # Verify logs directory creation
        mock_makedirs.assert_called_once_with("logs", exist_ok=True)
    
    def test_logging_event_structure(self):
        """Test that logged events have proper structure."""
        with patch.object(security_logger.logger, 'info') as mock_info:
            security_logger.log_authentication_attempt(
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
            
            try:
                event_data = json.loads(json_str)
                assert "event_type" in event_data
                assert "api_key" in event_data
                assert "success" in event_data
                assert "ip_address" in event_data
                assert "timestamp" in event_data
            except json.JSONDecodeError:
                pytest.fail("Logged event should contain valid JSON")
    
    def test_logging_timestamp_format(self):
        """Test that logged events have proper timestamp format."""
        with patch.object(security_logger.logger, 'info') as mock_info:
            security_logger.log_authentication_attempt(
                "test_key", True, "192.168.1.1"
            )
            
            call_args = mock_info.call_args[0][0]
            json_start = call_args.find("{")
            json_end = call_args.rfind("}") + 1
            json_str = call_args[json_start:json_end]
            
            event_data = json.loads(json_str)
            timestamp = event_data["timestamp"]
            
            # Should be ISO format
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Timestamp should be in ISO format: {timestamp}")
    
    def test_logging_api_key_masking(self):
        """Test that API keys are properly masked in logs."""
        with patch.object(security_logger.logger, 'info') as mock_info:
            security_logger.log_authentication_attempt(
                "very_long_api_key_12345", True, "192.168.1.1"
            )
            
            call_args = mock_info.call_args[0][0]
            json_start = call_args.find("{")
            json_end = call_args.rfind("}") + 1
            json_str = call_args[json_start:json_end]
            
            event_data = json.loads(json_str)
            api_key = event_data["api_key"]
            
            # Should be masked (first 8 chars + "...")
            assert api_key == "very_long" + "..."
            assert len(api_key) == 12  # 8 + "..."
    
    def test_logging_performance_metrics_calculation(self):
        """Test that performance metrics are calculated correctly."""
        with patch.object(performance_logger.logger, 'info') as mock_info:
            # Test file processing metrics
            performance_logger.log_file_processing_metrics(
                "test.csv", 1024, 2.0, 50.0
            )
            
            call_args = mock_info.call_args[0][0]
            json_start = call_args.find("{")
            json_end = call_args.rfind("}") + 1
            json_str = call_args[json_start:json_end]
            
            event_data = json.loads(json_str)
            
            # Test throughput calculation
            expected_throughput = 1024 / 2.0  # file_size / processing_time
            assert event_data["throughput_mb_per_sec"] == expected_throughput
            
            # Test attribution processing metrics
            performance_logger.log_attribution_processing_metrics(
                "linear", 1000, 1.5, 0.95
            )
            
            call_args = mock_info.call_args[0][0]
            json_start = call_args.find("{")
            json_end = call_args.rfind("}") + 1
            json_str = call_args[json_start:json_end]
            
            event_data = json.loads(json_str)
            
            # Test records per second calculation
            expected_rps = 1000 / 1.5  # data_size / processing_time
            assert abs(event_data["records_per_second"] - expected_rps) < 0.01
