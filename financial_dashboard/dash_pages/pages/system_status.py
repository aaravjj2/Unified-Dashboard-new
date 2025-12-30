"""
System Status Page - Health monitoring dashboard for data fabric components.

Displays:
- Redis health status badge
- TimescaleDB health status badge
- Feed latency gauges
- Real-time system metrics
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


# Status color mapping
STATUS_COLORS = {
    "healthy": "#28a745",      # Green
    "degraded": "#ffc107",     # Yellow/Amber
    "unhealthy": "#dc3545",    # Red
    "unknown": "#6c757d",      # Gray
    "connected": "#28a745",    # Green
    "disconnected": "#dc3545", # Red
    "stale": "#ffc107",        # Yellow
    "error": "#dc3545",        # Red
}

STATUS_ICONS = {
    "healthy": "✓",
    "degraded": "⚠",
    "unhealthy": "✗",
    "unknown": "?",
    "connected": "●",
    "disconnected": "○",
    "stale": "◐",
    "error": "✗",
}


def create_health_badge(service_name: str, status: str, latency_ms: float, message: str) -> dbc.Card:
    """
    Create a health status badge card.
    
    Args:
        service_name: Name of the service
        status: Health status string
        latency_ms: Last measured latency
        message: Status message
    
    Returns:
        Bootstrap Card component with health badge
    """
    color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    icon = STATUS_ICONS.get(status, "?")
    
    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div([
                    html.Span(
                        icon,
                        style={
                            "fontSize": "1.5rem",
                            "color": color,
                            "marginRight": "10px"
                        }
                    ),
                    html.Span(
                        service_name.upper(),
                        style={"fontWeight": "bold", "color": "#fff"}
                    )
                ], style={"display": "flex", "alignItems": "center"})
            ),
            dbc.CardBody([
                html.H3(
                    f"{latency_ms:.1f} ms",
                    style={"color": color, "marginBottom": "5px"},
                    id=f"health-latency-{service_name}"
                ),
                html.P(
                    message,
                    style={"color": "#aaa", "fontSize": "0.85rem", "marginBottom": "0"},
                    id=f"health-message-{service_name}"
                )
            ])
        ],
        style={
            "backgroundColor": "#1e1e1e",
            "border": f"1px solid {color}",
            "borderRadius": "8px",
            "minWidth": "200px"
        },
        id=f"health-badge-{service_name}"
    )


def create_latency_gauge(feed_name: str, latency_ms: float, status: str) -> go.Figure:
    """
    Create a latency gauge chart.
    
    Args:
        feed_name: Name of the data feed
        latency_ms: Current latency value
        status: Feed status
    
    Returns:
        Plotly Figure with gauge chart
    """
    color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    
    # Determine max range based on feed type
    max_range = 200.0
    if "surface" in feed_name.lower():
        max_range = 500.0
    elif "historical" in feed_name.lower():
        max_range = 300.0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=latency_ms,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': feed_name.replace("_", " ").title(), 'font': {'color': '#fff', 'size': 14}},
        number={'font': {'color': color, 'size': 24}, 'suffix': ' ms'},
        gauge={
            'axis': {
                'range': [0, max_range],
                'tickcolor': '#555',
                'tickfont': {'color': '#888'}
            },
            'bar': {'color': color},
            'bgcolor': '#2a2a2a',
            'borderwidth': 1,
            'bordercolor': '#444',
            'steps': [
                {'range': [0, max_range * 0.3], 'color': '#1a3d1a'},
                {'range': [max_range * 0.3, max_range * 0.7], 'color': '#3d3d1a'},
                {'range': [max_range * 0.7, max_range], 'color': '#3d1a1a'}
            ],
            'threshold': {
                'line': {'color': '#ff0', 'width': 2},
                'thickness': 0.75,
                'value': max_range * 0.5
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#fff'},
        height=180,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_system_status_layout() -> html.Div:
    """
    Create the system status page layout.
    
    Returns:
        Dash HTML Div containing the full system status page
    """
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2(
                    "📊 System Status",
                    style={"color": "#fff", "marginBottom": "5px"}
                ),
                html.P(
                    "Real-time data fabric health monitoring",
                    style={"color": "#888", "marginBottom": "20px"}
                )
            ])
        ]),
        
        # Health Status Badges Section
        dbc.Row([
            dbc.Col([
                html.H5("Infrastructure Health", style={"color": "#fff", "marginBottom": "15px"}),
                html.Div(
                    id="health-badges-container",
                    style={"display": "flex", "gap": "20px", "flexWrap": "wrap"}
                )
            ])
        ], style={"marginBottom": "30px"}),
        
        # Feed Latency Section
        dbc.Row([
            dbc.Col([
                html.H5("Feed Latency Monitor", style={"color": "#fff", "marginBottom": "15px"}),
                html.Div(
                    id="latency-gauges-container",
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
                        "gap": "15px"
                    }
                )
            ])
        ], style={"marginBottom": "30px"}),
        
        # Overall Status Banner
        dbc.Row([
            dbc.Col([
                dbc.Alert(
                    id="overall-status-banner",
                    children=[
                        html.Strong("Overall Status: "),
                        html.Span(id="overall-status-text")
                    ],
                    color="success",
                    style={"textAlign": "center"}
                )
            ])
        ], style={"marginBottom": "20px"}),
        
        # Auto-refresh controls
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Label("Auto-refresh: ", style={"color": "#fff", "marginRight": "10px"}),
                    dbc.Switch(
                        id="auto-refresh-switch",
                        value=True,
                        style={"display": "inline-block"}
                    ),
                    html.Span(
                        "Last updated: ",
                        style={"color": "#888", "marginLeft": "20px"}
                    ),
                    html.Span(
                        id="last-update-time",
                        style={"color": "#aaa"}
                    )
                ], style={"display": "flex", "alignItems": "center", "justifyContent": "flex-end"})
            ])
        ]),
        
        # Hidden stores for data
        dcc.Store(id="health-data-store", data={}),
        dcc.Store(id="feed-metrics-store", data={}),
        
        # Interval for auto-refresh
        dcc.Interval(
            id="health-refresh-interval",
            interval=1000,  # 1 second
            n_intervals=0,
            disabled=False
        )
        
    ], style={
        "padding": "20px",
        "backgroundColor": "#121212",
        "minHeight": "100vh"
    }, id="system-status-page")


def register_system_status_callbacks(app):
    """
    Register Dash callbacks for system status page.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        Output("health-refresh-interval", "disabled"),
        Input("auto-refresh-switch", "value")
    )
    def toggle_auto_refresh(enabled: bool):
        """Toggle auto-refresh interval."""
        return not enabled
    
    @app.callback(
        [
            Output("health-data-store", "data"),
            Output("feed-metrics-store", "data"),
            Output("last-update-time", "children")
        ],
        Input("health-refresh-interval", "n_intervals"),
        prevent_initial_call=False
    )
    def fetch_health_data(n_intervals: int):
        """Fetch health data from services."""
        try:
            from financial_dashboard.engines.data import get_health_service, get_data_fetcher
            
            # Get health service data
            health_service = get_health_service()
            # Run async check synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                health_results = loop.run_until_complete(health_service.check_all())
                health_data = {
                    name: result.to_dict()
                    for name, result in health_results.items()
                }
            finally:
                loop.close()
            
            # Get feed metrics
            data_fetcher = get_data_fetcher()
            feed_metrics = data_fetcher.get_all_metrics_dict()
            
            # Current time
            last_update = datetime.utcnow().strftime("%H:%M:%S UTC")
            
            return health_data, feed_metrics, last_update
            
        except Exception as e:
            logger.error(f"Error fetching health data: {e}")
            # Return mock data on error
            return {
                "redis": {
                    "service_name": "redis",
                    "status": "unknown",
                    "latency_ms": 0,
                    "message": f"Error: {str(e)[:50]}"
                },
                "timescaledb": {
                    "service_name": "timescaledb",
                    "status": "unknown",
                    "latency_ms": 0,
                    "message": f"Error: {str(e)[:50]}"
                }
            }, {}, datetime.utcnow().strftime("%H:%M:%S UTC")
    
    @app.callback(
        Output("health-badges-container", "children"),
        Input("health-data-store", "data")
    )
    def update_health_badges(health_data: Dict[str, Any]):
        """Update health status badges."""
        if not health_data:
            return [
                create_health_badge("redis", "unknown", 0, "No data"),
                create_health_badge("timescaledb", "unknown", 0, "No data")
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
        if not feed_metrics:
            # Show default gauges with no data
            default_feeds = ["market_quotes", "options_chain", "historical_bars", "news_feed", "volatility_surface"]
            return [
                dcc.Graph(
                    figure=create_latency_gauge(feed, 0, "disconnected"),
                    config={'displayModeBar': False},
                    style={'height': '180px'}
                )
                for feed in default_feeds
            ]
        
        gauges = []
        for feed_name, metrics in feed_metrics.items():
            latency = metrics.get("latency", {}).get("avg_ms", 0)
            status = metrics.get("status", "disconnected")
            
            gauges.append(
                dcc.Graph(
                    figure=create_latency_gauge(feed_name, latency, status),
                    config={'displayModeBar': False},
                    style={'height': '180px'},
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
        
        # Collect health statuses
        for data in health_data.values():
            statuses.append(data.get("status", "unknown"))
        
        # Collect feed statuses
        for metrics in feed_metrics.values():
            statuses.append(metrics.get("status", "disconnected"))
        
        # Determine overall status
        if "unhealthy" in statuses or "error" in statuses:
            return "danger", "UNHEALTHY - Some services are down"
        elif "degraded" in statuses or "stale" in statuses:
            return "warning", "DEGRADED - Some services have elevated latency"
        elif "unknown" in statuses or "disconnected" in statuses:
            return "secondary", "UNKNOWN - Waiting for health checks..."
        else:
            return "success", "HEALTHY - All systems operational"
    
    logger.info("System status callbacks registered")


# Convenience function for getting health/feed modules
def get_health_service():
    """Import and return health service."""
    from financial_dashboard.engines.data.health_service import get_health_service as _get_health_service
    return _get_health_service()


def get_data_fetcher():
    """Import and return data fetcher."""
    from financial_dashboard.engines.data.data_fetcher import get_data_fetcher as _get_data_fetcher
    return _get_data_fetcher()
