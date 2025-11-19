"""
Phase 9 — Scenario Caching Engine
==================================

High-performance caching layer for scenario generation with deterministic ID generation,
cache hit/miss tracking, TTL expiry management, and performance telemetry.

Features:
- Deterministic scenario ID generation (SHA256 content-based hashing)
- Cache hit/miss metrics with telemetry
- Configurable TTL expiry (default 24h)
- Cold vs warm performance benchmarking
- Integration with Phase 7/8 scenario_engine.py
- Thread-safe cache operations
- Automatic cache cleanup and LRU eviction

Architecture:
- CacheEngine: Main orchestrator
- CacheMetrics: Performance telemetry
- CacheEntry: Individual cached scenario with metadata
- DeterministicIDGenerator: Content-based hashing for reproducibility

Performance Target:
- Warm run speedup: ≥25-30% vs cold runs
- Cache lookup latency: <10ms
- Memory overhead: <100MB for 1000 scenarios

Author: Agent 1B — Phase 9 E2E Validation
Version: 1.0
Date: October 29, 2025
"""

import json
import hashlib
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import threading
from collections import OrderedDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CacheMetrics:
    """Performance telemetry for cache operations"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_lookup_time_ms: float = 0.0
    total_write_time_ms: float = 0.0
    total_evictions: int = 0
    total_expirations: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate percentage"""
        return 100.0 - self.hit_rate
    
    @property
    def avg_lookup_time_ms(self) -> float:
        """Average lookup time per request"""
        if self.total_requests == 0:
            return 0.0
        return self.total_lookup_time_ms / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(self.hit_rate, 2),
            "miss_rate_percent": round(self.miss_rate, 2),
            "avg_lookup_time_ms": round(self.avg_lookup_time_ms, 4),
            "total_lookup_time_ms": round(self.total_lookup_time_ms, 2),
            "total_write_time_ms": round(self.total_write_time_ms, 2),
            "total_evictions": self.total_evictions,
            "total_expirations": self.total_expirations
        }


@dataclass
class CacheEntry:
    """Individual cached scenario with metadata"""
    scenario_id: str
    scenario_data: Any  # Serialized scenario dataset
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_hours: float = 24.0
    
    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL"""
        expiry_time = self.created_at + timedelta(hours=self.ttl_hours)
        return datetime.now() > expiry_time
    
    def update_access(self) -> None:
        """Update access metadata"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary (excluding data)"""
        return {
            "scenario_id": self.scenario_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "size_bytes": self.size_bytes,
            "ttl_hours": self.ttl_hours,
            "is_expired": self.is_expired()
        }


@dataclass
class CacheBenchmarkResult:
    """Benchmark results for cold vs warm runs"""
    cold_run_time_s: float
    warm_run_time_s: float
    speedup_factor: float
    speedup_percent: float
    cache_hit_rate: float
    num_scenarios: int
    benchmark_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# ============================================================================
# DETERMINISTIC ID GENERATOR
# ============================================================================

