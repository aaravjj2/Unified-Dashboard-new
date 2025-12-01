"""
Azure ML Lab - Observability Layer

Sentry exception tracking and Datadog/Prometheus metrics emission.
Phase 20A: Production-grade observability for all ML operations.
"""

import logging
import time
import functools
from typing import Dict, Optional, Callable, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# ============================================================================
# METRICS COLLECTION
# ============================================================================

class MLMetricsCollector:
    """
    Collect and emit metrics for Azure ML operations.
    Compatible with Datadog and Prometheus formats.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = []
        logger.info("📊 ML Metrics Collector initialized")
    
    def emit_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: str = "gauge",
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Emit a metric for observability platforms.
        
        Args:
            metric_name: Metric identifier (e.g., 'ml.prediction.latency.ms')
            value: Metric value
            metric_type: Type (gauge, counter, histogram)
            tags: Additional tags (model_type, horizon_days, etc.)
            timestamp: Metric timestamp (defaults to now)
        """
        metric = {
            'name': metric_name,
            'value': value,
            'type': metric_type,
            'tags': tags or {},
            'timestamp': timestamp or datetime.now()
        }
        
        self.metrics.append(metric)
        
        # Log for debugging
        tags_str = ', '.join([f"{k}={v}" for k, v in metric.get('tags', {}).items()])
        logger.debug(f"📊 METRIC: {metric_name}={value} [{tags_str}]")
    
    def emit_timing(self, metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Emit timing metric (histogram)."""
        self.emit_metric(metric_name, duration_ms, metric_type="histogram", tags=tags)
    
    def emit_count(self, metric_name: str, count: int = 1, tags: Optional[Dict[str, str]] = None):
        """Emit counter metric."""
        self.emit_metric(metric_name, count, metric_type="counter", tags=tags)
    
    def emit_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Emit gauge metric."""
        self.emit_metric(metric_name, value, metric_type="gauge", tags=tags)
    
    def get_metrics(self) -> list:
        """Get all collected metrics."""
        return self.metrics
    
    def clear_metrics(self):
        """Clear collected metrics."""
        self.metrics = []
        logger.debug("🗑️ Metrics cleared")
    
    def format_datadog(self) -> str:
        """
        Format metrics for Datadog StatsD format.
        
        Returns:
            str: Metrics in Datadog format
        """
        formatted = []
        for metric in self.metrics:
            tags_str = ','.join([f"{k}:{v}" for k, v in metric['tags'].items()])
            formatted.append(f"{metric['name']}:{metric['value']}|{metric['type'][0]}|#{tags_str}")
        return '\n'.join(formatted)
    
    def format_prometheus(self) -> str:
        """
        Format metrics for Prometheus exposition format.
        
        Returns:
            str: Metrics in Prometheus format
        """
        formatted = []
        for metric in self.metrics:
            labels = ','.join([f'{k}="{v}"' for k, v in metric['tags'].items()])
            label_str = f"{{{labels}}}" if labels else ""
            formatted.append(f"{metric['name']}{label_str} {metric['value']}")
        return '\n'.join(formatted)


# Global metrics collector instance
metrics_collector = MLMetricsCollector()


# ============================================================================
# EXCEPTION TRACKING
# ============================================================================

class MLExceptionTracker:
    """
    Track exceptions for Sentry-compatible error monitoring.
    """
    
    def __init__(self):
        """Initialize exception tracker."""
        self.exceptions = []
        logger.info("🚨 ML Exception Tracker initialized")
    
    def capture_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error"
    ):
        """
        Capture exception with context.
        
        Args:
            exception: Exception to capture
            context: Additional context (model_type, run_id, etc.)
            level: Error level (error, warning, critical)
        """
        exception_data = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'level': level,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.exceptions.append(exception_data)
        
        # Log exception
        logger.error(f"🚨 EXCEPTION: {exception_data['exception_type']} - {exception_data['exception_message']}")
        if context:
            logger.error(f"   Context: {json.dumps(context, indent=2)}")
    
    def get_exceptions(self) -> list:
        """Get all captured exceptions."""
        return self.exceptions
    
    def clear_exceptions(self):
        """Clear captured exceptions."""
        self.exceptions = []
        logger.debug("🗑️ Exceptions cleared")
    
    def format_sentry(self) -> str:
        """
        Format exceptions for Sentry-compatible reporting.
        
        Returns:
            str: Exceptions in Sentry-compatible JSON format
        """
        return json.dumps(self.exceptions, indent=2)


