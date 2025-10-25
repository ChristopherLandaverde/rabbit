"""Tests for authentication and authorization module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient

from src.core.auth import (
    get_current_user, require_permission, validate_file_upload,
    validate_analysis_request, require_read_permission,
    require_write_permission, require_admin_permission
)
from src.config import get_settings


class TestGetCurrentUser:
    """Test get_current_user dependency."""
    
    @patch('src.core.auth.get_settings')
    @patch('src.core.auth.security_middleware')
    async def test_get_current_user_auth_disabled(self, mock_security_middleware, mock_get_settings):
        """Test get_current_user when authentication is disabled."""
        # Mock settings with auth disabled
        mock_settings = Mock()
        mock_settings.enable_api_key_auth = False
        mock_get_settings.return_value = mock_settings
        
        # Mock request
        mock_request = Mock()
        mock_credentials = Mock()
        
        # Test function
        result = await get_current_user(mock_request, mock_credentials)
        
        assert result["user_id"] == "dev_user"
        assert result["permissions"] == ["read", "write"]
        assert result["is_active"] is True
        assert result["rate_limit"] == 1000
    
    @patch('src.core.auth.get_settings')
    @patch('src.core.auth.security_middleware')
    async def test_get_current_user_auth_enabled_success(self, mock_security_middleware, mock_get_settings):
        """Test get_current_user when authentication is enabled and successful."""
        # Mock settings with auth enabled
        mock_settings = Mock()
        mock_settings.enable_api_key_auth = True
        mock_get_settings.return_value = mock_settings
        
        # Mock security middleware
        mock_user_info = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "created_at": "2024-01-01T00:00:00Z",
            "last_used": "2024-01-01T00:00:00Z",
            "is_active": True,
            "rate_limit": 1000
        }
        mock_security_middleware.validate_request = AsyncMock(return_value=mock_user_info)
        
        # Mock request
        mock_request = Mock()
        mock_credentials = Mock()
        
        # Test function
        result = await get_current_user(mock_request, mock_credentials)
        
        assert result["user_id"] == "test_user"
        assert result["permissions"] == ["read", "write"]
        mock_security_middleware.validate_request.assert_called_once_with(mock_request)
    
    @patch('src.core.auth.get_settings')
    @patch('src.core.auth.security_middleware')
    async def test_get_current_user_auth_enabled_http_exception(self, mock_security_middleware, mock_get_settings):
        """Test get_current_user when authentication raises HTTPException."""
        # Mock settings with auth enabled
        mock_settings = Mock()
        mock_settings.enable_api_key_auth = True
        mock_get_settings.return_value = mock_settings
        
        # Mock security middleware to raise HTTPException
        mock_security_middleware.validate_request = AsyncMock(
            side_effect=HTTPException(status_code=401, detail="Invalid API key")
        )
        
        # Mock request
        mock_request = Mock()
        mock_credentials = Mock()
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value.detail)
    
    @patch('src.core.auth.get_settings')
    @patch('src.core.auth.security_middleware')
    async def test_get_current_user_auth_enabled_general_exception(self, mock_security_middleware, mock_get_settings):
        """Test get_current_user when authentication raises general exception."""
        # Mock settings with auth enabled
        mock_settings = Mock()
        mock_settings.enable_api_key_auth = True
        mock_get_settings.return_value = mock_settings
        
        # Mock security middleware to raise general exception
        mock_security_middleware.validate_request = AsyncMock(
            side_effect=Exception("Connection error")
        )
        
        # Mock request
        mock_request = Mock()
        mock_credentials = Mock()
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "authentication_failed" in str(exc_info.value.detail)
        assert "Connection error" in str(exc_info.value.detail)


class TestRequirePermission:
    """Test require_permission dependency factory."""
    
    async def test_require_permission_success(self):
        """Test require_permission with valid permission."""
        # Mock current user with required permission
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Create permission checker
        permission_checker = require_permission("read")
        
        # Test function
        result = await permission_checker(mock_current_user)
        assert result == mock_current_user
    
    async def test_require_permission_insufficient(self):
        """Test require_permission with insufficient permissions."""
        # Mock current user without required permission
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read"]
        }
        
        # Create permission checker
        permission_checker = require_permission("admin")
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await permission_checker(mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)
        assert "Permission 'admin' required" in str(exc_info.value.detail)
    
    async def test_require_permission_no_permissions(self):
        """Test require_permission with no permissions."""
        # Mock current user with no permissions
        mock_current_user = {
            "user_id": "test_user",
            "permissions": []
        }
        
        # Create permission checker
        permission_checker = require_permission("read")
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await permission_checker(mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)


class TestValidateFileUpload:
    """Test validate_file_upload dependency."""
    
    async def test_validate_file_upload_success(self):
        """Test validate_file_upload with write permission."""
        # Mock current user with write permission
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock request
        mock_request = Mock()
        
        # Test function
        result = await validate_file_upload(mock_request, mock_current_user)
        assert result == mock_current_user
    
    async def test_validate_file_upload_insufficient_permission(self):
        """Test validate_file_upload without write permission."""
        # Mock current user without write permission
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read"]
        }
        
        # Mock request
        mock_request = Mock()
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_request, mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)
        assert "Write permission required for file uploads" in str(exc_info.value.detail)
    
    async def test_validate_file_upload_no_permissions(self):
        """Test validate_file_upload with no permissions."""
        # Mock current user with no permissions
        mock_current_user = {
            "user_id": "test_user",
            "permissions": []
        }
        
        # Mock request
        mock_request = Mock()
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_request, mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)


class TestValidateAnalysisRequest:
    """Test validate_analysis_request dependency."""
    
    async def test_validate_analysis_request_success(self):
        """Test validate_analysis_request with read permission."""
        # Mock current user with read permission
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock request
        mock_request = Mock()
        
        # Test function
        result = await validate_analysis_request(mock_request, mock_current_user)
        assert result == mock_current_user
    
    async def test_validate_analysis_request_insufficient_permission(self):
        """Test validate_analysis_request without read permission."""
        # Mock current user without read permission
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["write"]
        }
        
        # Mock request
        mock_request = Mock()
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await validate_analysis_request(mock_request, mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)
        assert "Read permission required for analysis requests" in str(exc_info.value.detail)
    
    async def test_validate_analysis_request_no_permissions(self):
        """Test validate_analysis_request with no permissions."""
        # Mock current user with no permissions
        mock_current_user = {
            "user_id": "test_user",
            "permissions": []
        }
        
        # Mock request
        mock_request = Mock()
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await validate_analysis_request(mock_request, mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)


class TestPermissionDependencies:
    """Test common permission dependencies."""
    
    async def test_require_read_permission_success(self):
        """Test require_read_permission with read permission."""
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        result = await require_read_permission(mock_current_user)
        assert result == mock_current_user
    
    async def test_require_read_permission_failure(self):
        """Test require_read_permission without read permission."""
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["write"]
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await require_read_permission(mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)
    
    async def test_require_write_permission_success(self):
        """Test require_write_permission with write permission."""
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        result = await require_write_permission(mock_current_user)
        assert result == mock_current_user
    
    async def test_require_write_permission_failure(self):
        """Test require_write_permission without write permission."""
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read"]
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await require_write_permission(mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)
    
    async def test_require_admin_permission_success(self):
        """Test require_admin_permission with admin permission."""
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write", "admin"]
        }
        
        result = await require_admin_permission(mock_current_user)
        assert result == mock_current_user
    
    async def test_require_admin_permission_failure(self):
        """Test require_admin_permission without admin permission."""
        mock_current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_permission(mock_current_user)
        
        assert exc_info.value.status_code == 403
        assert "insufficient_permissions" in str(exc_info.value.detail)


class TestAuthIntegration:
    """Integration tests for authentication and authorization."""
    
    @patch('src.core.auth.get_settings')
    @patch('src.core.auth.security_middleware')
    async def test_auth_flow_with_permissions(self, mock_security_middleware, mock_get_settings):
        """Test complete authentication flow with permission checking."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.enable_api_key_auth = True
        mock_get_settings.return_value = mock_settings
        
        # Mock security middleware
        mock_user_info = {
            "user_id": "test_user",
            "permissions": ["read", "write", "admin"],
            "created_at": "2024-01-01T00:00:00Z",
            "last_used": "2024-01-01T00:00:00Z",
            "is_active": True,
            "rate_limit": 1000
        }
        mock_security_middleware.validate_request = AsyncMock(return_value=mock_user_info)
        
        # Mock request
        mock_request = Mock()
        mock_credentials = Mock()
        
        # Test authentication
        user_info = await get_current_user(mock_request, mock_credentials)
        assert user_info["user_id"] == "test_user"
        assert "read" in user_info["permissions"]
        assert "write" in user_info["permissions"]
        assert "admin" in user_info["permissions"]
        
        # Test permission checking
        read_result = await require_read_permission(user_info)
        assert read_result == user_info
        
        write_result = await require_write_permission(user_info)
        assert write_result == user_info
        
        admin_result = await require_admin_permission(user_info)
        assert admin_result == user_info
    
    async def test_permission_hierarchy(self):
        """Test permission hierarchy and combinations."""
        # Test user with all permissions
        admin_user = {
            "user_id": "admin_user",
            "permissions": ["read", "write", "admin"]
        }
        
        # All permissions should work
        assert await require_read_permission(admin_user) == admin_user
        assert await require_write_permission(admin_user) == admin_user
        assert await require_admin_permission(admin_user) == admin_user
        
        # Test user with limited permissions
        limited_user = {
            "user_id": "limited_user",
            "permissions": ["read"]
        }
        
        # Only read permission should work
        assert await require_read_permission(limited_user) == limited_user
        
        with pytest.raises(HTTPException):
            await require_write_permission(limited_user)
        
        with pytest.raises(HTTPException):
            await require_admin_permission(limited_user)
    
    @patch('src.core.auth.get_settings')
    async def test_development_mode_auth(self, mock_get_settings):
        """Test authentication in development mode."""
        # Mock settings with auth disabled
        mock_settings = Mock()
        mock_settings.enable_api_key_auth = False
        mock_get_settings.return_value = mock_settings
        
        # Mock request
        mock_request = Mock()
        mock_credentials = Mock()
        
        # Test authentication
        user_info = await get_current_user(mock_request, mock_credentials)
        assert user_info["user_id"] == "dev_user"
        assert user_info["permissions"] == ["read", "write"]
        
        # Test that dev user can perform all operations
        assert await require_read_permission(user_info) == user_info
        assert await require_write_permission(user_info) == user_info
        
        # Dev user should not have admin permission
        with pytest.raises(HTTPException):
            await require_admin_permission(user_info)
