"""Tests for caching system - Redis, memory fallback, and cache decorators."""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.core.caching import (
    CacheManager, AttributionCache, APICache, cache_result,
    attribution_cache, api_cache, cache_manager
)
from src.config import get_settings


class TestCacheManager:
    """Test CacheManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.cache_manager = CacheManager()
    
    @patch('src.core.caching.redis.Redis')
    def test_cache_manager_with_redis(self, mock_redis):
        """Test CacheManager with Redis backend."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Create new manager with mocked Redis
        manager = CacheManager()
        
        # Test cache key generation
        cache_key = manager._generate_cache_key("test_prefix", param1="value1", param2="value2")
        assert isinstance(cache_key, str)
        assert len(cache_key) > 0
        
        # Test cache set operation
        test_data = {"key": "value", "number": 123}
        mock_redis_client.setex.return_value = True
        
        result = manager.set("test_key", test_data, 3600)
        assert result is True
        mock_redis_client.setex.assert_called_once()
        
        # Test cache get operation
        mock_redis_client.get.return_value = json.dumps(test_data)
        cached_data = manager.get("test_key")
        assert cached_data == test_data
        
        # Test cache delete operation
        mock_redis_client.delete.return_value = 1
        result = manager.delete("test_key")
        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")
    
    def test_cache_manager_without_redis(self):
        """Test CacheManager without Redis (memory fallback)."""
        with patch.object(self.cache_manager, 'redis_client', None):
            # Test cache set operation
            test_data = {"key": "value", "number": 123}
            result = self.cache_manager.set("test_key", test_data, 3600)
            assert result is True
            
            # Test cache get operation
            cached_data = self.cache_manager.get("test_key")
            assert cached_data == test_data
            
            # Test cache delete operation
            result = self.cache_manager.delete("test_key")
            assert result is True
            
            # Test cache miss after deletion
            cached_data = self.cache_manager.get("test_key")
            assert cached_data is None
    
    def test_cache_manager_ttl_expiration(self):
        """Test cache TTL expiration in memory cache."""
        with patch.object(self.cache_manager, 'redis_client', None):
            # Set data with short TTL
            test_data = {"key": "value"}
            self.cache_manager.set("test_key", test_data, 1)  # 1 second TTL
            
            # Should be available immediately
            cached_data = self.cache_manager.get("test_key")
            assert cached_data == test_data
            
            # Wait for expiration
            time.sleep(1.1)
            
            # Should be None after expiration
            cached_data = self.cache_manager.get("test_key")
            assert cached_data is None
    
    def test_cache_manager_error_handling(self):
        """Test cache manager error handling."""
        with patch.object(self.cache_manager, 'redis_client', None):
            # Test get with non-existent key
            result = self.cache_manager.get("non_existent_key")
            assert result is None
            
            # Test delete with non-existent key
            result = self.cache_manager.delete("non_existent_key")
            assert result is True  # Should not raise exception
    
    def test_cache_manager_stats(self):
        """Test cache statistics tracking."""
        with patch.object(self.cache_manager, 'redis_client', None):
            # Initial stats
            stats = self.cache_manager.get_stats()
            assert stats["hits"] == 0
            assert stats["misses"] == 0
            assert stats["sets"] == 0
            assert stats["deletes"] == 0
            assert stats["hit_rate"] == 0
            
            # Perform operations
            self.cache_manager.set("key1", "value1", 3600)
            self.cache_manager.get("key1")  # Hit
            self.cache_manager.get("key2")  # Miss
            self.cache_manager.delete("key1")
            
            # Check updated stats
            stats = self.cache_manager.get_stats()
            assert stats["hits"] == 1
            assert stats["misses"] == 1
            assert stats["sets"] == 1
            assert stats["deletes"] == 1
            assert stats["hit_rate"] == 0.5  # 1 hit out of 2 total requests


