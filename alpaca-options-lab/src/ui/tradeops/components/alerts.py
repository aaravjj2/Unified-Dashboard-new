"""
Alerts Components - Phase 5 TradeOps

UI components for displaying alerts:
- Live Alerts Feed
- Alert Cards (color-coded by severity)
"""

from dash import html
import dash_bootstrap_components as dbc
from typing import List, Dict, Any, Optional


def create_alert_card(alert: Dict[str, Any]) -> dbc.Card:
    """
    Create a color-coded alert card.
    
    Args:
        alert: Alert dictionary with type, severity, title, message, timestamp
        
    Returns:
        Bootstrap card component
    """
    severity = alert.get("severity", "info")
    alert_type = alert.get("alert_type", "system_info")
    
    # Color mapping
    color_map = {
        "critical": "danger",
        "warning": "warning",
        "info": "info"
    }
    color = color_map.get(severity, "secondary")
    
    # Icon mapping
    icon_map = {
        "iv_spike": "🔥",
        "price_gap": "📊",
        "volume_surge": "📈",
        "position_alert": "⚠️",
        "risk_warning": "🛡️",
        "order_fill": "✅",
        "order_reject": "❌",
        "system_info": "ℹ️",
        "market_close": "🔔",
        "earnings_warning": "📅"
    }
    icon = icon_map.get(alert_type, "📢")
    
    # Format timestamp
    timestamp = alert.get("timestamp", "")
    if timestamp:
        # Show only time portion for recent alerts
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp)
            timestamp = dt.strftime("%H:%M:%S")
        except:
            pass
    
    ticker_badge = None
    if alert.get("ticker"):
        ticker_badge = dbc.Badge(
            alert["ticker"],
            color="light",
            text_color="dark",
            className="me-2"
        )
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(icon, style={"fontSize": "1.2rem", "marginRight": "8px"}),
                html.Strong(alert.get("title", "Alert"), style={"flex": "1"}),
                ticker_badge,
                html.Small(
                    timestamp,
                    className="text-muted"
                )
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"}),
            html.P(
                alert.get("message", ""),
                className="mb-0",
                style={"fontSize": "0.9rem", "color": "#adb5bd"}
            )
        ], style={"padding": "10px"})
    ], color=color, outline=True, className="mb-2", style={"backgroundColor": "rgba(30,33,48,0.9)"})


def create_alerts_feed(alerts: Optional[List[Dict[str, Any]]] = None) -> html.Div:
    """
    Create the Live Alerts Feed panel.
    
    Args:
        alerts: List of alert dictionaries
        
    Returns:
        Div containing the alerts feed
    """
    if not alerts:
        alerts = []
    
    alert_cards = [create_alert_card(alert) for alert in alerts]
    
    if not alert_cards:
        alert_cards = [
            html.Div([
                html.Span("📭", style={"fontSize": "2rem", "opacity": "0.5"}),
                html.P("No alerts", className="text-muted mt-2")
            ], style={"textAlign": "center", "padding": "40px"})
        ]
    
    return html.Div([
        # Header
        html.Div([
            html.H5([
                html.Span("🔔 ", style={"marginRight": "8px"}),
                "Live Alerts"
            ], style={"margin": "0", "color": "#fff"}),
            dbc.Badge(
                str(len(alerts)) if alerts else "0",
                color="info",
                pill=True,
                className="ms-2"
            )
        ], style={
            "display": "flex",
            "alignItems": "center",
            "marginBottom": "15px",
            "paddingBottom": "10px",
            "borderBottom": "1px solid #333"
        }),
        
        # Alerts container (scrollable)
        html.Div(
            id="feed-alerts",
            children=alert_cards,
            style={
                "maxHeight": "400px",
                "overflowY": "auto",
                "paddingRight": "5px"
            }
        )
    ], style={
        "backgroundColor": "#1e2130",
        "padding": "15px",
        "borderRadius": "8px",
        "height": "100%"
    })
