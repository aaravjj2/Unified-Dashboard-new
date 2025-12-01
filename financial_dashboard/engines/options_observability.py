"""
Observability Module for Options Lab - Phase 20B

Provides:
- Sentry integration for error tracking
- Datadog/Prometheus metrics
- Telemetry for user queries, latency, and success rates
- Structured logging

Author: Agent 1C - Phase 20B
"""
import logging
import time
import os
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Sentry initialization (conditional)
SENTRY_ENABLED = False
try:
    import sentry_sdk
    sentry_dsn = os.getenv('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,
            environment=os.getenv('ENVIRONMENT', 'production')
        )
        SENTRY_ENABLED = True
        logger.info("✅ Sentry initialized for Options Lab observability")
except ImportError:
    logger.warning("⚠️ Sentry not available (package not installed)")
except Exception as e:
    logger.warning(f"⚠️ Sentry initialization failed: {e}")

# Datadog/Prometheus metrics (conditional)
METRICS_ENABLED = False
try:
    from datadog import statsd
    METRICS_ENABLED = True
    logger.info("✅ Datadog metrics enabled for Options Lab")
except ImportError:
    logger.info("ℹ️ Datadog not available, using local metrics")


class OptionsMetrics:
    """
    Metrics collector for Options Lab operations.
    
    Tracks:
    - Query count
    - Latency (fetch, greeks, oi, strategy, total)
    - Success/failure rates
    - Data source distribution
    """
    
    def __init__(self):
        self.metrics = {
            'query_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'fetch_latency': [],
            'greeks_latency': [],
            'oi_latency': [],
            'strategy_latency': [],
            'total_latency': [],
            'data_sources': {}
        }
    
    def record_query(self, ticker: str, success: bool, latencies: Dict[str, float], 
                     data_source: str):
        """Record a single query with all metrics."""
        self.metrics['query_count'] += 1
        
        if success:
            self.metrics['success_count'] += 1
        else:
            self.metrics['failure_count'] += 1
        
        # Record latencies
        self.metrics['fetch_latency'].append(latencies.get('fetch_time', 0))
        self.metrics['greeks_latency'].append(latencies.get('greeks_time', 0))
        self.metrics['oi_latency'].append(latencies.get('oi_time', 0))
        self.metrics['strategy_latency'].append(latencies.get('strategy_time', 0))
        self.metrics['total_latency'].append(latencies.get('total_time', 0))
        
        # Track data source
        self.metrics['data_sources'][data_source] = \
            self.metrics['data_sources'].get(data_source, 0) + 1
        
        # Send to Datadog if available
        if METRICS_ENABLED:
            try:
                statsd.increment('options.query.count', tags=[f'ticker:{ticker}', f'source:{data_source}'])
                statsd.timing('options.latency.fetch_ms', latencies.get('fetch_time', 0) * 1000)
                statsd.timing('options.latency.greeks_ms', latencies.get('greeks_time', 0) * 1000)
                statsd.timing('options.latency.oi_ms', latencies.get('oi_time', 0) * 1000)
                statsd.timing('options.latency.strategy_ms', latencies.get('strategy_time', 0) * 1000)
                statsd.timing('options.latency.total_ms', latencies.get('total_time', 0) * 1000)
                
                if success:
                    statsd.increment('options.success.count')
                else:
                    statsd.increment('options.failure.count')
            except Exception as e:
                logger.warning(f"⚠️ Failed to send metrics to Datadog: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        import numpy as np
        
        def calc_stats(values):
            if not values:
                return {'min': 0, 'max': 0, 'mean': 0, 'p50': 0, 'p95': 0, 'p99': 0}
            return {
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'mean': float(np.mean(values)),
                'p50': float(np.percentile(values, 50)),
                'p95': float(np.percentile(values, 95)),
                'p99': float(np.percentile(values, 99))
            }
        
        success_rate = self.metrics['success_count'] / max(self.metrics['query_count'], 1)
        
        return {
            'query_count': self.metrics['query_count'],
            'success_count': self.metrics['success_count'],
            'failure_count': self.metrics['failure_count'],
            'success_rate': success_rate,
            'fetch_latency_stats': calc_stats(self.metrics['fetch_latency']),
            'greeks_latency_stats': calc_stats(self.metrics['greeks_latency']),
            'oi_latency_stats': calc_stats(self.metrics['oi_latency']),
            'strategy_latency_stats': calc_stats(self.metrics['strategy_latency']),
            'total_latency_stats': calc_stats(self.metrics['total_latency']),
            'data_sources': self.metrics['data_sources']
        }


# Global metrics instance
_metrics = OptionsMetrics()


def get_metrics() -> OptionsMetrics:
    """Get global metrics instance."""
    return _metrics


def trace_options_operation(operation_name: str):
    """
    Decorator to trace Options Lab operations with Sentry.
    
    Usage:
        @trace_options_operation('fetch_chain')
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Start Sentry transaction if available
            if SENTRY_ENABLED:
                try:
                    with sentry_sdk.start_transaction(op=operation_name, name=func.__name__):
                        result = func(*args, **kwargs)
                        elapsed = time.time() - start_time
                        sentry_sdk.set_measurement(f"{operation_name}_duration", elapsed, "second")
                        return result
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    raise
            else:
                # No Sentry, just run function
                result = func(*args, **kwargs)
                return result
        
        return wrapper
    return decorator


def log_options_event(event_type: str, ticker: str, details: Dict[str, Any]):
    """
    Log structured event for Options Lab operations.
    
    Args:
        event_type: Type of event (e.g., 'forecast_start', 'forecast_complete', 'error')
        ticker: Stock ticker
        details: Additional event details
    """
    event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'ticker': ticker,
        **details
    }
    
    logger.info(f"📊 [Options Lab] {event_type.upper()}: {ticker}", extra=event)
    
    # Send to Sentry as breadcrumb
    if SENTRY_ENABLED:
        try:
            sentry_sdk.add_breadcrumb(
                category='options_lab',
                message=f"{event_type}: {ticker}",
                level='info',
                data=details
            )
        except Exception:
            pass


def capture_options_error(error: Exception, context: Dict[str, Any]):
    """
    Capture error with context for Sentry.
    
    Args:
        error: Exception that occurred
        context: Additional context (ticker, operation, etc.)
    """
    logger.error(f"❌ Options Lab error: {error}", exc_info=True, extra=context)
    
    if SENTRY_ENABLED:
        try:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, {'value': value})
                sentry_sdk.capture_exception(error)
        except Exception as e:
            logger.warning(f"⚠️ Failed to send error to Sentry: {e}")


# Prometheus metrics (if available)
try:
    from prometheus_client import Counter, Histogram, Gauge
    
    options_query_counter = Counter(
        'options_lab_queries_total',
        'Total number of options forecast queries',
        ['ticker', 'data_source']
    )
    
    options_latency_histogram = Histogram(
        'options_lab_latency_seconds',
        'Options forecast latency distribution',
        ['operation']
    )
    
    options_success_gauge = Gauge(
        'options_lab_success_rate',
        'Current success rate for options forecasts'
    )
    
    PROMETHEUS_ENABLED = True
    logger.info("✅ Prometheus metrics enabled for Options Lab")
    
except ImportError:
    PROMETHEUS_ENABLED = False
    logger.info("ℹ️ Prometheus not available")


def update_prometheus_metrics(ticker: str, data_source: str, latencies: Dict[str, float], success: bool):
    """Update Prometheus metrics."""
    if not PROMETHEUS_ENABLED:
        return
    
    try:
        # Increment query counter
        options_query_counter.labels(ticker=ticker, data_source=data_source).inc()
        
        # Record latencies
        for operation, latency in latencies.items():
            options_latency_histogram.labels(operation=operation).observe(latency)
        
        # Update success rate (simplified)
        metrics = get_metrics().get_summary()
        options_success_gauge.set(metrics['success_rate'])
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to update Prometheus metrics: {e}")


__all__ = [
    'OptionsMetrics',
    'get_metrics',
    'trace_options_operation',
    'log_options_event',
    'capture_options_error',
    'update_prometheus_metrics',
    'SENTRY_ENABLED',
    'METRICS_ENABLED',
    'PROMETHEUS_ENABLED'
]
