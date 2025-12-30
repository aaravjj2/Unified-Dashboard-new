"""
Data Fetcher - Real-time data feed management with latency tracking.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any, List, Callable
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class FeedStatus(Enum):
    """Data feed status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STALE = "stale"
    ERROR = "error"


@dataclass
class FeedLatencySample:
    """Single latency measurement."""
    timestamp: datetime
    latency_ms: float
    feed_name: str


@dataclass
class FeedMetrics:
    """Aggregated metrics for a data feed."""
    feed_name: str
    status: FeedStatus
    last_update: Optional[datetime]
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    samples_count: int
    error_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "feed_name": self.feed_name,
            "status": self.status.value,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "min_ms": round(self.min_latency_ms, 2),
                "max_ms": round(self.max_latency_ms, 2),
                "p95_ms": round(self.p95_latency_ms, 2)
            },
            "samples_count": self.samples_count,
            "error_count": self.error_count,
            "last_error": self.last_error
        }


class LatencyTracker:
    """
    Tracks latency samples with rolling window statistics.
    """
    
    def __init__(self, window_size: int = 100, stale_threshold_seconds: float = 30.0):
        """
        Initialize latency tracker.
        
        Args:
            window_size: Number of samples to keep for statistics
            stale_threshold_seconds: Seconds after which feed is considered stale
        """
        self.window_size = window_size
        self.stale_threshold = timedelta(seconds=stale_threshold_seconds)
        self._samples: deque = deque(maxlen=window_size)
        self._last_update: Optional[datetime] = None
        self._error_count: int = 0
        self._last_error: Optional[str] = None
    
    def record_sample(self, latency_ms: float):
        """Record a new latency sample."""
        self._samples.append(latency_ms)
        self._last_update = datetime.utcnow()
    
    def record_error(self, error_message: str):
        """Record an error occurrence."""
        self._error_count += 1
        self._last_error = error_message[:200]
    
    def get_status(self) -> FeedStatus:
        """Determine current feed status."""
        if self._last_update is None:
            return FeedStatus.DISCONNECTED
        
        age = datetime.utcnow() - self._last_update
        if age > self.stale_threshold:
            return FeedStatus.STALE
        
        if self._error_count > 5 and self._last_error:
            return FeedStatus.ERROR
        
        return FeedStatus.CONNECTED
    
    def get_stats(self) -> Dict[str, float]:
        """Calculate statistics from samples."""
        if not self._samples:
            return {
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p95": 0.0
            }
        
        samples = list(self._samples)
        sorted_samples = sorted(samples)
        
        return {
            "avg": sum(samples) / len(samples),
            "min": min(samples),
            "max": max(samples),
            "p95": sorted_samples[int(len(sorted_samples) * 0.95)] if len(sorted_samples) >= 20 else max(samples)
        }
    
    def get_metrics(self, feed_name: str) -> FeedMetrics:
        """Get aggregated metrics."""
        stats = self.get_stats()
        return FeedMetrics(
            feed_name=feed_name,
            status=self.get_status(),
            last_update=self._last_update,
            avg_latency_ms=stats["avg"],
            min_latency_ms=stats["min"],
            max_latency_ms=stats["max"],
            p95_latency_ms=stats["p95"],
            samples_count=len(self._samples),
            error_count=self._error_count,
            last_error=self._last_error
        )


class DataFetcher:
    """
    Manages data feed connections and latency monitoring.
    
    Provides real-time latency metrics for:
    - Market data feeds (quotes, options chains)
    - Database queries
    - External API calls
    """
    
    FEED_NAMES = [
        "market_quotes",
        "options_chain",
        "historical_bars",
        "news_feed",
        "volatility_surface"
    ]
    
    def __init__(self):
        """Initialize data fetcher with latency trackers for each feed."""
        self._trackers: Dict[str, LatencyTracker] = {
            name: LatencyTracker() for name in self.FEED_NAMES
        }
        self._callbacks: List[Callable[[str, FeedMetrics], None]] = []
        self._running = False
    
    def register_callback(self, callback: Callable[[str, FeedMetrics], None]):
        """Register a callback for feed updates."""
        self._callbacks.append(callback)
    
    async def record_latency(self, feed_name: str, latency_ms: float):
        """
        Record a latency measurement for a feed.
        
        Args:
            feed_name: Name of the data feed
            latency_ms: Measured latency in milliseconds
        """
        if feed_name not in self._trackers:
            self._trackers[feed_name] = LatencyTracker()
        
        self._trackers[feed_name].record_sample(latency_ms)
        
        # Notify callbacks
        metrics = self._trackers[feed_name].get_metrics(feed_name)
        for callback in self._callbacks:
            try:
                callback(feed_name, metrics)
            except Exception as e:
                logger.error(f"Callback error for {feed_name}: {e}")
    
    async def record_error(self, feed_name: str, error_message: str):
        """Record an error for a feed."""
        if feed_name in self._trackers:
            self._trackers[feed_name].record_error(error_message)
    
    def get_feed_metrics(self, feed_name: str) -> Optional[FeedMetrics]:
        """Get metrics for a specific feed."""
        if feed_name not in self._trackers:
            return None
        return self._trackers[feed_name].get_metrics(feed_name)
    
    def get_all_metrics(self) -> Dict[str, FeedMetrics]:
        """Get metrics for all feeds."""
        return {
            name: tracker.get_metrics(name)
            for name, tracker in self._trackers.items()
        }
    
    def get_all_metrics_dict(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics as JSON-serializable dictionaries."""
        return {
            name: tracker.get_metrics(name).to_dict()
            for name, tracker in self._trackers.items()
        }
    
    def get_average_latency(self) -> float:
        """Get average latency across all active feeds."""
        active_feeds = [
            tracker.get_stats()["avg"]
            for tracker in self._trackers.values()
            if tracker.get_status() == FeedStatus.CONNECTED
        ]
        if not active_feeds:
            return 0.0
        return sum(active_feeds) / len(active_feeds)
    
    def get_overall_status(self) -> FeedStatus:
        """Get worst-case status across all feeds."""
        statuses = [tracker.get_status() for tracker in self._trackers.values()]
        
        if FeedStatus.ERROR in statuses:
            return FeedStatus.ERROR
        if FeedStatus.DISCONNECTED in statuses:
            return FeedStatus.DISCONNECTED
        if FeedStatus.STALE in statuses:
            return FeedStatus.STALE
        return FeedStatus.CONNECTED
    
    async def simulate_feed_activity(self, duration_seconds: float = 60.0):
        """
        Simulate feed activity for testing/demo purposes.
        
        Args:
            duration_seconds: How long to run simulation
        """
        import random
        
        self._running = True
        start_time = time.time()
        
        while self._running and (time.time() - start_time) < duration_seconds:
            for feed_name in self.FEED_NAMES:
                # Simulate varying latencies
                base_latency = {
                    "market_quotes": 5.0,
                    "options_chain": 15.0,
                    "historical_bars": 25.0,
                    "news_feed": 50.0,
                    "volatility_surface": 100.0
                }.get(feed_name, 20.0)
                
                # Add some variance
                latency = base_latency * (0.5 + random.random())
                
                # Occasional spikes
                if random.random() < 0.05:
                    latency *= 3
                
                await self.record_latency(feed_name, latency)
            
            await asyncio.sleep(1.0)
        
        self._running = False
    
    def stop_simulation(self):
        """Stop the feed simulation."""
        self._running = False


# Global instance
_data_fetcher: Optional[DataFetcher] = None


def get_data_fetcher() -> DataFetcher:
    """Get or create global data fetcher instance."""
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher
