"""
AlphaSim Cache - TTL-backed caching using diskcache (dev) or Redis (prod).
"""
import os
import time
import hashlib
from typing import Any, Optional
from functools import wraps

# Try diskcache first, fall back to simple dict cache
try:
    from diskcache import Cache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False


class TTLCache:
    """Simple TTL cache abstraction that works with diskcache or in-memory."""
    
    def __init__(self, cache_dir: str = "/tmp/alpha_sim_cache", default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._cache_dir = cache_dir
        
        if DISKCACHE_AVAILABLE:
            self._cache = Cache(cache_dir)
        else:
            self._cache = {}
            self._expiry = {}
    
    def _make_key(self, key: str) -> str:
        """Create a safe cache key."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        safe_key = self._make_key(key)
        
        if DISKCACHE_AVAILABLE:
            return self._cache.get(safe_key)
        else:
            if safe_key in self._cache:
                if time.time() < self._expiry.get(safe_key, 0):
                    return self._cache[safe_key]
                else:
                    del self._cache[safe_key]
                    del self._expiry[safe_key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        safe_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        if DISKCACHE_AVAILABLE:
            self._cache.set(safe_key, value, expire=ttl)
        else:
            self._cache[safe_key] = value
            self._expiry[safe_key] = time.time() + ttl
    
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        safe_key = self._make_key(key)
        
        if DISKCACHE_AVAILABLE:
            self._cache.delete(safe_key)
        else:
            self._cache.pop(safe_key, None)
            self._expiry.pop(safe_key, None)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        if DISKCACHE_AVAILABLE:
            self._cache.clear()
        else:
            self._cache.clear()
            self._expiry.clear()
    
    def stats(self) -> dict:
        """Return cache statistics."""
        if DISKCACHE_AVAILABLE:
            return {
                "type": "diskcache",
                "size": len(self._cache),
                "directory": self._cache_dir
            }
        else:
            return {
                "type": "memory",
                "size": len(self._cache)
            }


# Global cache instance
_cache_instance: Optional[TTLCache] = None
_cache_reset_done = False


def get_cache() -> TTLCache:
    """Get or create the global cache instance."""
    global _cache_instance
    # In pytest runs, reset the cache once at first call to avoid cross-test contamination
    global _cache_reset_done
    if not _cache_reset_done and 'PYTEST_CURRENT_TEST' in os.environ:
        _cache_instance = None
        _cache_reset_done = True

    if _cache_instance is None:
        import tempfile
        # Use a fresh temporary cache directory during pytest runs to avoid stale diskcache entries
        if 'PYTEST_CURRENT_TEST' in os.environ:
            cache_dir = tempfile.mkdtemp(prefix="alpha_sim_cache_")
        else:
            cache_dir = os.getenv("ALPHA_SIM_CACHE_DIR", "/tmp/alpha_sim_cache")
        default_ttl = int(os.getenv("ALPHA_SIM_CACHE_TTL", "300"))
        _cache_instance = TTLCache(cache_dir=cache_dir, default_ttl=default_ttl)
    return _cache_instance


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Build cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        # Add cache_info for testing/debugging
        wrapper.cache_key_prefix = key_prefix or func.__name__
        return wrapper
    return decorator


# TTL constants matching the plan
class CacheTTL:
    """Cache TTL values in seconds."""
    INTRADAY = 30  # 30s dev, 5s prod
    DAILY = 3600  # 1 hour
    INDICATORS = 600  # 10 minutes
    NEWS_SENTIMENT = 900  # 15 minutes
    OPTIONS = 86400  # 24 hours
