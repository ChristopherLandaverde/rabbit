"""Tests for security module - API key management, rate limiting, and input validation."""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from src.core.security import (
    APIKeyManager, SecurityMiddleware, InputValidator,
    security_middleware, input_validator
)
from src.config import get_settings


class TestAPIKeyManager:
    """Test API key management functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.api_key_manager = APIKeyManager()
        self.settings = get_settings()
    
    @patch('src.core.security.redis.Redis')
    def test_generate_api_key_with_redis(self, mock_redis):
        """Test API key generation with Redis backend."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Create new manager with mocked Redis
        manager = APIKeyManager()
        
        # Generate API key
        api_key = manager.generate_api_key("test_user", ["read", "write"])
        
        # Verify API key format
        assert isinstance(api_key, str)
        assert len(api_key) == 64  # SHA256 hex length
        
        # Verify Redis setex was called
        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0].startswith("api_key:")
        assert call_args[0][1] == self.settings.api_key_ttl_seconds
        
        # Verify stored metadata
        stored_data = json.loads(call_args[0][2])
        assert stored_data["user_id"] == "test_user"
        assert stored_data["permissions"] == ["read", "write"]
        assert stored_data["is_active"] is True
    
    def test_generate_api_key_without_redis(self):
        """Test API key generation without Redis (fallback)."""
        with patch.object(self.api_key_manager, 'redis_client', None):
            api_key = self.api_key_manager.generate_api_key("test_user")
            
            assert isinstance(api_key, str)
            assert len(api_key) == 64
    
    @patch('src.core.security.redis.Redis')
    def test_validate_api_key_success(self, mock_redis):
        """Test successful API key validation."""
        # Mock Redis client with valid key data
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "created_at": "2024-01-01T00:00:00Z",
            "last_used": None,
            "is_active": True,
            "rate_limit": 1000
        }
        
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        
        manager = APIKeyManager()
        result = manager.validate_api_key("valid_key")
        
        assert result["user_id"] == "test_user"
        assert result["permissions"] == ["read", "write"]
        assert result["is_active"] is True
        
        # Verify last_used was updated
        mock_redis_client.setex.assert_called_once()
    
    def test_validate_api_key_missing(self):
        """Test API key validation with missing key."""
        with pytest.raises(HTTPException) as exc_info:
            self.api_key_manager.validate_api_key("")
        
        assert exc_info.value.status_code == 401
        assert "missing_api_key" in str(exc_info.value.detail)
    
    @patch('src.core.security.redis.Redis')
    def test_validate_api_key_invalid(self, mock_redis):
        """Test API key validation with invalid key."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = None
        
        manager = APIKeyManager()
        
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key("invalid_key")
        
        assert exc_info.value.status_code == 401
        assert "invalid_api_key" in str(exc_info.value.detail)
    
    @patch('src.core.security.redis.Redis')
    def test_validate_api_key_inactive(self, mock_redis):
        """Test API key validation with inactive key."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": False
        }
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        
        manager = APIKeyManager()
        
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key("inactive_key")
        
        assert exc_info.value.status_code == 401
        assert "inactive_api_key" in str(exc_info.value.detail)
    
    def test_validate_api_key_dev_fallback(self):
        """Test API key validation with development fallback."""
        with patch.object(self.api_key_manager, 'redis_client', None):
            # Test with dev key
            result = self.api_key_manager.validate_api_key("dev-api-key")
            assert result["user_id"] == "dev_user"
            assert result["permissions"] == ["read", "write"]
            
            # Test with invalid key
            with pytest.raises(HTTPException) as exc_info:
                self.api_key_manager.validate_api_key("invalid")
            assert exc_info.value.status_code == 401
    
    @patch('src.core.security.redis.Redis')
    def test_check_rate_limit_success(self, mock_redis):
        """Test successful rate limit check."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        key_metadata = {"rate_limit": 1000}
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 5  # Under limit
        
        manager = APIKeyManager()
        result = manager.check_rate_limit("test_key", "test_endpoint")
        
        assert result is True
        mock_redis_client.zadd.assert_called_once()
    
    @patch('src.core.security.redis.Redis')
    def test_check_rate_limit_exceeded(self, mock_redis):
        """Test rate limit check when limit is exceeded."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        key_metadata = {"rate_limit": 1000}
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 1000  # At limit
        
        manager = APIKeyManager()
        result = manager.check_rate_limit("test_key", "test_endpoint")
        
        assert result is False
    
    def test_check_rate_limit_no_redis(self):
        """Test rate limit check without Redis (development mode)."""
        with patch.object(self.api_key_manager, 'redis_client', None):
            result = self.api_key_manager.check_rate_limit("test_key", "test_endpoint")
            assert result is True
    
    @patch('src.core.security.redis.Redis')
    def test_revoke_api_key(self, mock_redis):
        """Test API key revocation."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.delete.return_value = 1
        
        manager = APIKeyManager()
        result = manager.revoke_api_key("test_key")
        
        assert result is True
        mock_redis_client.delete.assert_called_once_with("api_key:test_key")


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.middleware = SecurityMiddleware()
    
    @patch('src.core.security.redis.Redis')
    @pytest.mark.asyncio
    async def test_validate_request_success(self, mock_redis):
        """Test successful request validation."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.headers = {"X-API-Key": "test_key"}
        
        # Mock Redis responses
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": True,
            "rate_limit": 1000
        }
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 5  # Under rate limit
        mock_redis_client.zadd.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.zremrangebyscore.return_value = 0
        
        # Create new middleware with mocked Redis
        middleware = SecurityMiddleware()
        
        # Test validation
        result = await middleware.validate_request(mock_request)
        
        assert result["user_id"] == "test_user"
        assert result["permissions"] == ["read", "write"]
    
    @patch('src.core.security.redis.Redis')
    @pytest.mark.asyncio
    async def test_validate_request_rate_limit_exceeded(self, mock_redis):
        """Test request validation with rate limit exceeded."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.headers = {"X-API-Key": "test_key"}
        
        # Mock Redis responses
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": True,
            "rate_limit": 1000
        }
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 1000  # At rate limit
        mock_redis_client.zadd.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.zremrangebyscore.return_value = 0
        
        # Create new middleware with mocked Redis
        middleware = SecurityMiddleware()
        
        # Test validation
        with pytest.raises(HTTPException) as exc_info:
            await middleware.validate_request(mock_request)
        
        assert exc_info.value.status_code == 429
        assert "rate_limit_exceeded" in str(exc_info.value.detail)
    
    def test_extract_api_key_from_header(self):
        """Test API key extraction from X-API-Key header."""
        mock_request = Mock()
        mock_request.headers = {"X-API-Key": "test_key"}
        
        result = self.middleware._extract_api_key(mock_request)
        assert result == "test_key"
    
    def test_extract_api_key_from_authorization(self):
        """Test API key extraction from Authorization header."""
        mock_request = Mock()
        mock_request.headers = {"Authorization": "Bearer test_key"}
        
        result = self.middleware._extract_api_key(mock_request)
        assert result == "test_key"
    
    def test_extract_api_key_missing(self):
        """Test API key extraction when no key is provided."""
        mock_request = Mock()
        mock_request.headers = {}
        
        result = self.middleware._extract_api_key(mock_request)
        assert result is None
    
    def test_add_security_headers(self):
        """Test adding security headers to response."""
        mock_response = Mock()
        mock_response.headers = {}
        
        result = self.middleware.add_security_headers(mock_response)
        
        assert "X-Content-Type-Options" in result.headers
        assert "X-Frame-Options" in result.headers
        assert "X-XSS-Protection" in result.headers
        assert "Strict-Transport-Security" in result.headers
        assert "Referrer-Policy" in result.headers


class TestInputValidator:
    """Test input validation and sanitization."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = InputValidator()
    
    def test_validate_file_upload_valid(self):
        """Test valid file upload validation."""
        # Should not raise exception
        self.validator.validate_file_upload(1024, "test.csv")
    
    def test_validate_file_upload_too_large(self):
        """Test file upload validation with oversized file."""
        settings = get_settings()
        large_size = (settings.max_file_size_mb + 1) * 1024 * 1024
        
        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_file_upload(large_size, "test.csv")
        
        assert exc_info.value.status_code == 413
        assert "file_too_large" in str(exc_info.value.detail)
    
    def test_validate_file_upload_invalid_type(self):
        """Test file upload validation with invalid file type."""
        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_file_upload(1024, "test.txt")
        
        assert exc_info.value.status_code == 422
        assert "invalid_file_type" in str(exc_info.value.detail)
    
    def test_validate_file_upload_no_extension(self):
        """Test file upload validation with no file extension."""
        # Should not raise exception for files without extension
        self.validator.validate_file_upload(1024, None)
    
    def test_sanitize_string_valid(self):
        """Test string sanitization with valid input."""
        result = self.validator.sanitize_string("  test string  ")
        assert result == "test string"
    
    def test_sanitize_string_with_control_chars(self):
        """Test string sanitization with control characters."""
        result = self.validator.sanitize_string("test\x00string\x01")
        assert result == "teststring"
    
    def test_sanitize_string_too_long(self):
        """Test string sanitization with overly long input."""
        long_string = "a" * 2000
        result = self.validator.sanitize_string(long_string, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_string_invalid_type(self):
        """Test string sanitization with invalid input type."""
        with pytest.raises(ValueError):
            self.validator.sanitize_string(123)
    
    def test_validate_model_parameters_time_decay_valid(self):
        """Test time decay model parameter validation with valid parameters."""
        result = self.validator.validate_model_parameters(
            "time_decay", half_life_days=7.0
        )
        assert result["half_life_days"] == 7.0
    
    def test_validate_model_parameters_time_decay_invalid(self):
        """Test time decay model parameter validation with invalid parameters."""
        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_model_parameters(
                "time_decay", half_life_days=-1.0
            )
        
        assert exc_info.value.status_code == 422
        assert "invalid_parameter" in str(exc_info.value.detail)
    
    def test_validate_model_parameters_position_based_valid(self):
        """Test position-based model parameter validation with valid parameters."""
        result = self.validator.validate_model_parameters(
            "position_based",
            first_touch_weight=0.4,
            last_touch_weight=0.4
        )
        assert result["first_touch_weight"] == 0.4
        assert result["last_touch_weight"] == 0.4
    
    def test_validate_model_parameters_position_based_invalid_first_weight(self):
        """Test position-based model parameter validation with invalid first weight."""
        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_model_parameters(
                "position_based", first_touch_weight=1.5
            )
        
        assert exc_info.value.status_code == 422
        assert "invalid_parameter" in str(exc_info.value.detail)
    
    def test_validate_model_parameters_position_based_invalid_last_weight(self):
        """Test position-based model parameter validation with invalid last weight."""
        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_model_parameters(
                "position_based", last_touch_weight=-0.1
            )
        
        assert exc_info.value.status_code == 422
        assert "invalid_parameter" in str(exc_info.value.detail)
    
    def test_validate_model_parameters_unknown_model(self):
        """Test model parameter validation with unknown model type."""
        result = self.validator.validate_model_parameters("unknown_model")
        assert result == {}


class TestSecurityIntegration:
    """Integration tests for security components."""
    
    def test_security_middleware_global_instance(self):
        """Test that global security middleware instance is properly configured."""
        assert security_middleware is not None
        assert hasattr(security_middleware, 'validate_request')
        assert hasattr(security_middleware, 'add_security_headers')
    
    def test_input_validator_global_instance(self):
        """Test that global input validator instance is properly configured."""
        assert input_validator is not None
        assert hasattr(input_validator, 'validate_file_upload')
        assert hasattr(input_validator, 'sanitize_string')
        assert hasattr(input_validator, 'validate_model_parameters')
    
    @patch('src.core.security.redis.Redis')
    @pytest.mark.asyncio
    async def test_end_to_end_security_flow(self, mock_redis):
        """Test end-to-end security flow with mocked Redis."""
        # Setup mocked Redis
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        key_metadata = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": True,
            "rate_limit": 1000
        }
        mock_redis_client.get.return_value = json.dumps(key_metadata)
        mock_redis_client.zcard.return_value = 5
        
        # Test API key generation
        manager = APIKeyManager()
        api_key = manager.generate_api_key("test_user", ["read", "write"])
        
        # Test API key validation
        user_info = manager.validate_api_key(api_key)
        assert user_info["user_id"] == "test_user"
        
        # Test rate limiting
        rate_limit_ok = manager.check_rate_limit(api_key, "test_endpoint")
        assert rate_limit_ok is True
        
        # Test request validation
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.headers = {"X-API-Key": api_key}
        
        middleware = SecurityMiddleware()
        result = await middleware.validate_request(mock_request)
        assert result["user_id"] == "test_user"
