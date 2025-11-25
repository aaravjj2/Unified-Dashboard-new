"""
Telemetry Proxy (Phase 4 - Hybrid Readiness)

Lightweight event tracker that stores telemetry locally.
Mirrors Azure Application Insights schema for compatibility.

Telemetry is written to /data/hybrid_logs/telemetry.jsonl in JSONL format.

Usage:
    >>> proxy = TelemetryProxy()
    >>> proxy.track_event('prediction_completed', {'ticker': 'AAPL', 'latency_ms': 350})
    >>> proxy.track_metric('forecast_accuracy', 0.92)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEMETRY_DIR = Path(__file__).parent.parent.parent / "data" / "hybrid_logs"
TELEMETRY_FILE = TELEMETRY_DIR / "telemetry.jsonl"

# Ensure directory exists
TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# TELEMETRY EVENT SCHEMAS
# ============================================================================

@dataclass
class TelemetryEvent:
    """Base telemetry event (mirrors Application Insights customEvent)."""
    
    timestamp: str
    event_type: str  # 'event', 'metric', 'request', 'dependency', 'exception'
    name: str
    properties: Dict[str, Any]
    measurements: Dict[str, float]
    instrumentation_key: str = "local-stub-key"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MetricEvent:
    """Metric telemetry event."""
    
    timestamp: str
    metric_name: str
    value: float
    properties: Dict[str, Any]
    count: int = 1
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    instrumentation_key: str = "local-stub-key"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RequestEvent:
    """Request/operation telemetry event."""
    
    timestamp: str
    name: str
    duration_ms: float
    success: bool
    response_code: int
    properties: Dict[str, Any]
    instrumentation_key: str = "local-stub-key"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================================
# TELEMETRY PROXY
# ============================================================================

class TelemetryProxy:
    """
    Telemetry collection proxy.
    
    Stores events locally in JSONL format matching Azure Application Insights schema.
    Provides methods for tracking events, metrics, requests, dependencies, and exceptions.
    
    Example:
        >>> proxy = TelemetryProxy()
        >>> proxy.track_event('model_training_started', {'model_type': 'rf'})
        >>> proxy.track_metric('accuracy', 0.92, {'model': 'rf', 'ticker': 'AAPL'})
        >>> proxy.track_request('predict_endpoint', 250.5, True, 200)
    """
    
    def __init__(
        self,
        instrumentation_key: str = "local-stub-key",
        flush_interval_seconds: int = 60
    ):
        """
        Initialize telemetry proxy.
        
        Args:
            instrumentation_key: Instrumentation key (for Azure compatibility)
            flush_interval_seconds: Auto-flush interval (0 = immediate write)
        """
        self.instrumentation_key = instrumentation_key
        self.flush_interval = flush_interval_seconds
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush = time.time()
        
        # Initialize telemetry file
        if not TELEMETRY_FILE.exists():
            TELEMETRY_FILE.touch()
        
        logger.info(f"📊 TelemetryProxy initialized (key={instrumentation_key[:12]}...)")
    
    def track_event(
        self,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        measurements: Optional[Dict[str, float]] = None
    ):
        """
        Track custom event.
        
        Args:
            event_name: Event name
            properties: Event properties (dimensions)
            measurements: Event measurements (numeric metrics)
        
        Example:
            >>> proxy.track_event(
            ...     'prediction_completed',
            ...     properties={'ticker': 'AAPL', 'model': 'rf'},
            ...     measurements={'latency_ms': 350.0, 'confidence': 0.85}
            ... )
        """
        event = TelemetryEvent(
            timestamp=datetime.now().isoformat(),
            event_type='customEvent',
            name=event_name,
            properties=properties or {},
            measurements=measurements or {},
            instrumentation_key=self.instrumentation_key
        )
        
        self._write_event(event.to_dict())
        logger.debug(f"📝 Tracked event: {event_name}")
    
    def track_metric(
        self,
        metric_name: str,
        value: float,
        properties: Optional[Dict[str, Any]] = None,
        count: int = 1,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ):
        """
        Track metric value.
        
        Args:
            metric_name: Metric name
            value: Metric value
            properties: Metric properties (dimensions)
            count: Number of measurements (for aggregated metrics)
            min_value: Minimum value (for aggregated metrics)
            max_value: Maximum value (for aggregated metrics)
        
        Example:
            >>> proxy.track_metric('forecast_accuracy', 0.92, {'model': 'rf'})
            >>> proxy.track_metric('latency_ms', 350.0, count=10, min_value=200.0, max_value=500.0)
        """
        event = MetricEvent(
            timestamp=datetime.now().isoformat(),
            metric_name=metric_name,
            value=value,
            properties=properties or {},
            count=count,
            min_value=min_value if min_value is not None else value,
            max_value=max_value if max_value is not None else value,
            instrumentation_key=self.instrumentation_key
        )
        
        self._write_event(event.to_dict())
        logger.debug(f"📈 Tracked metric: {metric_name}={value}")
    
    def track_request(
        self,
        name: str,
        duration_ms: float,
        success: bool,
        response_code: int = 200,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Track HTTP request or operation.
        
        Args:
            name: Request name
            duration_ms: Request duration in milliseconds
            success: Whether request succeeded
            response_code: HTTP response code
            properties: Request properties
        
        Example:
            >>> proxy.track_request(
            ...     'forecast_api',
            ...     duration_ms=350.5,
            ...     success=True,
            ...     response_code=200,
            ...     properties={'ticker': 'AAPL'}
            ... )
        """
        event = RequestEvent(
            timestamp=datetime.now().isoformat(),
            name=name,
            duration_ms=duration_ms,
            success=success,
            response_code=response_code,
            properties=properties or {},
            instrumentation_key=self.instrumentation_key
        )
        
        self._write_event(event.to_dict())
        logger.debug(f"🌐 Tracked request: {name} ({duration_ms:.0f}ms, success={success})")
    
    def track_dependency(
        self,
        name: str,
        dependency_type: str,
        target: str,
        duration_ms: float,
        success: bool,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Track external dependency call.
        
        Args:
            name: Dependency name
            dependency_type: Type of dependency ('HTTP', 'SQL', 'Azure Blob', etc.)
            target: Dependency target (URL, database, etc.)
            duration_ms: Call duration in milliseconds
            success: Whether call succeeded
            properties: Dependency properties
        
        Example:
            >>> proxy.track_dependency(
            ...     'azure_blob_read',
            ...     'Azure Blob',
            ...     'ml-predictions/AAPL.json',
            ...     120.0,
            ...     True
            ... )
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'dependency',
            'name': name,
            'dependency_type': dependency_type,
            'target': target,
            'duration_ms': duration_ms,
            'success': success,
            'properties': properties or {},
            'instrumentation_key': self.instrumentation_key
        }
        
        self._write_event(event)
        logger.debug(f"🔗 Tracked dependency: {name} -> {target} ({duration_ms:.0f}ms)")
    
    def track_exception(
        self,
        exception: Exception,
        properties: Optional[Dict[str, Any]] = None,
        measurements: Optional[Dict[str, float]] = None
    ):
        """
        Track exception.
        
        Args:
            exception: Exception object
            properties: Exception properties
            measurements: Exception measurements
        
        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     proxy.track_exception(e, {'operation': 'forecast'})
        """
        import traceback
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'exception',
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'stack_trace': traceback.format_exc(),
            'properties': properties or {},
            'measurements': measurements or {},
            'instrumentation_key': self.instrumentation_key
        }
        
        self._write_event(event)
        logger.error(f"❌ Tracked exception: {type(exception).__name__}: {exception}")
    
    def _write_event(self, event: Dict[str, Any]):
        """
        Write event to telemetry file.
        
        Args:
            event: Event dictionary
        """
        # Add to buffer
        self.buffer.append(event)
        
        # Check if we should flush
        if self.flush_interval == 0 or (time.time() - self.last_flush) >= self.flush_interval:
            self.flush()
    
    def flush(self):
        """Flush buffered events to disk."""
        if not self.buffer:
            return
        
        with TELEMETRY_FILE.open('a') as f:
            for event in self.buffer:
                f.write(json.dumps(event) + '\n')
        
        num_events = len(self.buffer)
        self.buffer.clear()
        self.last_flush = time.time()
        
        logger.debug(f"💾 Flushed {num_events} telemetry events to disk")
    
    def read_events(
        self,
        limit: Optional[int] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Read telemetry events from file.
        
        Args:
            limit: Maximum number of events to return (None = all)
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
        
        Returns:
            List of event dictionaries
        
        Example:
            >>> events = proxy.read_events(limit=100, event_type='customEvent')
            >>> for event in events:
            ...     print(event['name'], event['timestamp'])
        """
        if not TELEMETRY_FILE.exists():
            return []
        
        events = []
        
        with TELEMETRY_FILE.open('r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    
                    # Apply filters
                    if event_type and event.get('event_type') != event_type:
                        continue
                    
                    if start_time or end_time:
                        event_time = datetime.fromisoformat(event['timestamp'])
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                    
                    events.append(event)
                    
                    # Check limit
                    if limit and len(events) >= limit:
                        break
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in telemetry file: {line[:50]}...")
                    continue
        
        logger.debug(f"📖 Read {len(events)} telemetry events")
        return events
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get telemetry summary statistics.
        
        Returns:
            Summary dictionary with counts, averages, etc.
        
        Example:
            >>> summary = proxy.get_summary()
            >>> print(f"Total events: {summary['total_events']}")
            >>> print(f"Event types: {summary['event_types']}")
        """
        events = self.read_events()
        
        if not events:
            return {
                'total_events': 0,
                'event_types': {},
                'time_range': None
            }
        
        # Count event types
        event_types = {}
        for event in events:
            event_type = event.get('event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        # Get time range
        timestamps = [datetime.fromisoformat(e['timestamp']) for e in events]
        time_range = {
            'start': min(timestamps).isoformat(),
            'end': max(timestamps).isoformat(),
            'duration_hours': (max(timestamps) - min(timestamps)).total_seconds() / 3600
        }
        
        # Calculate metrics summary
        metric_events = [e for e in events if e.get('event_type') == 'metric']
        metric_summary = {}
        
        for event in metric_events:
            metric_name = event.get('metric_name')
            if metric_name:
                if metric_name not in metric_summary:
                    metric_summary[metric_name] = []
                metric_summary[metric_name].append(event.get('value', 0))
        
        # Compute averages
        metric_averages = {
            name: sum(values) / len(values)
            for name, values in metric_summary.items()
        }
        
        return {
            'total_events': len(events),
            'event_types': event_types,
            'time_range': time_range,
            'metric_averages': metric_averages,
            'unique_metrics': len(metric_summary)
        }
    
    def clear_telemetry(self):
        """Clear all telemetry data (truncate file)."""
        TELEMETRY_FILE.write_text('')
        self.buffer.clear()
        logger.info("🗑️  Cleared all telemetry data")


# ============================================================================
# GLOBAL TELEMETRY INSTANCE
# ============================================================================

# Singleton telemetry instance for dashboard use
_global_proxy: Optional[TelemetryProxy] = None


def get_telemetry() -> TelemetryProxy:
    """
    Get global TelemetryProxy instance.
    
    Returns:
        Shared TelemetryProxy instance
    """
    global _global_proxy
    
    if _global_proxy is None:
        _global_proxy = TelemetryProxy()
    
    return _global_proxy


logger.info("✓ Telemetry Proxy loaded (Phase 4 - Hybrid Readiness)")