class DeterministicIDGenerator:
    """
    Generate deterministic scenario IDs using content-based hashing.
    
    Uses SHA256 hash of normalized parameter dictionary to ensure:
    - Same inputs → Same ID (deterministic)
    - Different inputs → Different ID (collision-resistant)
    - Order-independent (sorted keys)
    """
    
    @staticmethod
    def normalize_params(params: Dict[str, Any]) -> str:
        """
        Normalize parameters to canonical string representation.
        
        Args:
            params: Scenario parameters dictionary
            
        Returns:
            Canonical string representation
        """
        # Sort keys for order independence
        sorted_keys = sorted(params.keys())
        
        # Build canonical representation
        canonical_parts = []
        for key in sorted_keys:
            value = params[key]
            
            # Handle different types
            if isinstance(value, (list, tuple)):
                value_str = ",".join(str(v) for v in sorted(value))
            elif isinstance(value, dict):
                # Recursively normalize nested dicts
                value_str = DeterministicIDGenerator.normalize_params(value)
            elif isinstance(value, float):
                # Use fixed precision for floats to avoid rounding issues
                value_str = f"{value:.8f}"
            else:
                value_str = str(value)
            
            canonical_parts.append(f"{key}={value_str}")
        
        return "|".join(canonical_parts)
    
    @staticmethod
    def generate_id(params: Dict[str, Any], prefix: str = "scenario") -> str:
        """
        Generate deterministic scenario ID from parameters.
        
        Args:
            params: Scenario parameters
            prefix: ID prefix (default: "scenario")
            
        Returns:
            Deterministic scenario ID (e.g., "scenario_a3f2c8...")
        """
        # Normalize parameters
        canonical = DeterministicIDGenerator.normalize_params(params)
        
        # Generate SHA256 hash
        hash_digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        
        # Use first 16 characters for compact ID
        short_hash = hash_digest[:16]
        
        return f"{prefix}_{short_hash}"
    
    @staticmethod
    def verify_determinism(params: Dict[str, Any], expected_id: str) -> bool:
        """
        Verify that parameters generate expected ID (determinism check).
        
        Args:
            params: Scenario parameters
            expected_id: Expected scenario ID
            
        Returns:
            True if IDs match, False otherwise
        """
        generated_id = DeterministicIDGenerator.generate_id(params)
        return generated_id == expected_id


# ============================================================================
# CACHE ENGINE
# ============================================================================

