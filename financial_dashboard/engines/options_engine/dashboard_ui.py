"""
Options Bot Dashboard UI - OptionsAlpha Style Interface
========================================================

Dashboard component for managing options trading bots without
any Python scripts - fully automated from the UI.

Features:
- Create bots with visual recipe builder
- Start/Stop/Delete bots with one click
- Real-time status monitoring
- Live market data display
- Trade history & event logs
- GLD ETF pre-configured templates

Similar to OptionsAlpha's automation dashboard.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER COMPONENTS
# =============================================================================

def create_status_badge(status: str) -> dbc.Badge:
    """Create status badge based on bot status."""
    color_map = {
        "running": "success",
        "stopped": "secondary",
        "paused": "warning",
        "error": "danger",
    }
    return dbc.Badge(
        status.upper(),
        color=color_map.get(status, "secondary"),
        className="ms-2",
        pill=True
    )


def create_stat_card(title: str, value: str, icon: str, color: str = "primary") -> dbc.Card:
    """Create a small stat card."""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon} text-{color} me-2"),
                html.Small(title, className="text-muted"),
            ]),
            html.H4(value, className=f"text-{color} mb-0 mt-1")
        ], className="py-2 px-3")
    ], className="h-100")


# =============================================================================
# CONNECTION STATUS PANEL
# =============================================================================

def create_options_connection_panel() -> dbc.Card:
    """Create connection status panel for Options Engine."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-plug me-2"),
                html.Strong("Options Engine Connection"),
                dbc.Badge("LIVE", color="success", className="ms-auto", pill=True, id="options-connection-badge")
            ], className="d-flex align-items-center")
        ], style={'backgroundColor': 'rgba(40, 167, 69, 0.15)'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Small("Alpaca API", className="text-muted d-block"),
                        html.Span(id="options-alpaca-status", children=[
                            dbc.Spinner(size="sm"),
                            " Checking..."
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Small("Market Status", className="text-muted d-block"),
                        html.Span(id="options-market-status", children="--", className="fw-bold")
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Small("Buying Power", className="text-muted d-block"),
                        html.Span(id="options-buying-power", children="$--", className="fw-bold text-success")
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Small("Active Bots", className="text-muted d-block"),
                        html.Span(id="options-active-bots", children="0", className="fw-bold text-primary")
                    ])
                ], width=3),
            ]),
            dbc.Button([
                html.I(className="fas fa-sync-alt me-1"),
                "Refresh"
            ], id="options-refresh-connection", color="outline-secondary", size="sm", className="mt-2")
        ], className="py-2")
    ], className="mb-3", style={'border': '1px solid rgba(40, 167, 69, 0.3)'})


# =============================================================================
# LIVE MARKET DATA PANEL
# =============================================================================