class TestAttributionCache:
    """Test AttributionCache functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.attribution_cache = AttributionCache()
    
    @patch('src.core.caching.redis.Redis')
    def test_attribution_cache_with_redis(self, mock_redis):
        """Test AttributionCache with Redis backend."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Create new cache with mocked Redis
        cache = AttributionCache()
        
        # Test attribution result caching
        file_hash = "test_hash"
        model_type = "linear"
        model_params = {"param1": "value1"}
        result_data = {"attribution": "result", "confidence": 0.95}
        
        # Test cache set
        mock_redis_client.setex.return_value = True
        result = cache.set_attribution_result(file_hash, model_type, model_params, result_data)
        assert result is True
        
        # Test cache get
        mock_redis_client.get.return_value = json.dumps(result_data)
        cached_result = cache.get_attribution_result(file_hash, model_type, model_params)
        assert cached_result == result_data
        
        # Test file metadata caching
        metadata = {"file_size": 1024, "columns": ["col1", "col2"]}
        cache.set_file_metadata(file_hash, metadata)
        mock_redis_client.get.return_value = json.dumps(metadata)
        cached_metadata = cache.get_file_metadata(file_hash)
        assert cached_metadata == metadata
        
        # Test validation result caching
        validation_result = {"valid": True, "errors": []}
        cache.set_validation_result(file_hash, validation_result)
        mock_redis_client.get.return_value = json.dumps(validation_result)
        cached_validation = cache.get_validation_result(file_hash)
        assert cached_validation == validation_result
    
    def test_attribution_cache_without_redis(self):
        """Test AttributionCache without Redis (memory fallback)."""
        with patch.object(self.attribution_cache.cache_manager, 'redis_client', None):
            # Test attribution result caching
            file_hash = "test_hash"
            model_type = "linear"
            model_params = {"param1": "value1"}
            result_data = {"attribution": "result", "confidence": 0.95}
            
            # Test cache set
            result = self.attribution_cache.set_attribution_result(
                file_hash, model_type, model_params, result_data
            )
            assert result is True
            
            # Test cache get
            cached_result = self.attribution_cache.get_attribution_result(
                file_hash, model_type, model_params
            )
            assert cached_result == result_data
            
            # Test file metadata caching
            metadata = {"file_size": 1024, "columns": ["col1", "col2"]}
            self.attribution_cache.set_file_metadata(file_hash, metadata)
            cached_metadata = self.attribution_cache.get_file_metadata(file_hash)
            assert cached_metadata == metadata
    
    def test_attribution_cache_key_generation(self):
        """Test cache key generation for attribution results."""
        with patch.object(self.attribution_cache.cache_manager, 'redis_client', None):
            file_hash = "test_hash"
            model_type = "linear"
            model_params = {"param1": "value1", "param2": "value2"}
            
            # Set result
            result_data = {"attribution": "result"}
            self.attribution_cache.set_attribution_result(
                file_hash, model_type, model_params, result_data
            )
            
            # Get result with same parameters
            cached_result = self.attribution_cache.get_attribution_result(
                file_hash, model_type, model_params
            )
            assert cached_result == result_data
            
            # Get result with different parameters (should be None)
            different_params = {"param1": "different_value"}
            cached_result = self.attribution_cache.get_attribution_result(
                file_hash, model_type, different_params
            )
            assert cached_result is None


