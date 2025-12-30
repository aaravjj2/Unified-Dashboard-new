"""
Options Bots Tab Layout
=======================
A dedicated tab for automated options trading bots.
Inspired by OptionsAlpha - fully automated, no Python scripts required.

Features:
- Connection panel (Alpaca API status)
- Live market data panel
- Bot builder with templates
- Active bots management
- Trade history & performance
- Event logs
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Optional

# Import UI components from options engine
try:
    from financial_dashboard.engines.options_engine.dashboard_ui import (
        create_options_connection_panel,
        create_options_market_panel,
        create_bot_builder_panel,
        create_active_bots_panel,
    )
    OPTIONS_ENGINE_AVAILABLE = True
except ImportError:
    OPTIONS_ENGINE_AVAILABLE = False


def create_options_bots_layout() -> html.Div:
    """Create the main Options Bots tab layout."""
    
    if not OPTIONS_ENGINE_AVAILABLE:
        return html.Div([
            dbc.Alert([
                html.H4("Options Engine Not Available", className="alert-heading"),
                html.P("The options trading engine is not installed or configured."),
                html.Hr(),
                html.P([
                    "Please ensure the options engine is properly set up in ",
                    html.Code("financial_dashboard/engines/options_engine/"),
                ], className="mb-0"),
            ], color="warning", className="m-4"),
        ])
    
    return html.Div([
        # Page Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className="fas fa-robot me-2"),
                        "Options Trading Bots"
                    ], className="mb-1"),
                    html.P(
                        "Automated options strategies - fully managed from this dashboard",
                        className="text-muted mb-0"
                    ),
                ], className="mb-3"),
            ], width=8),
            dbc.Col([
                html.Div([
                    dbc.Button([
                        html.I(className="fas fa-sync-alt me-2"),
                        "Refresh All"
                    ], id="options-bots-refresh-all", color="primary", outline=True, size="sm", className="me-2"),
                    dbc.Button([
                        html.I(className="fas fa-cog me-2"),
                        "Settings"
                    ], id="options-bots-settings-btn", color="secondary", outline=True, size="sm"),
                ], className="text-end pt-2"),
            ], width=4),
        ], className="mb-4"),
        
        # Status Row - Connection + Market Data
        dbc.Row([
            dbc.Col([
                create_connection_status_card(),
            ], md=4, className="mb-3"),
            dbc.Col([
                create_market_overview_card(),
            ], md=8, className="mb-3"),
        ]),
        
        # Main Content Tabs
        dbc.Tabs([
            dbc.Tab(
                create_dashboard_tab(),
                label="Dashboard",
                tab_id="tab-bots-dashboard",
                className="pt-3",
            ),
            dbc.Tab(
                create_bot_builder_tab(),
                label="Create Bot",
                tab_id="tab-bots-builder",
                className="pt-3",
            ),
            dbc.Tab(
                create_active_bots_tab(),
                label="Active Bots",
                tab_id="tab-bots-active",
                className="pt-3",
            ),
            dbc.Tab(
                create_trade_history_tab(),
                label="Trade History",
                tab_id="tab-bots-history",
                className="pt-3",
            ),
            dbc.Tab(
                create_performance_tab(),
                label="Performance",
                tab_id="tab-bots-performance",
                className="pt-3",
            ),
            dbc.Tab(
                create_settings_tab(),
                label="Settings",
                tab_id="tab-bots-settings",
                className="pt-3",
            ),
        ], id="options-bots-tabs", active_tab="tab-bots-dashboard"),
        
        # Hidden stores for state management
        dcc.Store(id="options-bots-connection-store", data={}),
        dcc.Store(id="options-bots-active-bots-store", data=[]),
        dcc.Store(id="options-bots-selected-bot-store", data=None),
        dcc.Store(id="options-bots-trade-log-store", data=[]),
        
        # Refresh interval
        dcc.Interval(
            id="options-bots-refresh-interval",
            interval=30 * 1000,  # 30 seconds
            n_intervals=0,
        ),
        
        # Settings Modal
        create_settings_modal(),
        
    ], className="options-bots-container p-4", id="options-bots-main")


def create_connection_status_card() -> dbc.Card:
    """Create the API connection status card."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-plug me-2"),
            "Connection Status"
        ]),
        dbc.CardBody([
            html.Div(id="options-bots-connection-status", children=[
                # Alpaca API
                html.Div([
                    html.Div([
                        html.Span(className="status-dot status-loading me-2"),
                        html.Strong("Alpaca API"),
                    ], className="d-flex align-items-center"),
                    html.Small("Checking...", className="text-muted"),
                ], className="mb-3"),
                # yFinance
                html.Div([
                    html.Div([
                        html.Span(className="status-dot status-loading me-2"),
                        html.Strong("yFinance"),
                    ], className="d-flex align-items-center"),
                    html.Small("Checking...", className="text-muted"),
                ]),
            ]),
        ]),
    ], className="h-100")


