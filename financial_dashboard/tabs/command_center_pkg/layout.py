"""
Command Center Layout - Enhanced with UX improvements
Includes loading states, tooltips, accessibility features, and better error handling.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import logging

logger = logging.getLogger(__name__)


def create_loading_skeleton(height="100px"):
    """Create animated loading skeleton placeholder."""
    return html.Div([
        html.Div(className="skeleton-line", style={
            "height": "20px",
            "backgroundColor": "rgba(255,255,255,0.1)",
            "borderRadius": "4px",
            "marginBottom": "8px",
            "animation": "pulse 1.5s infinite"
        }),
        html.Div(className="skeleton-line", style={
            "height": "20px",
            "backgroundColor": "rgba(255,255,255,0.08)",
            "borderRadius": "4px",
            "width": "80%",
            "animation": "pulse 1.5s infinite",
            "animationDelay": "0.2s"
        })
    ], style={"minHeight": height})


def create_metric_card(title, value_id, icon="📊", tooltip=None):
    """Create a reusable metric card with tooltip."""
    card = html.Div([
        html.Div([
            html.Span(icon, style={"fontSize": "24px", "marginRight": "8px"}),
            html.Div([
                html.Small(title, className="text-muted d-block"),
                html.H4(id=value_id, children="--", className="mb-0")
            ])
        ], className="d-flex align-items-center")
    ], className="p-2")
    
    if tooltip:
        return dbc.Tooltip(tooltip, target=value_id, placement="top")
    return card


def create_layout():
    """
    Create Command Center skeleton layout with enhanced UX.
    Returns a pure layout structure with stable test IDs.
    """
    logger.info("🎯 Creating Command Center layout skeleton")
    
    return dbc.Container([
        # CSS for loading animations
        html.Style("""
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .skeleton-line { animation: pulse 1.5s infinite; }
            .card:hover { transform: translateY(-2px); transition: transform 0.2s; }
            .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
            .status-online { background-color: #4ade80; }
            .status-offline { background-color: #ef4444; }
            .status-warning { background-color: #fbbf24; }
        """),
        
        # Header with system status
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.Span("🎯", style={"marginRight": "10px"}),
                        "Command Center"
                    ], id="cc-header", className="mb-1"),
                    html.P([
                        "Central mission control and diagnostics ",
                        html.Span("•", className="mx-2"),
                        html.Span(id="cc-last-updated", children="Last updated: --", className="small")
                    ], className="text-muted mb-0"),
                ], className="d-flex flex-column")
            ], md=8),
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span(className="status-dot", id="cc-status-dot"),
                        html.Span(id="cc-status-text", children="Checking...")
                    ], className="d-flex align-items-center"),
                ], className="text-end")
            ], md=4)
        ], className="mb-3 align-items-center"),
        
        # System Status Banner with connection indicators
        dbc.Row([
            dbc.Col([
                dbc.Alert(
                    id="cc-system-status",
                    children=[
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Span(className="status-dot status-online"),
                                    html.Span("Dashboard", className="me-3"),
                                ], className="d-inline-flex align-items-center")
                            ], width="auto"),
                            dbc.Col([
                                html.Div([
                                    html.Span(className="status-dot", id="cc-api-status-dot"),
                                    html.Span("API Services", id="cc-api-status", className="me-3"),
                                ], className="d-inline-flex align-items-center")
                            ], width="auto"),
                            dbc.Col([
                                html.Div([
                                    html.Span(className="status-dot", id="cc-alpaca-status-dot"),
                                    html.Span("Alpaca", id="cc-alpaca-status"),
                                ], className="d-inline-flex align-items-center")
                            ], width="auto"),
                        ], className="g-3")
                    ],
                    color="dark",
                    className="mb-3 py-2"
                ),
            ])
        ]),
        
        # Action Bar with tooltips
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(
                        [html.I(className="bi bi-play-circle me-1"), "Run Tests"],
                        id="cc-run-smoke-btn",
                        color="primary",
                        size="sm",
                        n_clicks=0
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh"],
                        id="cc-refresh-btn",
                        color="secondary",
                        size="sm",
                        n_clicks=0
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-gear me-1"), "Settings"],
                        id="cc-settings-btn",
                        color="outline-secondary",
                        size="sm",
                        n_clicks=0
                    ),
                ], className="mb-3"),
                # Tooltips
                dbc.Tooltip("Run smoke tests across all dashboard components", target="cc-run-smoke-btn"),
                dbc.Tooltip("Refresh all data from connected services", target="cc-refresh-btn"),
                dbc.Tooltip("Configure dashboard settings", target="cc-settings-btn"),
            ])
        ]),
        
        # Main Dashboard Grid
        dbc.Row([
            # Left Column: Picks & Portfolio
            dbc.Col([
                # Picks Widget
                dbc.Card([
                    dbc.CardHeader("📊 Picks Status"),
                    dbc.CardBody([
                        html.Div(id="cc-picks-card", children=[
                            html.P("Loading picks status...", className="text-muted"),
                        ]),
                        dbc.Button(
                            "Run Picks (Dry)",
                            id="cc-picks-run-btn",
                            color="success",
                            size="sm",
                            n_clicks=0,
                            className="mt-2"
                        ),
                        html.Small(
                            id="cc-picks-last-run-id",
                            children="Last run: N/A",
                            className="text-muted d-block mt-2"
                        ),
                    ]),
                ], className="mb-3"),
                
                # Portfolio Snapshot
                dbc.Card([
                    dbc.CardHeader("💼 Portfolio Snapshot"),
                    dbc.CardBody(
                        html.Div(id="cc-portfolio-snapshot", children=[
                            html.P("Loading portfolio...", className="text-muted"),
                        ])
                    ),
                ], className="mb-3"),
            ], md=6),
            
            # Right Column: Sentiment & Chat
            dbc.Col([
                # Market Sentiment Widget
                dbc.Card([
                    dbc.CardHeader("📈 Market Sentiment"),
                    dbc.CardBody([
                        html.Div(id="cc-sentiment-card", children=[
                            html.Div([
                                html.H4(
                                    "Neutral",
                                    id="cc-sentiment-indicator",
                                    className="text-muted"
                                ),
                                html.Small(
                                    "Score: 0.0",
                                    id="cc-sentiment-score",
                                    className="d-block"
                                ),
                                html.Small(
                                    "Last updated: N/A",
                                    id="cc-sentiment-last-updated",
                                    className="text-muted d-block mt-1"
                                ),
                            ]),
                        ]),
                        dbc.Button(
                            "View Details",
                            id="cc-sentiment-details-btn",
                            color="info",
                            size="sm",
                            className="mt-2",
                            n_clicks=0
                        ),
                    ]),
                ], className="mb-3"),
                
                # Chat Widget
                dbc.Card([
                    dbc.CardHeader("💬 Quick Query"),
                    dbc.CardBody([
                        html.Div(id="cc-chat-card", children=[
                            dbc.Input(
                                id="cc-chat-input",
                                placeholder="Ask about picks, portfolio, or market...",
                                type="text",
                                className="mb-2"
                            ),
                            dbc.Button(
                                "Send",
                                id="cc-chat-send",
                                color="primary",
                                size="sm",
                                n_clicks=0
                            ),
                            html.Div(
                                id="cc-chat-response",
                                className="mt-3",
                                style={"minHeight": "100px"}
                            ),
                        ]),
                    ]),
                ]),
            ], md=6),
        ], className="mb-4"),
        
        # Performance Insights Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("⚡ Performance Insights"),
                    dbc.CardBody(
                        html.Div(id="cc-perf-insights", children=[
                            html.P("Performance metrics loading...", className="text-muted"),
                        ])
                    ),
                ]),
            ])
        ], className="mb-4"),
        
        # Jobs & Admin Area
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🔧 Jobs & Background Tasks"),
                    dbc.CardBody(
                        html.Div(id="cc-jobs-card", children=[
                            html.P("Loading jobs status...", className="text-muted"),
                        ])
                    ),
                ], className="mb-3"),
            ], md=6),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🛠️ Admin Tools"),
                    dbc.CardBody([
                        html.Div(id="cc-admin-area", children=[
                            dbc.ButtonGroup([
                                dbc.Button(
                                    "Callback Map",
                                    id="cc-callback-map-btn",
                                    color="secondary",
                                    size="sm",
                                    n_clicks=0
                                ),
                                dbc.Button(
                                    "Reindex Data",
                                    id="cc-reindex-btn",
                                    color="warning",
                                    size="sm",
                                    n_clicks=0
                                ),
                            ], className="mb-2"),
                            html.Div(id="cc-admin-output", className="mt-2"),
                        ]),
                    ]),
                ]),
            ], md=6),
        ]),
        
        # Hidden stores for state management
        dcc.Store(id="cc-smoke-results", data=None),
        dcc.Store(id="cc-last-refresh", data=None),
        dcc.Interval(id="cc-auto-refresh", interval=60000, n_intervals=0),  # 60s auto-refresh
        
    ], fluid=True, className="command-center-container")
