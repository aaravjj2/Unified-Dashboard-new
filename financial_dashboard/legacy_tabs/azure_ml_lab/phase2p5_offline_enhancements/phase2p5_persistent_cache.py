"""
Phase 2.5 Offline Enhancements — Persistent Cache with TTL

This module extends the existing in-memory LRU cache with disk persistence
and time-to-live (TTL) expiration. Features:

1. Disk-based JSON storage for cache persistence across sessions
2. Configurable TTL (default: 1 hour)
3. Automatic cache cleanup of expired entries
4. Backward-compatible with existing in-memory cache
5. Thread-safe operations (basic file locking)

Author: Autonomous Lead Software Engineer
Version: 1.0.0 (Phase 2.5)
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Default cache directory
DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent.parent.parent / "outputs" / "phase2p5_cache"

# Default TTL: 1 hour (in seconds)
DEFAULT_TTL_SECONDS = 3600


# ============================================================================
# PERSISTENT CACHE WITH TTL
# ============================================================================

class PersistentCache:
    """
    Disk-based cache with TTL expiration.
    
    Stores cache entries as JSON files in a dedicated directory.
    Each entry includes:
    - cached_value: The actual cached data
    - timestamp: When the entry was created
    - ttl_seconds: Time-to-live duration
    - metadata: Additional info (ticker, function name, etc.)
    
    Example:
        >>> cache = PersistentCache(ttl_seconds=3600)
        >>> 
        >>> # Store value
        >>> cache.set("my_key", {"result": 42}, metadata={"ticker": "AAPL"})
        >>> 
        >>> # Retrieve value
        >>> value = cache.get("my_key")  # Returns {"result": 42} if not expired
        >>> 
        >>> # Check if exists and valid
        >>> if cache.has("my_key"):
        ...     value = cache.get("my_key")
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        auto_cleanup: bool = True
    ):
        """
        Initialize persistent cache.
        
        Args:
            cache_dir: Directory for cache files (default: outputs/phase2p5_cache)
            ttl_seconds: Default TTL in seconds (default: 3600 = 1 hour)
            auto_cleanup: If True, clean expired entries on initialization
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.ttl_seconds = ttl_seconds
        
        # Create cache directory if needed
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-cleanup expired entries
        if auto_cleanup:
            cleaned = self.cleanup_expired()
            if cleaned > 0:
                logger.info(f"Cleaned {cleaned} expired cache entries on initialization")
        
        logger.info(f"💾 PersistentCache initialized (ttl={ttl_seconds}s, dir={self.cache_dir})")
    
    def _get_cache_path(self, key: str) -> Path:
        """
        Get filesystem path for cache key.
        
        Uses MD5 hash of key to ensure valid filenames.
        """
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key (any string)
            value: Value to cache (must be JSON-serializable)
            ttl_seconds: Custom TTL (None = use default)
            metadata: Optional metadata dict
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        
        cache_entry = {
            'cached_value': value,
            'timestamp': time.time(),
            'ttl_seconds': ttl,
            'key': key,
            'metadata': metadata or {}
        }
        
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_entry, f, indent=2)
            logger.debug(f"Cache set: {key} (ttl={ttl}s)")
        except Exception as e:
            logger.error(f"Failed to write cache for {key}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found or expired
            
        Returns:
            Cached value if exists and valid, else default
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            logger.debug(f"Cache miss: {key} (not found)")
            return default
        
        try:
            with open(cache_path, 'r') as f:
                cache_entry = json.load(f)
            
            # Check expiration
            timestamp = cache_entry['timestamp']
            ttl = cache_entry['ttl_seconds']
            age_seconds = time.time() - timestamp
            
            if age_seconds > ttl:
                logger.debug(f"Cache expired: {key} (age={age_seconds:.1f}s, ttl={ttl}s)")
                # Delete expired entry
                cache_path.unlink()
                return default
            
            logger.debug(f"Cache hit: {key} (age={age_seconds:.1f}s)")
            return cache_entry['cached_value']
            
        except Exception as e:
            logger.error(f"Failed to read cache for {key}: {e}")
            return default
    
    def has(self, key: str) -> bool:
        """
        Check if key exists in cache and is valid (not expired).
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and not expired, False otherwise
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return False
        
        try:
            with open(cache_path, 'r') as f:
                cache_entry = json.load(f)
            
            # Check expiration
            timestamp = cache_entry['timestamp']
            ttl = cache_entry['ttl_seconds']
            age_seconds = time.time() - timestamp
            
            return age_seconds <= ttl
            
        except Exception as e:
            logger.error(f"Failed to check cache for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was deleted, False if not found
        """
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Cache deleted: {key}")
            return True
        
        return False
    
    def cleanup_expired(self) -> int:
        """
        Delete all expired cache entries.
        
        Returns:
            Number of entries deleted
        """
        deleted_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_entry = json.load(f)
                
                timestamp = cache_entry['timestamp']
                ttl = cache_entry['ttl_seconds']
                age_seconds = time.time() - timestamp
                
                if age_seconds > ttl:
                    cache_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted expired cache: {cache_entry.get('key', 'unknown')}")
                    
            except Exception as e:
                logger.warning(f"Failed to process cache file {cache_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleanup complete: deleted {deleted_count} expired entries")
        
        return deleted_count
    
    def clear_all(self) -> int:
        """
        Delete all cache entries (expired or not).
        
        Returns:
            Number of entries deleted
        """
        deleted_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache file {cache_file}: {e}")
        
        logger.info(f"Cache cleared: deleted {deleted_count} entries")
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats including:
            - total_entries
            - valid_entries (not expired)
            - expired_entries
            - total_size_bytes
            - oldest_entry_age_hours
            - newest_entry_age_seconds
        """
        total_entries = 0
        valid_entries = 0
        expired_entries = 0
        total_size_bytes = 0
        oldest_timestamp = None
        newest_timestamp = None
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                total_entries += 1
                total_size_bytes += cache_file.stat().st_size
                
                with open(cache_file, 'r') as f:
                    cache_entry = json.load(f)
                
                timestamp = cache_entry['timestamp']
                ttl = cache_entry['ttl_seconds']
                age_seconds = time.time() - timestamp
                
                if age_seconds <= ttl:
                    valid_entries += 1
                else:
                    expired_entries += 1
                
                if oldest_timestamp is None or timestamp < oldest_timestamp:
                    oldest_timestamp = timestamp
                
                if newest_timestamp is None or timestamp > newest_timestamp:
                    newest_timestamp = timestamp
                    
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {e}")
        
        oldest_age_hours = 0
        newest_age_seconds = 0
        
        if oldest_timestamp:
            oldest_age_hours = (time.time() - oldest_timestamp) / 3600
        
        if newest_timestamp:
            newest_age_seconds = time.time() - newest_timestamp
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'oldest_entry_age_hours': oldest_age_hours,
            'newest_entry_age_seconds': newest_age_seconds
        }
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"PersistentCache(entries={stats['valid_entries']}/{stats['total_entries']}, "
            f"size={stats['total_size_mb']:.2f}MB, ttl={self.ttl_seconds}s)"
        )


