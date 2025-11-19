"""
Phase 6 — Cache Optimization Configuration
===========================================

Optimizes Phase 3.5 CacheRouter for Phase 6 Azure ML workloads:
- Batch SHAP explanations (large portfolios, 10+ tickers)
- Options chains (less frequently changing, higher TTL)
- Feature vectors (deterministic, highly cacheable)

Provides tuned L1/L2/L3 configuration for:
- Maximum cache hit rate (95%+ target)
- Minimal latency (<50ms L1, <100ms L2)
- Deterministic reproducibility (SHA256 keys)

Author: Agent 1A — Unified Financial Dashboard Team
Version: 1.0 (Phase 6 — Task 4)
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import timedelta

logger = logging.getLogger(__name__)


# ============================================================================
# CACHE TIER CONFIGURATIONS
# ============================================================================

@dataclass
class L1CacheConfig:
    """
    L1 (In-Memory LRU) Configuration for Phase 6.
    
    Tuned for batch SHAP workloads with multiple tickers.
    Phase 3.5 baseline: 100 items, <1ms latency
    Phase 6 optimized: 200 items to accommodate batch SHAP
    
    Rationale:
    - Batch SHAP for 10 tickers = 10 SHAP results + 10 feature vectors = 20 cache entries
    - Portfolio SHAP + single ticker SHAP = 2x cache needs
    - 200 items provides 10x portfolio capacity (100 tickers)
    """
    max_size: int = 200  # Increased from 100
    eviction_policy: str = "lru"  # Least Recently Used
    ttl_seconds: Optional[int] = None  # No TTL for L1 (size-based eviction only)
    
    # Performance targets
    target_latency_ms: float = 1.0  # <1ms
    target_hit_rate_pct: float = 85.0  # 85%+ for hot data
    
    def __post_init__(self):
        logger.info(f"L1 Cache Config: max_size={self.max_size}, policy={self.eviction_policy}")


@dataclass
class L2CacheConfig:
    """
    L2 (Disk/Redis) Configuration for Phase 6.
    
    Tuned for options chains and feature vectors with longer TTL.
    Phase 3.5 baseline: 24h TTL, 10-50ms latency
    Phase 6 optimized: 7-day TTL for options, 48h for SHAP
    
    Rationale:
    - Options chains change less frequently (daily at most)
    - SHAP feature vectors are deterministic (can cache longer)
    - 7-day TTL balances freshness vs cache efficiency
    """
    ttl_shap_seconds: int = 48 * 3600  # 48 hours for SHAP results
    ttl_options_seconds: int = 7 * 24 * 3600  # 7 days for options chains
    ttl_features_seconds: int = 30 * 24 * 3600  # 30 days for feature vectors (deterministic)
    
    # Performance targets
    target_latency_ms: float = 50.0  # <50ms
    target_hit_rate_pct: float = 75.0  # 75%+ for warm data
    
    def __post_init__(self):
        logger.info(
            f"L2 Cache Config: TTL SHAP={self.ttl_shap_seconds}s, "
            f"Options={self.ttl_options_seconds}s, Features={self.ttl_features_seconds}s"
        )


@dataclass
class L3CacheConfig:
    """
    L3 (Cloud Storage) Configuration for Phase 6.
    
    Phase 3.5 baseline: Stub implementation, no active caching
    Phase 6: Remains stub, fallback to Azure ML endpoints
    
    Future enhancements:
    - S3/Azure Blob Storage for historical SHAP results
    - Long-term options chain archives
    - Model versioning and A/B test caching
    """
    enabled: bool = False  # Stub mode
    target_latency_ms: float = 500.0  # <500ms (not critical)
    
    def __post_init__(self):
        if self.enabled:
            logger.info("L3 Cache Config: Enabled (cloud storage)")
        else:
            logger.info("L3 Cache Config: Disabled (stub mode)")


@dataclass
class Phase6CacheConfig:
    """
    Complete Phase 6 cache configuration bundle.
    
    Combines L1/L2/L3 settings with cache key generation strategies.
    """
    l1: L1CacheConfig
    l2: L2CacheConfig
    l3: L3CacheConfig
    
    # Cache invalidation settings
    invalidate_on_model_update: bool = True  # Clear SHAP cache when model changes
    invalidate_on_market_open: bool = False  # Don't invalidate options on market open (too frequent)
    
    # Telemetry settings
    enable_telemetry: bool = True  # Track hit rates, latency, key counts
    telemetry_log_interval_seconds: int = 300  # Log stats every 5 minutes
    
    @classmethod
    def create_default(cls) -> "Phase6CacheConfig":
        """Create default Phase 6 optimized configuration."""
        return cls(
            l1=L1CacheConfig(),
            l2=L2CacheConfig(),
            l3=L3CacheConfig()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging/debugging."""
        return {
            "l1": {
                "max_size": self.l1.max_size,
                "eviction_policy": self.l1.eviction_policy,
                "ttl_seconds": self.l1.ttl_seconds,
                "target_latency_ms": self.l1.target_latency_ms,
                "target_hit_rate_pct": self.l1.target_hit_rate_pct
            },
            "l2": {
                "ttl_shap_seconds": self.l2.ttl_shap_seconds,
                "ttl_options_seconds": self.l2.ttl_options_seconds,
                "ttl_features_seconds": self.l2.ttl_features_seconds,
                "target_latency_ms": self.l2.target_latency_ms,
                "target_hit_rate_pct": self.l2.target_hit_rate_pct
            },
            "l3": {
                "enabled": self.l3.enabled,
                "target_latency_ms": self.l3.target_latency_ms
            },
            "invalidation": {
                "invalidate_on_model_update": self.invalidate_on_model_update,
                "invalidate_on_market_open": self.invalidate_on_market_open
            },
            "telemetry": {
                "enable_telemetry": self.enable_telemetry,
                "telemetry_log_interval_seconds": self.telemetry_log_interval_seconds
            }
        }


