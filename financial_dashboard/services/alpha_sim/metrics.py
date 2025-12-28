"""
AlphaSim Metrics - Prometheus metrics instrumentation.

Provides request counting, latency tracking, cache metrics, and token bucket metrics.
"""
import time
from typing import Optional, Callable, Any
from functools import wraps

# Try to import prometheus_client, fall back to no-op implementation
try:
    from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


if PROMETHEUS_AVAILABLE:
    # Request metrics
    REQUESTS_TOTAL = Counter(
        'alpha_sim_requests_total',
        'Total number of requests',
        ['function', 'status']
    )
    
    REQUEST_LATENCY = Histogram(
        'alpha_sim_latency_seconds',
        'Request latency in seconds',
        ['function'],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )
    
    # Cache metrics
    CACHE_HITS = Counter(
        'alpha_sim_cache_hits_total',
        'Total cache hits',
        ['function']
    )
    
    CACHE_MISSES = Counter(
        'alpha_sim_cache_misses_total',
        'Total cache misses',
        ['function']
    )
    
    # Rate limiter metrics
    TOKEN_BALANCE = Gauge(
        'alpha_sim_token_balance',
        'Current token balance per API key',
        ['apikey_hash']
    )
    
    RATE_LIMIT_REJECTIONS = Counter(
        'alpha_sim_rate_limit_rejections_total',
        'Total rate limit rejections'
    )
    
    # Error metrics
    ERRORS_TOTAL = Counter(
        'alpha_sim_errors_total',
        'Total errors',
        ['function', 'error_type']
    )

else:
    # No-op implementations when prometheus_client is not available
    class NoOpMetric:
        """No-op metric that does nothing."""
        def labels(self, *args, **kwargs):
            return self
        def inc(self, amount=1):
            pass
        def dec(self, amount=1):
            pass
        def set(self, value):
            pass
        def observe(self, amount):
            pass
    
    REQUESTS_TOTAL = NoOpMetric()
    REQUEST_LATENCY = NoOpMetric()
    CACHE_HITS = NoOpMetric()
    CACHE_MISSES = NoOpMetric()
    TOKEN_BALANCE = NoOpMetric()
    RATE_LIMIT_REJECTIONS = NoOpMetric()
    ERRORS_TOTAL = NoOpMetric()


def track_request(function: str, status: str = "200"):
    """Track a request."""
    REQUESTS_TOTAL.labels(function=function, status=status).inc()


def track_latency(function: str, latency_seconds: float):
    """Track request latency."""
    REQUEST_LATENCY.labels(function=function).observe(latency_seconds)


def track_cache_hit(function: str):
    """Track a cache hit."""
    CACHE_HITS.labels(function=function).inc()


def track_cache_miss(function: str):
    """Track a cache miss."""
    CACHE_MISSES.labels(function=function).inc()


def track_token_balance(apikey_hash: str, balance: float):
    """Track token balance for an API key."""
    TOKEN_BALANCE.labels(apikey_hash=apikey_hash).set(balance)


def track_rate_limit_rejection():
    """Track a rate limit rejection."""
    RATE_LIMIT_REJECTIONS.inc()


def track_error(function: str, error_type: str):
    """Track an error."""
    ERRORS_TOTAL.labels(function=function, error_type=error_type).inc()


def timed(function_name: Optional[str] = None):
    """
    Decorator to time function execution.
    
    Usage:
        @timed("TIME_SERIES_DAILY")
        def time_series_daily(symbol, outputsize):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            fname = function_name or func.__name__
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                track_request(fname, "200")
                track_latency(fname, elapsed)
                return result
            except Exception as e:
                elapsed = time.time() - start
                track_request(fname, "500")
                track_latency(fname, elapsed)
                track_error(fname, type(e).__name__)
                raise
        return wrapper
    return decorator


def get_metrics_text() -> str:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        Prometheus metrics string for /metrics endpoint
    """
    if PROMETHEUS_AVAILABLE:
        return generate_latest(REGISTRY).decode('utf-8')
    return ""


def get_metrics_dict() -> dict:
    """
    Get metrics as a dictionary for JSON endpoint.
    
    Returns:
        Dict with key metrics
    """
    return {
        "prometheus_available": PROMETHEUS_AVAILABLE,
        "metrics": {
            "requests_total": "alpha_sim_requests_total",
            "latency_seconds": "alpha_sim_latency_seconds",
            "cache_hits_total": "alpha_sim_cache_hits_total",
            "cache_misses_total": "alpha_sim_cache_misses_total",
            "token_balance": "alpha_sim_token_balance",
            "rate_limit_rejections_total": "alpha_sim_rate_limit_rejections_total",
            "errors_total": "alpha_sim_errors_total"
        }
    }


# Context manager for timing
class RequestTimer:
    """
    Context manager for timing requests.
    
    Usage:
        with RequestTimer("TIME_SERIES_DAILY") as timer:
            result = fetch_data()
        # latency automatically recorded
    """
    
    def __init__(self, function_name: str):
        self.function_name = function_name
        self.start_time = None
        self.elapsed = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        
        if exc_type is None:
            track_request(self.function_name, "200")
        else:
            track_request(self.function_name, "500")
            track_error(self.function_name, exc_type.__name__)
        
        track_latency(self.function_name, self.elapsed)
        
        # Don't suppress exceptions
        return False