def create_options_market_panel() -> dbc.Card:
    """Create live market data panel for GLD and other symbols."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-chart-line me-2"),
                html.Strong("Live Market Data"),
                dbc.Badge("REAL-TIME", color="info", className="ms-auto", pill=True)
            ], className="d-flex align-items-center")
        ], style={'backgroundColor': 'rgba(0, 123, 255, 0.1)'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Small("Symbol", className="text-muted d-block"),
                        dcc.Dropdown(
                            id="options-symbol-select",
                            options=[
                                {"label": "GLD - Gold ETF", "value": "GLD"},
                                {"label": "SPY - S&P 500", "value": "SPY"},
                                {"label": "QQQ - Nasdaq", "value": "QQQ"},
                                {"label": "IWM - Russell 2000", "value": "IWM"},
                                {"label": "SLV - Silver ETF", "value": "SLV"},
                                {"label": "TLT - Treasury ETF", "value": "TLT"},
                            ],
                            value="GLD",
                            clearable=False,
                            style={'width': '100%'}
                        )
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("Last Price", className="text-muted d-block"),
                        html.Span(id="options-live-price", children="$--", className="fs-4 fw-bold text-info")
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("Change", className="text-muted d-block"),
                        html.Span(id="options-live-change", children="--", className="fs-5 fw-bold")
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("RSI (14)", className="text-muted d-block"),
                        html.Div([
                            html.Span(id="options-live-rsi", children="--", className="fs-4 fw-bold"),
                            html.Span(id="options-rsi-signal", className="ms-2")
                        ])
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("VIX", className="text-muted d-block"),
                        html.Span(id="options-live-vix", children="--", className="fs-4 fw-bold")
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("IV Rank", className="text-muted d-block"),
                        html.Span(id="options-live-ivrank", children="--", className="fs-5")
                    ])
                ], width=2),
            ]),
            # RSI Gauge
            dcc.Graph(
                id="options-rsi-gauge",
                config={'displayModeBar': False},
                style={'height': '100px', 'marginTop': '10px'}
            ),
            # Auto-refresh interval
            dcc.Interval(
                id="options-data-interval",
                interval=30 * 1000,  # 30 seconds
                n_intervals=0
            )
        ])
    ], className="mb-3", style={'border': '1px solid rgba(0, 123, 255, 0.3)'})


# =============================================================================
# BOT CREATION PANEL
# =============================================================================

def create_bot_builder_panel() -> dbc.Card:
    """Create the bot builder/creation panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-robot me-2"),
                html.Strong("Create Options Bot"),
                html.Small(" - No Code Required", className="text-muted ms-2")
            ], className="d-flex align-items-center")
        ], style={'backgroundColor': 'rgba(255, 193, 7, 0.15)'}),
        dbc.CardBody([
            dbc.Row([
                # Bot Name
                dbc.Col([
                    dbc.Label("Bot Name", className="small"),
                    dbc.Input(
                        id="options-bot-name",
                        type="text",
                        placeholder="My GLD Strategy",
                        value="GLD RSI Bot"
                    )
                ], width=3),
                
                # Symbol
                dbc.Col([
                    dbc.Label("Symbol", className="small"),
                    dcc.Dropdown(
                        id="options-bot-symbol",
                        options=[
                            {"label": "GLD", "value": "GLD"},
                            {"label": "SPY", "value": "SPY"},
                            {"label": "QQQ", "value": "QQQ"},
                            {"label": "SLV", "value": "SLV"},
                        ],
                        value="GLD",
                        clearable=False
                    )
                ], width=2),
                
                # Strategy Template
                dbc.Col([
                    dbc.Label("Strategy", className="small"),
                    dcc.Dropdown(
                        id="options-bot-strategy",
                        options=[
                            {"label": "Short Put Spread", "value": "short_put_spread"},
                            {"label": "Iron Condor", "value": "iron_condor"},
                            {"label": "Cash Secured Put", "value": "cash_secured_put"},
                            {"label": "Covered Call", "value": "covered_call"},
                            {"label": "Strangle", "value": "strangle"},
                        ],
                        value="short_put_spread",
                        clearable=False
                    )
                ], width=3),
                
                # Check Interval
                dbc.Col([
                    dbc.Label("Check Interval", className="small"),
                    dcc.Dropdown(
                        id="options-bot-interval",
                        options=[
                            {"label": "30 sec", "value": 30},
                            {"label": "1 min", "value": 60},
                            {"label": "5 min", "value": 300},
                            {"label": "15 min", "value": 900},
                        ],
                        value=60,
                        clearable=False
                    )
                ], width=2),
                
                # Create Button
                dbc.Col([
                    dbc.Label(" ", className="small d-block"),
                    dbc.Button([
                        html.I(className="fas fa-plus me-1"),
                        "Create Bot"
                    ], id="options-create-bot-btn", color="success", className="w-100")
                ], width=2),
            ], className="mb-3"),
            
            # Entry Conditions
            dbc.Row([
                dbc.Col([
                    html.H6("Entry Conditions", className="text-muted mb-2"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("RSI Below", className="small"),
                            dbc.Input(id="options-rsi-threshold", type="number", value=30, min=0, max=100)
                        ], width=3),
                        dbc.Col([
                            dbc.Label("VIX Above", className="small"),
                            dbc.Input(id="options-vix-threshold", type="number", value=20, min=0, max=100)
                        ], width=3),
                        dbc.Col([
                            dbc.Label("IV Rank Above", className="small"),
                            dbc.Input(id="options-iv-threshold", type="number", value=25, min=0, max=100)
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Market", className="small"),
                            dcc.Dropdown(
                                id="options-market-condition",
                                options=[
                                    {"label": "Must Be Open", "value": "open"},
                                    {"label": "Any Time", "value": "any"},
                                ],
                                value="open",
                                clearable=False
                            )
                        ], width=3),
                    ])
                ], width=12)
            ]),
            
            # Condition Preview
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                html.Strong("Condition: "),
                html.Span(id="options-condition-preview", children="RSI < 30 AND VIX > 20 AND IV_RANK > 25 AND Market = OPEN")
            ], color="info", className="mt-3 mb-0")
        ])
    ], className="mb-3")