# ============================================================================
# CACHE KEY GENERATION STRATEGIES
# ============================================================================

class Phase6CacheKeyGenerator:
    """
    Deterministic cache key generation for Phase 6 Azure ML operations.
    
    Uses SHA256 hashing to ensure:
    - Reproducibility: Same inputs → same keys
    - Uniqueness: Different inputs → different keys
    - Collision resistance: Vanishingly small chance of duplicates
    
    Key formats:
    - SHAP: "shap_v1_{ticker}_{features_hash}_{model_version}"
    - Options: "options_v1_{ticker}_{expiration}_{current_price_bucket}"
    - Features: "features_v1_{ticker}_{date}_{feature_set_hash}"
    """
    
    VERSION = "v1"  # Cache format version (bump to invalidate all keys)
    
    @staticmethod
    def generate_shap_key(ticker: str, features: Dict[str, float], model_version: str = "1.0") -> str:
        """
        Generate cache key for SHAP explanation.
        
        Args:
            ticker: Stock ticker (e.g., "AAPL")
            features: Feature vector (28 features)
            model_version: Azure ML model version
        
        Returns:
            Cache key: "shap_v1_AAPL_{hash}_{model}"
        
        Example:
            >>> gen = Phase6CacheKeyGenerator()
            >>> features = {"rsi": 0.65, "macd": 0.02, ...}
            >>> gen.generate_shap_key("AAPL", features, "1.0")
            'shap_v1_AAPL_a3f5b2c..._1.0'
        """
        # Sort features for deterministic hash
        features_json = json.dumps(features, sort_keys=True)
        features_hash = hashlib.sha256(features_json.encode()).hexdigest()[:12]
        
        return f"shap_{Phase6CacheKeyGenerator.VERSION}_{ticker}_{features_hash}_{model_version}"
    
    @staticmethod
    def generate_options_key(ticker: str, expiration_days: int, current_price: float) -> str:
        """
        Generate cache key for options chain.
        
        Args:
            ticker: Stock ticker
            expiration_days: Days until expiration (7, 30, 90)
            current_price: Current stock price (bucketed to reduce key proliferation)
        
        Returns:
            Cache key: "options_v1_AAPL_30_{price_bucket}"
        
        Example:
            >>> gen = Phase6CacheKeyGenerator()
            >>> gen.generate_options_key("AAPL", 30, 182.45)
            'options_v1_AAPL_30_180'
        
        Note:
            Price is bucketed to nearest $5 to improve cache hit rate
            (182.45 → 180, 184.99 → 185)
        """
        # Bucket price to nearest $5 for cache efficiency
        price_bucket = int(round(current_price / 5.0) * 5)
        
        return f"options_{Phase6CacheKeyGenerator.VERSION}_{ticker}_{expiration_days}_{price_bucket}"
    
    @staticmethod
    def generate_features_key(ticker: str, date: str, feature_names: List[str]) -> str:
        """
        Generate cache key for feature vector.
        
        Args:
            ticker: Stock ticker
            date: Feature date (YYYY-MM-DD)
            feature_names: List of feature names (for hash)
        
        Returns:
            Cache key: "features_v1_AAPL_2025-10-29_{hash}"
        
        Example:
            >>> gen = Phase6CacheKeyGenerator()
            >>> features = ["rsi", "macd", "volume_ratio", ...]
            >>> gen.generate_features_key("AAPL", "2025-10-29", features)
            'features_v1_AAPL_2025-10-29_7a8f3e1'
        """
        # Hash feature names for deterministic key
        features_str = ",".join(sorted(feature_names))
        features_hash = hashlib.sha256(features_str.encode()).hexdigest()[:8]
        
        return f"features_{Phase6CacheKeyGenerator.VERSION}_{ticker}_{date}_{features_hash}"
    
    @staticmethod
    def generate_batch_shap_key(tickers: List[str], model_version: str = "1.0") -> str:
        """
        Generate cache key for batch SHAP result.
        
        Args:
            tickers: List of tickers in batch
            model_version: Azure ML model version
        
        Returns:
            Cache key: "batch_shap_v1_{tickers_hash}_{model}"
        
        Example:
            >>> gen = Phase6CacheKeyGenerator()
            >>> gen.generate_batch_shap_key(["AAPL", "TSLA", "NVDA"], "1.0")
            'batch_shap_v1_3f8a2c1_1.0'
        """
        # Sort tickers for deterministic hash
        tickers_str = ",".join(sorted(tickers))
        tickers_hash = hashlib.sha256(tickers_str.encode()).hexdigest()[:8]
        
        return f"batch_shap_{Phase6CacheKeyGenerator.VERSION}_{tickers_hash}_{model_version}"


