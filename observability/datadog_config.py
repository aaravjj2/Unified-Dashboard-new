"""
Datadog Metrics Configuration
Phase 22: Observability, Monitoring, and Optional Enhancements

Provides centralized Datadog/Prometheus metrics emission utilities.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Datadog initialization flag
_datadog_initialized = False
_statsd_client = None


def init_datadog() -> bool:
    """
    Initialize Datadog StatsD client for metrics.
    
    Returns:
        bool: True if Datadog initialized successfully, False otherwise
    """
    global _datadog_initialized, _statsd_client
    
    if _datadog_initialized:
        logger.info("✅ Datadog already initialized")
        return True
    
    datadog_enabled = os.getenv('DATADOG_ENABLED', 'false').lower() == 'true'
    
    if not datadog_enabled:
        logger.warning("⚠️ DATADOG_ENABLED=false - metrics disabled")
        return False
    
    try:
        from datadog import initialize, statsd
        
        # Initialize Datadog
        options = {
            'api_key': os.getenv('DATADOG_API_KEY'),
            'app_key': os.getenv('DATADOG_APP_KEY'),
            'statsd_host': os.getenv('DATADOG_STATSD_HOST', 'localhost'),
            'statsd_port': int(os.getenv('DATADOG_STATSD_PORT', '8125'))
        }
        
        initialize(**options)
        _statsd_client = statsd
        _datadog_initialized = True
        
        logger.info("✅ Datadog initialized successfully")
        return True
        
    except ImportError:
        logger.warning("⚠️ datadog package not installed - metrics disabled")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to initialize Datadog: {e}")
        return False


def emit_metric(
    metric_name: str,
    value: float,
    metric_type: str = 'gauge',
    tags: Optional[List[str]] = None,
    sample_rate: float = 1.0
) -> None:
    """
    Emit metric to Datadog/Prometheus.
    
    Args:
        metric_name: Metric name (e.g., 'dashboard.ml.prediction.latency')
        value: Metric value
        metric_type: 'gauge', 'increment', 'histogram', 'timing'
        tags: List of tags (e.g., ['env:production', 'module:azure_ml'])
        sample_rate: Sampling rate (0.0 to 1.0)
    """
    if not _datadog_initialized:
        return
    
    try:
        tags = tags or []
        tags.append(f"env:{os.getenv('DASH_ENV', 'production')}")
        
        if metric_type == 'gauge':
            _statsd_client.gauge(metric_name, value, tags=tags, sample_rate=sample_rate)
        elif metric_type == 'increment':
            _statsd_client.increment(metric_name, value, tags=tags, sample_rate=sample_rate)
        elif metric_type == 'histogram':
            _statsd_client.histogram(metric_name, value, tags=tags, sample_rate=sample_rate)
        elif metric_type == 'timing':
            _statsd_client.timing(metric_name, value, tags=tags, sample_rate=sample_rate)
        
        logger.debug(f"📊 Metric emitted: {metric_name}={value} ({metric_type}) {tags}")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to emit metric {metric_name}: {e}")


def increment_counter(
    counter_name: str,
    value: int = 1,
    tags: Optional[List[str]] = None
) -> None:
    """
    Increment counter metric.
    
    Args:
        counter_name: Counter name
        value: Increment value (default 1)
        tags: Optional tags
    """
    emit_metric(counter_name, value, metric_type='increment', tags=tags)


def record_gauge(
    gauge_name: str,
    value: float,
    tags: Optional[List[str]] = None
) -> None:
    """
    Record gauge metric (current value).
    
    Args:
        gauge_name: Gauge name
        value: Current value
        tags: Optional tags
    """
    emit_metric(gauge_name, value, metric_type='gauge', tags=tags)


def record_histogram(
    histogram_name: str,
    value: float,
    tags: Optional[List[str]] = None
) -> None:
    """
    Record histogram metric (distribution).
    
    Args:
        histogram_name: Histogram name
        value: Value to record
        tags: Optional tags
    """
    emit_metric(histogram_name, value, metric_type='histogram', tags=tags)


def record_timing(
    timing_name: str,
    duration_ms: float,
    tags: Optional[List[str]] = None
) -> None:
    """
    Record timing metric (duration in milliseconds).
    
    Args:
        timing_name: Timing metric name
        duration_ms: Duration in milliseconds
        tags: Optional tags
    """
    emit_metric(timing_name, duration_ms, metric_type='timing', tags=tags)


class MetricTimer:
    """
    Context manager for timing operations.
    
    Usage:
        with MetricTimer('dashboard.ml.prediction.latency', tags=['module:azure_ml']):
            # code to time
    """
    
    def __init__(self, metric_name: str, tags: Optional[List[str]] = None):
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        record_timing(self.metric_name, duration_ms, tags=self.tags)


def metric_timing(metric_name: str, tags: Optional[List[str]] = None):
    """
    Decorator to automatically time function execution.
    
    Usage:
        @metric_timing('dashboard.callback.duration', tags=['callback:azure_ml'])
        def my_callback():
            # callback code
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                func_tags = tags or []
                func_tags.append(f"function:{func.__name__}")
                record_timing(metric_name, duration_ms, tags=func_tags)
        return wrapper
    return decorator


# Predefined metric functions for common dashboard operations

def record_ml_prediction_latency(duration_ms: float, module: str = 'azure_ml'):
    """Record ML prediction latency."""
    record_timing(
        'dashboard.ml.prediction.latency',
        duration_ms,
        tags=[f'module:{module}']
    )


def record_forecast_generation_latency(duration_ms: float, forecast_type: str = 'market'):
    """Record forecast generation latency."""
    record_timing(
        'dashboard.forecast.generation.latency',
        duration_ms,
        tags=[f'type:{forecast_type}']
    )


def record_options_calculation_latency(duration_ms: float, calculation_type: str = 'chain'):
    """Record Options Lab calculation latency."""
    record_timing(
        'dashboard.options.calculation.latency',
        duration_ms,
        tags=[f'type:{calculation_type}']
    )


def record_database_query_latency(duration_ms: float, query_type: str = 'select'):
    """Record database query latency."""
    record_timing(
        'dashboard.database.query.latency',
        duration_ms,
        tags=[f'type:{query_type}']
    )


def increment_callback_invocation(callback_name: str, status: str = 'success'):
    """Increment callback invocation counter."""
    increment_counter(
        'dashboard.callback.invocations',
        tags=[f'callback:{callback_name}', f'status:{status}']
    )


def increment_api_request(endpoint: str, method: str, status_code: int):
    """Increment API request counter."""
    increment_counter(
        'dashboard.api.requests',
        tags=[f'endpoint:{endpoint}', f'method:{method}', f'status:{status_code}']
    )


def record_active_users(count: int):
    """Record active user count."""
    record_gauge('dashboard.users.active', count)


def record_cache_hit_rate(rate: float):
    """Record cache hit rate (0.0 to 1.0)."""
    record_gauge('dashboard.cache.hit_rate', rate)


def record_strategy_lab_latency(duration_ms: float, operation: str = 'backtest'):
    """
    Record Strategy Lab operation latency.
    
    Phase 23: Added for Benchmark and Risk subtab sync observability.
    
    Args:
        duration_ms: Operation duration in milliseconds
        operation: Operation type (e.g., 'backtest', 'benchmark_metrics_update', 'risk_metrics_update')
    """
    record_timing(
        'dashboard.strategy_lab.operation.latency',
        duration_ms,
        tags=[f'operation:{operation}']
    )


# Initialize Datadog on module import
init_datadog()
