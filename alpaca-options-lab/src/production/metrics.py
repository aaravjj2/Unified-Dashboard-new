"""
Alpaca Options Lab - Metrics Collector

Performance metrics and monitoring:
- Counter, Gauge, Timer metrics
- Metric aggregation
- Export to various backends
- Dashboard integration
"""
from __future__ import annotations

import asyncio
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"  # Monotonically increasing
    GAUGE = "gauge"  # Can go up or down
    HISTOGRAM = "histogram"  # Distribution
    TIMER = "timer"  # Duration measurements


@dataclass
class MetricSample:
    """Single metric sample."""
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric definition."""
    name: str
    metric_type: MetricType
    description: str = ""
    unit: str = ""
    
    # Current value
    value: float = 0.0
    
    # Labels
    labels: Dict[str, str] = field(default_factory=dict)
    
    # History (for aggregations)
    samples: List[MetricSample] = field(default_factory=list)
    max_samples: int = 1000
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def record(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a value."""
        self.value = value
        self.updated_at = datetime.now(timezone.utc)
        
        sample = MetricSample(value=value, labels=labels or {})
        self.samples.append(sample)
        
        # Trim samples
        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples:]
    
    def increment(self, amount: float = 1.0) -> None:
        """Increment counter."""
        self.value += amount
        self.updated_at = datetime.now(timezone.utc)
    
    def decrement(self, amount: float = 1.0) -> None:
        """Decrement gauge."""
        self.value -= amount
        self.updated_at = datetime.now(timezone.utc)
    
    def set(self, value: float) -> None:
        """Set gauge value."""
        self.record(value)
    
    @property
    def average(self) -> float:
        """Average of recent samples."""
        if not self.samples:
            return 0.0
        return sum(s.value for s in self.samples) / len(self.samples)
    
    @property
    def minimum(self) -> float:
        """Minimum of recent samples."""
        if not self.samples:
            return 0.0
        return min(s.value for s in self.samples)
    
    @property
    def maximum(self) -> float:
        """Maximum of recent samples."""
        if not self.samples:
            return 0.0
        return max(s.value for s in self.samples)
    
    def percentile(self, p: float) -> float:
        """Calculate percentile."""
        if not self.samples:
            return 0.0
        
        sorted_values = sorted(s.value for s in self.samples)
        index = int(len(sorted_values) * p / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "description": self.description,
            "unit": self.unit,
            "labels": self.labels,
            "updated_at": self.updated_at.isoformat(),
            "samples_count": len(self.samples),
        }


class Counter:
    """Counter metric (monotonically increasing)."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ):
        self.metric = Metric(
            name=name,
            metric_type=MetricType.COUNTER,
            description=description,
            labels=labels or {},
        )
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment counter."""
        self.metric.increment(amount)
    
    @property
    def value(self) -> float:
        return self.metric.value
    
    def __repr__(self) -> str:
        return f"Counter({self.metric.name}={self.value})"


class Gauge:
    """Gauge metric (can increase or decrease)."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ):
        self.metric = Metric(
            name=name,
            metric_type=MetricType.GAUGE,
            description=description,
            labels=labels or {},
        )
    
    def set(self, value: float) -> None:
        """Set gauge value."""
        self.metric.set(value)
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge."""
        self.metric.increment(amount)
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge."""
        self.metric.decrement(amount)
    
    @property
    def value(self) -> float:
        return self.metric.value
    
    def __repr__(self) -> str:
        return f"Gauge({self.metric.name}={self.value})"


class Timer:
    """Timer metric for measuring durations."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ):
        self.metric = Metric(
            name=name,
            metric_type=MetricType.TIMER,
            description=description,
            unit="seconds",
            labels=labels or {},
        )
        self._start_time: Optional[float] = None
    
    def start(self) -> None:
        """Start timer."""
        self._start_time = time.perf_counter()
    
    def stop(self) -> float:
        """Stop timer and record duration."""
        if self._start_time is None:
            return 0.0
        
        duration = time.perf_counter() - self._start_time
        self.metric.record(duration)
        self._start_time = None
        
        return duration
    
    @contextmanager
    def time(self) -> Generator[None, None, None]:
        """Context manager for timing."""
        self.start()
        try:
            yield
        finally:
            self.stop()
    
    def record(self, duration: float) -> None:
        """Manually record a duration."""
        self.metric.record(duration)
    
    @property
    def average(self) -> float:
        return self.metric.average
    
    @property
    def p50(self) -> float:
        return self.metric.percentile(50)
    
    @property
    def p95(self) -> float:
        return self.metric.percentile(95)
    
    @property
    def p99(self) -> float:
        return self.metric.percentile(99)
    
    def __repr__(self) -> str:
        return f"Timer({self.metric.name}, avg={self.average:.4f}s)"