def create_market_overview_card() -> dbc.Card:
    """Create the market overview card."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-line me-2"),
            "Market Overview"
        ]),
        dbc.CardBody([
            html.Div(id="options-bots-market-overview", children=[
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Small("Market Status", className="text-muted"),
                            html.H5("Loading...", id="options-bots-market-status"),
                        ]),
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.Small("SPY", className="text-muted"),
                            html.H5("--", id="options-bots-spy-price"),
                        ]),
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.Small("VIX", className="text-muted"),
                            html.H5("--", id="options-bots-vix-price"),
                        ]),
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.Small("GLD", className="text-muted"),
                            html.H5("--", id="options-bots-gld-price"),
                        ]),
                    ], width=3),
                ]),
            ]),
        ]),
    ], className="h-100")


def create_dashboard_tab() -> html.Div:
    """Create the main dashboard overview tab."""
    return html.Div([
        # Summary Stats Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-robot fa-2x text-primary mb-2"),
                            html.H3("0", id="options-bots-total-bots", className="mb-0"),
                            html.Small("Total Bots", className="text-muted"),
                        ], className="text-center"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-play-circle fa-2x text-success mb-2"),
                            html.H3("0", id="options-bots-running-bots", className="mb-0"),
                            html.Small("Running", className="text-muted"),
                        ], className="text-center"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-exchange-alt fa-2x text-info mb-2"),
                            html.H3("0", id="options-bots-total-trades", className="mb-0"),
                            html.Small("Total Trades", className="text-muted"),
                        ], className="text-center"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-dollar-sign fa-2x text-warning mb-2"),
                            html.H3("$0", id="options-bots-total-pnl", className="mb-0"),
                            html.Small("Total P&L", className="text-muted"),
                        ], className="text-center"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
        ]),
        
        # Active Bots Preview + Recent Activity
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.Span([
                                html.I(className="fas fa-robot me-2"),
                                "Active Bots"
                            ]),
                            dbc.Button(
                                "View All",
                                id="options-bots-view-all-btn",
                                color="link",
                                size="sm",
                                className="float-end p-0",
                            ),
                        ], className="d-flex justify-content-between align-items-center"),
                    ]),
                    dbc.CardBody([
                        html.Div(id="options-bots-active-preview", children=[
                            html.P("No active bots", className="text-muted text-center my-4"),
                        ]),
                    ]),
                ]),
            ], md=8, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-history me-2"),
                        "Recent Activity"
                    ]),
                    dbc.CardBody([
                        html.Div(id="options-bots-recent-activity", children=[
                            html.P("No recent activity", className="text-muted text-center my-4"),
                        ], style={"maxHeight": "300px", "overflowY": "auto"}),
                    ]),
                ]),
            ], md=4, className="mb-3"),
        ]),
        
        # Quick Actions
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-bolt me-2"),
                        "Quick Actions"
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-plus me-2"),
                                    "Create GLD RSI Bot"
                                ], id="options-bots-quick-gld", color="success", className="w-100 mb-2"),
                            ], md=3),
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-plus me-2"),
                                    "Create SPY Iron Condor"
                                ], id="options-bots-quick-spy-ic", color="info", className="w-100 mb-2"),
                            ], md=3),
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-stop-circle me-2"),
                                    "Stop All Bots"
                                ], id="options-bots-stop-all", color="danger", outline=True, className="w-100 mb-2"),
                            ], md=3),
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-play-circle me-2"),
                                    "Start All Bots"
                                ], id="options-bots-start-all", color="success", outline=True, className="w-100 mb-2"),
                            ], md=3),
                        ]),
                    ]),
                ]),
            ], className="mb-3"),
        ]),
    ])


def create_bot_builder_tab() -> html.Div:
    """Create the bot builder tab."""
    return html.Div([
        dbc.Row([
            # Template Selection
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-th-large me-2"),
                        "Strategy Templates"
                    ]),
                    dbc.CardBody([
                        dbc.RadioItems(
                            id="options-bots-template-select",
                            options=[
                                {"label": "RSI Short Put Spread", "value": "rsi_put_spread"},
                                {"label": "VIX Iron Condor", "value": "vix_iron_condor"},
                                {"label": "Earnings Strangle", "value": "earnings_strangle"},
                                {"label": "Custom Recipe", "value": "custom"},
                            ],
                            value="rsi_put_spread",
                            className="mb-3",
                        ),
                        html.Hr(),
                        html.Div(id="options-bots-template-description", children=[
                            html.H6("RSI Short Put Spread"),
                            html.P("Sell put spreads when RSI indicates oversold conditions, with automatic position management.", className="text-muted small"),
                        ]),
                    ]),
                ]),
            ], md=4, className="mb-3"),
            
            # Configuration
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-sliders-h me-2"),
                        "Bot Configuration"
                    ]),
                    dbc.CardBody([
                        dbc.Form([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Bot Name"),
                                    dbc.Input(
                                        id="options-bots-name-input",
                                        type="text",
                                        placeholder="My Trading Bot",
                                        value="GLD RSI Bot",
                                    ),
                                ], md=6),
                                dbc.Col([
                                    dbc.Label("Symbol"),
                                    dbc.Select(
                                        id="options-bots-symbol-select",
                                        options=[
                                            {"label": "GLD - Gold ETF", "value": "GLD"},
                                            {"label": "SPY - S&P 500", "value": "SPY"},
                                            {"label": "QQQ - Nasdaq 100", "value": "QQQ"},
                                            {"label": "IWM - Russell 2000", "value": "IWM"},
                                            {"label": "TLT - Treasury Bonds", "value": "TLT"},
                                        ],
                                        value="GLD",
                                    ),
                                ], md=6),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("RSI Threshold"),
                                    dbc.Input(
                                        id="options-bots-rsi-threshold",
                                        type="number",
                                        min=10, max=90, step=5,
                                        value=40,
                                    ),
                                ], md=4),
                                dbc.Col([
                                    dbc.Label("Check Interval (sec)"),
                                    dbc.Input(
                                        id="options-bots-check-interval",
                                        type="number",
                                        min=10, max=3600, step=10,
                                        value=60,
                                    ),
                                ], md=4),
                                dbc.Col([
                                    dbc.Label("Max Positions"),
                                    dbc.Input(
                                        id="options-bots-max-positions",
                                        type="number",
                                        min=1, max=10, step=1,
                                        value=3,
                                    ),
                                ], md=4),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Take Profit %"),
                                    dbc.Input(
                                        id="options-bots-take-profit",
                                        type="number",
                                        min=10, max=100, step=5,
                                        value=50,
                                    ),
                                ], md=4),
                                dbc.Col([
                                    dbc.Label("Stop Loss %"),
                                    dbc.Input(
                                        id="options-bots-stop-loss",
                                        type="number",
                                        min=50, max=500, step=25,
                                        value=200,
                                    ),
                                ], md=4),
                                dbc.Col([
                                    dbc.Label("DTE Exit"),
                                    dbc.Input(
                                        id="options-bots-dte-exit",
                                        type="number",
                                        min=0, max=30, step=1,
                                        value=7,
                                    ),
                                ], md=4),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Checklist(
                                        id="options-bots-options",
                                        options=[
                                            {"label": "Paper Trading Mode", "value": "paper"},
                                            {"label": "Only Trade Market Hours", "value": "market_hours"},
                                            {"label": "Auto-Start on Create", "value": "auto_start"},
                                        ],
                                        value=["paper", "market_hours"],
                                        inline=True,
                                    ),
                                ]),
                            ], className="mb-3"),
                            html.Hr(),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-plus me-2"),
                                        "Create Bot"
                                    ], id="options-bots-create-btn", color="success", size="lg", className="w-100"),
                                ], md=6),
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-eye me-2"),
                                        "Preview Recipe"
                                    ], id="options-bots-preview-btn", color="secondary", outline=True, size="lg", className="w-100"),
                                ], md=6),
                            ]),
                        ]),
                    ]),
                ]),
            ], md=8, className="mb-3"),
        ]),
        
        # Recipe Preview
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-code me-2"),
                        "Recipe JSON Preview"
                    ]),
                    dbc.CardBody([
                        html.Pre(
                            id="options-bots-recipe-preview",
                            children="Select a template to see the recipe...",
                            className="bg-dark text-light p-3 rounded",
                            style={"maxHeight": "300px", "overflowY": "auto"},
                        ),
                    ]),
                ]),
            ], className="mb-3"),
        ]),
    ])


def create_active_bots_tab() -> html.Div:
    """Create the active bots management tab."""
    return html.Div([
        # Filter Row
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText(html.I(className="fas fa-search")),
                    dbc.Input(
                        id="options-bots-search",
                        type="text",
                        placeholder="Search bots...",
                    ),
                ]),
            ], md=4),
            dbc.Col([
                dbc.Select(
                    id="options-bots-status-filter",
                    options=[
                        {"label": "All Status", "value": "all"},
                        {"label": "Running", "value": "running"},
                        {"label": "Stopped", "value": "stopped"},
                        {"label": "Error", "value": "error"},
                    ],
                    value="all",
                ),
            ], md=2),
            dbc.Col([
                dbc.Select(
                    id="options-bots-symbol-filter",
                    options=[
                        {"label": "All Symbols", "value": "all"},
                        {"label": "GLD", "value": "GLD"},
                        {"label": "SPY", "value": "SPY"},
                        {"label": "QQQ", "value": "QQQ"},
                    ],
                    value="all",
                ),
            ], md=2),
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-sync-alt me-2"),
                    "Refresh"
                ], id="options-bots-refresh-list", color="primary", outline=True, className="w-100"),
            ], md=2),
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-download me-2"),
                    "Export"
                ], id="options-bots-export-btn", color="secondary", outline=True, className="w-100"),
            ], md=2),
        ], className="mb-4"),
        
        # Bots List
        html.Div(id="options-bots-list-container", children=[
            html.P("Loading bots...", className="text-muted text-center my-5"),
        ]),
    ])


def create_trade_history_tab() -> html.Div:
    """Create the trade history tab."""
    return html.Div([
        # Filters
        dbc.Row([
            dbc.Col([
                dbc.Label("Date Range"),
                dcc.DatePickerRange(
                    id="options-bots-date-range",
                    className="w-100",
                ),
            ], md=4),
            dbc.Col([
                dbc.Label("Bot Filter"),
                dbc.Select(
                    id="options-bots-history-bot-filter",
                    options=[{"label": "All Bots", "value": "all"}],
                    value="all",
                ),
            ], md=3),
            dbc.Col([
                dbc.Label("Action Type"),
                dbc.Select(
                    id="options-bots-action-filter",
                    options=[
                        {"label": "All Actions", "value": "all"},
                        {"label": "Open", "value": "OPEN"},
                        {"label": "Close", "value": "CLOSE"},
                    ],
                    value="all",
                ),
            ], md=2),
            dbc.Col([
                dbc.Label("⠀"),  # Spacer
                dbc.Button([
                    html.I(className="fas fa-filter me-2"),
                    "Apply Filters"
                ], id="options-bots-apply-filters", color="primary", className="w-100"),
            ], md=3),
        ], className="mb-4"),
        
        # Trade Table
        dbc.Card([
            dbc.CardBody([
                html.Div(id="options-bots-trade-table", children=[
                    html.P("No trades to display", className="text-muted text-center my-5"),
                ]),
            ]),
        ]),
    ])


def create_performance_tab() -> html.Div:
    """Create the performance analytics tab."""
    return html.Div([
        # Summary Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Win Rate", className="text-muted"),
                        html.H3("--", id="options-bots-win-rate"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Avg Win", className="text-muted"),
                        html.H3("--", id="options-bots-avg-win"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Avg Loss", className="text-muted"),
                        html.H3("--", id="options-bots-avg-loss"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Profit Factor", className="text-muted"),
                        html.H3("--", id="options-bots-profit-factor"),
                    ]),
                ]),
            ], md=3, className="mb-3"),
        ]),
        
        # Charts
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Cumulative P&L"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="options-bots-pnl-chart",
                            config={"displayModeBar": False},
                            style={"height": "300px"},
                        ),
                    ]),
                ]),
            ], md=8, className="mb-3"),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("P&L by Strategy"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="options-bots-strategy-chart",
                            config={"displayModeBar": False},
                            style={"height": "300px"},
                        ),
                    ]),
                ]),
            ], md=4, className="mb-3"),
        ]),
        
        # Monthly Breakdown
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Monthly Performance"),
                    dbc.CardBody([
                        html.Div(id="options-bots-monthly-table", children=[
                            html.P("No performance data available", className="text-muted text-center my-4"),
                        ]),
                    ]),
                ]),
            ], className="mb-3"),
        ]),
    ])


def create_settings_tab() -> html.Div:
    """Create the settings tab."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-key me-2"),
                        "API Configuration"
                    ]),
                    dbc.CardBody([
                        dbc.Form([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Alpaca API Key"),
                                    dbc.Input(
                                        id="options-bots-api-key",
                                        type="password",
                                        placeholder="APCA_API_KEY_ID",
                                    ),
                                ], md=6),
                                dbc.Col([
                                    dbc.Label("Alpaca Secret Key"),
                                    dbc.Input(
                                        id="options-bots-secret-key",
                                        type="password",
                                        placeholder="APCA_API_SECRET_KEY",
                                    ),
                                ], md=6),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Checklist(
                                        id="options-bots-api-options",
                                        options=[
                                            {"label": "Use Paper Trading API", "value": "paper"},
                                            {"label": "Enable Real-time Streaming", "value": "streaming"},
                                        ],
                                        value=["paper"],
                                    ),
                                ]),
                            ], className="mb-3"),
                            dbc.Button("Test Connection", id="options-bots-test-connection", color="primary"),
                        ]),
                    ]),
                ]),
            ], md=6, className="mb-3"),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-bell me-2"),
                        "Notifications"
                    ]),
                    dbc.CardBody([
                        dbc.Checklist(
                            id="options-bots-notifications",
                            options=[
                                {"label": "Trade Executed", "value": "trade"},
                                {"label": "Bot Started/Stopped", "value": "bot_status"},
                                {"label": "Error Alerts", "value": "errors"},
                                {"label": "Daily Summary", "value": "daily"},
                            ],
                            value=["trade", "errors"],
                            className="mb-3",
                        ),
                        dbc.Label("Email for Alerts"),
                        dbc.Input(
                            id="options-bots-alert-email",
                            type="email",
                            placeholder="your@email.com",
                        ),
                    ]),
                ]),
            ], md=6, className="mb-3"),
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-database me-2"),
                        "Data Management"
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-download me-2"),
                                    "Export All Data"
                                ], id="options-bots-export-all", color="primary", outline=True, className="me-2"),
                                dbc.Button([
                                    html.I(className="fas fa-upload me-2"),
                                    "Import Bots"
                                ], id="options-bots-import", color="secondary", outline=True, className="me-2"),
                                dbc.Button([
                                    html.I(className="fas fa-trash me-2"),
                                    "Clear All Data"
                                ], id="options-bots-clear-all", color="danger", outline=True),
                            ]),
                        ]),
                    ]),
                ]),
            ], className="mb-3"),
        ]),
    ])


def create_settings_modal() -> dbc.Modal:
    """Create the settings modal."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Bot Settings")),
        dbc.ModalBody([
            html.P("Configure your bot settings here."),
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="options-bots-settings-close", color="secondary"),
            dbc.Button("Save", id="options-bots-settings-save", color="primary"),
        ]),
    ], id="options-bots-settings-modal", is_open=False)


# CSS Styles for the tab
CUSTOM_CSS = """
.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.status-connected { background-color: #28a745; }
.status-disconnected { background-color: #dc3545; }
.status-loading { background-color: #ffc107; animation: pulse 1s infinite; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.options-bots-container {
    background-color: #f8f9fa;
    min-height: 100vh;
}
"""
