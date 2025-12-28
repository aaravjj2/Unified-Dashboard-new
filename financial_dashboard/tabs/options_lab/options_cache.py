"""
Options Chain Cache - TTL-based caching for Alpaca options data

Reduces API calls by caching chain data with configurable TTL.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with data and metadata."""
    data: Any
    timestamp: float
    ttl: int
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'size': self.size,
            'hit_rate': f"{self.hit_rate:.2%}"
        }


class OptionsChainCache:
    """
    Thread-safe TTL cache for options chain data.
    
    Features:
    - Configurable TTL per entry
    - Automatic expiration cleanup
    - Hit/miss statistics
    - Max size limit with LRU eviction
    
    Usage:
        cache = OptionsChainCache(default_ttl=300, max_size=100)
        
        # Store chain
        cache.set('SPY_2025-12-29', chain_data)
        
        # Retrieve chain
        data = cache.get('SPY_2025-12-29')
        
        # Get with default
        data = cache.get_or_fetch('SPY_2025-12-29', fetch_func)
    """
    
    _instance: Optional['OptionsChainCache'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global cache."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, default_ttl: int = 300, max_size: int = 100):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
            max_size: Maximum number of entries
        """
        if self._initialized:
            return
            
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []  # For LRU eviction
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._stats = CacheStats()
        self._cache_lock = threading.RLock()
        self._initialized = True
        
        logger.info(f"📦 Options cache initialized (TTL={default_ttl}s, max_size={max_size})")
    
    def _make_key(self, ticker: str, expiration: Optional[str] = None) -> str:
        """Create cache key from ticker and optional expiration."""
        if expiration:
            return f"{ticker.upper()}_{expiration}"
        return ticker.upper()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        with self._cache_lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired:
                self._stats.misses += 1
                self._evict(key)
                return None
            
            # Update access order for LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            entry.hits += 1
            self._stats.hits += 1
            
            logger.debug(f"📦 Cache HIT: {key} (age={entry.age_seconds:.1f}s)")
            return entry.data
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Optional custom TTL (uses default if not specified)
        """
        with self._cache_lock:
            # Enforce max size with LRU eviction
            while len(self._cache) >= self._max_size:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(
                data=data,
                timestamp=time.time(),
                ttl=ttl or self._default_ttl
            )
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self._stats.size = len(self._cache)
            logger.debug(f"📦 Cache SET: {key} (ttl={ttl or self._default_ttl}s)")
    
    def get_or_fetch(
        self, 
        key: str, 
        fetch_func: callable, 
        ttl: Optional[int] = None
    ) -> Tuple[Any, bool]:
        """
        Get from cache or fetch using provided function.
        
        Args:
            key: Cache key
            fetch_func: Function to call if cache miss
            ttl: Optional custom TTL
            
        Returns:
            Tuple of (data, was_cached)
        """
        # Check cache first
        cached = self.get(key)
        if cached is not None:
            return cached, True
        
        # Fetch and cache
        try:
            data = fetch_func()
            if data is not None:
                self.set(key, data, ttl)
            return data, False
        except Exception as e:
            logger.error(f"📦 Cache fetch error for {key}: {e}")
            raise
    
    def invalidate(self, key: str) -> bool:
        """
        Remove specific key from cache.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if key was found and removed
        """
        with self._cache_lock:
            if key in self._cache:
                self._evict(key)
                return True
            return False
    
    def invalidate_ticker(self, ticker: str) -> int:
        """
        Remove all entries for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Number of entries removed
        """
        ticker_upper = ticker.upper()
        count = 0
        
        with self._cache_lock:
            keys_to_remove = [
                k for k in self._cache.keys() 
                if k.startswith(f"{ticker_upper}_") or k == ticker_upper
            ]
            
            for key in keys_to_remove:
                self._evict(key)
                count += 1
        
        logger.info(f"📦 Invalidated {count} entries for {ticker}")
        return count
    
    def clear(self) -> int:
        """
        Clear entire cache.
        
        Returns:
            Number of entries cleared
        """
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            self._stats.size = 0
            logger.info(f"📦 Cache cleared ({count} entries)")
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        count = 0
        
        with self._cache_lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired
            ]
            
            for key in expired_keys:
                self._evict(key)
                count += 1
        
        if count > 0:
            logger.debug(f"📦 Cleaned up {count} expired entries")
        
        return count
    
    def _evict(self, key: str) -> None:
        """Remove a specific key (internal use)."""
        if key in self._cache:
            del self._cache[key]
            self._stats.evictions += 1
            self._stats.size = len(self._cache)
        
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            self._evict(lru_key)
            logger.debug(f"📦 LRU evicted: {lru_key}")
    
    @property
    def stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats
    
    def get_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        with self._cache_lock:
            entries = []
            for key, entry in self._cache.items():
                entries.append({
                    'key': key,
                    'age_seconds': round(entry.age_seconds, 1),
                    'ttl': entry.ttl,
                    'hits': entry.hits,
                    'expired': entry.is_expired
                })
            
            return {
                'stats': self._stats.to_dict(),
                'entries': entries,
                'default_ttl': self._default_ttl,
                'max_size': self._max_size
            }


# Singleton accessor
_cache_instance: Optional[OptionsChainCache] = None


def get_options_cache(default_ttl: int = 300, max_size: int = 100) -> OptionsChainCache:
    """
    Get or create the global options cache instance.
    
    Args:
        default_ttl: Default TTL in seconds (default: 5 minutes)
        max_size: Maximum cache entries (default: 100)
        
    Returns:
        OptionsChainCache singleton instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = OptionsChainCache(default_ttl, max_size)
    
    return _cache_instance


def reset_cache() -> None:
    """Reset the global cache instance (for testing)."""
    global _cache_instance
    if _cache_instance is not None:
        _cache_instance.clear()
    _cache_instance = None
