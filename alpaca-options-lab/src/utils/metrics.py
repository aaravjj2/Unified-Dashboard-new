"""
Alpaca Options Lab - Metrics Module

Production-grade metrics collection with Prometheus export.
Provides latency histograms, counters, and gauges for observability.

Usage:
    from src.utils.metrics import (
        MetricsCollector,
        track_latency,
        increment_counter,
        set_gauge,
    )
    
    # Use decorator for automatic latency tracking
    @track_latency("greeks_calculation")
    def calculate_greeks(option):
        ...
    
    # Manual metric updates
    increment_counter("orders_placed", labels={"symbol": "AAPL"})
    set_gauge("portfolio_delta", value=150.5)
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class HistogramBucket:
    """Histogram bucket for latency tracking."""
    le: float  # Less than or equal to
    count: int = 0


@dataclass
class Histogram:
    """Histogram metric for latency distribution."""
    name: str
    help_text: str
    buckets: List[HistogramBucket] = field(default_factory=list)
    sum_value: float = 0.0
    count: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)
    
    def __post_init__(self) -> None:
        if not self.buckets:
            # Default latency buckets in seconds
            default_bounds = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            self.buckets = [HistogramBucket(le=b) for b in default_bounds]
            self.buckets.append(HistogramBucket(le=float('inf')))
    
    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self.sum_value += value
            self.count += 1
            for bucket in self.buckets:
                if value <= bucket.le:
                    bucket.count += 1
    
    def get_percentile(self, percentile: float) -> float:
        """Estimate percentile value from histogram."""
        if self.count == 0:
            return 0.0
        
        target_count = self.count * (percentile / 100.0)
        prev_count = 0
        prev_bound = 0.0
        
        for bucket in self.buckets:
            if bucket.count >= target_count:
                # Linear interpolation within bucket
                if bucket.count == prev_count:
                    return bucket.le
                ratio = (target_count - prev_count) / (bucket.count - prev_count)
                return prev_bound + ratio * (bucket.le - prev_bound)
            prev_count = bucket.count
            prev_bound = bucket.le
        
        return self.buckets[-1].le


@dataclass
class Counter:
    """Counter metric that only increases."""
    name: str
    help_text: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter."""
        if amount < 0:
            raise ValueError("Counter can only be incremented")
        with self._lock:
            self.value += amount


