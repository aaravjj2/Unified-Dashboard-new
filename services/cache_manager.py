"""
Cache Manager for Model Service
Provides LRU caching for predictions and model loading.
"""
import time
import logging
from typing import Any, Dict, Optional
from functools import lru_cache
from collections import OrderedDict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Time-To-Live cache with automatic expiration.
    Thread-safe for single-process use.
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Initialize TTL cache.
        
        Args:
            max_size: Maximum number of items to cache
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0
    
    def _is_expired(self, key: str) -> bool:
        """Check if a cache entry has expired."""
        if key not in self.timestamps:
            return True
        
        age = time.time() - self.timestamps[key]
        return age > self.ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache if not expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache or self._is_expired(key):
            self._misses += 1
            if key in self.cache:
                # Clean up expired entry
                del self.cache[key]
                del self.timestamps[key]
            return None
        
        self._hits += 1
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # Remove if already exists
        if key in self.cache:
            del self.cache[key]
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.timestamps.clear()
        self._hits = 0
        self._misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl
        }


class CacheManager:
    """
    Cache Manager for Model Service.
    Manages prediction cache and model loading cache.
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            max_size: Maximum cache size
            ttl: Time-to-live in seconds
        """
        self.prediction_cache = TTLCache(max_size=max_size, ttl=ttl)
        self.model_cache = TTLCache(max_size=10, ttl=3600)  # Models cached for 1 hour
        
        logger.info(f"CacheManager initialized: max_size={max_size}, ttl={ttl}s")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from prediction cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        return self.prediction_cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in prediction cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.prediction_cache.set(key, value)
    
    def get_model(self, model_key: str) -> Optional[Any]:
        """
        Get model from model cache.
        
        Args:
            model_key: Model identifier
        
        Returns:
            Cached model or None
        """
        return self.model_cache.get(model_key)
    
    def set_model(self, model_key: str, model: Any) -> None:
        """
        Set model in model cache.
        
        Args:
            model_key: Model identifier
            model: Model object to cache
        """
        self.model_cache.set(model_key, model)
        logger.info(f"Model cached: {model_key}")
    
    def clear_predictions(self) -> None:
        """Clear prediction cache."""
        self.prediction_cache.clear()
        logger.info("Prediction cache cleared")
    
    def clear_models(self) -> None:
        """Clear model cache."""
        self.model_cache.clear()
        logger.info("Model cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "predictions": self.prediction_cache.stats(),
            "models": self.model_cache.stats(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


# Global cache instance (singleton pattern)
_global_cache: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get global cache manager instance (singleton).
    
    Returns:
        CacheManager instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager(max_size=1000, ttl=300)
    return _global_cache


def generate_cache_key(features: Dict[str, float]) -> str:
    """
    Generate a cache key from feature dictionary.
    
    Args:
        features: Feature dictionary
    
    Returns:
        Cache key string
    """
    # Sort keys for consistent hashing
    sorted_items = sorted(features.items())
    key_parts = [f"{k}:{v:.4f}" for k, v in sorted_items]
    return "|".join(key_parts)