# Global exception tracker instance
exception_tracker = MLExceptionTracker()


# ============================================================================
# DECORATORS
# ============================================================================

def track_ml_timing(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to track execution timing of ML functions.
    
    Usage:
        @track_ml_timing('ml.prediction.execution', tags={'model_type': 'ensemble'})
        def run_prediction(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.emit_timing(metric_name, duration_ms, tags=tags)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.emit_timing(f"{metric_name}.error", duration_ms, tags=tags)
                raise
        return wrapper
    return decorator


def track_ml_exceptions(context: Optional[Dict[str, Any]] = None):
    """
    Decorator to track exceptions in ML functions.
    
    Usage:
        @track_ml_exceptions(context={'operation': 'prediction'})
        def run_prediction(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exception_context = context.copy() if context else {}
                exception_context['function'] = func.__name__
                exception_tracker.capture_exception(e, context=exception_context)
                raise
        return wrapper
    return decorator


def track_ml_operation(metric_name: str, tags: Optional[Dict[str, str]] = None, context: Optional[Dict[str, Any]] = None):
    """
    Decorator to track both timing and exceptions for ML operations.
    
    Usage:
        @track_ml_operation('ml.prediction', tags={'model_type': 'ensemble'}, context={'operation': 'predict'})
        def run_prediction(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Record success metrics
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.emit_timing(f"{metric_name}.latency.ms", duration_ms, tags=tags)
                metrics_collector.emit_count(f"{metric_name}.success", tags=tags)
                
                return result
            
            except Exception as e:
                # Record failure metrics
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.emit_timing(f"{metric_name}.latency.ms", duration_ms, tags=tags)
                metrics_collector.emit_count(f"{metric_name}.error", tags=tags)
                
                # Capture exception
                exception_context = context.copy() if context else {}
                exception_context['function'] = func.__name__
                exception_context['duration_ms'] = duration_ms
                exception_tracker.capture_exception(e, context=exception_context)
                
                raise
        
        return wrapper
    return decorator


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def log_metric(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """
    Convenience function to emit a metric.
    
    Args:
        metric_name: Metric identifier
        value: Metric value
        tags: Additional tags
    """
    metrics_collector.emit_metric(metric_name, value, tags=tags)


def log_timing(metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
    """
    Convenience function to emit a timing metric.
    
    Args:
        metric_name: Metric identifier
        duration_ms: Duration in milliseconds
        tags: Additional tags
    """
    metrics_collector.emit_timing(metric_name, duration_ms, tags=tags)


def log_count(metric_name: str, count: int = 1, tags: Optional[Dict[str, str]] = None):
    """
    Convenience function to emit a counter metric.
    
    Args:
        metric_name: Metric identifier
        count: Count value
        tags: Additional tags
    """
    metrics_collector.emit_count(metric_name, count, tags=tags)


def capture_exception(exception: Exception, context: Optional[Dict[str, Any]] = None):
    """
    Convenience function to capture an exception.
    
    Args:
        exception: Exception to capture
        context: Additional context
    """
    exception_tracker.capture_exception(exception, context=context)


def get_observability_summary() -> Dict:
    """
    Get summary of all observability data.
    
    Returns:
        Dict: Summary with metrics and exceptions
    """
    return {
        'metrics': {
            'total_count': len(metrics_collector.get_metrics()),
            'metrics': metrics_collector.get_metrics()
        },
        'exceptions': {
            'total_count': len(exception_tracker.get_exceptions()),
            'exceptions': exception_tracker.get_exceptions()
        },
        'timestamp': datetime.now().isoformat()
    }


def clear_observability_data():
    """Clear all collected observability data."""
    metrics_collector.clear_metrics()
    exception_tracker.clear_exceptions()
    logger.info("🗑️ Observability data cleared")


def export_metrics_datadog() -> str:
    """Export metrics in Datadog format."""
    return metrics_collector.format_datadog()


def export_metrics_prometheus() -> str:
    """Export metrics in Prometheus format."""
    return metrics_collector.format_prometheus()


def export_exceptions_sentry() -> str:
    """Export exceptions in Sentry format."""
    return exception_tracker.format_sentry()


logger.info("✓ Azure ML observability layer loaded (Phase 20A)")