class Histogram:
    """Histogram for value distribution."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        self.metric = Metric(
            name=name,
            metric_type=MetricType.HISTOGRAM,
            description=description,
            labels=labels or {},
        )
        
        # Default buckets
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        self._bucket_counts: Dict[float, int] = {b: 0 for b in self.buckets}
        self._bucket_counts[float('inf')] = 0
    
    def observe(self, value: float) -> None:
        """Observe a value."""
        self.metric.record(value)
        
        # Update buckets
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[bucket] += 1
        self._bucket_counts[float('inf')] += 1
    
    def get_buckets(self) -> Dict[float, int]:
        """Get bucket counts."""
        return dict(self._bucket_counts)
    
    @property
    def count(self) -> int:
        return self._bucket_counts[float('inf')]
    
    @property
    def sum(self) -> float:
        return sum(s.value for s in self.metric.samples)


class MetricsCollector:
    """
    Central metrics collection and management.
    
    Features:
    - Metric registration
    - Aggregation
    - Export formats (Prometheus, JSON)
    - Dashboard integration
    """
    
    def __init__(self):
        # Metrics storage
        self._metrics: Dict[str, Metric] = {}
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._timers: Dict[str, Timer] = {}
        self._histograms: Dict[str, Histogram] = {}
        
        # Collection interval
        self._collection_task: Optional[asyncio.Task] = None
        self._collection_interval = 60  # seconds
        
        # Exporters
        self._exporters: List[Callable] = []
        
        logger.info("MetricsCollector initialized")
    
    # -------------------- Metric Creation --------------------
    
    def counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Counter:
        """Create or get a counter."""
        if name not in self._counters:
            self._counters[name] = Counter(name, description, labels)
            self._metrics[name] = self._counters[name].metric
        return self._counters[name]
    
    def gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Gauge:
        """Create or get a gauge."""
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, description, labels)
            self._metrics[name] = self._gauges[name].metric
        return self._gauges[name]
    
    def timer(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Timer:
        """Create or get a timer."""
        if name not in self._timers:
            self._timers[name] = Timer(name, description, labels)
            self._metrics[name] = self._timers[name].metric
        return self._timers[name]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> Histogram:
        """Create or get a histogram."""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, description, buckets, labels)
            self._metrics[name] = self._histograms[name].metric
        return self._histograms[name]
    
    # -------------------- Access --------------------
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name."""
        return self._metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all metrics."""
        return dict(self._metrics)
    
    # -------------------- Export --------------------
    
    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for name, metric in self._metrics.items():
            # Help and type
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} {metric.metric_type.value}")
            
            # Labels
            if metric.labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                lines.append(f"{name}{{{label_str}}} {metric.value}")
            else:
                lines.append(f"{name} {metric.value}")
        
        return "\n".join(lines)
    
    def to_json(self) -> Dict[str, Any]:
        """Export metrics as JSON."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                name: metric.to_dict()
                for name, metric in self._metrics.items()
            },
            "summary": self.get_summary(),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_metrics": len(self._metrics),
            "counters": len(self._counters),
            "gauges": len(self._gauges),
            "timers": len(self._timers),
            "histograms": len(self._histograms),
        }
    
    # -------------------- Collection --------------------
    
    async def start_collection(self, interval: int = 60) -> None:
        """Start periodic metric collection."""
        self._collection_interval = interval
        
        if self._collection_task is None or self._collection_task.done():
            self._collection_task = asyncio.create_task(self._collection_loop())
            logger.info(f"Metrics collection started (interval: {interval}s)")
    
    async def stop_collection(self) -> None:
        """Stop metric collection."""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            logger.info("Metrics collection stopped")
    
    async def _collection_loop(self) -> None:
        """Background collection loop."""
        while True:
            try:
                # Export to registered exporters
                await self._export()
                await asyncio.sleep(self._collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Collection error: {e}")
                await asyncio.sleep(self._collection_interval)
    
    async def _export(self) -> None:
        """Export metrics to all registered exporters."""
        data = self.to_json()
        
        for exporter in self._exporters:
            try:
                if asyncio.iscoroutinefunction(exporter):
                    await exporter(data)
                else:
                    exporter(data)
            except Exception as e:
                logger.error(f"Export error: {e}")
    
    def register_exporter(self, exporter: Callable) -> None:
        """Register a metrics exporter."""
        self._exporters.append(exporter)
    
    # -------------------- Utilities --------------------
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()
        self._histograms.clear()
        logger.info("Metrics reset")


# Singleton instance
_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


# -------------------- Pre-defined Trading Metrics --------------------

def create_trading_metrics(collector: MetricsCollector) -> Dict[str, Any]:
    """Create standard trading metrics."""
    return {
        # Order metrics
        "orders_submitted": collector.counter(
            "orders_submitted_total",
            "Total orders submitted",
        ),
        "orders_filled": collector.counter(
            "orders_filled_total",
            "Total orders filled",
        ),
        "orders_rejected": collector.counter(
            "orders_rejected_total",
            "Total orders rejected",
        ),
        "order_latency": collector.timer(
            "order_latency_seconds",
            "Order submission latency",
        ),
        
        # Position metrics
        "open_positions": collector.gauge(
            "open_positions",
            "Current open positions",
        ),
        "portfolio_value": collector.gauge(
            "portfolio_value_dollars",
            "Current portfolio value",
        ),
        
        # P&L metrics
        "realized_pnl": collector.gauge(
            "realized_pnl_dollars",
            "Realized P&L",
        ),
        "unrealized_pnl": collector.gauge(
            "unrealized_pnl_dollars",
            "Unrealized P&L",
        ),
        
        # Risk metrics
        "daily_pnl": collector.gauge(
            "daily_pnl_dollars",
            "Daily P&L",
        ),
        "max_drawdown": collector.gauge(
            "max_drawdown_percent",
            "Maximum drawdown percentage",
        ),
        
        # API metrics
        "api_requests": collector.counter(
            "api_requests_total",
            "Total API requests",
        ),
        "api_errors": collector.counter(
            "api_errors_total",
            "Total API errors",
        ),
        "api_latency": collector.histogram(
            "api_latency_seconds",
            "API request latency",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
        ),
    }