@dataclass
class Gauge:
    """Gauge metric that can increase or decrease."""
    name: str
    help_text: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)
    
    def set(self, value: float) -> None:
        """Set the gauge value."""
        with self._lock:
            self.value = value
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge."""
        with self._lock:
            self.value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        with self._lock:
            self.value -= amount


class MetricsCollector:
    """
    Centralized metrics collection and export.
    
    Provides:
    - Latency histograms with percentile calculations
    - Counters for event counting
    - Gauges for current-state metrics
    - Prometheus-compatible export format
    """
    
    _instance: Optional["MetricsCollector"] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> "MetricsCollector":
        """Singleton pattern for global metrics access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._histograms: Dict[str, Histogram] = {}
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._metrics_lock = Lock()
        self._initialized = True
        
        # Register default metrics
        self._register_defaults()
    
    def _register_defaults(self) -> None:
        """Register default application metrics."""
        # Latency histograms
        self.register_histogram("greeks_calculation_seconds", "Greeks calculation latency")
        self.register_histogram("db_query_seconds", "Database query latency")
        self.register_histogram("feed_handler_seconds", "Market data processing latency")
        self.register_histogram("iv_solver_seconds", "Implied volatility solver latency")
        self.register_histogram("backtest_step_seconds", "Backtest step latency")
        
        # Counters
        self.register_counter("market_data_messages_total", "Total market data messages received")
        self.register_counter("orders_placed_total", "Total orders placed")
        self.register_counter("cache_hits_total", "Total cache hits")
        self.register_counter("cache_misses_total", "Total cache misses")
        self.register_counter("errors_total", "Total errors encountered")
        
        # Gauges
        self.register_gauge("portfolio_delta", "Current portfolio delta")
        self.register_gauge("portfolio_gamma", "Current portfolio gamma")
        self.register_gauge("portfolio_theta", "Current portfolio theta")
        self.register_gauge("portfolio_vega", "Current portfolio vega")
        self.register_gauge("open_positions", "Number of open positions")
        self.register_gauge("margin_utilization", "Current margin utilization ratio")
        self.register_gauge("cache_size", "Current cache size")
        self.register_gauge("websocket_connections", "Active WebSocket connections")
    
    def register_histogram(
        self,
        name: str,
        help_text: str,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """Register a new histogram metric."""
        with self._metrics_lock:
            if name not in self._histograms:
                bucket_list = None
                if buckets:
                    bucket_list = [HistogramBucket(le=b) for b in buckets]
                    bucket_list.append(HistogramBucket(le=float('inf')))
                self._histograms[name] = Histogram(
                    name=name,
                    help_text=help_text,
                    buckets=bucket_list or [],
                )
            return self._histograms[name]
    
    def register_counter(
        self,
        name: str,
        help_text: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Counter:
        """Register a new counter metric."""
        with self._metrics_lock:
            if name not in self._counters:
                self._counters[name] = Counter(
                    name=name,
                    help_text=help_text,
                    labels=labels or {},
                )
            return self._counters[name]
    
    def register_gauge(
        self,
        name: str,
        help_text: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Gauge:
        """Register a new gauge metric."""
        with self._metrics_lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(
                    name=name,
                    help_text=help_text,
                    labels=labels or {},
                )
            return self._gauges[name]
    
    def observe_histogram(self, name: str, value: float) -> None:
        """Record a histogram observation."""
        if name in self._histograms:
            self._histograms[name].observe(value)
    
    def increment_counter(self, name: str, amount: float = 1.0) -> None:
        """Increment a counter."""
        if name in self._counters:
            self._counters[name].inc(amount)
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        if name in self._gauges:
            self._gauges[name].set(value)
    
    def get_histogram_p99(self, name: str) -> float:
        """Get P99 latency for a histogram."""
        if name in self._histograms:
            return self._histograms[name].get_percentile(99)
        return 0.0
    
    def get_histogram_p50(self, name: str) -> float:
        """Get P50 (median) latency for a histogram."""
        if name in self._histograms:
            return self._histograms[name].get_percentile(50)
        return 0.0
    
    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines: List[str] = []
        
        # Export histograms
        for name, hist in self._histograms.items():
            lines.append(f"# HELP {name} {hist.help_text}")
            lines.append(f"# TYPE {name} histogram")
            for bucket in hist.buckets:
                le = "+Inf" if bucket.le == float('inf') else str(bucket.le)
                lines.append(f'{name}_bucket{{le="{le}"}} {bucket.count}')
            lines.append(f"{name}_sum {hist.sum_value}")
            lines.append(f"{name}_count {hist.count}")
        
        # Export counters
        for name, counter in self._counters.items():
            lines.append(f"# HELP {name} {counter.help_text}")
            lines.append(f"# TYPE {name} counter")
            labels_str = ",".join(f'{k}="{v}"' for k, v in counter.labels.items())
            if labels_str:
                lines.append(f"{name}{{{labels_str}}} {counter.value}")
            else:
                lines.append(f"{name} {counter.value}")
        
        # Export gauges
        for name, gauge in self._gauges.items():
            lines.append(f"# HELP {name} {gauge.help_text}")
            lines.append(f"# TYPE {name} gauge")
            labels_str = ",".join(f'{k}="{v}"' for k, v in gauge.labels.items())
            if labels_str:
                lines.append(f"{name}{{{labels_str}}} {gauge.value}")
            else:
                lines.append(f"{name} {gauge.value}")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary for debugging."""
        return {
            "histograms": {
                name: {
                    "count": h.count,
                    "sum": h.sum_value,
                    "p50": h.get_percentile(50),
                    "p99": h.get_percentile(99),
                }
                for name, h in self._histograms.items()
            },
            "counters": {name: c.value for name, c in self._counters.items()},
            "gauges": {name: g.value for name, g in self._gauges.items()},
        }


# Global metrics instance
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics


@contextmanager
def measure_latency(metric_name: str) -> Generator[None, None, None]:
    """Context manager to measure and record latency."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _metrics.observe_histogram(metric_name, elapsed)


def track_latency(metric_name: str) -> Callable[[F], F]:
    """Decorator to track function latency."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with measure_latency(metric_name):
                return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def increment_counter(name: str, amount: float = 1.0) -> None:
    """Increment a counter metric."""
    _metrics.increment_counter(name, amount)


def set_gauge(name: str, value: float) -> None:
    """Set a gauge metric value."""
    _metrics.set_gauge(name, value)
