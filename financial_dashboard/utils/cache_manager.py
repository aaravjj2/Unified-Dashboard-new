"""
Cache Manager for Market Trends Tab

Provides centralized cache operations with disk/memory synchronization,
thread-safe access, and TTL validation.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
Agent-1B: Enhanced with comprehensive logging, atomic writes, and extended API
"""

import json
import os
import time
import threading
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Enhanced logging to diagnostics directory
_log_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'reports/market_trends_fix/diagnostics/cache_ops.log'
)
os.makedirs(os.path.dirname(_log_file), exist_ok=True)
_file_handler = logging.FileHandler(_log_file)
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(_file_handler)
logger.setLevel(logging.INFO)


class CacheManager:
    """
    Manages cache operations for Market Trends data.
    
    Provides thread-safe access to both memory and disk cache,
    ensuring consistency between the two storage layers.
    """
    
    def __init__(self, cache_file_path: str, memory_cache: Dict[str, Any], ttl_seconds: int = 300):
        """
        Initialize Cache Manager.
        
        Args:
            cache_file_path: Path to disk cache file (e.g., market_brief.json)
            memory_cache: Reference to shared memory cache dict (e.g., RESULTS_CACHE)
            ttl_seconds: Time-to-live in seconds (default 300 = 5 minutes)
        """
        self.cache_file_path = cache_file_path
        self.memory_cache = memory_cache
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._memory_loaded_at = None
        
        # Ensure cache directory exists
        cache_dir = os.path.dirname(cache_file_path)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
            logger.info(f"Created cache directory: {cache_dir}")
        
        logger.info(f"CacheManager initialized: path={cache_file_path}, ttl={ttl_seconds}s")
    
    def load_from_disk(self) -> Dict[str, Any]:
        """
        Load cached data from disk atomically.
        
        Returns:
            Dict containing cached data, or empty dict if file doesn't exist
            or is corrupted.
        
        Thread-safe operation.
        """
        with self._lock:
            if not os.path.exists(self.cache_file_path):
                logger.warning(f"Cache file not found: {self.cache_file_path}")
                return {}
            
            try:
                with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._memory_loaded_at = time.time()
                record_count = len(data.get('detailed', []))
                logger.info(f"Loaded cache from disk: {record_count} records")
                return data
                
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted cache file (JSON decode error): {e}")
                return {}
            except Exception as e:
                logger.error(f"Failed to load cache from disk: {e}")
                return {}
    
    def save_to_disk(self, data: Dict[str, Any]) -> bool:
        """
        Save data to disk cache with atomic write.
        
        Uses atomic write pattern (write to temp file, then rename)
        to prevent corruption from partial writes.
        
        Args:
            data: Data to save
            
        Returns:
            True if save successful, False otherwise
            
        Thread-safe operation.
        """
        with self._lock:
            try:
                # Add metadata
                data_with_meta = data.copy()
                if 'generated_at' not in data_with_meta:
                    data_with_meta['generated_at'] = datetime.now(timezone.utc).isoformat()
                
                data_with_meta['_cache_metadata'] = {
                    'generated_at': data_with_meta.get('generated_at'),
                    'ttl_seconds': self.ttl_seconds,
                    'record_count': len(data.get('detailed', []))
                }
                
                # Atomic write: write to temp file first
                temp_file = self.cache_file_path + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data_with_meta, f, indent=2, default=str, ensure_ascii=False)
                
                # Atomic rename (overwrites existing file on POSIX)
                os.replace(temp_file, self.cache_file_path)
                
                # Update memory ref and timestamp
                self.memory_cache['results'] = data
                self._memory_loaded_at = time.time()
                
                record_count = len(data.get('detailed', []))
                logger.info(f"Saved cache to disk atomically: {record_count} records")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save cache to disk: {e}")
                # Clean up temp file if it exists
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
                return False
    
    def get_cached_data(self) -> Dict[str, Any]:
        """
        Get cached data from memory cache.
        
        Returns:
            Dict containing cached data from memory, or empty dict if not present
            
        Thread-safe operation.
        """
        with self._lock:
            return self.memory_cache.get('results', {})
    
    def get(self, key: Optional[str] = None) -> Any:
        """
        Get data from memory cache.
        
        Args:
            key: Optional key to retrieve. If None, return entire cache.
            
        Returns:
            Cached value or entire cache dict
        """
        with self._lock:
            try:
                if key is None:
                    return self.memory_cache.copy()
                else:
                    return self.memory_cache.get(key, {})
            except Exception as e:
                logger.error(f"Error getting cache key '{key}': {e}")
                return {} if key is None else None
    
    def update_cache(self, data: Dict[str, Any]) -> bool:
        """
        Update both memory and disk cache atomically.
        
        Ensures consistency between memory and disk storage.
        
        Args:
            data: Data to cache
            
        Returns:
            True if both updates successful, False otherwise
            
        Thread-safe operation.
        """
        with self._lock:
            try:
                # Update memory cache
                self.memory_cache['results'] = data
                self.memory_cache['loaded_at'] = time.time()
                
                # Update disk cache
                disk_success = self.save_to_disk(data)
                
                if disk_success:
                    logger.info("Cache updated successfully (memory + disk)")
                    return True
                else:
                    logger.warning("Cache updated in memory but disk save failed")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to update cache: {e}")
                return False
    
    def is_cache_fresh(self, max_age_seconds: Optional[int] = None) -> bool:
        """
        Check if cache is fresh (within TTL).
        
        Args:
            max_age_seconds: Maximum age in seconds (default uses self.ttl_seconds)
            
        Returns:
            True if cache is fresh, False otherwise
            
        Thread-safe operation.
        """
        with self._lock:
            if max_age_seconds is None:
                max_age_seconds = self.ttl_seconds
            
            cache_timestamp = self.get_cache_timestamp()
            
            if cache_timestamp is None:
                logger.debug("No cache timestamp available, considering stale")
                return False
            
            age = time.time() - cache_timestamp
            is_fresh = age < max_age_seconds
            
            logger.debug(f"Cache age: {age:.1f}s, fresh: {is_fresh} (TTL: {max_age_seconds}s)")
            return is_fresh
    
    def get_cache_timestamp(self) -> Optional[float]:
        """
        Get cache timestamp (Unix timestamp).
        
        Tries multiple sources in order:
        1. Memory cache '_memory_loaded_at' field
        2. Memory cache 'loaded_at' field
        3. Disk cache 'generated_at' field (ISO format)
        4. Disk file modification time
        
        Returns:
            Unix timestamp, or None if no timestamp available
            
        Thread-safe operation.
        """
        with self._lock:
            # Try internal memory timestamp first
            if self._memory_loaded_at:
                return float(self._memory_loaded_at)
            
            # Try memory cache loaded_at field
            loaded_at = self.memory_cache.get('loaded_at')
            if loaded_at:
                return float(loaded_at)
            
            # Try disk cache generated_at
            try:
                data = self.load_from_disk()
                if data and 'generated_at' in data:
                    generated_at_str = data['generated_at']
                    # Parse ISO format timestamp
                    dt = datetime.fromisoformat(generated_at_str.replace('Z', '+00:00'))
                    return dt.timestamp()
            except Exception as e:
                logger.debug(f"Could not parse generated_at: {e}")
            
            # Fallback to file mtime
            try:
                if os.path.exists(self.cache_file_path):
                    return os.path.getmtime(self.cache_file_path)
            except Exception as e:
                logger.debug(f"Could not get file mtime: {e}")
            
            return None
    
    def clear_cache(self) -> bool:
        """
        Clear both memory and disk cache.
        
        Returns:
            True if successful, False otherwise
            
        Thread-safe operation.
        """
        with self._lock:
            try:
                # Clear memory cache
                if 'results' in self.memory_cache:
                    del self.memory_cache['results']
                if 'loaded_at' in self.memory_cache:
                    del self.memory_cache['loaded_at']
                
                # Delete disk cache file
                if os.path.exists(self.cache_file_path):
                    os.remove(self.cache_file_path)
                
                logger.info("Cache cleared successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")
                return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache metadata for debugging.
        
        Returns:
            Dict with cache information including path, exists, age_seconds, 
            record_count, freshness_flag, ttl_seconds
        """
        with self._lock:
            timestamp = self.get_cache_timestamp()
            age = time.time() - timestamp if timestamp else None
            
            info = {
                'path': self.cache_file_path,
                'file_exists': os.path.exists(self.cache_file_path),
                'timestamp': timestamp,
                'age_seconds': age,
                'is_fresh': self.is_cache_fresh() if timestamp else False,
                'memory_cache_present': 'results' in self.memory_cache,
                'record_count': len(self.get_cached_data().get('detailed', [])),
                'ttl_seconds': self.ttl_seconds
            }
            
            logger.debug(f"Cache info: {info}")
            return info
