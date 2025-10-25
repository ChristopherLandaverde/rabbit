"""Security utilities for API authentication and authorization."""

import hashlib
import secrets
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
import redis
import json

from ..config import get_settings


class APIKeyManager:
    """Manages API key generation, validation, and rate limiting."""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = self._get_redis_client()
        
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for caching and rate limiting."""
        try:
            return redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                decode_responses=True
            )
        except Exception:
            # Fallback to in-memory storage if Redis is not available
            return None
    
    def generate_api_key(self, user_id: str, permissions: list = None) -> str:
        """Generate a new API key for a user."""
        if permissions is None:
            permissions = ["read", "write"]
            
        # Generate secure random key
        key_data = f"{user_id}:{secrets.token_urlsafe(32)}:{int(time.time())}"
        api_key = hashlib.sha256(key_data.encode()).hexdigest()
        
        # Store key metadata
        key_metadata = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "is_active": True,
            "rate_limit": self.settings.default_rate_limit
        }
        
        if self.redis_client:
            self.redis_client.setex(
                f"api_key:{api_key}",
                self.settings.api_key_ttl_seconds,
                json.dumps(key_metadata)
            )
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate API key and return user information."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "missing_api_key",
                    "message": "API key is required",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Check if key exists and is valid
        if self.redis_client:
            key_data = self.redis_client.get(f"api_key:{api_key}")
            if not key_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "invalid_api_key",
                        "message": "Invalid or expired API key",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            key_metadata = json.loads(key_data)
            if not key_metadata.get("is_active", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "inactive_api_key",
                        "message": "API key is inactive",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            # Update last used timestamp
            key_metadata["last_used"] = datetime.utcnow().isoformat()
            self.redis_client.setex(
                f"api_key:{api_key}",
                self.settings.api_key_ttl_seconds,
                json.dumps(key_metadata)
            )
            
            return key_metadata
        else:
            # Fallback validation for development
            if api_key == "dev-api-key":
                return {
                    "user_id": "dev_user",
                    "permissions": ["read", "write"],
                    "created_at": datetime.utcnow().isoformat(),
                    "last_used": datetime.utcnow().isoformat(),
                    "is_active": True,
                    "rate_limit": 1000
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "invalid_api_key",
                        "message": "Invalid API key",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
    
    def check_rate_limit(self, api_key: str, endpoint: str) -> bool:
        """Check if request is within rate limits."""
        if not self.redis_client:
            return True  # Skip rate limiting in development
        
        # Get rate limit for the API key
        key_data = self.redis_client.get(f"api_key:{api_key}")
        if not key_data:
            return False
        
        key_metadata = json.loads(key_data)
        rate_limit = key_metadata.get("rate_limit", 1000)
        
        # Check rate limit for this endpoint
        current_time = int(time.time())
        window_start = current_time - 3600  # 1 hour window
        
        # Clean old entries
        self.redis_client.zremrangebyscore(
            f"rate_limit:{api_key}:{endpoint}",
            0,
            window_start
        )
        
        # Count requests in current window
        request_count = self.redis_client.zcard(f"rate_limit:{api_key}:{endpoint}")
        
        if request_count >= rate_limit:
            return False
        
        # Add current request
        self.redis_client.zadd(
            f"rate_limit:{api_key}:{endpoint}",
            {str(current_time): current_time}
        )
        self.redis_client.expire(
            f"rate_limit:{api_key}:{endpoint}",
            3600
        )
        
        return True
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if self.redis_client:
            return bool(self.redis_client.delete(f"api_key:{api_key}"))
        return False


class SecurityMiddleware:
    """Security middleware for request validation and protection."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key_manager = APIKeyManager()
    
    async def validate_request(self, request: Request) -> Dict[str, Any]:
        """Validate incoming request for security."""
        # Check for API key
        api_key = self._extract_api_key(request)
        user_info = self.api_key_manager.validate_api_key(api_key)
        
        # Check rate limiting
        endpoint = f"{request.method}:{request.url.path}"
        if not self.api_key_manager.check_rate_limit(api_key, endpoint):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Rate limit exceeded for this API key",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return user_info
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers."""
        # Check X-API-Key header first
        api_key = request.headers.get(self.settings.api_key_header)
        if api_key:
            return api_key
        
        # Check Authorization header as fallback
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, param = get_authorization_scheme_param(authorization)
            if scheme.lower() == "bearer":
                return param
        
        return None
    
    def add_security_headers(self, response):
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class InputValidator:
    """Validates and sanitizes input data."""
    
    @staticmethod
    def validate_file_upload(file_size: int, filename: str) -> None:
        """Validate file upload parameters."""
        settings = get_settings()
        
        # Check file size
        if file_size > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "file_too_large",
                    "message": f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Check file extension
        allowed_extensions = ['.csv', '.json', '.parquet']
        if filename:
            file_ext = filename.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": "invalid_file_type",
                        "message": f"File type not supported. Allowed types: {allowed_extensions}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Remove potentially dangerous characters
        sanitized = value.strip()[:max_length]
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
        
        return sanitized
    
    @staticmethod
    def validate_model_parameters(model_type: str, **kwargs) -> Dict[str, Any]:
        """Validate attribution model parameters."""
        settings = get_settings()
        
        if model_type == "time_decay":
            half_life = kwargs.get("half_life_days")
            if half_life is not None:
                if not isinstance(half_life, (int, float)) or half_life <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "invalid_parameter",
                            "message": "half_life_days must be a positive number",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
        
        elif model_type == "position_based":
            first_weight = kwargs.get("first_touch_weight")
            last_weight = kwargs.get("last_touch_weight")
            
            if first_weight is not None:
                if not isinstance(first_weight, (int, float)) or not 0 <= first_weight <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "invalid_parameter",
                            "message": "first_touch_weight must be between 0 and 1",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
            
            if last_weight is not None:
                if not isinstance(last_weight, (int, float)) or not 0 <= last_weight <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "invalid_parameter",
                            "message": "last_touch_weight must be between 0 and 1",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
        
        return kwargs


# Global security instances
security_middleware = SecurityMiddleware()
input_validator = InputValidator()
