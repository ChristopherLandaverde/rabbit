"""Authentication dependencies for FastAPI."""

from typing import Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .security import security_middleware, input_validator
from ..config import get_settings


# HTTP Bearer security scheme
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    Get current authenticated user from API key.
    
    Args:
        request: FastAPI request object
        credentials: HTTP authorization credentials
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    settings = get_settings()
    
    # Skip authentication in development if disabled
    if not settings.enable_api_key_auth:
        return {
            "user_id": "dev_user",
            "permissions": ["read", "write"],
            "created_at": "2024-01-01T00:00:00Z",
            "last_used": "2024-01-01T00:00:00Z",
            "is_active": True,
            "rate_limit": 1000
        }
    
    try:
        # Validate request and get user info
        user_info = await security_middleware.validate_request(request)
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_failed",
                "message": f"Authentication failed: {str(e)}",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )


async def require_permission(permission: str):
    """
    Dependency factory for permission-based access control.
    
    Args:
        permission: Required permission (read, write, admin)
        
    Returns:
        Dependency function that checks for the required permission
    """
    async def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """Check if user has required permission."""
        user_permissions = current_user.get("permissions", [])
        
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_permissions",
                    "message": f"Permission '{permission}' required",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            )
        
        return current_user
    
    return permission_checker


async def validate_file_upload(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate file upload request with security checks.
    
    Args:
        request: FastAPI request object
        current_user: Authenticated user information
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    # Check if user has write permission
    user_permissions = current_user.get("permissions", [])
    if "write" not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "insufficient_permissions",
                "message": "Write permission required for file uploads",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )
    
    return current_user


async def validate_analysis_request(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate attribution analysis request with security checks.
    
    Args:
        request: FastAPI request object
        current_user: Authenticated user information
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    # Check if user has read permission
    user_permissions = current_user.get("permissions", [])
    if "read" not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "insufficient_permissions",
                "message": "Read permission required for analysis requests",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )
    
    return current_user


# Common permission dependencies
require_read_permission = require_permission("read")
require_write_permission = require_permission("write")
require_admin_permission = require_permission("admin")
