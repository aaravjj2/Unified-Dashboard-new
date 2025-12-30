"""
System Status Callbacks for Alpaca Options Dashboard

Registers callbacks for:
- Health data fetching
- Badge updates
- Gauge updates
- Status banner updates
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from dash import callback, Input, Output, dcc
from .health_service import get_health_service, get_data_fetcher
from .system_status_ui import create_health_badge, create_latency_gauge

logger = logging.getLogger(__name__)


def register_system_status_callbacks(app):
    """Register all system status callbacks."""
    
    @app.callback(
        Output("health-refresh-interval", "disabled"),
        Input("health-auto-refresh-switch", "value"),
        prevent_initial_call=True
    )
    def toggle_health_auto_refresh(enabled: bool):
        """Toggle auto-refresh interval."""
        return not enabled
    
    @app.callback(
        [
            Output("health-data-store", "data"),
            Output("feed-metrics-store", "data"),
            Output("health-last-update-time", "children")
        ],
        Input("health-refresh-interval", "n_intervals"),
        prevent_initial_call=False
    )
    def fetch_health_data(n_intervals: int):
        """Fetch health data from services (synchronous version)."""
        try:
            health_service = get_health_service()
            
            # Run async check safely without nested event loop issues
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running (Dash's event loop), use synchronous fallback
                    health_data = health_service.check_all_sync()
                else:
                    health_results = loop.run_until_complete(health_service.check_all())
                    health_data = {name: result.to_dict() for name, result in health_results.items()}
            except RuntimeError:
                # No event loop exists or nested issue, use sync fallback
                health_data = health_service.check_all_sync()
            
            # Get feed metrics
            data_fetcher = get_data_fetcher()
            feed_metrics = data_fetcher.get_all_metrics()
            
            last_update = datetime.utcnow().strftime("%H:%M:%S UTC")
            return health_data, feed_metrics, last_update
            
        except Exception as e:
            logger.error(f"Error fetching health data: {e}")
            return {
                "redis": {"status": "unknown", "latency_ms": 0, "message": f"Error: {str(e)[:25]}"},
                "timescaledb": {"status": "unknown", "latency_ms": 0, "message": f"Error: {str(e)[:25]}"}
            }, {}, datetime.utcnow().strftime("%H:%M:%S UTC")
    
    @app.callback(
        Output("health-badges-container", "children"),
        Input("health-data-store", "data")
    )
    def update_health_badges(health_data: Dict[str, Any]):
        """Update health status badges."""
        if not health_data:
            return [
                create_health_badge("redis"),
                create_health_badge("timescaledb")
            ]
        
        badges = []
        for service_name, data in health_data.items():
            badges.append(
                create_health_badge(
                    service_name=service_name,
                    status=data.get("status", "unknown"),
                    latency_ms=data.get("latency_ms", 0),
                    message=data.get("message", "No data")
                )
            )
        return badges
    
    @app.callback(
        Output("latency-gauges-container", "children"),
        Input("feed-metrics-store", "data")
    )
    def update_latency_gauges(feed_metrics: Dict[str, Any]):
        """Update latency gauge charts."""
        default_feeds = ["market_quotes", "options_chain", "historical_bars", "news_feed", "volatility_surface"]
        
        if not feed_metrics:
            return [
                dcc.Graph(figure=create_latency_gauge(f), config={'displayModeBar': False}, style={'height': '150px', 'width': '180px'})
                for f in default_feeds
            ]
        
        gauges = []
        for feed_name, metrics in feed_metrics.items():
            latency = metrics.get("latency", {}).get("avg_ms", 0)
            status = metrics.get("status", "disconnected")
            gauges.append(
                dcc.Graph(
                    figure=create_latency_gauge(feed_name, latency, status),
                    config={'displayModeBar': False},
                    style={'height': '150px', 'width': '180px'},
                    id=f"gauge-{feed_name}"
                )
            )
        return gauges
    
    @app.callback(
        [
            Output("overall-status-banner", "color"),
            Output("overall-status-text", "children")
        ],
        [
            Input("health-data-store", "data"),
            Input("feed-metrics-store", "data")
        ]
    )
    def update_overall_status(health_data: Dict[str, Any], feed_metrics: Dict[str, Any]):
        """Update overall status banner."""
        statuses = []
        
        for data in health_data.values():
            statuses.append(data.get("status", "unknown"))
        
        for metrics in feed_metrics.values():
            statuses.append(metrics.get("status", "disconnected"))
        
        if "unhealthy" in statuses or "error" in statuses:
            return "danger", "UNHEALTHY - Some services are down"
        elif "degraded" in statuses or "stale" in statuses:
            return "warning", "DEGRADED - Elevated latency detected"
        elif "unknown" in statuses or "disconnected" in statuses:
            return "secondary", "UNKNOWN - Waiting for health checks..."
        else:
            return "success", "HEALTHY - All systems operational"
    
    logger.info("✅ System status callbacks registered")
