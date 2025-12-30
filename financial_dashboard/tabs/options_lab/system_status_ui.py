"""
System Status UI Panel for Alpaca Options Dashboard

Provides:
- Redis/TimescaleDB health badges
- Feed latency gauges
- Overall system status banner
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

STATUS_COLORS = {
    "healthy": "#28a745", "degraded": "#ffc107", "unhealthy": "#dc3545", "unknown": "#6c757d",
    "connected": "#28a745", "disconnected": "#dc3545", "stale": "#ffc107", "error": "#dc3545",
}
STATUS_ICONS = {
    "healthy": "✓", "degraded": "⚠", "unhealthy": "✗", "unknown": "?",
    "connected": "●", "disconnected": "○", "stale": "◐", "error": "✗",
}


def create_health_badge(service_name: str, status: str = "unknown", latency_ms: float = 0, message: str = "Waiting...") -> dbc.Card:
    """Create a health status badge card."""
    color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    icon = STATUS_ICONS.get(status, "?")
    return dbc.Card([
        dbc.CardHeader(html.Div([
            html.Span(icon, style={"fontSize": "1.5rem", "color": color, "marginRight": "10px"}),
            html.Span(service_name.upper(), style={"fontWeight": "bold", "color": "#fff"})
        ], style={"display": "flex", "alignItems": "center"})),
        dbc.CardBody([
            html.H3(f"{latency_ms:.1f} ms", style={"color": color, "marginBottom": "5px"}, id=f"health-latency-{service_name}"),
            html.P(message, style={"color": "#aaa", "fontSize": "0.85rem", "marginBottom": "0"}, id=f"health-message-{service_name}")
        ])
    ], style={"backgroundColor": "#1e1e1e", "border": f"1px solid {color}", "borderRadius": "8px", "minWidth": "180px"}, id=f"health-badge-{service_name}")


def create_latency_gauge(feed_name: str, latency_ms: float = 0, status: str = "disconnected") -> go.Figure:
    """Create a latency gauge chart."""
    color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    max_range = 500.0 if "surface" in feed_name.lower() else 300.0 if "historical" in feed_name.lower() else 200.0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=latency_ms, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': feed_name.replace("_", " ").title(), 'font': {'color': '#fff', 'size': 12}},
        number={'font': {'color': color, 'size': 20}, 'suffix': ' ms'},
        gauge={
            'axis': {'range': [0, max_range], 'tickcolor': '#555'},
            'bar': {'color': color},
            'bgcolor': '#2a2a2a',
            'borderwidth': 1,
            'bordercolor': '#444',
            'steps': [
                {'range': [0, max_range * 0.3], 'color': '#1a3d1a'},
                {'range': [max_range * 0.3, max_range * 0.7], 'color': '#3d3d1a'},
                {'range': [max_range * 0.7, max_range], 'color': '#3d1a1a'}
            ]
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': '#fff'}, height=150, margin=dict(l=15, r=15, t=35, b=15))
    return fig


def create_system_status_panel() -> html.Div:
    """Create the System Status panel for the Alpaca Options Dashboard."""
    return html.Div([
        # Header
        html.Div([
            html.H4([
                html.Span("🔧 System Status", style={'marginRight': '10px'}),
                dbc.Badge("LIVE", color="success", className="me-2"),
            ], style={'color': '#ffffff', 'marginBottom': '5px'}),
            html.P("Real-time data fabric health monitoring", style={"color": "#888", "marginBottom": "15px", "fontSize": "13px"})
        ]),
        
        # Infrastructure Health Section
        html.Div([
            html.H6("Infrastructure Health", style={"color": "#00d4ff", "marginBottom": "10px"}),
            html.Div(
                id="health-badges-container",
                children=[
                    create_health_badge("redis"),
                    create_health_badge("timescaledb"),
                ],
                style={"display": "flex", "gap": "15px", "flexWrap": "wrap", "marginBottom": "20px"}
            )
        ], style={"backgroundColor": "#262a3d", "padding": "15px", "borderRadius": "8px", "marginBottom": "15px"}),
        
        # Feed Latency Monitor Section
        html.Div([
            html.H6("Feed Latency Monitor", style={"color": "#00d4ff", "marginBottom": "10px"}),
            html.Div(
                id="latency-gauges-container",
                children=[
                    dcc.Graph(figure=create_latency_gauge(f), config={'displayModeBar': False}, style={'height': '150px', 'width': '180px'})
                    for f in ["market_quotes", "options_chain", "historical_bars", "news_feed", "volatility_surface"]
                ],
                style={"display": "flex", "flexWrap": "wrap", "gap": "10px"}
            )
        ], style={"backgroundColor": "#262a3d", "padding": "15px", "borderRadius": "8px", "marginBottom": "15px"}),
        
        # Overall Status Banner
        dbc.Alert(
            id="overall-status-banner",
            children=[
                html.Strong("Overall Status: "),
                html.Span("Waiting for health checks...", id="overall-status-text")
            ],
            color="secondary",
            style={"textAlign": "center", "marginBottom": "15px"}
        ),
        
        # Auto-refresh controls
        html.Div([
            html.Div([
                html.Label("Auto-refresh: ", style={"color": "#fff", "marginRight": "10px", "fontSize": "13px"}),
                dbc.Switch(id="health-auto-refresh-switch", value=True),
                html.Span("Last updated: ", style={"color": "#888", "marginLeft": "20px", "fontSize": "12px"}),
                html.Span(datetime.utcnow().strftime("%H:%M:%S UTC"), id="health-last-update-time", style={"color": "#aaa", "fontSize": "12px"})
            ], style={"display": "flex", "alignItems": "center", "justifyContent": "flex-end"})
        ]),
        
        # Hidden stores and interval
        dcc.Store(id="health-data-store", data={}),
        dcc.Store(id="feed-metrics-store", data={}),
        dcc.Interval(id="health-refresh-interval", interval=1000, n_intervals=0, disabled=False)
        
    ], style={"padding": "15px"})