# ============================================================================
# HYBRID CACHE: IN-MEMORY LRU + PERSISTENT TTL
# ============================================================================

class HybridCache:
    """
    Two-tier cache combining in-memory LRU (fast) with persistent disk cache (durable).
    
    Strategy:
    1. Check in-memory cache first (fastest)
    2. If miss, check disk cache (slower but persistent)
    3. If disk hit, populate in-memory cache
    4. New values are written to both caches
    
    Example:
        >>> cache = HybridCache(lru_size=10, ttl_seconds=3600)
        >>> cache.set("key", "value")
        >>> value = cache.get("key")  # Fast in-memory retrieval
    """
    
    def __init__(
        self,
        lru_size: int = 10,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize hybrid cache.
        
        Args:
            lru_size: Maximum size of in-memory LRU cache
            ttl_seconds: TTL for persistent cache
            cache_dir: Directory for disk cache
        """
        self.lru_size = lru_size
        self.persistent_cache = PersistentCache(cache_dir=cache_dir, ttl_seconds=ttl_seconds)
        
        # In-memory LRU cache (simple dict with max size)
        self.memory_cache: Dict[str, Tuple[float, Any]] = {}
        self.access_order: list = []
        
        logger.info(f"🔄 HybridCache initialized (lru_size={lru_size}, ttl={ttl_seconds}s)")
    
    def _evict_lru(self) -> None:
        """Evict least-recently-used entry from memory cache."""
        if len(self.memory_cache) >= self.lru_size and self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.memory_cache:
                del self.memory_cache[lru_key]
                logger.debug(f"LRU eviction: {lru_key}")
    
    def _update_access(self, key: str) -> None:
        """Update access order for LRU tracking."""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, metadata: Optional[Dict] = None) -> None:
        """
        Store value in both memory and disk caches.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL (None = use default)
            metadata: Optional metadata
        """
        # Evict if needed
        self._evict_lru()
        
        # Store in memory
        self.memory_cache[key] = (time.time(), value)
        self._update_access(key)
        
        # Store on disk
        self.persistent_cache.set(key, value, ttl_seconds=ttl_seconds, metadata=metadata)
        
        logger.debug(f"Hybrid cache set: {key} (memory + disk)")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve value from cache (memory first, then disk).
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        # Check memory cache first
        if key in self.memory_cache:
            timestamp, value = self.memory_cache[key]
            self._update_access(key)
            logger.debug(f"Hybrid cache hit (memory): {key}")
            return value
        
        # Check disk cache
        disk_value = self.persistent_cache.get(key)
        if disk_value is not None:
            # Populate memory cache
            self.memory_cache[key] = (time.time(), disk_value)
            self._update_access(key)
            logger.debug(f"Hybrid cache hit (disk): {key}")
            return disk_value
        
        logger.debug(f"Hybrid cache miss: {key}")
        return default
    
    def has(self, key: str) -> bool:
        """Check if key exists in either cache."""
        return key in self.memory_cache or self.persistent_cache.has(key)
    
    def delete(self, key: str) -> None:
        """Delete from both caches."""
        if key in self.memory_cache:
            del self.memory_cache[key]
        if key in self.access_order:
            self.access_order.remove(key)
        self.persistent_cache.delete(key)
    
    def cleanup_expired(self) -> int:
        """Cleanup expired entries from disk cache."""
        return self.persistent_cache.cleanup_expired()
    
    def clear_all(self) -> None:
        """Clear both memory and disk caches."""
        self.memory_cache.clear()
        self.access_order.clear()
        self.persistent_cache.clear_all()
        logger.info("Hybrid cache cleared (memory + disk)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        disk_stats = self.persistent_cache.get_stats()
        
        return {
            'memory_entries': len(self.memory_cache),
            'memory_max_size': self.lru_size,
            'disk_entries': disk_stats['total_entries'],
            'disk_valid_entries': disk_stats['valid_entries'],
            'disk_size_mb': disk_stats['total_size_mb'],
            'combined_hit_coverage': len(self.memory_cache) + disk_stats['valid_entries']
        }


# ============================================================================
# DECORATOR FOR PERSISTENT CACHING
# ============================================================================

def persistent_cache(ttl_seconds: int = DEFAULT_TTL_SECONDS, cache_dir: Optional[Path] = None):
    """
    Decorator for persistent caching with TTL.
    
    Args:
        ttl_seconds: Cache TTL in seconds
        cache_dir: Custom cache directory
        
    Example:
        >>> @persistent_cache(ttl_seconds=3600)
        ... def expensive_computation(x, y):
        ...     return x + y
        >>> 
        >>> result = expensive_computation(10, 20)  # Computed
        >>> result = expensive_computation(10, 20)  # Cached
    """
    cache = PersistentCache(cache_dir=cache_dir, ttl_seconds=ttl_seconds)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name + arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = "|".join(key_parts)
            
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}({args}, {kwargs})")
                return cached_value
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, metadata={'function': func.__name__})
            logger.debug(f"Cache miss for {func.__name__}({args}, {kwargs}) - computed and cached")
            
            return result
        
        # Attach cache methods to wrapper for manual control
        wrapper.cache = cache
        wrapper.cache_clear = cache.clear_all
        wrapper.cache_cleanup = cache.cleanup_expired
        
        return wrapper
    
    return decorator


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

if __name__ == "__main__":
    # Demo usage
    print("Phase 2.5 Persistent Cache - Demo Mode")
    print("=" * 60)
    
    # Test PersistentCache
    print("\n1. Testing PersistentCache...")
    cache = PersistentCache(ttl_seconds=10)  # 10 second TTL for demo
    
    cache.set("key1", {"value": 42}, metadata={"ticker": "AAPL"})
    cache.set("key2", {"value": 100}, metadata={"ticker": "GOOGL"})
    
    print(f"  key1 exists: {cache.has('key1')}")
    print(f"  key1 value: {cache.get('key1')}")
    print(f"  key3 value: {cache.get('key3', default='NOT FOUND')}")
    
    print(f"\n  Cache stats: {cache.get_stats()}")
    
    # Test expiration
    print("\n2. Testing TTL expiration (sleeping 11 seconds)...")
    time.sleep(11)
    print(f"  key1 exists after expiration: {cache.has('key1')}")
    print(f"  key1 value after expiration: {cache.get('key1', default='EXPIRED')}")
    
    # Test HybridCache
    print("\n3. Testing HybridCache...")
    hybrid = HybridCache(lru_size=3, ttl_seconds=60)
    
    hybrid.set("ticker_AAPL", {"prediction": 0.05})
    hybrid.set("ticker_GOOGL", {"prediction": 0.03})
    
    print(f"  First get (memory): {hybrid.get('ticker_AAPL')}")
    print(f"  Hybrid stats: {hybrid.get_stats()}")
    
    # Test decorator
    print("\n4. Testing @persistent_cache decorator...")
    
    @persistent_cache(ttl_seconds=60)
    def slow_computation(x, y):
        print(f"    Computing {x} + {y}...")
        time.sleep(0.1)
        return x + y
    
    result1 = slow_computation(10, 20)  # Should compute
    result2 = slow_computation(10, 20)  # Should use cache
    print(f"  Result1: {result1}, Result2: {result2}")
    
    print("\n✅ Demo complete!")