# ============================================================================
# CACHE INVALIDATION POLICIES
# ============================================================================

class Phase6CacheInvalidator:
    """
    Cache invalidation logic for Phase 6 workloads.
    
    Handles:
    - Model version updates (invalidate all SHAP caches)
    - Market data refresh (selective invalidation)
    - Manual cache clearing (debugging, testing)
    """
    
    def __init__(self, cache_router):
        """
        Initialize invalidator with Phase 3.5 CacheRouter.
        
        Args:
            cache_router: Phase 3.5 CacheRouter instance (from data_integrity_bridge)
        """
        self.cache_router = cache_router
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def invalidate_shap_cache(self, ticker: Optional[str] = None) -> int:
        """
        Invalidate SHAP cache entries.
        
        Args:
            ticker: Specific ticker to invalidate (None = all tickers)
        
        Returns:
            Number of keys invalidated
        
        Example:
            >>> invalidator.invalidate_shap_cache("AAPL")  # Clear AAPL SHAP only
            3
            >>> invalidator.invalidate_shap_cache()  # Clear all SHAP
            47
        """
        # Phase 3.5 CacheRouter doesn't expose key listing, so we use prefix-based clearing
        prefix = f"shap_{Phase6CacheKeyGenerator.VERSION}"
        if ticker:
            prefix += f"_{ticker}"
        
        self.logger.info(f"Invalidating SHAP cache with prefix: {prefix}")
        
        # NOTE: Phase 3.5 CacheRouter API doesn't support prefix deletion
        # This is a stub implementation - real implementation would iterate L1/L2/L3
        # and delete matching keys
        
        # For now, log and return 0 (manual cache clearing required)
        self.logger.warning("Cache invalidation not fully implemented - requires Phase 3.5 API extension")
        return 0
    
    def invalidate_options_cache(self, ticker: Optional[str] = None) -> int:
        """
        Invalidate options chain cache entries.
        
        Args:
            ticker: Specific ticker to invalidate (None = all tickers)
        
        Returns:
            Number of keys invalidated
        """
        prefix = f"options_{Phase6CacheKeyGenerator.VERSION}"
        if ticker:
            prefix += f"_{ticker}"
        
        self.logger.info(f"Invalidating options cache with prefix: {prefix}")
        self.logger.warning("Cache invalidation not fully implemented - requires Phase 3.5 API extension")
        return 0
    
    def invalidate_all_phase6_caches(self) -> int:
        """
        Nuclear option: Clear ALL Phase 6 caches (SHAP + options + features).
        
        Use cases:
        - Major model update
        - Data quality issues detected
        - Testing/debugging
        
        Returns:
            Total keys invalidated
        """
        self.logger.warning("Clearing ALL Phase 6 caches (SHAP + options + features)")
        
        total = 0
        total += self.invalidate_shap_cache()
        total += self.invalidate_options_cache()
        
        self.logger.info(f"Cleared {total} Phase 6 cache entries")
        return total


# ============================================================================
# TELEMETRY & MONITORING
# ============================================================================

@dataclass
class CacheTelemetry:
    """
    Cache performance telemetry for Phase 6 operations.
    
    Tracks:
    - Hit rates (L1/L2/L3)
    - Latencies (p50, p95, p99)
    - Key counts
    - Eviction rates
    """
    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    l3_hits: int = 0
    l3_misses: int = 0
    
    total_requests: int = 0
    total_latency_ms: float = 0.0
    
    def get_hit_rate(self, tier: str = "all") -> float:
        """
        Calculate cache hit rate percentage.
        
        Args:
            tier: "l1", "l2", "l3", or "all"
        
        Returns:
            Hit rate percentage (0-100)
        
        Example:
            >>> telemetry.get_hit_rate("l1")
            87.3
            >>> telemetry.get_hit_rate("all")
            92.5
        """
        if tier == "l1":
            total = self.l1_hits + self.l1_misses
            return (self.l1_hits / total * 100.0) if total > 0 else 0.0
        
        elif tier == "l2":
            total = self.l2_hits + self.l2_misses
            return (self.l2_hits / total * 100.0) if total > 0 else 0.0
        
        elif tier == "l3":
            total = self.l3_hits + self.l3_misses
            return (self.l3_hits / total * 100.0) if total > 0 else 0.0
        
        else:  # "all"
            total_hits = self.l1_hits + self.l2_hits + self.l3_hits
            total_requests = self.l1_hits + self.l1_misses + self.l2_hits + self.l2_misses + self.l3_hits + self.l3_misses
            return (total_hits / total_requests * 100.0) if total_requests > 0 else 0.0
    
    def get_avg_latency_ms(self) -> float:
        """Calculate average latency across all requests."""
        return (self.total_latency_ms / self.total_requests) if self.total_requests > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "l1": {
                "hits": self.l1_hits,
                "misses": self.l1_misses,
                "hit_rate_pct": self.get_hit_rate("l1")
            },
            "l2": {
                "hits": self.l2_hits,
                "misses": self.l2_misses,
                "hit_rate_pct": self.get_hit_rate("l2")
            },
            "l3": {
                "hits": self.l3_hits,
                "misses": self.l3_misses,
                "hit_rate_pct": self.get_hit_rate("l3")
            },
            "overall": {
                "total_requests": self.total_requests,
                "hit_rate_pct": self.get_hit_rate("all"),
                "avg_latency_ms": self.get_avg_latency_ms()
            }
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_phase6_cache_config() -> Phase6CacheConfig:
    """
    Create default Phase 6 cache configuration.
    
    Returns:
        Phase6CacheConfig with optimized L1/L2/L3 settings
    
    Example:
        >>> config = create_phase6_cache_config()
        >>> config.l1.max_size
        200
        >>> config.l2.ttl_options_seconds
        604800  # 7 days
    """
    return Phase6CacheConfig.create_default()


