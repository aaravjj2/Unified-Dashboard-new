"""
System Status Page - Health monitoring dashboard for data fabric components.
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

STATUS_COLORS = {
    "healthy": "#28a745", "degraded": "#ffc107", "unhealthy": "#dc3545",
    "unknown": "#6c757d", "connected": "#28a745", "disconnected": "#dc3545",
    "stale": "#ffc107", "error": "#dc3545",
}
STATUS_ICONS = {
    "healthy": "✓", "degraded": "⚠", "unhealthy": "✗", "unknown": "?",
    "connected": "●", "disconnected": "○", "stale": "◐", "error": "✗",
}

def create_health_badge(service_name: str, status: str, latency_ms: float, message: str) -> dbc.Card:
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
    ], style={"backgroundColor": "#1e1e1e", "border": f"1px solid {color}", "borderRadius": "8px", "minWidth": "200px"}, id=f"health-badge-{service_name}")

def create_latency_gauge(feed_name: str, latency_ms: float, status: str) -> go.Figure:
    color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    max_range = 500.0 if "surface" in feed_name.lower() else 300.0 if "historical" in feed_name.lower() else 200.0
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=latency_ms, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': feed_name.replace("_", " ").title(), 'font': {'color': '#fff', 'size': 14}},
        number={'font': {'color': color, 'size': 24}, 'suffix': ' ms'},
        gauge={'axis': {'range': [0, max_range], 'tickcolor': '#555'}, 'bar': {'color': color}, 'bgcolor': '#2a2a2a', 'borderwidth': 1, 'bordercolor': '#444',
               'steps': [{'range': [0, max_range * 0.3], 'color': '#1a3d1a'}, {'range': [max_range * 0.3, max_range * 0.7], 'color': '#3d3d1a'}, {'range': [max_range * 0.7, max_range], 'color': '#3d1a1a'}]}
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': '#fff'}, height=180, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def create_layout() -> html.Div:
    return html.Div([
        dbc.Row([dbc.Col([html.H2("📊 System Status", style={"color": "#fff", "marginBottom": "5px"}), html.P("Real-time data fabric health monitoring", style={"color": "#888", "marginBottom": "20px"})])]),
        dbc.Row([dbc.Col([html.H5("Infrastructure Health", style={"color": "#fff", "marginBottom": "15px"}),
            html.Div(id="health-badges-container", children=[create_health_badge("redis", "unknown", 0, "Waiting..."), create_health_badge("timescaledb", "unknown", 0, "Waiting...")], style={"display": "flex", "gap": "20px", "flexWrap": "wrap"})])], style={"marginBottom": "30px"}),
        dbc.Row([dbc.Col([html.H5("Feed Latency Monitor", style={"color": "#fff", "marginBottom": "15px"}),
            html.Div(id="latency-gauges-container", children=[dcc.Graph(figure=create_latency_gauge(f, 0, "disconnected"), config={'displayModeBar': False}, style={'height': '180px'}) for f in ["market_quotes", "options_chain", "historical_bars", "news_feed", "volatility_surface"]],
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))", "gap": "15px"})])], style={"marginBottom": "30px"}),
        dbc.Row([dbc.Col([dbc.Alert(id="overall-status-banner", children=[html.Strong("Overall Status: "), html.Span("Waiting...", id="overall-status-text")], color="secondary", style={"textAlign": "center"})])], style={"marginBottom": "20px"}),
        dbc.Row([dbc.Col([html.Div([html.Label("Auto-refresh: ", style={"color": "#fff", "marginRight": "10px"}), dbc.Switch(id="auto-refresh-switch", value=True), html.Span("Last updated: ", style={"color": "#888", "marginLeft": "20px"}), html.Span(datetime.utcnow().strftime("%H:%M:%S UTC"), id="last-update-time", style={"color": "#aaa"})], style={"display": "flex", "alignItems": "center", "justifyContent": "flex-end"})])]),
        dcc.Store(id="health-data-store", data={}), dcc.Store(id="feed-metrics-store", data={}),
        dcc.Interval(id="health-refresh-interval", interval=1000, n_intervals=0, disabled=False)
    ], style={"padding": "20px", "backgroundColor": "#121212", "minHeight": "100vh"}, id="system-status-page")

def register_system_status_callbacks(app):
    from dash import Input, Output
    @app.callback(Output("health-refresh-interval", "disabled"), Input("auto-refresh-switch", "value"))
    def toggle_auto_refresh(enabled): return not enabled
    @app.callback([Output("health-data-store", "data"), Output("feed-metrics-store", "data"), Output("last-update-time", "children")], Input("health-refresh-interval", "n_intervals"), prevent_initial_call=False)
    def fetch_health_data(n):
        try:
            from financial_dashboard.engines.data import get_health_service, get_data_fetcher
            hs = get_health_service()
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try: hr = loop.run_until_complete(hs.check_all()); hd = {n: r.to_dict() for n, r in hr.items()}
            finally: loop.close()
            df = get_data_fetcher(); fm = df.get_all_metrics_dict()
            return hd, fm, datetime.utcnow().strftime("%H:%M:%S UTC")
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"redis": {"status": "unknown", "latency_ms": 0, "message": str(e)[:30]}, "timescaledb": {"status": "unknown", "latency_ms": 0, "message": str(e)[:30]}}, {}, datetime.utcnow().strftime("%H:%M:%S UTC")
    @app.callback(Output("health-badges-container", "children"), Input("health-data-store", "data"))
    def update_badges(hd):
        if not hd: return [create_health_badge("redis", "unknown", 0, "No data"), create_health_badge("timescaledb", "unknown", 0, "No data")]
        return [create_health_badge(n, d.get("status", "unknown"), d.get("latency_ms", 0), d.get("message", "No data")) for n, d in hd.items()]
    @app.callback(Output("latency-gauges-container", "children"), Input("feed-metrics-store", "data"))
    def update_gauges(fm):
        if not fm: return [dcc.Graph(figure=create_latency_gauge(f, 0, "disconnected"), config={'displayModeBar': False}, style={'height': '180px'}) for f in ["market_quotes", "options_chain", "historical_bars", "news_feed", "volatility_surface"]]
        return [dcc.Graph(figure=create_latency_gauge(n, m.get("latency", {}).get("avg_ms", 0), m.get("status", "disconnected")), config={'displayModeBar': False}, style={'height': '180px'}, id=f"gauge-{n}") for n, m in fm.items()]
    @app.callback([Output("overall-status-banner", "color"), Output("overall-status-text", "children")], [Input("health-data-store", "data"), Input("feed-metrics-store", "data")])
    def update_status(hd, fm):
        sts = [d.get("status", "unknown") for d in hd.values()] + [m.get("status", "disconnected") for m in fm.values()]
        if "unhealthy" in sts or "error" in sts: return "danger", "UNHEALTHY"
        elif "degraded" in sts or "stale" in sts: return "warning", "DEGRADED"
        elif "unknown" in sts or "disconnected" in sts: return "secondary", "UNKNOWN"
        return "success", "HEALTHY"
    logger.info("System status callbacks registered")
