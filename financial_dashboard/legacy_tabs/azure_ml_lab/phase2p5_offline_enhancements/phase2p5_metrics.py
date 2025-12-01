"""
Phase 2.5 Offline Enhancements — Local Analytics Tracker

This module provides lightweight, privacy-preserving analytics for Phase 2.5
visualization and explainability features. Tracks:

1. Compute time per explanation
2. Cache hit/miss rates
3. Most-used tickers
4. Chart type usage frequency
5. Session statistics

No external dependencies required. Metrics are stored locally in JSON format.

Author: Autonomous Lead Software Engineer
Version: 1.0.0 (Phase 2.5)
"""

import json
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Default metrics storage path
DEFAULT_METRICS_PATH = Path(__file__).parent.parent.parent.parent.parent / "outputs" / "phase2p5_reports" / "metrics.json"


# ============================================================================
# METRICS TRACKER
# ============================================================================

class Phase25MetricsTracker:
    """
    Lightweight analytics tracker for Phase 2.5 features.
    
    Tracks usage patterns, performance metrics, and cache statistics
    without external dependencies or network calls.
    
    Example:
        >>> tracker = Phase25MetricsTracker()
        >>> 
        >>> # Track explanation generation
        >>> with tracker.track_explanation("AAPL", chart_type="bar"):
        ...     # Generate explanation
        ...     pass
        >>> 
        >>> # Record cache hit
        >>> tracker.record_cache_hit("AAPL")
        >>> 
        >>> # Get session stats
        >>> stats = tracker.get_session_stats()
    """
    
    def __init__(self, metrics_path: Optional[Path] = None, auto_save: bool = True):
        """
        Initialize metrics tracker.
        
        Args:
            metrics_path: Path to JSON metrics file (default: outputs/phase2p5_reports/metrics.json)
            auto_save: If True, automatically save metrics after each operation
        """
        self.metrics_path = metrics_path or DEFAULT_METRICS_PATH
        self.auto_save = auto_save
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = time.time()
        
        # Metrics storage
        self.compute_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.ticker_usage: Counter = Counter()
        self.chart_type_usage: Counter = Counter()
        self.explanation_count = 0
        self.comparison_count = 0
        self.narrative_template_usage: Counter = Counter()
        
        # Load existing metrics if available
        self._load_metrics()
        
        logger.info(f"📊 Phase25MetricsTracker initialized (session={self.session_id})")
    
    def _load_metrics(self) -> None:
        """Load existing metrics from disk if available."""
        if not self.metrics_path.exists():
            logger.info("No existing metrics file found. Starting fresh.")
            return
        
        try:
            with open(self.metrics_path, 'r') as f:
                data = json.load(f)
            
            # Load historical totals (don't overwrite session-specific data)
            self.cache_hits = data.get('total_cache_hits', 0)
            self.cache_misses = data.get('total_cache_misses', 0)
            self.explanation_count = data.get('total_explanations', 0)
            self.comparison_count = data.get('total_comparisons', 0)
            
            logger.info(f"Loaded existing metrics: {self.explanation_count} explanations, {self.cache_hits} cache hits")
            
        except Exception as e:
            logger.warning(f"Failed to load metrics: {e}. Starting fresh.")
    
    def _save_metrics(self) -> None:
        """Save current metrics to disk."""
        if not self.auto_save:
            return
        
        try:
            # Ensure output directory exists
            self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare metrics payload
            metrics = {
                'session_id': self.session_id,
                'session_start': datetime.fromtimestamp(self.session_start).isoformat(),
                'session_duration_seconds': time.time() - self.session_start,
                'total_explanations': self.explanation_count,
                'total_comparisons': self.comparison_count,
                'total_cache_hits': self.cache_hits,
                'total_cache_misses': self.cache_misses,
                'cache_hit_rate': self._calculate_cache_hit_rate(),
                'average_compute_time_ms': self._calculate_avg_compute_time(),
                'ticker_usage': dict(self.ticker_usage.most_common(20)),
                'chart_type_usage': dict(self.chart_type_usage),
                'narrative_template_usage': dict(self.narrative_template_usage.most_common(15)),
                'last_updated': datetime.now().isoformat()
            }
            
            # Write to disk
            with open(self.metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100
    
    def _calculate_avg_compute_time(self) -> float:
        """Calculate average compute time in milliseconds."""
        if not self.compute_times:
            return 0.0
        return (sum(self.compute_times) / len(self.compute_times)) * 1000
    
    def track_explanation(self, ticker: str, chart_type: Optional[str] = None):
        """
        Context manager for tracking explanation generation.
        
        Args:
            ticker: Ticker symbol
            chart_type: Chart type used (e.g., 'bar', 'waterfall')
            
        Usage:
            >>> with tracker.track_explanation("AAPL", chart_type="bar"):
            ...     # Generate explanation
            ...     pass
        """
        return _ExplanationContext(self, ticker, chart_type)
    
    def record_cache_hit(self, ticker: str) -> None:
        """
        Record a cache hit.
        
        Args:
            ticker: Ticker symbol
        """
        self.cache_hits += 1
        self.ticker_usage[ticker] += 1
        self._save_metrics()
        logger.debug(f"Cache hit recorded for {ticker} (total hits: {self.cache_hits})")
    
    def record_cache_miss(self, ticker: str) -> None:
        """
        Record a cache miss.
        
        Args:
            ticker: Ticker symbol
        """
        self.cache_misses += 1
        self.ticker_usage[ticker] += 1
        self._save_metrics()
        logger.debug(f"Cache miss recorded for {ticker} (total misses: {self.cache_misses})")
    
    def record_comparison(self, tickers: List[str]) -> None:
        """
        Record a multi-ticker comparison.
        
        Args:
            tickers: List of ticker symbols compared
        """
        self.comparison_count += 1
        for ticker in tickers:
            self.ticker_usage[ticker] += 1
        self._save_metrics()
        logger.debug(f"Comparison recorded for {len(tickers)} tickers")
    
    def record_narrative_template(self, template_name: str) -> None:
        """
        Record usage of a narrative template.
        
        Args:
            template_name: Template key (e.g., 'growth_momentum', 'volatility_risk')
        """
        self.narrative_template_usage[template_name] += 1
        self._save_metrics()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get current session statistics.
        
        Returns:
            Dictionary with session metrics including:
            - explanation_count
            - comparison_count
            - cache_hit_rate
            - avg_compute_time_ms
            - top_tickers (top 10)
            - chart_type_distribution
        """
        return {
            'session_id': self.session_id,
            'session_duration_minutes': (time.time() - self.session_start) / 60,
            'explanation_count': self.explanation_count,
            'comparison_count': self.comparison_count,
            'cache_hit_rate': self._calculate_cache_hit_rate(),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'avg_compute_time_ms': self._calculate_avg_compute_time(),
            'top_tickers': dict(self.ticker_usage.most_common(10)),
            'chart_type_distribution': dict(self.chart_type_usage),
            'narrative_template_distribution': dict(self.narrative_template_usage.most_common(10))
        }
    
    def export_summary(self, output_path: Optional[Path] = None) -> Path:
        """
        Export session summary as formatted JSON report.
        
        Args:
            output_path: Custom output path (default: metrics_summary_{session_id}.json)
            
        Returns:
            Path to exported summary file
        """
        if output_path is None:
            output_path = self.metrics_path.parent / f"metrics_summary_{self.session_id}.json"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build summary
        summary = {
            'session_id': self.session_id,
            'session_start': datetime.fromtimestamp(self.session_start).isoformat(),
            'session_end': datetime.now().isoformat(),
            'session_duration_minutes': (time.time() - self.session_start) / 60,
            'metrics': self.get_session_stats(),
            'performance': {
                'total_compute_time_seconds': sum(self.compute_times),
                'min_compute_time_ms': min(self.compute_times) * 1000 if self.compute_times else 0,
                'max_compute_time_ms': max(self.compute_times) * 1000 if self.compute_times else 0,
                'p50_compute_time_ms': self._percentile(self.compute_times, 50) * 1000 if self.compute_times else 0,
                'p95_compute_time_ms': self._percentile(self.compute_times, 95) * 1000 if self.compute_times else 0,
            },
            'usage_patterns': {
                'top_10_tickers': dict(self.ticker_usage.most_common(10)),
                'chart_type_breakdown': dict(self.chart_type_usage),
                'narrative_template_breakdown': dict(self.narrative_template_usage.most_common(15))
            }
        }
        
        # Write summary
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Session summary exported to {output_path}")
        return output_path
    
    def _percentile(self, data: List[float], p: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def reset_session(self) -> None:
        """Reset session-specific metrics (preserve total counts)."""
        logger.info(f"Resetting session metrics (preserving totals)")
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = time.time()
        self.compute_times = []
        self.ticker_usage = Counter()
        self.chart_type_usage = Counter()
        self.narrative_template_usage = Counter()
        
        # Don't reset totals (cache_hits, cache_misses, explanation_count, comparison_count)
    
    def __repr__(self) -> str:
        stats = self.get_session_stats()
        return (
            f"Phase25MetricsTracker(session={self.session_id}, "
            f"explanations={stats['explanation_count']}, "
            f"cache_hit_rate={stats['cache_hit_rate']:.1f}%, "
            f"avg_time={stats['avg_compute_time_ms']:.1f}ms)"
        )


# ============================================================================
# CONTEXT MANAGER FOR EXPLANATION TRACKING
# ============================================================================

class _ExplanationContext:
    """Context manager for tracking explanation generation time."""
    
    def __init__(self, tracker: Phase25MetricsTracker, ticker: str, chart_type: Optional[str]):
        self.tracker = tracker
        self.ticker = ticker
        self.chart_type = chart_type
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        
        # Record metrics
        self.tracker.compute_times.append(elapsed)
        self.tracker.explanation_count += 1
        self.tracker.ticker_usage[self.ticker] += 1
        
        if self.chart_type:
            self.tracker.chart_type_usage[self.chart_type] += 1
        
        # Auto-save if enabled
        self.tracker._save_metrics()
        
        # Log performance
        logger.debug(f"Explanation for {self.ticker} completed in {elapsed*1000:.1f}ms")
        
        # Return False to propagate exceptions
        return False


# ============================================================================
# GLOBAL TRACKER SINGLETON
# ============================================================================

# Initialize global tracker for easy access
_global_tracker: Optional[Phase25MetricsTracker] = None

def get_global_tracker() -> Phase25MetricsTracker:
    """
    Get or create the global metrics tracker instance.
    
    Returns:
        Global Phase25MetricsTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = Phase25MetricsTracker()
    return _global_tracker


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def track_explanation(ticker: str, chart_type: Optional[str] = None):
    """
    Convenience function for tracking explanation generation.
    
    Args:
        ticker: Ticker symbol
        chart_type: Chart type used
        
    Returns:
        Context manager for tracking
    """
    return get_global_tracker().track_explanation(ticker, chart_type)

def record_cache_hit(ticker: str) -> None:
    """Convenience function for recording cache hit."""
    get_global_tracker().record_cache_hit(ticker)

def record_cache_miss(ticker: str) -> None:
    """Convenience function for recording cache miss."""
    get_global_tracker().record_cache_miss(ticker)

def record_comparison(tickers: List[str]) -> None:
    """Convenience function for recording comparison."""
    get_global_tracker().record_comparison(tickers)

def record_narrative_template(template_name: str) -> None:
    """Convenience function for recording narrative template usage."""
    get_global_tracker().record_narrative_template(template_name)

def get_session_stats() -> Dict[str, Any]:
    """Convenience function for getting session stats."""
    return get_global_tracker().get_session_stats()

def export_session_summary(output_path: Optional[Path] = None) -> Path:
    """Convenience function for exporting session summary."""
    return get_global_tracker().export_summary(output_path)


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

if __name__ == "__main__":
    # Demo usage
    print("Phase 2.5 Metrics Tracker - Demo Mode")
    print("=" * 60)
    
    # Create tracker
    tracker = Phase25MetricsTracker()
    
    # Simulate some activity
    print("\nSimulating explanation generation...")
    with tracker.track_explanation("AAPL", chart_type="bar"):
        time.sleep(0.05)  # Simulate 50ms compute
    
    with tracker.track_explanation("GOOGL", chart_type="waterfall"):
        time.sleep(0.08)  # Simulate 80ms compute
    
    # Record cache activity
    tracker.record_cache_hit("AAPL")
    tracker.record_cache_miss("TSLA")
    tracker.record_cache_hit("AAPL")
    
    # Record comparison
    tracker.record_comparison(["AAPL", "GOOGL", "TSLA"])
    
    # Record narrative templates
    tracker.record_narrative_template("growth_momentum")
    tracker.record_narrative_template("volatility_risk")
    tracker.record_narrative_template("growth_momentum")
    
    # Display stats
    print("\nSession Statistics:")
    print("-" * 60)
    stats = tracker.get_session_stats()
    for key, value in stats.items():
        print(f"{key:30s}: {value}")
    
    # Export summary
    print("\nExporting session summary...")
    summary_path = tracker.export_summary()
    print(f"Summary saved to: {summary_path}")
    
    print("\n✅ Demo complete!")