def create_cache_key_generator() -> Phase6CacheKeyGenerator:
    """
    Create cache key generator instance.
    
    Returns:
        Phase6CacheKeyGenerator (stateless, can be reused)
    """
    return Phase6CacheKeyGenerator()


def create_cache_invalidator(cache_router) -> Phase6CacheInvalidator:
    """
    Create cache invalidator with Phase 3.5 CacheRouter.
    
    Args:
        cache_router: Phase 3.5 CacheRouter instance
    
    Returns:
        Phase6CacheInvalidator
    
    Example:
        >>> from financial_dashboard.tabs.azure_ml_lab.phase3_5_contracts.data_integrity_bridge import create_cache_router
        >>> router = create_cache_router()
        >>> invalidator = create_cache_invalidator(router)
        >>> invalidator.invalidate_shap_cache("AAPL")
    """
    return Phase6CacheInvalidator(cache_router)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Configuration classes
    "L1CacheConfig",
    "L2CacheConfig",
    "L3CacheConfig",
    "Phase6CacheConfig",
    
    # Key generation
    "Phase6CacheKeyGenerator",
    
    # Invalidation
    "Phase6CacheInvalidator",
    
    # Telemetry
    "CacheTelemetry",
    
    # Factory functions
    "create_phase6_cache_config",
    "create_cache_key_generator",
    "create_cache_invalidator"
]


# ============================================================================
# USAGE EXAMPLES (FOR DOCUMENTATION)
# ============================================================================

if __name__ == "__main__":
    # Example 1: Create optimized cache configuration
    config = create_phase6_cache_config()
    print("Phase 6 Cache Configuration:")
    print(json.dumps(config.to_dict(), indent=2))
    
    # Example 2: Generate cache keys
    keygen = create_cache_key_generator()
    
    shap_key = keygen.generate_shap_key(
        ticker="AAPL",
        features={"rsi": 0.65, "macd": 0.02, "volume_ratio": 1.2},
        model_version="1.0"
    )
    print(f"\nSHAP Cache Key: {shap_key}")
    
    options_key = keygen.generate_options_key(
        ticker="AAPL",
        expiration_days=30,
        current_price=182.45
    )
    print(f"Options Cache Key: {options_key}")
    
    batch_key = keygen.generate_batch_shap_key(
        tickers=["AAPL", "TSLA", "NVDA"],
        model_version="1.0"
    )
    print(f"Batch SHAP Cache Key: {batch_key}")
    
    # Example 3: Telemetry tracking
    telemetry = CacheTelemetry()
    telemetry.l1_hits = 85
    telemetry.l1_misses = 15
    telemetry.l2_hits = 12
    telemetry.l2_misses = 3
    telemetry.total_requests = 115
    telemetry.total_latency_ms = 3450.0
    
    print("\nCache Telemetry:")
    print(json.dumps(telemetry.to_dict(), indent=2))
