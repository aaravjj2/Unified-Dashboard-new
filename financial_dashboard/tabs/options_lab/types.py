"""
Type definitions for Options Lab module.

Provides type hints and TypedDicts for better code clarity.
"""

from typing import TypedDict, List, Dict, Optional, Any, Union
from datetime import datetime
import pandas as pd


class OptionContract(TypedDict, total=False):
    """Single option contract data."""
    strike: float
    lastPrice: float
    bid: float
    ask: float
    change: float
    percentChange: float
    volume: int
    openInterest: int
    impliedVolatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    inTheMoney: bool


class OptionChain(TypedDict):
    """Options chain for a single expiration."""
    calls: Union[List[OptionContract], pd.DataFrame]
    puts: Union[List[OptionContract], pd.DataFrame]


class ChainData(TypedDict):
    """Full options chain data structure."""
    ticker: str
    spot_price: float
    expirations: List[str]
    timestamp: str
    chains: Dict[str, OptionChain]
    source: str


class CacheEntry(TypedDict):
    """Cache entry structure."""
    data: Any
    timestamp: float
    ttl: int
    hits: int


class CacheStats(TypedDict):
    """Cache statistics."""
    hits: int
    misses: int
    evictions: int
    size: int
    hit_rate: str


class CircuitBreakerStats(TypedDict):
    """Circuit breaker statistics."""
    state: str
    failures: int
    successes: int
    total_calls: int
    rejected_calls: int
    last_failure: Optional[float]
    last_success: Optional[float]


class AlpacaMetrics(TypedDict):
    """Alpaca client metrics."""
    api_calls: int
    cache_hits: int
    cache_misses: int
    errors: int
    avg_fetch_time_ms: float
    total_fetch_time_ms: float
    cache_stats: CacheStats


class ExportResult(TypedDict):
    """Export result for dcc.Download."""
    content: str
    filename: str
    type: str


class HealthCheckResult(TypedDict):
    """Health check response."""
    status: str
    service: str
    timestamp: str
    checks: Optional[Dict[str, Any]]


# Type aliases for common patterns
Ticker = str
ExpirationDate = str
StrikePrice = float
Greeks = Dict[str, float]
