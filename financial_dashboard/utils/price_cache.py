"""
Price Data Caching Layer

Provides in-memory and file-based caching for PriceClient results.
Cache keys are based on parameter hash (tickers, date_range, window).

Features:
- In-memory LRU cache for fast access
- Optional file-based persistence
- Configurable TTL (time-to-live)
- Cache invalidation support
"""

import hashlib
import json
import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import pandas as pd

logger = logging.getLogger(__name__)


class PriceDataCache:
    """
    Cache manager for price data with in-memory and optional file storage.
    
    Usage:
        cache = PriceDataCache(cache_dir="cache_price", ttl_seconds=3600)
        
        # Try to get from cache
        df = cache.get(tickers=['AAPL'], start='2024-01-01', end='2024-01-15')
        if df is None:
            # Cache miss - fetch and store
            df = fetch_price_data(...)
            cache.set(df, tickers=['AAPL'], start='2024-01-01', end='2024-01-15')
    """
    
    def __init__(
        self,
        cache_dir: str = "cache_price",
        ttl_seconds: int = 3600,
        enable_file_cache: bool = True
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.enable_file_cache = enable_file_cache
        self._memory_cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
        # In-memory metadata mapping to support smarter invalidation
        self._meta_map: Dict[str, Dict] = {}
        
        if self.enable_file_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _make_cache_key(
        self,
        tickers: List[str],
        start: str,
        end: str,
        **kwargs
    ) -> str:
        """
        Generate cache key from parameters.
        
        Args:
            tickers: List of ticker symbols
            start: Start date string
            end: End date string
            **kwargs: Additional parameters to include in key
            
        Returns:
            Cache key string (SHA256 hash)
        """
        # Sort tickers for consistent keys
        sorted_tickers = sorted(tickers)
        
        # Create key components
        key_parts = {
            'tickers': sorted_tickers,
            'start': start,
            'end': end,
            **kwargs
        }
        
        # Generate hash
        key_str = json.dumps(key_parts, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        
        return f"price_cache_{key_hash}"
    
    def get(
        self,
        tickers: List[str],
        start: str,
        end: str,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Get cached price data.
        
        Returns:
            DataFrame if cache hit and not expired, None otherwise
        """
        cache_key = self._make_cache_key(tickers, start, end, **kwargs)
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            df, cached_at = self._memory_cache[cache_key]
            age = time.time() - cached_at
            
            if age < self.ttl_seconds:
                logger.debug(f"Cache HIT (memory): {cache_key}, age={age:.1f}s")
                return df.copy()
            else:
                logger.debug(f"Cache EXPIRED (memory): {cache_key}, age={age:.1f}s")
                del self._memory_cache[cache_key]
        
        # Check file cache
        if self.enable_file_cache:
            cache_file = self.cache_dir / f"{cache_key}.parquet"
            meta_file = self.cache_dir / f"{cache_key}.meta.json"
            
            if cache_file.exists() and meta_file.exists():
                try:
                    with open(meta_file, 'r') as f:
                        meta = json.load(f)
                    
                    cached_at = meta['cached_at']
                    age = time.time() - cached_at
                    
                    if age < self.ttl_seconds:
                        df = pd.read_parquet(cache_file)
                        # Load into memory cache too
                        self._memory_cache[cache_key] = (df.copy(), cached_at)
                        # Populate metadata map for invalidation/search
                        try:
                            self._meta_map[cache_key] = meta
                        except Exception:
                            pass
                        logger.debug(f"Cache HIT (file): {cache_key}, age={age:.1f}s")
                        return df
                    else:
                        logger.debug(f"Cache EXPIRED (file): {cache_key}, age={age:.1f}s")
                        cache_file.unlink()
                        meta_file.unlink()
                except Exception as e:
                    logger.warning(f"Cache read error: {e}")
        
        logger.debug(f"Cache MISS: {cache_key}")
        return None
    
    def set(
        self,
        df: pd.DataFrame,
        tickers: List[str],
        start: str,
        end: str,
        **kwargs
    ) -> None:
        """
        Store price data in cache.
        
        Args:
            df: DataFrame to cache
            tickers: List of ticker symbols
            start: Start date string
            end: End date string
            **kwargs: Additional parameters for cache key
        """
        cache_key = self._make_cache_key(tickers, start, end, **kwargs)
        cached_at = time.time()
        
        # Store in memory
        self._memory_cache[cache_key] = (df.copy(), cached_at)
        logger.debug(f"Cache SET (memory): {cache_key}")
        
        # Store in file if enabled
        if self.enable_file_cache:
            try:
                cache_file = self.cache_dir / f"{cache_key}.parquet"
                meta_file = self.cache_dir / f"{cache_key}.meta.json"
                
                df.to_parquet(cache_file, index=False)
                
                meta = {
                    'cached_at': cached_at,
                    'tickers': tickers,
                    'start': start,
                    'end': end,
                    'rows': len(df),
                    **kwargs
                }
                with open(meta_file, 'w') as f:
                    json.dump(meta, f)

                # Keep metadata in memory as well for fast invalidation/search
                try:
                    self._meta_map[cache_key] = meta
                except Exception:
                    pass
                
                logger.debug(f"Cache SET (file): {cache_key}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
    
    def invalidate(
        self,
        tickers: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        Invalidate specific cache entries or clear all.
        
        Args:
            tickers: Optional ticker list to invalidate (None = clear all)
            start: Optional start date (None = clear all)
            end: Optional end date (None = clear all)
            **kwargs: Additional parameters
            
        Returns:
            Number of cache entries invalidated
        """
        if tickers is None and start is None and end is None:
            # Clear all caches
            count = len(self._memory_cache)
            self._memory_cache.clear()
            
            if self.enable_file_cache:
                for cache_file in self.cache_dir.glob("price_cache_*.parquet"):
                    cache_file.unlink()
                    meta_file = cache_file.with_suffix('.meta.json')
                    if meta_file.exists():
                        meta_file.unlink()
                    count += 1
            
            logger.info(f"Cache CLEAR ALL: {count} entries")
            return count
        
        # Invalidate specific entry
        # If exact parameters were provided, try to match by metadata instead
        count = 0

        # Normalize tickers for comparison
        norm_tickers = sorted(tickers) if tickers is not None else None

        # Check in-memory metadata map first
        keys_to_delete = []
        for key, meta in list(self._meta_map.items()):
            try:
                meta_tickers = meta.get('tickers')
                if isinstance(meta_tickers, list):
                    meta_tickers_sorted = sorted(meta_tickers)
                else:
                    meta_tickers_sorted = meta_tickers

                if ((norm_tickers is None or meta_tickers_sorted == norm_tickers) and
                    (start is None or meta.get('start') == start) and
                    (end is None or meta.get('end') == end)):
                    keys_to_delete.append(key)
            except Exception:
                continue

        # Remove matched keys from memory and files
        for key in keys_to_delete:
            if key in self._memory_cache:
                del self._memory_cache[key]
                count += 1

            if self.enable_file_cache:
                cache_file = self.cache_dir / f"{key}.parquet"
                meta_file = self.cache_dir / f"{key}.meta.json"
                if cache_file.exists():
                    try:
                        cache_file.unlink()
                        count += 1
                    except Exception:
                        pass
                if meta_file.exists():
                    try:
                        meta_file.unlink()
                    except Exception:
                        pass

            # Remove from meta map
            try:
                del self._meta_map[key]
            except KeyError:
                pass

        logger.info(f"Cache INVALIDATE (by meta): tickers={tickers}, start={start}, end={end} => {count} entries")
        return count
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        stats = {
            'memory_entries': len(self._memory_cache),
            'file_cache_enabled': self.enable_file_cache,
            'ttl_seconds': self.ttl_seconds
        }
        
        if self.enable_file_cache:
            cache_files = list(self.cache_dir.glob("price_cache_*.parquet"))
            stats['file_entries'] = len(cache_files)
            stats['cache_dir'] = str(self.cache_dir)
        
        return stats


# Global cache instance
_global_cache: Optional[PriceDataCache] = None


def get_price_cache() -> PriceDataCache:
    """
    Get or create global price cache instance.
    
    Returns:
        PriceDataCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = PriceDataCache(
            cache_dir="cache_price",
            ttl_seconds=3600,  # 1 hour default
            enable_file_cache=True
        )
    return _global_cache


def clear_all_price_cache() -> int:
    """
    Clear all cached price data.
    
    Returns:
        Number of entries cleared
    """
    cache = get_price_cache()
    return cache.invalidate()
