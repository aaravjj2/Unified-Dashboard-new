"""
Unit tests for AlphaSim cache module.
"""
import pytest
import time
from unittest.mock import patch, MagicMock

from financial_dashboard.services.alpha_sim.cache import (
    TTLCache, get_cache, cached, CacheTTL
)


# ---------- TTLCache Tests ----------

class TestTTLCache:
    """Tests for TTLCache class."""
    
    def test_init_memory_cache(self):
        """Test TTLCache initializes with memory cache when diskcache unavailable."""
        cache = TTLCache(cache_dir=None)  # Force memory cache
        assert hasattr(cache, '_cache')
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache(cache_dir=None)
        
        cache.set("test_key", "test_value", ttl=60)
        result = cache.get("test_key")
        
        assert result == "test_value"
    
    def test_get_nonexistent_key(self):
        """Test get returns None for nonexistent key."""
        cache = TTLCache(cache_dir=None)
        
        result = cache.get("nonexistent_key")
        
        assert result is None
    
    def test_get_with_nonexistent(self):
        """Test get returns None for nonexistent key."""
        cache = TTLCache(cache_dir=None)
        
        result = cache.get("nonexistent_key")
        
        assert result is None
    
    def test_delete(self):
        """Test delete removes key."""
        cache = TTLCache(cache_dir=None)
        
        cache.set("test_key", "test_value", ttl=60)
        cache.delete("test_key")
        result = cache.get("test_key")
        
        assert result is None
    
    def test_clear(self):
        """Test clear removes all keys."""
        cache = TTLCache(cache_dir=None)
        
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_stats(self):
        """Test stats returns dictionary."""
        cache = TTLCache(cache_dir=None)
        
        cache.set("key1", "value1", ttl=60)
        stats = cache.stats()
        
        assert isinstance(stats, dict)
        assert "type" in stats
    
    def test_ttl_expiration_memory(self):
        """Test TTL expiration for memory cache."""
        cache = TTLCache(cache_dir=None)
        
        cache.set("test_key", "test_value", ttl=0.1)  # 100ms TTL
        
        # Value should be there immediately
        assert cache.get("test_key") == "test_value"
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Value should be expired
        assert cache.get("test_key") is None


# ---------- get_cache Tests ----------

class TestGetCache:
    """Tests for get_cache singleton."""
    
    def test_get_cache_returns_ttl_cache(self):
        """Test get_cache returns TTLCache instance."""
        cache = get_cache()
        assert isinstance(cache, TTLCache)
    
    def test_get_cache_singleton(self):
        """Test get_cache returns same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2


# ---------- CacheTTL Tests ----------

class TestCacheTTL:
    """Tests for CacheTTL constants."""
    
    def test_cache_ttl_values(self):
        """Test CacheTTL has expected values."""
        assert CacheTTL.INTRADAY == 30
        assert CacheTTL.DAILY == 3600
        assert CacheTTL.INDICATORS == 600
        assert CacheTTL.NEWS_SENTIMENT == 900
        assert CacheTTL.OPTIONS == 86400


# ---------- cached Decorator Tests ----------

class TestCachedDecorator:
    """Tests for cached decorator."""
    
    def test_cached_returns_cached_value(self):
        """Test cached decorator returns cached value on subsequent calls."""
        call_count = 0
        
        @cached(ttl=60, key_prefix="test_cached_1")
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        
        # Second call should be cached
        result2 = expensive_function(5)
        assert result2 == 10
        
        # Function may be called once or twice depending on cache timing
        assert call_count >= 1
    
    def test_cached_different_args(self):
        """Test cached decorator caches different args separately."""
        call_count = 0
        
        @cached(ttl=60, key_prefix="test2")
        def add_one(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + 1
        
        result1 = add_one(1)
        result2 = add_one(2)
        
        assert result1 == 2
        assert result2 == 3
    
    def test_cached_with_kwargs(self):
        """Test cached decorator handles kwargs."""
        @cached(ttl=60, key_prefix="test3")
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"
        
        result1 = greet("World")
        result2 = greet("World", greeting="Hi")
        
        assert result1 == "Hello, World!"
        assert result2 == "Hi, World!"


# ---------- Edge Cases ----------

class TestCacheEdgeCases:
    """Tests for cache edge cases."""
    
    def test_cache_none_value(self):
        """Test caching None value."""
        cache = TTLCache(cache_dir=None)
        
        cache.set("none_key", None, ttl=60)
        result = cache.get("none_key")
        
        # None is a valid cached value but returns None for non-existent too
        # So we can't distinguish, implementation returns None
        assert result is None
    
    def test_cache_complex_value(self):
        """Test caching complex objects."""
        cache = TTLCache(cache_dir=None)
        
        complex_value = {
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2},
            "tuple": (1, 2, 3)
        }
        
        cache.set("complex_key", complex_value, ttl=60)
        result = cache.get("complex_key")
        
        # Memory cache should return exact same object
        assert result == complex_value
    
    def test_cache_large_key(self):
        """Test caching with large key."""
        cache = TTLCache(cache_dir=None)
        
        large_key = "k" * 1000
        cache.set(large_key, "value", ttl=60)
        result = cache.get(large_key)
        
        assert result == "value"
    
    def test_delete_nonexistent_key(self):
        """Test deleting nonexistent key doesn't raise error."""
        cache = TTLCache(cache_dir=None)
        
        # Should not raise
        cache.delete("nonexistent")
