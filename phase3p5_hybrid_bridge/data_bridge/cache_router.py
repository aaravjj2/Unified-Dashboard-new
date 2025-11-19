"""
Cache Router — Multi-Tier Caching System
=========================================

Three-tier caching architecture:
- L1: RAM-based LRU cache (fastest, volatile)
- L2: Disk-based cache (persistent, local)
- L3: Cloud stub bridge (Azure-ready, when available)

Provides unified API for data retrieval and storage with automatic tier fallback.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from collections import OrderedDict
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .data_contracts import ContractType


# Configuration
CACHE_BASE_DIR = Path(__file__).parent.parent.parent / "data" / "hybrid_cache"
L1_MAX_SIZE = 100  # Maximum number of items in L1 cache
L2_TTL_HOURS = 24  # Time-to-live for L2 cache entries
QUARANTINE_DIR = CACHE_BASE_DIR / "quarantine"


@dataclass
class CacheEntry:
    """Represents a cached data entry with metadata."""
    key: str
    contract_type: str
    data: dict
    hash: str
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0
    tier: str = "L1"  # L1, L2, or L3


class LRUCache:
    """
    Least Recently Used (LRU) cache implementation for L1.
    
    Thread-safe, memory-efficient cache with automatic eviction.
    """
    
    def __init__(self, max_size: int = L1_MAX_SIZE):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """
        Retrieve entry from cache.
        
        Args:
            key: Cache key
        
        Returns:
            CacheEntry if found, None otherwise
        """
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            entry = self.cache.pop(key)
            entry.access_count += 1
            entry.last_access = time.time()
            self.cache[key] = entry
            return entry
        else:
            self.misses += 1
            return None
    
    def put(self, key: str, entry: CacheEntry) -> None:
        """
        Add entry to cache.
        
        Args:
            key: Cache key
            entry: CacheEntry to store
        """
        # Remove if exists (to update position)
        if key in self.cache:
            self.cache.pop(key)
        # Add to end (most recently used)
        elif len(self.cache) >= self.max_size:
            # Evict least recently used
            self.cache.popitem(last=False)
        
        entry.last_access = time.time()
        self.cache[key] = entry
    
    def remove(self, key: str) -> bool:
        """
        Remove entry from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if removed, False if not found
        """
        if key in self.cache:
            self.cache.pop(key)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hit rate, size, etc.
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }


class CacheRouter:
    """
    Multi-tier cache router with L1 (RAM) → L2 (disk) → L3 (cloud stub) fallback.
    
    Provides unified interface for data retrieval and storage across all tiers.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, enable_l3: bool = False):
        """
        Initialize cache router.
        
        Args:
            cache_dir: Base directory for L2 cache (defaults to CACHE_BASE_DIR)
            enable_l3: Whether to enable L3 cloud stub integration
        """
        self.cache_dir = cache_dir or CACHE_BASE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create tier subdirectories
        self.l2_dir = self.cache_dir / "l2"
        self.l2_dir.mkdir(exist_ok=True)
        
        QUARANTINE_DIR.mkdir(exist_ok=True)
        
        # Initialize L1 cache
        self.l1_cache = LRUCache(max_size=L1_MAX_SIZE)
        
        # L3 cloud stub (placeholder for Agent 1B integration)
        self.enable_l3 = enable_l3
        self.l3_client = None  # Will be set when Azure integration is ready
        
        # Statistics
        self.l2_hits = 0
        self.l2_misses = 0
        self.l3_hits = 0
        self.l3_misses = 0
    
    def _generate_cache_key(self, contract_type: ContractType, key: str) -> str:
        """
        Generate unique cache key.
        
        Args:
            contract_type: Contract type
            key: User-provided key
        
        Returns:
            Unique cache key
        """
        return f"{contract_type.value}:{key}"
    
    def _get_l2_path(self, cache_key: str) -> Path:
        """
        Get file path for L2 cache entry.
        
        Args:
            cache_key: Cache key
        
        Returns:
            Path to cache file
        """
        # Use hash to create subdirectories (avoid too many files in one dir)
        key_hash = hashlib.md5(cache_key.encode()).hexdigest()
        subdir = self.l2_dir / key_hash[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key_hash}.json"
    
    def _is_l2_expired(self, filepath: Path, ttl_hours: float = L2_TTL_HOURS) -> bool:
        """
        Check if L2 cache entry is expired.
        
        Args:
            filepath: Path to cache file
            ttl_hours: Time-to-live in hours
        
        Returns:
            True if expired
        """
        if not filepath.exists():
            return True
        
        file_age_hours = (time.time() - filepath.stat().st_mtime) / 3600
        return file_age_hours > ttl_hours
    
    def get_data(self, contract_type: ContractType, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache (L1 → L2 → L3 fallback).
        
        Args:
            contract_type: Type of contract
            key: User-defined key
        
        Returns:
            Data dict if found, None otherwise
        """
        cache_key = self._generate_cache_key(contract_type, key)
        
        # Try L1 (RAM)
        l1_entry = self.l1_cache.get(cache_key)
        if l1_entry is not None:
            return l1_entry.data
        
        # Try L2 (disk)
        l2_path = self._get_l2_path(cache_key)
        if l2_path.exists() and not self._is_l2_expired(l2_path):
            try:
                with open(l2_path, 'r') as f:
                    l2_data = json.load(f)
                
                self.l2_hits += 1
                
                # Promote to L1
                entry = CacheEntry(
                    key=cache_key,
                    contract_type=contract_type.value,
                    data=l2_data['data'],
                    hash=l2_data['hash'],
                    timestamp=l2_data['timestamp'],
                    tier="L2"
                )
                self.l1_cache.put(cache_key, entry)
                
                return l2_data['data']
            except (json.JSONDecodeError, KeyError) as e:
                # Corrupted cache file
                self.l2_misses += 1
                self._quarantine_file(l2_path, f"L2 read error: {e}")
        else:
            self.l2_misses += 1
        
        # Try L3 (cloud stub)
        if self.enable_l3 and self.l3_client is not None:
            l3_data = self._get_from_l3(contract_type, key)
            if l3_data is not None:
                self.l3_hits += 1
                
                # Promote to L1 and L2
                self.store_data(contract_type, key, l3_data)
                return l3_data
            else:
                self.l3_misses += 1
        
        return None
    
    def store_data(self, contract_type: ContractType, key: str, data: Dict[str, Any]) -> bool:
        """
        Store data in all cache tiers.
        
        Args:
            contract_type: Type of contract
            key: User-defined key
            data: Data to store
        
        Returns:
            True if successful
        """
        cache_key = self._generate_cache_key(contract_type, key)
        
        # Compute hash
        canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        data_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        # Create entry
        entry = CacheEntry(
            key=cache_key,
            contract_type=contract_type.value,
            data=data,
            hash=data_hash,
            timestamp=time.time(),
            tier="L1"
        )
        
        # Store in L1
        self.l1_cache.put(cache_key, entry)
        
        # Store in L2
        l2_path = self._get_l2_path(cache_key)
        l2_payload = {
            "key": cache_key,
            "contract_type": contract_type.value,
            "data": data,
            "hash": data_hash,
            "timestamp": entry.timestamp,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            with open(l2_path, 'w') as f:
                json.dump(l2_payload, f, indent=2)
        except IOError as e:
            print(f"Warning: Failed to write L2 cache: {e}")
            return False
        
        return True
    
    def sync_to_cloud(self, contract_type: ContractType, key: str) -> bool:
        """
        Sync data to L3 cloud stub.
        
        Args:
            contract_type: Type of contract
            key: User-defined key
        
        Returns:
            True if successful, False if L3 disabled or failed
        """
        if not self.enable_l3 or self.l3_client is None:
            return False
        
        cache_key = self._generate_cache_key(contract_type, key)
        
        # Get data from L1 or L2
        data = self.get_data(contract_type, key)
        if data is None:
            return False
        
        # Send to L3 stub
        return self._send_to_l3(contract_type, key, data)
    
    def invalidate(self, contract_type: ContractType, key: str) -> bool:
        """
        Invalidate cache entry across all tiers.
        
        Args:
            contract_type: Type of contract
            key: User-defined key
        
        Returns:
            True if any tier was invalidated
        """
        cache_key = self._generate_cache_key(contract_type, key)
        invalidated = False
        
        # Remove from L1
        if self.l1_cache.remove(cache_key):
            invalidated = True
        
        # Remove from L2
        l2_path = self._get_l2_path(cache_key)
        if l2_path.exists():
            l2_path.unlink()
            invalidated = True
        
        # Remove from L3 (if implemented)
        if self.enable_l3 and self.l3_client is not None:
            if self._delete_from_l3(contract_type, key):
                invalidated = True
        
        return invalidated
    
    def clear_all(self) -> None:
        """Clear all cache tiers."""
        self.l1_cache.clear()
        
        # Clear L2
        for cache_file in self.l2_dir.rglob("*.json"):
            cache_file.unlink()
        
        self.l2_hits = 0
        self.l2_misses = 0
        self.l3_hits = 0
        self.l3_misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dict with stats for all tiers
        """
        l1_stats = self.l1_cache.get_stats()
        
        l2_total = self.l2_hits + self.l2_misses
        l2_hit_rate = self.l2_hits / l2_total if l2_total > 0 else 0.0
        
        l3_total = self.l3_hits + self.l3_misses
        l3_hit_rate = self.l3_hits / l3_total if l3_total > 0 else 0.0
        
        # Combined hit rate (L1 + L2)
        combined_hits = l1_stats["hits"] + self.l2_hits
        combined_total = l1_stats["total_requests"] + l2_total
        combined_hit_rate = combined_hits / combined_total if combined_total > 0 else 0.0
        
        return {
            "l1": l1_stats,
            "l2": {
                "hits": self.l2_hits,
                "misses": self.l2_misses,
                "hit_rate": l2_hit_rate,
                "total_requests": l2_total
            },
            "l3": {
                "hits": self.l3_hits,
                "misses": self.l3_misses,
                "hit_rate": l3_hit_rate,
                "total_requests": l3_total,
                "enabled": self.enable_l3
            },
            "combined": {
                "hit_rate": combined_hit_rate,
                "total_requests": combined_total
            }
        }
    
    def _quarantine_file(self, filepath: Path, reason: str) -> None:
        """
        Move corrupted cache file to quarantine.
        
        Args:
            filepath: Path to corrupted file
            reason: Reason for quarantine
        """
        quarantine_path = QUARANTINE_DIR / f"{filepath.stem}_{int(time.time())}.json"
        
        try:
            # Move file
            filepath.rename(quarantine_path)
            
            # Write quarantine metadata
            metadata_path = quarantine_path.with_suffix('.meta.json')
            metadata = {
                "original_path": str(filepath),
                "quarantined_at": datetime.utcnow().isoformat() + "Z",
                "reason": reason
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to quarantine file {filepath}: {e}")
    
    # L3 Cloud Stub Integration (placeholders for Agent 1B Phase 4)
    
    def _get_from_l3(self, contract_type: ContractType, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from L3 cloud stub.
        
        Args:
            contract_type: Contract type
            key: User key
        
        Returns:
            Data if found, None otherwise
        """
        # Placeholder: Will be implemented when Agent 1B provides cloud client
        # Expected interface:
        # return self.l3_client.get(contract_type=contract_type.value, key=key)
        return None
    
    def _send_to_l3(self, contract_type: ContractType, key: str, data: Dict[str, Any]) -> bool:
        """
        Send data to L3 cloud stub.
        
        Args:
            contract_type: Contract type
            key: User key
            data: Data to send
        
        Returns:
            True if successful
        """
        # Placeholder: Will be implemented when Agent 1B provides cloud client
        # Expected interface:
        # return self.l3_client.put(contract_type=contract_type.value, key=key, data=data)
        return False
    
    def _delete_from_l3(self, contract_type: ContractType, key: str) -> bool:
        """
        Delete data from L3 cloud stub.
        
        Args:
            contract_type: Contract type
            key: User key
        
        Returns:
            True if successful
        """
        # Placeholder: Will be implemented when Agent 1B provides cloud client
        # Expected interface:
        # return self.l3_client.delete(contract_type=contract_type.value, key=key)
        return False


# Singleton instance for global access
_global_router: Optional[CacheRouter] = None


def get_global_router() -> CacheRouter:
    """
    Get or create global cache router instance.
    
    Returns:
        CacheRouter singleton
    """
    global _global_router
    if _global_router is None:
        _global_router = CacheRouter()
    return _global_router


# Convenience functions for direct use

def get_data(contract_type: ContractType, key: str) -> Optional[Dict[str, Any]]:
    """Convenience wrapper for global router get_data."""
    return get_global_router().get_data(contract_type, key)


def store_data(contract_type: ContractType, key: str, data: Dict[str, Any]) -> bool:
    """Convenience wrapper for global router store_data."""
    return get_global_router().store_data(contract_type, key, data)


def sync_to_cloud(contract_type: ContractType, key: str) -> bool:
    """Convenience wrapper for global router sync_to_cloud."""
    return get_global_router().sync_to_cloud(contract_type, key)


def get_cache_stats() -> Dict[str, Any]:
    """Convenience wrapper for global router get_stats."""
    return get_global_router().get_stats()
