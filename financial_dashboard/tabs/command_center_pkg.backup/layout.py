"""
Command Center Layout - Pure skeleton with stable IDs
No heavy imports or network calls at module import time.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import logging

logger = logging.getLogger(__name__)


def create_layout():
    """
    Create Command Center skeleton layout.
    Returns a pure layout structure with stable test IDs.
    Widgets are lazy-loaded via callbacks to prevent import-time overhead.
    """
    logger.info("🎯 Creating Command Center layout skeleton")
    
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2("🎯 Command Center", id="cc-header", className="mb-3"),
                html.P("Central mission control and diagnostics", className="text-muted"),
            ])
        ], className="mb-4"),
        
        # System Status Banner
        dbc.Row([
            dbc.Col([
                dbc.Alert(
                    id="cc-system-status",
                    children=[
                        html.Div([
                            html.Strong("System Status: "),
                            html.Span("Initializing...", id="cc-status-text"),
                        ]),
                    ],
                    color="info",
                    className="mb-3"
                ),
            ])
        ]),
        
        # Action Bar
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(
                        "🔍 Run Smoke Tests",
                        id="cc-run-smoke-btn",
                        color="primary",
                        size="sm",
                        n_clicks=0
                    ),
                    dbc.Button(
                        "🔄 Refresh Data",
                        id="cc-refresh-btn",
                        color="secondary",
                        size="sm",
                        n_clicks=0
                    ),
                ], className="mb-3"),
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