# =============================================================================
# ACTIVE BOTS PANEL
# =============================================================================

def create_bot_card(
    bot_id: str,
    name: str,
    symbol: str,
    status: str,
    stats: dict
) -> dbc.Card:
    """Create a card for a single bot."""
    is_running = status == "running"
    pnl = stats.get('total_pnl', 0)
    pnl_color = "success" if pnl >= 0 else "danger"
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Strong(name),
                create_status_badge(status),
            ], className="d-flex align-items-center justify-content-between")
        ], style={
            'backgroundColor': 'rgba(40, 167, 69, 0.1)' if is_running else 'rgba(108, 117, 125, 0.1)'
        }),
        dbc.CardBody([
            # Symbol and Stats
            dbc.Row([
                dbc.Col([
                    html.Small("Symbol", className="text-muted d-block"),
                    html.Strong(symbol, className="text-primary fs-5")
                ], width=4),
                dbc.Col([
                    html.Small("Checks", className="text-muted d-block"),
                    html.Strong(str(stats.get('total_checks', 0)))
                ], width=4),
                dbc.Col([
                    html.Small("Trades", className="text-muted d-block"),
                    html.Strong(str(stats.get('trades_executed', 0)), className="text-success")
                ], width=4),
            ], className="mb-2"),
            
            # P&L
            html.Div([
                html.Small("P&L: ", className="text-muted"),
                html.Span(f"${pnl:,.2f}", className=f"fw-bold text-{pnl_color}")
            ], className="mb-2"),
            
            # Action buttons
            html.Div([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-play" if not is_running else "fas fa-stop")
                    ], 
                    id={"type": "bot-toggle", "index": bot_id},
                    color="success" if not is_running else "warning",
                    size="sm",
                    title="Start" if not is_running else "Stop"
                    ),
                    dbc.Button([
                        html.I(className="fas fa-sync-alt")
                    ],
                    id={"type": "bot-trigger", "index": bot_id},
                    color="info",
                    size="sm",
                    outline=True,
                    title="Trigger Once"
                    ),
                    dbc.Button([
                        html.I(className="fas fa-trash")
                    ],
                    id={"type": "bot-delete", "index": bot_id},
                    color="danger",
                    size="sm",
                    outline=True,
                    title="Delete"
                    ),
                ], size="sm")
            ], className="d-flex justify-content-end")
        ], className="py-2")
    ], className="mb-2", style={'border': f'1px solid {"#28a745" if is_running else "#6c757d"}'})


def create_active_bots_panel() -> dbc.Card:
    """Create the active bots management panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-list me-2"),
                html.Strong("Your Options Bots"),
                dbc.Button([
                    html.I(className="fas fa-sync-alt")
                ], id="options-refresh-bots", color="link", size="sm", className="ms-auto")
            ], className="d-flex align-items-center")
        ]),
        dbc.CardBody([
            # Bot cards container
            html.Div(id="options-bots-container", children=[
                # Placeholder - will be populated by callback
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "No bots created yet. Create one above!"
                ], color="info", className="text-center")
            ])
        ])
    ], className="h-100")


# =============================================================================
# TRADE LOG PANEL
# =============================================================================

def create_trade_log_panel() -> dbc.Card:
    """Create the trade log panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-history me-2"),
                html.Strong("Trade Log"),
            ], className="d-flex align-items-center")
        ]),
        dbc.CardBody([
            html.Div(id="options-trade-log", children=[
                # Placeholder - will be populated by callback
                html.Div([
                    html.I(className="fas fa-clock text-muted me-2"),
                    html.Span("No trades yet", className="text-muted")
                ], className="text-center py-3")
            ], style={'maxHeight': '300px', 'overflowY': 'auto'})
        ])
    ], className="h-100")