class TestAPICache:
    """Test APICache functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.api_cache = APICache()
    
    @patch('src.core.caching.redis.Redis')
    def test_api_cache_with_redis(self, mock_redis):
        """Test APICache with Redis backend."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Create new cache with mocked Redis
        cache = APICache()
        
        # Test available methods caching
        methods_data = {"attribution_models": [], "linking_methods": []}
        mock_redis_client.setex.return_value = True
        result = cache.set_available_methods(methods_data)
        assert result is True
        
        mock_redis_client.get.return_value = json.dumps(methods_data)
        cached_methods = cache.get_available_methods()
        assert cached_methods == methods_data
        
        # Test health status caching
        health_data = {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
        cache.set_health_status(health_data, 60)
        mock_redis_client.get.return_value = json.dumps(health_data)
        cached_health = cache.get_health_status()
        assert cached_health == health_data
    
    def test_api_cache_without_redis(self):
        """Test APICache without Redis (memory fallback)."""
        with patch.object(self.api_cache.cache_manager, 'redis_client', None):
            # Test available methods caching
            methods_data = {"attribution_models": [], "linking_methods": []}
            result = self.api_cache.set_available_methods(methods_data)
            assert result is True
            
            cached_methods = self.api_cache.get_available_methods()
            assert cached_methods == methods_data
            
            # Test health status caching
            health_data = {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
            result = self.api_cache.set_health_status(health_data, 60)
            assert result is True
            
            cached_health = self.api_cache.get_health_status()
            assert cached_health == health_data


class TestCacheResultDecorator:
    """Test cache_result decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_result_decorator_success(self):
        """Test cache_result decorator with successful caching."""
        with patch('src.core.caching.CacheManager') as mock_cache_manager_class:
            # Mock cache manager
            mock_cache_manager = Mock()
            mock_cache_manager_class.return_value = mock_cache_manager
            mock_cache_manager.get.return_value = None  # Cache miss
            mock_cache_manager.set.return_value = True
            
            # Create decorated function
            @cache_result(ttl_seconds=3600, key_prefix="test")
            async def test_function(param1, param2):
                return {"result": f"{param1}_{param2}"}
            
            # Test function execution
            result = await test_function("value1", "value2")
            assert result == {"result": "value1_value2"}
            
            # Verify cache operations
            mock_cache_manager.get.assert_called_once()
            mock_cache_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_result_decorator_cache_hit(self):
        """Test cache_result decorator with cache hit."""
        with patch('src.core.caching.CacheManager') as mock_cache_manager_class:
            # Mock cache manager
            mock_cache_manager = Mock()
            mock_cache_manager_class.return_value = mock_cache_manager
            mock_cache_manager.get.return_value = {"result": "cached_value"}
            
            # Create decorated function
            @cache_result(ttl_seconds=3600, key_prefix="test")
            async def test_function(param1, param2):
                return {"result": f"{param1}_{param2}"}
            
            # Test function execution
            result = await test_function("value1", "value2")
            assert result == {"result": "cached_value"}
            
            # Verify only get was called, not set
            mock_cache_manager.get.assert_called_once()
            mock_cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_result_decorator_key_generation(self):
        """Test cache_result decorator key generation."""
        with patch('src.core.caching.CacheManager') as mock_cache_manager_class:
            # Mock cache manager
            mock_cache_manager = Mock()
            mock_cache_manager_class.return_value = mock_cache_manager
            mock_cache_manager.get.return_value = None
            mock_cache_manager.set.return_value = True
            
            # Create decorated function
            @cache_result(ttl_seconds=3600, key_prefix="test")
            async def test_function(param1, param2):
                return {"result": f"{param1}_{param2}"}
            
            # Test function execution
            await test_function("value1", "value2")
            
            # Verify cache key generation
            mock_cache_manager._generate_cache_key.assert_called_once()
            call_args = mock_cache_manager._generate_cache_key.call_args
            assert call_args[0][0] == "test:test_function"
            assert call_args[1]["args"] == ("value1", "value2")


class TestCacheIntegration:
    """Integration tests for caching system."""
    
    def test_global_cache_instances(self):
        """Test that global cache instances are properly configured."""
        assert attribution_cache is not None
        assert api_cache is not None
        assert cache_manager is not None
        
        # Test that instances have required methods
        assert hasattr(attribution_cache, 'get_attribution_result')
        assert hasattr(attribution_cache, 'set_attribution_result')
        assert hasattr(api_cache, 'get_available_methods')
        assert hasattr(api_cache, 'set_available_methods')
        assert hasattr(cache_manager, 'get')
        assert hasattr(cache_manager, 'set')
    
    def test_cache_manager_redis_fallback(self):
        """Test cache manager fallback from Redis to memory."""
        # Test with Redis unavailable
        with patch('src.core.caching.redis.Redis', side_effect=Exception("Redis unavailable")):
            manager = CacheManager()
            assert manager.redis_client is None
            
            # Should work with memory fallback
            test_data = {"key": "value"}
            result = manager.set("test_key", test_data, 3600)
            assert result is True
            
            cached_data = manager.get("test_key")
            assert cached_data == test_data
    
    def test_cache_ttl_consistency(self):
        """Test cache TTL consistency across different cache types."""
        with patch.object(attribution_cache.cache_manager, 'redis_client', None):
            with patch.object(api_cache.cache_manager, 'redis_client', None):
                # Test different TTL values
                attribution_cache.set_attribution_result(
                    "hash1", "linear", {}, {"result": "data"}, ttl_seconds=1800
                )
                api_cache.set_health_status({"status": "healthy"}, ttl_seconds=60)
                
                # Both should be cached
                assert attribution_cache.get_attribution_result("hash1", "linear", {}) is not None
                assert api_cache.get_health_status() is not None
    
    def test_cache_error_handling(self):
        """Test cache error handling and recovery."""
        with patch.object(cache_manager, 'redis_client', None):
            # Test with invalid data
            result = cache_manager.set("test_key", {"invalid": object()}, 3600)
            assert result is True  # Should handle serialization gracefully
            
            # Test cache miss handling
            cached_data = cache_manager.get("non_existent_key")
            assert cached_data is None
    
    def test_cache_statistics_accuracy(self):
        """Test cache statistics accuracy."""
        with patch.object(cache_manager, 'redis_client', None):
            # Reset stats
            cache_manager.cache_stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
            
            # Perform operations
            cache_manager.set("key1", "value1", 3600)
            cache_manager.get("key1")  # Hit
            cache_manager.get("key2")  # Miss
            cache_manager.delete("key1")
            
            # Check stats
            stats = cache_manager.get_stats()
            assert stats["hits"] == 1
            assert stats["misses"] == 1
            assert stats["sets"] == 1
            assert stats["deletes"] == 1
            assert stats["hit_rate"] == 0.5
            assert stats["total_requests"] == 2
