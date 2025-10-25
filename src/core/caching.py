"""Caching system for performance optimization."""

import hashlib
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis
from functools import wraps

from ..config import get_settings


class CacheManager:
    """Manages caching for API responses and processed data."""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = self._get_redis_client()
        self.memory_cache = {}  # Fallback in-memory cache
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for caching."""
        try:
            return redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                decode_responses=True
            )
        except Exception:
            return None
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key from parameters."""
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        key_data = f"{prefix}:{json.dumps(sorted_kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    self.cache_stats["hits"] += 1
                    return json.loads(value)
                else:
                    self.cache_stats["misses"] += 1
                    return None
            else:
                # Fallback to memory cache
                if key in self.memory_cache:
                    cached_item = self.memory_cache[key]
                    if cached_item["expires_at"] > time.time():
                        self.cache_stats["hits"] += 1
                        return cached_item["value"]
                    else:
                        del self.memory_cache[key]
                self.cache_stats["misses"] += 1
                return None
        except Exception:
            self.cache_stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache with TTL."""
        try:
            if self.redis_client:
                success = self.redis_client.setex(
                    key,
                    ttl_seconds,
                    json.dumps(value, default=str)
                )
                if success:
                    self.cache_stats["sets"] += 1
                return bool(success)
            else:
                # Fallback to memory cache
                self.memory_cache[key] = {
                    "value": value,
                    "expires_at": time.time() + ttl_seconds
                }
                self.cache_stats["sets"] += 1
                return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if self.redis_client:
                success = self.redis_client.delete(key)
                if success:
                    self.cache_stats["deletes"] += 1
                return bool(success)
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    self.cache_stats["deletes"] += 1
                return True
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "sets": self.cache_stats["sets"],
            "deletes": self.cache_stats["deletes"],
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }


class AttributionCache:
    """Specialized cache for attribution analysis results."""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.default_ttl = 3600  # 1 hour
    
    def get_attribution_result(self, file_hash: str, model_type: str, 
                             model_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached attribution result."""
        cache_key = self.cache_manager._generate_cache_key(
            "attribution_result",
            file_hash=file_hash,
            model_type=model_type,
            **model_params
        )
        return self.cache_manager.get(cache_key)
    
    def set_attribution_result(self, file_hash: str, model_type: str,
                              model_params: Dict[str, Any], result: Dict[str, Any],
                              ttl_seconds: int = None) -> bool:
        """Cache attribution result."""
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl
            
        cache_key = self.cache_manager._generate_cache_key(
            "attribution_result",
            file_hash=file_hash,
            model_type=model_type,
            **model_params
        )
        return self.cache_manager.set(cache_key, result, ttl_seconds)
    
    def get_file_metadata(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached file metadata."""
        cache_key = f"file_metadata:{file_hash}"
        return self.cache_manager.get(cache_key)
    
    def set_file_metadata(self, file_hash: str, metadata: Dict[str, Any],
                         ttl_seconds: int = 7200) -> bool:  # 2 hours
        """Cache file metadata."""
        cache_key = f"file_metadata:{file_hash}"
        return self.cache_manager.set(cache_key, metadata, ttl_seconds)
    
    def get_validation_result(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result."""
        cache_key = f"validation_result:{file_hash}"
        return self.cache_manager.get(cache_key)
    
    def set_validation_result(self, file_hash: str, result: Dict[str, Any],
                             ttl_seconds: int = 1800) -> bool:  # 30 minutes
        """Cache validation result."""
        cache_key = f"validation_result:{file_hash}"
        return self.cache_manager.set(cache_key, result, ttl_seconds)


class APICache:
    """Cache for API responses and method listings."""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.methods_ttl = 86400  # 24 hours
    
    def get_available_methods(self) -> Optional[Dict[str, Any]]:
        """Get cached available methods."""
        cache_key = "available_methods"
        return self.cache_manager.get(cache_key)
    
    def set_available_methods(self, methods: Dict[str, Any]) -> bool:
        """Cache available methods."""
        cache_key = "available_methods"
        return self.cache_manager.set(cache_key, methods, self.methods_ttl)
    
    def get_health_status(self) -> Optional[Dict[str, Any]]:
        """Get cached health status."""
        cache_key = "health_status"
        return self.cache_manager.get(cache_key)
    
    def set_health_status(self, status: Dict[str, Any], ttl_seconds: int = 60) -> bool:
        """Cache health status."""
        cache_key = "health_status"
        return self.cache_manager.set(cache_key, status, ttl_seconds)


def cache_result(ttl_seconds: int = 3600, key_prefix: str = "default"):
    """
    Decorator for caching function results.
    
    Args:
        ttl_seconds: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_manager = CacheManager()
            
            # Generate cache key from function name and arguments
            cache_key = cache_manager._generate_cache_key(
                f"{key_prefix}:{func.__name__}",
                args=args,
                **kwargs
            )
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


# Global cache instances
attribution_cache = AttributionCache()
api_cache = APICache()
cache_manager = CacheManager()