# =============================================================================
# EVENT LOG PANEL
# =============================================================================

def create_event_log_panel() -> dbc.Card:
    """Create the event log panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-stream me-2"),
                html.Strong("Event Log"),
                dbc.Badge(id="options-event-count", children="0", color="secondary", className="ms-2")
            ], className="d-flex align-items-center")
        ]),
        dbc.CardBody([
            html.Div(id="options-event-log", children=[
                # Placeholder - will be populated by callback
            ], style={'maxHeight': '200px', 'overflowY': 'auto', 'fontSize': '0.85em'})
        ])
    ])


# =============================================================================
# QUICK STATS
# =============================================================================

def create_quick_stats() -> dbc.Row:
    """Create quick stats row."""
    return dbc.Row([
        dbc.Col(create_stat_card("Active Bots", "0", "fa-robot", "primary"), width=3, id="stat-active-bots"),
        dbc.Col(create_stat_card("Today's Trades", "0", "fa-exchange-alt", "success"), width=3, id="stat-today-trades"),
        dbc.Col(create_stat_card("Total P&L", "$0.00", "fa-dollar-sign", "info"), width=3, id="stat-total-pnl"),
        dbc.Col(create_stat_card("Win Rate", "0%", "fa-chart-pie", "warning"), width=3, id="stat-win-rate"),
    ], className="mb-3")


# =============================================================================
# MAIN LAYOUT
# =============================================================================

def create_options_bots_layout() -> html.Div:
    """Create the main Options Bots layout."""
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-cogs me-2"),
                    "Options Trading Bots"
                ]),
                html.P("Automated options trading with no code required - like OptionsAlpha", 
                       className="text-muted mb-0")
            ], width=8),
            dbc.Col([
                dbc.Badge("GLD OPTIMIZED", color="warning", className="me-2", pill=True),
                dbc.Badge("PAPER TRADING", color="info", pill=True),
            ], width=4, className="text-end"),
        ], className="mb-4"),
        
        # Connection Status
        create_options_connection_panel(),
        
        # Live Market Data
        create_options_market_panel(),
        
        # Quick Stats
        create_quick_stats(),
        
        # Bot Builder
        create_bot_builder_panel(),
        
        # Main Content Row
        dbc.Row([
            # Active Bots Column
            dbc.Col([
                create_active_bots_panel()
            ], width=4),
            
            # Trade & Event Logs Column
            dbc.Col([
                create_trade_log_panel(),
                html.Div(className="mb-3"),
                create_event_log_panel(),
            ], width=8),
        ]),
        
        # Store for bot data
        dcc.Store(id="options-bots-store", data={}),
        
        # Interval for auto-refresh
        dcc.Interval(
            id="options-bots-interval",
            interval=5 * 1000,  # 5 seconds
            n_intervals=0
        ),
        
        # Confirmation modal
        dbc.Modal([
            dbc.ModalHeader("Confirm Action"),
            dbc.ModalBody(id="options-confirm-body"),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="options-confirm-cancel", color="secondary"),
                dbc.Button("Confirm", id="options-confirm-ok", color="danger"),
            ])
        ], id="options-confirm-modal", is_open=False),
        
        # Toast for notifications
        dbc.Toast(
            id="options-toast",
            header="Notification",
            is_open=False,
            dismissable=True,
            icon="info",
            duration=4000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 9999}
        ),
    ])


def get_layout():
    """Return the Options Bots subtab layout."""
    return create_options_bots_layout()


# =============================================================================
# FOR INTEGRATION INTO EXISTING BOTS.PY
# =============================================================================

def add_options_tab_to_existing() -> dbc.Tab:
    """
    Creates an Options Bot tab that can be added to existing bots page.
    
    Usage in bots.py:
    ```python
    from financial_dashboard.engines.options_engine.dashboard_ui import add_options_tab_to_existing
    
    dbc.Tabs([
        dbc.Tab(label="Strategy Bots", children=[...]),
        add_options_tab_to_existing(),  # Add this
    ])
    ```
    """
    return dbc.Tab(
        label="Options Bots",
        tab_id="options-bots-tab",
        children=[
            html.Div([
                create_options_bots_layout()
            ], className="p-3")
        ]
    )
