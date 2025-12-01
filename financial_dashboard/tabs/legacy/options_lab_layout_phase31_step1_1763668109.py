"""
Options Lab Canonical Layout Module (Phase 31 Validation)

Provides 6 canonical subtabs with stable IDs:
1. Chain Viewer (id: options-chain-tab)
2. Greeks Calculator (id: options-greeks-tab)
3. IV Surface & Forecast (id: options-vol-tab)
4. Manual Trade / Paper Orders (id: options-manual-tab)
5. Backtester / Strategy (id: options-backtest-tab)
6. Settings (id: options-settings-tab)

All interactive controls follow the STABLE ID RULE (id starts with 'ol-').
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
import logging

logger = logging.getLogger(__name__)


def create_layout():
    """
    Safe layout factory for Options Lab.
    
    Returns:
        Dash component tree with error boundaries
    """
    try:
        return _build_safe_layout()
    except Exception as e:
        logger.error(f"Options Lab layout creation failed: {e}", exc_info=True)
        return _error_fallback_layout(e)


def _build_safe_layout():
    """Build the full Options Lab layout with 6 canonical subtabs."""
    return dbc.Container([
        # Header
        html.Div([
            html.H3("💹 Options Lab", className="mb-2"),
            html.P(
                "Comprehensive options analytics: chains, Greeks, forecasts, backtesting, and paper trading",
                className="mb-4", style={'color': '#000000'}
            )
        ]),
        
        # Global Ticker Input Row
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Ticker"),
                    dbc.Input(
                        id='ol-ticker-input',
                        type='text',
                        value='AAPL',
                        placeholder='Enter ticker...',
                        style={'textTransform': 'uppercase'}
                    ),
                    dbc.Button(
                        "Load Data",
                        id='ol-load-data-btn',
                        color='primary',
                        n_clicks=0
                    )
                ], className="mb-3")
            ], width=6),
            dbc.Col([
                html.Div(id='ol-status-message', className="pt-2", style={'color': '#000000'})
            ], width=6)
        ]),
        
        # Canonical 6 Subtabs
        dbc.Tabs(
            id="ol-subtabs",
            active_tab="options-chain-tab",
            className="mb-4",
            children=[
                dbc.Tab(
                    label="📊 Chain Viewer",
                    tab_id="options-chain-tab",
                    children=[_tab_shell("Chain Viewer", _create_chain_viewer_subtab)]
                ),
                dbc.Tab(
                    label="🔢 Greeks Calculator",
                    tab_id="options-greeks-tab",
                    children=[_tab_shell("Greeks Calculator", _create_greeks_subtab)]
                ),
                dbc.Tab(
                    label="🌐 IV Surface & Forecast",
                    tab_id="options-vol-tab",
                    children=[_tab_shell("IV Surface & Forecast", _create_vol_forecast_subtab)]
                ),
                dbc.Tab(
                    label="📝 Manual Trade",
                    tab_id="options-manual-tab",
                    children=[_tab_shell("Manual Trade", _create_manual_trade_subtab)]
                ),
                dbc.Tab(
                    label="🎯 Backtester",
                    tab_id="options-backtest-tab",
                    children=[_tab_shell("Backtester", _create_backtester_subtab)]
                ),
                dbc.Tab(
                    label="⚙️ Settings",
                    tab_id="options-settings-tab",
                    children=[_tab_shell("Settings", _create_settings_subtab)]
                )
            ]
        ),
        
        # Hidden stores for data
        dcc.Store(id='ol-chain-store'),
        dcc.Store(id='ol-greeks-store'),
        dcc.Store(id='ol-forecast-store'),
        dcc.Store(id='ol-orders-store'),
        dcc.Store(id='ol-backtest-store'),
        
    ], fluid=True)


def _tab_shell(tab_name, builder_func):
    """
    Wrapper to safely build subtab content with error boundary.
    
    Args:
        tab_name: Human-readable tab name
        builder_func: Function that returns the subtab layout
        
    Returns:
        Tab content with error handling
    """
    try:
        return builder_func()
    except Exception as e:
        logger.error(f"Failed to build {tab_name} subtab: {e}", exc_info=True)
        return dbc.Alert([
            html.H5(f"⚠️ {tab_name} Load Error", className="alert-heading"),
            html.P(f"Error: {str(e)}"),
            html.Hr(),
            html.P("Check logs for stack trace.", className="mb-0")
        ], color="warning", className="m-3")


# ============================================================================
# SUBTAB 1: Chain Viewer
# ============================================================================

def _create_chain_viewer_subtab():
    """Create Chain Viewer subtab with stable IDs."""
    return dbc.Container([
        html.H5("Options Chain Viewer", className="mt-3 mb-3"),
        
        # Summary Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Spot Price", className="mb-1"),
                        html.H4(id='ol-chain-spot-price', children="--"),
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Volume", className="mb-1"),
                        html.H4(id='ol-chain-volume', children="--"),
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Open Interest", className="mb-1"),
                        html.H4(id='ol-chain-oi', children="--"),
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Put/Call Ratio", className="mb-1"),
                        html.H4(id='ol-chain-pcr', children="--"),
                    ])
                ])
            ], width=3)
        ], className="mb-4"),
        
        # Filter Controls
        dbc.Row([
            dbc.Col([
                dbc.Label("Expiration Date"),
                dcc.Dropdown(
                    id='ol-expiry-dropdown',
                    options=[],
                    value=None,
                    placeholder="Select expiration..."
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Strike Price"),
                dcc.Dropdown(
                    id='ol-strike-dropdown',
                    options=[],
                    value=None,
                    placeholder="Select strike..."
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Option Type"),
                dbc.RadioItems(
                    id='ol-option-type-radio',
                    options=[
                        {'label': 'Calls', 'value': 'calls'},
                        {'label': 'Puts', 'value': 'puts'},
                        {'label': 'Both', 'value': 'both'}
                    ],
                    value='both',
                    inline=True
                )
            ], width=4)
        ], className="mb-3"),
        
        # Chain Table
        html.Div([
            dbc.Spinner(
                html.Div(id='ol-chain-table-container'),
                color="primary"
            )
        ]),
        
        # Contract Selector
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Load Selected Contract",
                    id='ol-contract-select-btn',
                    color='info',
                    className="mt-3",
                    n_clicks=0
                )
            ])
        ]),
        
    ], fluid=True)


# ============================================================================
# SUBTAB 2: Greeks Calculator
# ============================================================================

def _create_greeks_subtab():
    """Create Greeks Calculator subtab with stable IDs."""
    return dbc.Container([
        html.H5("Greeks Calculator", className="mt-3 mb-3"),
        html.P("Calculate option Greeks and sensitivity analysis", className="mb-4"),
        
        # Input Controls
        dbc.Row([
            dbc.Col([
                dbc.Label("Strike Price"),
                dbc.Input(
                    id='ol-calc-strike',
                    type='number',
                    placeholder='Enter strike...'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Spot Price"),
                dbc.Input(
                    id='ol-calc-spot',
                    type='number',
                    placeholder='Current price...'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Days to Expiry"),
                dbc.Input(
                    id='ol-calc-dte',
                    type='number',
                    placeholder='Days...'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Implied Vol %"),
                dbc.Input(
                    id='ol-calc-iv',
                    type='number',
                    placeholder='IV...'
                )
            ], width=3)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Calculate Greeks",
                    id='ol-greeks-run-btn',
                    color='primary',
                    n_clicks=0,
                    className="w-100"
                )
            ], width=6)
        ], className="mb-4"),
        
        # Results Table
        html.Div([
            html.H6("Greeks Results", className="mb-2"),
            html.Div(id='ol-greeks-table')
        ], className="mb-4"),
        
        # Heatmap
        html.Div([
            html.H6("Greeks Heatmap (Strike vs DTE)", className="mb-2"),
            dcc.Graph(id='ol-heatmap', config={'displayModeBar': False})
        ]),
        
        # IV Metrics Table
        html.Div([
            html.H6("IV Metrics", className="mt-4 mb-2"),
            html.Div(id='ol-iv-metrics-table')
        ])
        
    ], fluid=True)


# ============================================================================
# SUBTAB 3: IV Surface & Forecast
# ============================================================================

def _create_vol_forecast_subtab():
    """Create IV Surface & Forecast subtab with stable IDs."""
    return dbc.Container([
        html.H5("IV Surface & Forecast", className="mt-3 mb-3"),
        html.P("Visualize implied volatility surface and generate forecasts", className="mb-4"),
        
        # Control Panel
        dbc.Row([
            dbc.Col([
                dbc.Label("Ticker"),
                dbc.Input(
                    id='ol-forecast-ticker',
                    type='text',
                    value='AAPL',
                    placeholder='Ticker...'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Forecast Horizon (Days)"),
                dbc.Input(
                    id='ol-forecast-horizon',
                    type='number',
                    value=30,
                    min=1,
                    max=365
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "Generate Forecast",
                    id='ol-forecast-run-btn',
                    color='primary',
                    className="mt-4",
                    n_clicks=0
                )
            ], width=3)
        ], className="mb-4"),
        
        # 3D Surface Chart
        dbc.Row([
            dbc.Col([
                html.H6("3D Volatility Surface"),
                dcc.Graph(
                    id='ol-vol-surface-3d',
                    config={'displayModeBar': True},
                    style={'height': '500px'}
                )
            ], width=12)
        ], className="mb-4"),
        
        # Forecast Results
        html.Div([
            html.H6("Forecast Results", className="mb-2"),
            html.Div(id='ol-forecast-results')
        ], className="mb-3"),
        
        # Forecast Chart
        dbc.Row([
            dbc.Col([
                html.H6("Forecast Chart"),
                dcc.Graph(
                    id='ol-forecast-chart',
                    config={'displayModeBar': True}
                )
            ], width=12)
        ])
        
    ], fluid=True)


# ============================================================================
# SUBTAB 4: Manual Trade / Paper Orders
# ============================================================================

def _create_manual_trade_subtab():
    """Create Manual Trade subtab with stable IDs (PAPER ONLY)."""
    return dbc.Container([
        html.H5("Manual Trade (Paper Orders Only)", className="mt-3 mb-3"),
        
        dbc.Alert([
            html.I(className="bi bi-shield-check me-2"),
            "All orders created here are PAPER ONLY. No live broker integration."
        ], color="info", className="mb-4"),
        
        # Order Entry Form
        dbc.Card([
            dbc.CardHeader("New Paper Order"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Action"),
                        dbc.RadioItems(
                            id='ol-order-action',
                            options=[
                                {'label': 'Buy', 'value': 'buy'},
                                {'label': 'Sell', 'value': 'sell'}
                            ],
                            value='buy',
                            inline=True
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Option Type"),
                        dbc.RadioItems(
                            id='ol-order-type',
                            options=[
                                {'label': 'Call', 'value': 'call'},
                                {'label': 'Put', 'value': 'put'}
                            ],
                            value='call',
                            inline=True
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Quantity"),
                        dbc.Input(
                            id='ol-order-quantity',
                            type='number',
                            value=1,
                            min=1
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Limit Price"),
                        dbc.Input(
                            id='ol-order-price',
                            type='number',
                            placeholder='Price...'
                        )
                    ], width=3)
                ], className="mb-3"),
                
                dbc.Button(
                    "Submit Paper Order",
                    id='ol-manual-order-submit',
                    color='success',
                    n_clicks=0,
                    className="w-100"
                )
            ])
        ], className="mb-4"),
        
        # Order Status
        html.Div(id='ol-order-status', className="mb-3"),
        
        # Orders Table
        html.Div([
            html.H6("Paper Orders", className="mb-2"),
            html.Div(id='ol-manual-order-table')
        ])
        
    ], fluid=True)


# ============================================================================
# SUBTAB 5: Backtester / Strategy
# ============================================================================

def _create_backtester_subtab():
    """Create Backtester subtab with stable IDs."""
    return dbc.Container([
        html.H5("Options Backtester", className="mt-3 mb-3"),
        html.P("Backtest options strategies with historical data", className="mb-4"),
        
        # Backtest Configuration
        dbc.Card([
            dbc.CardHeader("Backtest Configuration"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Strategy"),
                        dcc.Dropdown(
                            id='ol-backtest-strategy',
                            options=[
                                {'label': 'Long Call', 'value': 'long_call'},
                                {'label': 'Long Put', 'value': 'long_put'},
                                {'label': 'Covered Call', 'value': 'covered_call'},
                                {'label': 'Iron Condor', 'value': 'iron_condor'}
                            ],
                            value='long_call'
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Initial Capital"),
                        dbc.Input(
                            id='ol-backtest-capital',
                            type='number',
                            value=10000,
                            min=1000
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Lookback Days"),
                        dbc.Input(
                            id='ol-backtest-lookback',
                            type='number',
                            value=252,
                            min=30
                        )
                    ], width=4)
                ], className="mb-3"),
                
                dbc.Button(
                    "Run Backtest",
                    id='ol-backtest-run-btn',
                    color='primary',
                    n_clicks=0,
                    className="w-100"
                )
            ])
        ], className="mb-4"),
        
        # Results Summary
        html.Div(id='ol-backtest-results', className="mb-4"),
        
        # Equity Curve
        dbc.Row([
            dbc.Col([
                html.H6("Equity Curve", className="mb-2"),
                dcc.Graph(
                    id='ol-backtest-equity-chart',
                    config={'displayModeBar': True}
                )
            ], width=12)
        ], className="mb-3"),
        
        # Trade List
        html.Div([
            html.H6("Trade List", className="mb-2"),
            html.Div(id='ol-backtest-trades-table')
        ], className="mb-3"),
        
        # Export Button
        dbc.Button(
            "Export Results",
            id='ol-backtest-export-btn',
            color='info',
            outline=True,
            n_clicks=0
        ),
        dcc.Download(id='ol-backtest-download')
        
    ], fluid=True)


# ============================================================================
# SUBTAB 6: Settings
# ============================================================================

def _create_settings_subtab():
    """Create Settings subtab with stable IDs."""
    return dbc.Container([
        html.H5("Options Lab Settings", className="mt-3 mb-3"),
        
        dbc.Card([
            dbc.CardHeader("Data Sources"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Preferred Data Source"),
                        dbc.RadioItems(
                            id='ol-settings-datasource',
                            options=[
                                {'label': 'Alpaca (Live)', 'value': 'alpaca'},
                                {'label': 'Mock (Deterministic)', 'value': 'mock'}
                            ],
                            value='mock',
                            inline=True
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Auto-Refresh Interval (sec)"),
                        dbc.Input(
                            id='ol-settings-refresh-interval',
                            type='number',
                            value=30,
                            min=10,
                            max=300
                        )
                    ], width=6)
                ], className="mb-3")
            ])
        ], className="mb-3"),
        
        dbc.Card([
            dbc.CardHeader("Paper Trading"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Enable Paper Trading"),
                        dbc.Switch(
                            id='ol-settings-paper-enabled',
                            value=True,
                            className="mb-2"
                        )
                    ], width=6)
                ])
            ])
        ], className="mb-3"),
        
        dbc.Button(
            "Save Settings",
            id='ol-settings-save-btn',
            color='success',
            n_clicks=0
        )
        
    ], fluid=True)


# ============================================================================
# Error Fallback
# ============================================================================

def _error_fallback_layout(error):
    """Fallback layout when main layout fails to build."""
    return dbc.Container([
        dbc.Alert([
            html.H4("⚠️ Options Lab Layout Error", className="alert-heading"),
            html.P(f"Failed to build layout: {str(error)}"),
            html.Hr(),
            html.P("Check server logs for full stack trace.", className="mb-0")
        ], color="danger")
    ], fluid=True, className="mt-5")