class CacheEngine:
    """
    High-performance caching engine for scenario generation.
    
    Features:
    - Deterministic ID generation
    - TTL-based expiry
    - LRU eviction policy
    - Thread-safe operations
    - Performance telemetry
    """
    
    def __init__(
        self,
        cache_dir: str = "outputs/phase9_cache",
        max_cache_size: int = 1000,
        default_ttl_hours: float = 24.0,
        enable_disk_cache: bool = True
    ):
        """
        Initialize cache engine.
        
        Args:
            cache_dir: Directory for disk-based cache
            max_cache_size: Maximum number of cached scenarios
            default_ttl_hours: Default TTL in hours
            enable_disk_cache: Enable persistent disk cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_cache_size = max_cache_size
        self.default_ttl_hours = default_ttl_hours
        self.enable_disk_cache = enable_disk_cache
        
        # In-memory cache (OrderedDict for LRU)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Thread lock for thread-safe operations
        self._lock = threading.Lock()
        
        # Performance metrics
        self.metrics = CacheMetrics()
        
        # Load disk cache if enabled
        if self.enable_disk_cache:
            self._load_disk_cache()
        
        logger.info(f"✅ Cache engine initialized: {self.cache_dir}")
        logger.info(f"   Max size: {self.max_cache_size} scenarios")
        logger.info(f"   Default TTL: {self.default_ttl_hours}h")
        logger.info(f"   Disk cache: {'enabled' if self.enable_disk_cache else 'disabled'}")
    
    def get(self, params: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieve scenario from cache.
        
        Args:
            params: Scenario parameters
            
        Returns:
            Cached scenario data or None if not found
        """
        start_time = time.perf_counter()
        
        with self._lock:
            self.metrics.total_requests += 1
            
            # Generate deterministic ID
            scenario_id = DeterministicIDGenerator.generate_id(params)
            
            # Check if in cache
            if scenario_id not in self._cache:
                self.metrics.cache_misses += 1
                lookup_time_ms = (time.perf_counter() - start_time) * 1000
                self.metrics.total_lookup_time_ms += lookup_time_ms
                logger.debug(f"❌ Cache MISS: {scenario_id} ({lookup_time_ms:.2f}ms)")
                return None
            
            # Get entry
            entry = self._cache[scenario_id]
            
            # Check expiry
            if entry.is_expired():
                logger.debug(f"⏰ Cache entry EXPIRED: {scenario_id}")
                del self._cache[scenario_id]
                self.metrics.cache_misses += 1
                self.metrics.total_expirations += 1
                
                # Delete from disk
                if self.enable_disk_cache:
                    self._delete_from_disk(scenario_id)
                
                lookup_time_ms = (time.perf_counter() - start_time) * 1000
                self.metrics.total_lookup_time_ms += lookup_time_ms
                return None
            
            # Cache hit
            self.metrics.cache_hits += 1
            entry.update_access()
            
            # Move to end (LRU)
            self._cache.move_to_end(scenario_id)
            
            lookup_time_ms = (time.perf_counter() - start_time) * 1000
            self.metrics.total_lookup_time_ms += lookup_time_ms
            
            logger.debug(f"✅ Cache HIT: {scenario_id} ({lookup_time_ms:.2f}ms, access #{entry.access_count})")
            
            return entry.scenario_data
    
    def put(self, params: Dict[str, Any], scenario_data: Any, ttl_hours: Optional[float] = None) -> str:
        """
        Store scenario in cache.
        
        Args:
            params: Scenario parameters
            scenario_data: Scenario data to cache
            ttl_hours: Custom TTL (uses default if None)
            
        Returns:
            Scenario ID
        """
        start_time = time.perf_counter()
        
        with self._lock:
            # Generate deterministic ID
            scenario_id = DeterministicIDGenerator.generate_id(params)
            
            # Calculate size
            size_bytes = len(pickle.dumps(scenario_data))
            
            # Create entry
            entry = CacheEntry(
                scenario_id=scenario_id,
                scenario_data=scenario_data,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
                size_bytes=size_bytes,
                ttl_hours=ttl_hours or self.default_ttl_hours
            )
            
            # Check if cache is full
            if len(self._cache) >= self.max_cache_size:
                self._evict_lru()
            
            # Store in cache
            self._cache[scenario_id] = entry
            
            # Write to disk if enabled
            if self.enable_disk_cache:
                self._write_to_disk(scenario_id, scenario_data)
            
            write_time_ms = (time.perf_counter() - start_time) * 1000
            self.metrics.total_write_time_ms += write_time_ms
            
            logger.debug(f"💾 Cache WRITE: {scenario_id} ({size_bytes} bytes, {write_time_ms:.2f}ms)")
            
            return scenario_id
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._cache:
            return
        
        # OrderedDict: first item is least recently used
        oldest_id, oldest_entry = self._cache.popitem(last=False)
        
        self.metrics.total_evictions += 1
        
        # Delete from disk
        if self.enable_disk_cache:
            self._delete_from_disk(oldest_id)
        
        logger.debug(f"🗑️  Cache EVICT (LRU): {oldest_id}")
    
    def _write_to_disk(self, scenario_id: str, scenario_data: Any) -> None:
        """Write scenario to disk cache"""
        try:
            cache_file = self.cache_dir / f"{scenario_id}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(scenario_data, f)
        except Exception as e:
            logger.warning(f"⚠️  Failed to write disk cache for {scenario_id}: {e}")
    
    def _delete_from_disk(self, scenario_id: str) -> None:
        """Delete scenario from disk cache"""
        try:
            cache_file = self.cache_dir / f"{scenario_id}.pkl"
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            logger.warning(f"⚠️  Failed to delete disk cache for {scenario_id}: {e}")
    
    def _load_disk_cache(self) -> None:
        """Load cache entries from disk"""
        logger.info("📂 Loading disk cache...")
        
        loaded_count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                scenario_id = cache_file.stem
                
                with open(cache_file, 'rb') as f:
                    scenario_data = pickle.load(f)
                
                # Create entry (reconstruct metadata from file)
                created_at = datetime.fromtimestamp(cache_file.stat().st_ctime)
                last_accessed = datetime.fromtimestamp(cache_file.stat().st_mtime)
                size_bytes = cache_file.stat().st_size
                
                entry = CacheEntry(
                    scenario_id=scenario_id,
                    scenario_data=scenario_data,
                    created_at=created_at,
                    last_accessed=last_accessed,
                    access_count=0,
                    size_bytes=size_bytes,
                    ttl_hours=self.default_ttl_hours
                )
                
                # Check if expired
                if entry.is_expired():
                    cache_file.unlink()
                    continue
                
                self._cache[scenario_id] = entry
                loaded_count += 1
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to load {cache_file.name}: {e}")
        
        logger.info(f"✅ Loaded {loaded_count} scenarios from disk cache")
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            num_cleared = len(self._cache)
            self._cache.clear()
            
            # Clear disk cache
            if self.enable_disk_cache:
                for cache_file in self.cache_dir.glob("*.pkl"):
                    cache_file.unlink()
            
            logger.info(f"🗑️  Cleared {num_cleared} cache entries")
    
    def get_metrics(self) -> CacheMetrics:
        """Get current cache metrics"""
        return self.metrics
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information summary"""
        with self._lock:
            total_size_bytes = sum(entry.size_bytes for entry in self._cache.values())
            
            return {
                "num_entries": len(self._cache),
                "max_cache_size": self.max_cache_size,
                "total_size_bytes": total_size_bytes,
                "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                "metrics": self.metrics.to_dict(),
                "oldest_entry": list(self._cache.values())[0].to_dict() if self._cache else None,
                "newest_entry": list(self._cache.values())[-1].to_dict() if self._cache else None
            }
    
    def save_metrics(self, filepath: str) -> None:
        """Save cache metrics to JSON file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "cache_info": self.get_cache_info(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Saved cache metrics to {filepath}")


# ============================================================================
# CACHE-AWARE SCENARIO WRAPPER
# ============================================================================

class CachedScenarioEngine:
    """
    Wrapper around ScenarioEngine with caching support.
    
    Transparently caches scenario generation results and serves from cache
    when parameters match.
    """
    
    def __init__(self, cache_engine: CacheEngine):
        """
        Initialize cached scenario engine.
        
        Args:
            cache_engine: Cache engine instance
        """
        self.cache = cache_engine
    
    def generate_with_cache(self, scenario_engine, params_dict: Dict[str, Any]) -> Any:
        """
        Generate scenario with caching.
        
        Args:
            scenario_engine: ScenarioEngine instance
            params_dict: Normalized parameters dictionary
            
        Returns:
            ScenarioDataset (from cache or fresh generation)
        """
        # Check cache first
        cached_result = self.cache.get(params_dict)
        
        if cached_result is not None:
            logger.info(f"✅ Using CACHED scenario (hit rate: {self.cache.metrics.hit_rate:.1f}%)")
            return cached_result
        
        # Cache miss - generate fresh
        logger.info("🔄 Generating FRESH scenario (cache miss)")
        start_time = time.perf_counter()
        
        result = scenario_engine.generate()
        
        generation_time = time.perf_counter() - start_time
        logger.info(f"✅ Scenario generated in {generation_time:.2f}s")
        
        # Store in cache
        self.cache.put(params_dict, result)
        
        return result


# ============================================================================
# BENCHMARKING UTILITIES
# ============================================================================

class CacheBenchmark:
    """
    Benchmark cold vs warm cache performance.
    """
    
    @staticmethod
    def run_benchmark(
        scenario_engine_factory,
        params_list: List[Dict[str, Any]],
        cache_engine: CacheEngine,
        num_iterations: int = 3
    ) -> CacheBenchmarkResult:
        """
        Run cold vs warm benchmark.
        
        Args:
            scenario_engine_factory: Function that creates ScenarioEngine instance
            params_list: List of parameter dictionaries
            cache_engine: Cache engine instance
            num_iterations: Number of iterations for warm run
            
        Returns:
            CacheBenchmarkResult
        """
        logger.info("🏁 Starting cache benchmark...")
        
        # Clear cache for cold run
        cache_engine.clear()
        cache_engine.metrics = CacheMetrics()  # Reset metrics
        
        # COLD RUN
        logger.info("❄️  Running COLD benchmark (no cache)...")
        cold_start = time.perf_counter()
        
        for params_dict in params_list:
            engine = scenario_engine_factory(params_dict)
            cached_engine = CachedScenarioEngine(cache_engine)
            cached_engine.generate_with_cache(engine, params_dict)
        
        cold_time = time.perf_counter() - cold_start
        logger.info(f"✅ Cold run: {cold_time:.2f}s")
        
        # WARM RUN
        logger.info(f"🔥 Running WARM benchmark ({num_iterations} iterations with cache)...")
        warm_times = []
        
        for iteration in range(num_iterations):
            warm_start = time.perf_counter()
            
            for params_dict in params_list:
                engine = scenario_engine_factory(params_dict)
                cached_engine = CachedScenarioEngine(cache_engine)
                cached_engine.generate_with_cache(engine, params_dict)
            
            warm_time = time.perf_counter() - warm_start
            warm_times.append(warm_time)
            logger.info(f"   Iteration {iteration + 1}/{num_iterations}: {warm_time:.2f}s")
        
        avg_warm_time = sum(warm_times) / len(warm_times)
        logger.info(f"✅ Warm run (avg): {avg_warm_time:.2f}s")
        
        # Calculate speedup
        speedup_factor = cold_time / avg_warm_time
        speedup_percent = ((cold_time - avg_warm_time) / cold_time) * 100
        
        logger.info(f"🚀 Speedup: {speedup_factor:.2f}x ({speedup_percent:.1f}% faster)")
        logger.info(f"📊 Cache hit rate: {cache_engine.metrics.hit_rate:.1f}%")
        
        return CacheBenchmarkResult(
            cold_run_time_s=cold_time,
            warm_run_time_s=avg_warm_time,
            speedup_factor=speedup_factor,
            speedup_percent=speedup_percent,
            cache_hit_rate=cache_engine.metrics.hit_rate,
            num_scenarios=len(params_list)
        )


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("PHASE 9 — CACHE ENGINE TEST")
    logger.info("=" * 80)
    
    # Initialize cache engine
    cache = CacheEngine(
        cache_dir="outputs/phase9_cache",
        max_cache_size=100,
        default_ttl_hours=24.0,
        enable_disk_cache=True
    )
    
    # Test 1: Deterministic ID generation
    logger.info("\n🔍 Test 1: Deterministic ID Generation")
    
    params1 = {
        "tickers": ["SPY", "QQQ", "IWM"],
        "num_simulations": 1000,
        "num_days": 252,
        "random_seed": 42,
        "mean_return": 0.0003,
        "volatility": 0.015
    }
    
    id1 = DeterministicIDGenerator.generate_id(params1)
    id2 = DeterministicIDGenerator.generate_id(params1)  # Same params
    
    logger.info(f"   ID 1: {id1}")
    logger.info(f"   ID 2: {id2}")
    logger.info(f"   Match: {id1 == id2}")
    
    # Test 2: Cache put/get
    logger.info("\n💾 Test 2: Cache Operations")
    
    # Store scenario
    scenario_data = {"test": "data", "timestamp": datetime.now().isoformat()}
    scenario_id = cache.put(params1, scenario_data)
    logger.info(f"   Stored scenario: {scenario_id}")
    
    # Retrieve scenario
    retrieved = cache.get(params1)
    logger.info(f"   Retrieved: {retrieved is not None}")
    logger.info(f"   Data match: {retrieved == scenario_data}")
    
    # Test 3: Cache miss
    params2 = {**params1, "num_simulations": 500}  # Different params
    missed = cache.get(params2)
    logger.info(f"   Cache miss test: {missed is None}")
    
    # Test 4: Metrics
    logger.info("\n📊 Test 4: Cache Metrics")
    metrics = cache.get_metrics()
    logger.info(f"   Total requests: {metrics.total_requests}")
    logger.info(f"   Cache hits: {metrics.cache_hits}")
    logger.info(f"   Cache misses: {metrics.cache_misses}")
    logger.info(f"   Hit rate: {metrics.hit_rate:.1f}%")
    logger.info(f"   Avg lookup time: {metrics.avg_lookup_time_ms:.2f}ms")
    
    # Save metrics
    cache.save_metrics("outputs/phase9_cache/cache_metrics_test.json")
    
    # Test 5: Cache info
    logger.info("\n📋 Test 5: Cache Info")
    info = cache.get_cache_info()
    logger.info(f"   Entries: {info['num_entries']}")
    logger.info(f"   Total size: {info['total_size_mb']} MB")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ CACHE ENGINE TESTS COMPLETE")
    logger.info("=" * 80)
