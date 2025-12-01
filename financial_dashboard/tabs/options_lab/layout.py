"""
Options Lab Layout - Canonical Phase 31 (Callback-Compatible Edition)

6 canonical subtabs with callback-aligned IDs:
1. Chain Viewer - uses existing chain-* IDs
2. Greeks Calculator - uses existing greeks-* IDs  
3. IV Surface & Forecast - uses existing vol-surface-3d + surface-* IDs
4. Manual Trade - uses existing sim-* IDs
5. Backtester - NEW, uses ol-backtest-* IDs (no callbacks yet)
6. Settings - NEW, uses ol-settings-* IDs (no callbacks yet)

Global controls use existing options-* IDs to preserve callback compatibility.

ID Strategy:
- Existing subtabs (1-4): Use callback-expected IDs (cannot edit callbacks.py constraint)
- New subtabs (5-6): Use ol-* prefix per STABLE ID RULE
- Hybrid approach satisfies both constraints

Safe layout factory pattern with error boundaries.

Author: Phase 31 - Agent 1A STEP 2
Status: Callback-Compatible Canonical
"""

import logging
from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def create_layout():
    """
    Safe factory function for Options Lab layout.
    Returns complete layout with error boundaries.
    """
    try:
        return _build_safe_layout()
    except Exception as e:
        logger.error(f"Options Lab layout creation failed: {e}", exc_info=True)
        return _error_fallback_layout(e)


def _build_safe_layout():
    """Main layout builder with 6 canonical subtabs."""
    return dbc.Container([
        # Global Controls (uses existing options-* IDs for callback compatibility)
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Ticker Symbol", className="fw-bold"),
                        dbc.Input(
                            id='options-ticker-input',  # Existing ID for callback
                            type='text',
                            placeholder='e.g., AAPL, SPY, TSLA',
                            className="mb-2"
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Actions", className="fw-bold"),
                        html.Div([
                            dbc.Button(
                                "📊 Load Data", 
                                id='options-load-btn',  # Existing ID
                                color="primary", 
                                className="me-2"
                            ),
                            dbc.Button(
                                "🎲 Use Mock Data", 
                                id='options-mock-btn',  # Existing ID
                                color="secondary"
                            ),
                        ])
                    ], width=8),
                ], className="g-2"),
                html.Hr(),
                html.Div(id='options-status-message', className="pt-2")  # Existing ID
            ])
        ], className="mb-3"),

        # Subtabs (12 tabs with enhanced features)
        dbc.Tabs([
            dbc.Tab(
                _tab_shell("Chain Viewer", _create_chain_viewer_subtab),
                label="📋 Chain Viewer",
                tab_id="chain-viewer",  # Match old tab_id
                id="options-chain-tab"
            ),
            dbc.Tab(
                _tab_shell("Greeks Calculator", _create_greeks_subtab),
                label="🔢 Greeks Calculator",
                tab_id="greeks-dashboard",  # Match old tab_id
                id="options-greeks-tab"
            ),
            dbc.Tab(
                _tab_shell("IV Surface & Forecast", _create_vol_forecast_subtab),
                label="📈 IV Surface & Forecast",
                tab_id="vol-surface",  # Match old tab_id
                id="options-vol-tab"
            ),
            dbc.Tab(
                _tab_shell("Flow Scanner", _create_flow_scanner_subtab),
                label="🔍 Flow Scanner",
                tab_id="flow-scanner",  # NEW tab
                id="options-flow-tab"
            ),
            dbc.Tab(
                _tab_shell("IV Analysis", _create_iv_analysis_subtab),
                label="📊 IV Analysis",
                tab_id="iv-analysis",  # NEW tab
                id="options-iv-tab"
            ),
            dbc.Tab(
                _tab_shell("Strategy Builder", _create_strategy_builder_subtab),
                label="🏗️ Strategy Builder",
                tab_id="strategy-builder",  # NEW tab
                id="options-strategy-tab"
            ),
            dbc.Tab(
                _tab_shell("Manual Trade", _create_manual_trade_subtab),
                label="💼 Manual Trade",
                tab_id="trade-simulator",  # Match old tab_id
                id="options-manual-tab"
            ),
            dbc.Tab(
                _tab_shell("Portfolio Greeks", _create_portfolio_greeks_subtab),
                label="📉 Portfolio Greeks",
                tab_id="portfolio-greeks",  # NEW tab
                id="options-portfolio-tab"
            ),
            dbc.Tab(
                _tab_shell("Screener", _create_screener_subtab),
                label="🔎 Screener",
                tab_id="screener",  # NEW tab
                id="options-screener-tab"
            ),
            dbc.Tab(
                _tab_shell("AI Recommendations", _create_ai_recommendations_subtab),
                label="🤖 AI Recs",
                tab_id="ai-recommendations",  # NEW tab
                id="options-ai-tab"
            ),
            dbc.Tab(
                _tab_shell("Earnings Calendar", _create_earnings_calendar_subtab),
                label="📅 Earnings",
                tab_id="earnings-calendar",  # NEW tab
                id="options-earnings-tab"
            ),
            dbc.Tab(
                _tab_shell("Backtester", _create_backtester_subtab),
                label="🎯 Backtester",
                tab_id="backtester",  # NEW tab
                id="options-backtest-tab"
            ),
        ], id='options-subtabs', active_tab="chain-viewer"),

        # NOTE: Data stores moved to layout_placeholders.py for app-level access
        # This ensures callbacks can access stores even when Options Lab tab is not active
        
    ], fluid=True, className="p-4")


def _tab_shell(tab_name, builder_func):
    """
    Error boundary wrapper for individual subtabs.
    Catches exceptions and displays error without crashing entire tab.
    """
    try:
        return builder_func()
    except Exception as e:
        logger.error(f"Failed to build {tab_name} subtab: {e}", exc_info=True)
        return dbc.Alert([
            html.H5(f"⚠️ {tab_name} Temporarily Unavailable", className="alert-heading"),
            html.P(f"Error: {str(e)}"),
            html.Hr(),
            html.P([
                "This subtab encountered an error during initialization. ",
                "The issue has been logged. Please try refreshing the page or contact support."
            ], className="mb-0 small")
        ], color="warning", className="m-3")


def _create_chain_viewer_subtab():
    """Chain Viewer - uses existing chain-* IDs for callback compatibility."""
    return dbc.Container([
        # Summary cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Spot Price", className="text-muted mb-2"),
                        html.H4(id='chain-spot-price', children="--", className="text-primary")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Volume", className="text-muted mb-2"),
                        html.H4(id='chain-total-volume', children="--", className="text-info")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total OI", className="text-muted mb-2"),
                        html.H4(id='chain-total-oi', children="--", className="text-success")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Put/Call Ratio", className="text-muted mb-2"),
                        html.H4(id='chain-pcr', children="--", className="text-warning")
                    ])
                ])
            ], width=3),
        ], className="mb-3 g-2"),

        # Filters
        dbc.Row([
            dbc.Col([
                dbc.Label("Expiration Date", className="fw-bold"),
                dcc.Dropdown(
                    id='chain-expiration-dropdown',
                    placeholder="Select expiration...",
                    className="mb-2"
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Option Type", className="fw-bold"),
                dbc.RadioItems(
                    id='chain-type-radio',
                    options=[
                        {'label': 'Calls', 'value': 'call'},
                        {'label': 'Puts', 'value': 'put'},
                        {'label': 'Both', 'value': 'both'}
                    ],
                    value='both',
                    inline=True
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Moneyness Filter", className="fw-bold"),
                dbc.RadioItems(
                    id='chain-moneyness-radio',
                    options=[
                        {'label': 'All', 'value': 'all'},
                        {'label': 'ITM', 'value': 'itm'},
                        {'label': 'OTM', 'value': 'otm'}
                    ],
                    value='all',
                    inline=True
                )
            ], width=4),
        ], className="mb-3 g-2"),

        # Chain table
        html.Div(id='chain-table-container', className="mb-3"),

        # RESTORED: Options Forecast Controls (Agent-1A STEP 2)
        dbc.Card([
            dbc.CardHeader([
                html.H6("📈 Options Price Forecast", className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Contract Selection", className="fw-bold small"),
                        html.P("Select a contract from the table above, then click Generate Forecast", 
                               className="text-muted small mb-2")
                    ], width=12)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Ticker", className="small"),
                        dcc.Dropdown(
                            id='contract-ticker-selector',
                            options=[
                                {'label': '🍎 AAPL', 'value': 'AAPL'},
                                {'label': '📱 MSFT', 'value': 'MSFT'},
                                {'label': '🔍 GOOGL', 'value': 'GOOGL'},
                                {'label': '🚗 TSLA', 'value': 'TSLA'},
                                {'label': '📦 AMZN', 'value': 'AMZN'},
                                {'label': '🎮 NVDA', 'value': 'NVDA'},
                                {'label': '📘 META', 'value': 'META'},
                                {'label': '📊 SPY', 'value': 'SPY'}
                            ],
                            value='AAPL',
                            className="mb-2"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Option Type", className="small"),
                        dcc.Dropdown(
                            id='contract-option-type',
                            options=[
                                {'label': 'Call', 'value': 'call'},
                                {'label': 'Put', 'value': 'put'}
                            ],
                            value='call',
                            className="mb-2"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Strike", className="small"),
                        dcc.Dropdown(
                            id='contract-strike-selector',
                            options=[],
                            placeholder="Select strike",
                            className="mb-2"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Expiration", className="small"),
                        dcc.Dropdown(
                            id='contract-expiration-selector',
                            options=[],
                            placeholder="Select expiration",
                            className="mb-2"
                        )
                    ], width=3)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col([
                        # Using existing callback ID: options-forecast-btn
                        dbc.Button(
                            "🔮 Generate Forecast",
                            id='options-forecast-btn',
                            color="primary",
                            size="sm",
                            className="me-2"
                        ),
                        # New OL-prefixed ID for testing (same action)
                        dbc.Button(
                            "🔮 Generate Forecast (OL)",
                            id='ol-forecast-run-btn',
                            color="primary",
                            size="sm",
                            outline=True
                        )
                    ], width=12)
                ], className="mb-3"),
                # Results container (existing callback ID)
                html.Div(id='options-forecast-results', className="mb-2"),
                # OL-prefixed results for testing
                html.Div(id='ol-forecast-results')
            ])
        ], className="mb-3"),

        # TradingView Signals Widget
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-broadcast me-2"),
                "TradingView Signals",
                dbc.Button(
                    [html.I(className="bi bi-arrow-clockwise me-1"), "Fetch"],
                    id='tradingview-fetch-btn',
                    color="primary",
                    size="sm",
                    className="float-end"
                )
            ]),
            dbc.CardBody([
                html.Div(id='tradingview-signals-container', children=[
                    html.P("Click 'Fetch' to load TradingView signals for the selected ticker.",
                           className="text-muted small")
                ])
            ])
        ], className="mb-3"),
        
        html.Div([
            html.Div(id='tradingview-preview', style={'display': 'none'}),
            html.Div(id='ol-tv-signal-widget', style={'display': 'none'}),
            dcc.Interval(
                id='tradingview-interval',
                interval=60000,
                n_intervals=0,
                disabled=True
            )
        ]),

        # Export button
        dbc.Button(
            "📥 Export Chain Data",
            id='chain-export-btn',
            color="success",
            size="sm"
        ),
        dcc.Download(id='chain-download'),

    ], fluid=True, className="p-3")


def _create_greeks_subtab():
    """Greeks Calculator - uses existing greeks-* IDs."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("Greeks Visualization", className="mb-3"),
                dcc.Graph(id='greeks-delta-chart', config={'displayModeBar': False}),
            ], width=6),
            dbc.Col([
                dcc.Graph(id='greeks-gamma-chart', config={'displayModeBar': False}),
            ], width=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='greeks-theta-chart', config={'displayModeBar': False}),
            ], width=6),
            dbc.Col([
                dcc.Graph(id='greeks-vega-chart', config={'displayModeBar': False}),
            ], width=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.H5("IV Smile", className="mb-3"),
                dcc.Graph(id='greeks-iv-smile', config={'displayModeBar': True}),
            ], width=12),
        ]),
    ], fluid=True, className="p-3")


def _create_vol_forecast_subtab():
    """IV Surface & Forecast - uses existing vol-surface-3d + surface-* + options-forecast-* IDs."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("Volatility Surface", className="mb-3"),
                dcc.Graph(
                    id='vol-surface-3d', 
                    config={'displayModeBar': True},
                    style={'height': '500px'}
                ),
            ], width=8),
            dbc.Col([
                html.H6("Surface Controls", className="mb-3"),
                dbc.Label("Viewing Angle"),
                dcc.Slider(
                    id='surface-angle-slider',
                    min=0, max=360, step=10, value=45,
                    marks={i: str(i) for i in range(0, 361, 90)}
                ),
                html.Br(),
                dbc.Label("Color Scale"),
                dcc.Dropdown(
                    id='surface-colorscale-dropdown',
                    options=[
                        {'label': 'Viridis', 'value': 'Viridis'},
                        {'label': 'Plasma', 'value': 'Plasma'},
                        {'label': 'Jet', 'value': 'Jet'},
                    ],
                    value='Viridis'
                ),
            ], width=4),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.H5("📈 IV Term Structure & Forecast", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Current IV", className="text-muted mb-2"),
                                html.H3(id='ol-current-iv', children="--", className="text-primary")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("IV Percentile", className="text-muted mb-2"),
                                html.H3(id='ol-iv-percentile', children="--", className="text-info")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("IV Rank (52w)", className="text-muted mb-2"),
                                html.H3(id='ol-iv-rank-surface', children="--", className="text-success")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("HV20", className="text-muted mb-2"),
                                html.H3(id='ol-hv20', children="--", className="text-warning")
                            ])
                        ])
                    ], width=3),
                ], className="mb-3"),
                dcc.Graph(id='ol-iv-term-structure-chart', config={'displayModeBar': True}, style={'height': '300px'}),
                html.Div(id='ol-vol-forecast-results'),
            ], width=12),
        ]),
    ], fluid=True, className="p-3")


def _create_manual_trade_subtab():
    """Manual Trade / Trade Simulator - uses existing sim-* IDs."""
    return dbc.Container([
        # Contract Selection
        dbc.Row([
            dbc.Col([
                dbc.Label("Option Type", className="fw-bold"),
                dcc.Dropdown(
                    id='sim-option-type',
                    options=[
                        {'label': 'Call', 'value': 'call'},
                        {'label': 'Put', 'value': 'put'},
                    ],
                    value='call'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Expiration", className="fw-bold"),
                dcc.Dropdown(id='sim-expiration-dropdown', options=[], value=None)
            ], width=3),
            dbc.Col([
                dbc.Label("Strike", className="fw-bold"),
                dcc.Dropdown(id='sim-strike-dropdown', options=[], value=None)
            ], width=3),
            dbc.Col([
                dbc.Label("Quantity", className="fw-bold"),
                dbc.Input(
                    id='sim-quantity-input',
                    type='number',
                    value=1,
                    min=1,
                    max=100
                )
            ], width=3),
        ], className="mb-3 g-2"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("Strategy Type (Optional Multi-Leg)", className="fw-bold"),
                dcc.Dropdown(
                    id='sim-strategy-dropdown',
                    options=[
                        {'label': 'Single Option', 'value': 'single'},
                        {'label': 'Covered Call', 'value': 'covered_call'},
                        {'label': 'Protective Put', 'value': 'protective_put'},
                        {'label': 'Bull Call Spread', 'value': 'bull_call_spread'},
                        {'label': 'Bear Put Spread', 'value': 'bear_put_spread'},
                        {'label': 'Iron Condor', 'value': 'iron_condor'},
                    ],
                    value='single'
                )
            ], width=6),
        ], className="mb-3 g-2"),

        dbc.Button(
            "🧮 Calculate P&L",
            id='sim-calculate-btn',
            color="primary",
            className="mb-3"
        ),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Max Profit", className="text-muted mb-2"),
                        html.H4(id='sim-max-profit', children="--", className="text-success")
                    ])
                ])
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Max Loss", className="text-muted mb-2"),
                        html.H4(id='sim-max-loss', children="--", className="text-danger")
                    ])
                ])
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Breakeven", className="text-muted mb-2"),
                        html.H4(id='sim-breakeven', children="--", className="text-warning")
                    ])
                ])
            ], width=4),
        ], className="mb-3 g-2"),

        dcc.Graph(id='sim-pnl-chart', config={'displayModeBar': True}),
        
        html.Hr(),
        
        # AGENT 1A TASK 5: Paper Orders Section
        dbc.Card([
            dbc.CardHeader([
                html.H6("📝 Paper Order Placement", className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Action", className="fw-bold"),
                        dcc.Dropdown(
                            id='sim-order-action',
                            options=[
                                {'label': 'Buy to Open', 'value': 'BTO'},
                                {'label': 'Sell to Close', 'value': 'STC'},
                                {'label': 'Sell to Open', 'value': 'STO'},
                                {'label': 'Buy to Close', 'value': 'BTC'},
                            ],
                            value='BTO'
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Contracts", className="fw-bold"),
                        dbc.Input(
                            id='sim-order-quantity',
                            type='number',
                            value=1,
                            min=1,
                            max=100
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Limit Price", className="fw-bold"),
                        dbc.Input(
                            id='sim-order-price',
                            type='number',
                            value=5.00,
                            min=0.01,
                            step=0.01
                        )
                    ], width=4),
                ], className="mb-3 g-2"),
                
                dbc.Button(
                    "📤 Submit Paper Order (Mock)",
                    id='sim-order-submit-btn',
                    color="success",
                    className="mb-2"
                ),
                
                html.Div(id='sim-order-confirmation', className="mt-2")
            ])
        ], className="mb-3"),

    ], fluid=True, className="p-3")


def _create_flow_scanner_subtab():
    """Flow Scanner - Options flow & unusual activity detection."""
    return dbc.Container([
        dbc.Alert([
            html.H5("🔍 Options Flow Scanner", className="alert-heading"),
            html.P("Detect unusual options activity, calculate GEX (Gamma Exposure), and identify max pain levels."),
        ], color="info", className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Ticker", className="fw-bold"),
                dbc.Input(
                    id='ol-flow-ticker',
                    type='text',
                    value='SPY',
                    placeholder='Enter ticker...'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Min Premium ($K)", className="fw-bold"),
                dbc.Input(
                    id='ol-flow-min-premium',
                    type='number',
                    value=100,
                    min=10,
                    step=10
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Volume Threshold (% OI)", className="fw-bold"),
                dbc.Input(
                    id='ol-flow-vol-threshold',
                    type='number',
                    value=50,
                    min=10,
                    step=10
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "🔍 Scan Flow",
                    id='ol-flow-scan-btn',
                    color="primary",
                    className="mt-4"
                )
            ], width=3),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("Unusual Options Activity", className="mb-2"),
                html.Div(id='ol-flow-table'),
            ], width=12),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("GEX Profile", className="mb-2"),
                dcc.Graph(id='ol-gex-chart', config={'displayModeBar': True}),
            ], width=6),
            dbc.Col([
                html.H6("Max Pain Analysis", className="mb-2"),
                dcc.Graph(id='ol-max-pain-chart', config={'displayModeBar': True}),
            ], width=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Max Pain Strike", className="text-muted mb-2"),
                        html.H4(id='ol-max-pain-value', children="--", className="text-warning")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Net GEX", className="text-muted mb-2"),
                        html.H4(id='ol-net-gex', children="--", className="text-info")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Call Sweeps", className="text-muted mb-2"),
                        html.H4(id='ol-call-sweeps', children="--", className="text-success")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Put Sweeps", className="text-muted mb-2"),
                        html.H4(id='ol-put-sweeps', children="--", className="text-danger")
                    ])
                ])
            ], width=3),
        ], className="mb-3 g-2"),
    ], fluid=True, className="p-3")


def _create_iv_analysis_subtab():
    """IV Analysis - Term structure, skew, and IV percentile."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Label("Ticker", className="fw-bold"),
                dbc.Input(
                    id='ol-iv-ticker',
                    type='text',
                    value='AAPL',
                    placeholder='Enter ticker...'
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "📊 Analyze IV",
                    id='ol-iv-analyze-btn',
                    color="primary",
                    className="mt-4"
                )
            ], width=3),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("IV Percentile (30D)", className="text-muted mb-2"),
                        html.H4(id='ol-iv-percentile-30', children="--", className="text-primary")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("IV Percentile (1Y)", className="text-muted mb-2"),
                        html.H4(id='ol-iv-percentile-1y', children="--", className="text-info")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("IV Rank", className="text-muted mb-2"),
                        html.H4(id='ol-iv-rank', children="--", className="text-warning")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Term Structure", className="text-muted mb-2"),
                        html.H4(id='ol-term-structure', children="--", className="text-success")
                    ])
                ])
            ], width=3),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("IV Term Structure", className="mb-2"),
                dcc.Graph(id='ol-term-structure-chart', config={'displayModeBar': True}),
            ], width=6),
            dbc.Col([
                html.H6("IV Skew", className="mb-2"),
                dcc.Graph(id='ol-skew-chart', config={'displayModeBar': True}),
            ], width=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("IV Percentile Gauge", className="mb-2"),
                dcc.Graph(id='ol-iv-gauge', config={'displayModeBar': False}),
            ], width=6),
            dbc.Col([
                html.H6("Earnings IV Crush Estimate", className="mb-2"),
                dbc.Card([
                    dbc.CardBody([
                        html.P("Estimated post-earnings IV crush based on historical patterns:", className="mb-2"),
                        html.Div(id='ol-iv-crush-estimate')
                    ])
                ])
            ], width=6),
        ]),
    ], fluid=True, className="p-3")


def _create_strategy_builder_subtab():
    """Strategy Builder - Visual multi-leg strategy constructor."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Label("Strategy Template", className="fw-bold"),
                dcc.Dropdown(
                    id='ol-strategy-template',
                    options=[
                        {'label': '📈 Long Call', 'value': 'long_call'},
                        {'label': '📉 Long Put', 'value': 'long_put'},
                        {'label': '💰 Covered Call', 'value': 'covered_call'},
                        {'label': '🛡️ Protective Put', 'value': 'protective_put'},
                        {'label': '🐂 Bull Call Spread', 'value': 'bull_call_spread'},
                        {'label': '🐻 Bear Put Spread', 'value': 'bear_put_spread'},
                        {'label': '🦅 Iron Condor', 'value': 'iron_condor'},
                        {'label': '🎯 Straddle', 'value': 'straddle'},
                        {'label': '⬛ Strangle', 'value': 'strangle'},
                        {'label': '🦋 Butterfly', 'value': 'butterfly'},
                        {'label': '📅 Calendar Spread', 'value': 'calendar_spread'},
                    ],
                    value='iron_condor',
                    placeholder='Select strategy template...'
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Spot Price", className="fw-bold"),
                dbc.Input(
                    id='ol-strategy-spot',
                    type='number',
                    value=100,
                    min=1
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Base Premium", className="fw-bold"),
                dbc.Input(
                    id='ol-strategy-premium',
                    type='number',
                    value=5.0,
                    min=0.1,
                    step=0.1
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "🏗️ Build Strategy",
                    id='ol-strategy-build-btn',
                    color="primary",
                    className="mt-4"
                )
            ], width=2),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("Strategy Legs", className="mb-2"),
                html.Div(id='ol-strategy-legs'),
            ], width=6),
            dbc.Col([
                html.H6("Strategy Metrics", className="mb-2"),
                html.Div(id='ol-strategy-metrics'),
            ], width=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("Payoff Diagram", className="mb-2"),
                dcc.Graph(id='ol-payoff-chart', config={'displayModeBar': True}),
            ], width=12),
        ], className="mb-3"),

        html.Hr(),

        dbc.Row([
            dbc.Col([
                html.H6("Compare Strategies", className="mb-2"),
                dbc.Checklist(
                    id='ol-strategy-compare',
                    options=[
                        {'label': 'Iron Condor', 'value': 'iron_condor'},
                        {'label': 'Straddle', 'value': 'straddle'},
                        {'label': 'Bull Call Spread', 'value': 'bull_call_spread'},
                    ],
                    value=['iron_condor'],
                    inline=True
                )
            ], width=12),
        ], className="mb-3"),

        dcc.Graph(id='ol-strategy-comparison-chart', config={'displayModeBar': True}),
    ], fluid=True, className="p-3")


def _create_portfolio_greeks_subtab():
    """Portfolio Greeks - Aggregate Greeks dashboard."""
    return dbc.Container([
        dbc.Alert([
            html.H5("📉 Portfolio Greeks Dashboard", className="alert-heading"),
            html.P("View aggregate Greeks across all open positions and analyze risk exposure."),
        ], color="info", className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Net Delta", className="text-muted mb-2"),
                        html.H4(id='ol-portfolio-delta', children="--", className="text-primary")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Net Gamma", className="text-muted mb-2"),
                        html.H4(id='ol-portfolio-gamma', children="--", className="text-info")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Net Theta", className="text-muted mb-2"),
                        html.H4(id='ol-portfolio-theta', children="--", className="text-success")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Net Vega", className="text-muted mb-2"),
                        html.H4(id='ol-portfolio-vega', children="--", className="text-warning")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Risk Score", className="text-muted mb-2"),
                        html.H4(id='ol-risk-score', children="--", className="text-danger")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Button(
                    "🔄 Refresh",
                    id='ol-portfolio-refresh-btn',
                    color="primary",
                    className="mt-3"
                )
            ], width=2),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("Greeks Visualization", className="mb-2"),
                dcc.Graph(id='ol-greeks-dashboard', config={'displayModeBar': True}),
            ], width=6),
            dbc.Col([
                html.H6("Greeks Heatmap by Position", className="mb-2"),
                dcc.Graph(id='ol-greeks-heatmap', config={'displayModeBar': True}),
            ], width=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("P&L Scenario Analysis", className="mb-2"),
                dcc.Graph(id='ol-scenario-heatmap', config={'displayModeBar': True}),
            ], width=12),
        ]),
    ], fluid=True, className="p-3")


def _create_screener_subtab():
    """Options Screener - Find options by criteria."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Label("Preset Filters", className="fw-bold"),
                dcc.Dropdown(
                    id='ol-screener-preset',
                    options=[
                        {'label': '🔥 High IV Percentile', 'value': 'high_iv_percentile'},
                        {'label': '❄️ Low IV Percentile', 'value': 'low_iv_percentile'},
                        {'label': '📊 High Open Interest', 'value': 'high_open_interest'},
                        {'label': '⚡ Unusual Volume', 'value': 'unusual_volume'},
                        {'label': '💵 Cheap Premium', 'value': 'cheap_premium'},
                        {'label': '🎯 High Delta', 'value': 'high_delta'},
                        {'label': '📆 Weekly Options', 'value': 'weekly_options'},
                        {'label': '📅 LEAPS', 'value': 'leaps'},
                    ],
                    value='high_iv_percentile',
                    placeholder='Select preset filter...'
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Option Type", className="fw-bold"),
                dcc.Dropdown(
                    id='ol-screener-type',
                    options=[
                        {'label': 'All', 'value': ''},
                        {'label': 'Calls Only', 'value': 'call'},
                        {'label': 'Puts Only', 'value': 'put'},
                    ],
                    value=''
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Max DTE", className="fw-bold"),
                dbc.Input(
                    id='ol-screener-max-dte',
                    type='number',
                    value=60,
                    min=1
                )
            ], width=2),
            dbc.Col([
                dbc.Button(
                    "🔎 Run Screen",
                    id='ol-screener-run-btn',
                    color="primary",
                    className="mt-4"
                )
            ], width=3),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("Screener Results", className="mb-2"),
                html.Div(id='ol-screener-results'),
            ], width=12),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("Results Visualization", className="mb-2"),
                dcc.Graph(id='ol-screener-chart', config={'displayModeBar': True}),
            ], width=6),
            dbc.Col([
                html.H6("IV Heatmap", className="mb-2"),
                dcc.Graph(id='ol-screener-heatmap', config={'displayModeBar': True}),
            ], width=6),
        ]),
    ], fluid=True, className="p-3")


def _create_ai_recommendations_subtab():
    """AI Trade Recommendations - Smart trade suggestions."""
    return dbc.Container([
        dbc.Alert([
            html.H5("🤖 AI Trade Recommendations", className="alert-heading"),
            html.P("Smart trade suggestions based on current market conditions, IV levels, and historical patterns."),
        ], color="primary", className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Recommendation Type", className="fw-bold"),
                dcc.Dropdown(
                    id='ol-ai-rec-type',
                    options=[
                        {'label': '🎯 All Recommendations', 'value': ''},
                        {'label': '📈 Bullish', 'value': 'bullish'},
                        {'label': '📉 Bearish', 'value': 'bearish'},
                        {'label': '↔️ Neutral', 'value': 'neutral'},
                        {'label': '🔥 High IV (Sell Premium)', 'value': 'high_iv'},
                        {'label': '❄️ Low IV (Buy Premium)', 'value': 'low_iv'},
                        {'label': '📅 Earnings Plays', 'value': 'earnings'},
                        {'label': '💰 Income', 'value': 'income'},
                    ],
                    value='',
                    placeholder='Filter recommendations...'
                )
            ], width=4),
            dbc.Col([
                dbc.Button(
                    "🔄 Generate Recommendations",
                    id='ol-ai-generate-btn',
                    color="success",
                    className="mt-4"
                )
            ], width=4),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("Top Recommendations", className="mb-2"),
                html.Div(id='ol-ai-recommendations'),
            ], width=12),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("Risk vs Reward", className="mb-2"),
                dcc.Graph(id='ol-ai-chart', config={'displayModeBar': True}),
            ], width=12),
        ]),
    ], fluid=True, className="p-3")


def _create_earnings_calendar_subtab():
    """Earnings Calendar - Track earnings dates and expected moves."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Label("Days Ahead", className="fw-bold"),
                dbc.Input(
                    id='ol-earnings-days',
                    type='number',
                    value=14,
                    min=1,
                    max=60
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "📅 Load Calendar",
                    id='ol-earnings-load-btn',
                    color="primary",
                    className="mt-4"
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "🔥 High IV Opportunities",
                    id='ol-earnings-high-iv-btn',
                    color="warning",
                    className="mt-4"
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "📊 Underpriced Straddles",
                    id='ol-earnings-underpriced-btn',
                    color="info",
                    className="mt-4"
                )
            ], width=3),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("Upcoming Earnings", className="mb-2"),
                html.Div(id='ol-earnings-table'),
            ], width=12),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("Earnings Calendar", className="mb-2"),
                dcc.Graph(id='ol-earnings-chart', config={'displayModeBar': True}),
            ], width=8),
            dbc.Col([
                html.H6("Weekly Heatmap", className="mb-2"),
                dcc.Graph(id='ol-earnings-heatmap', config={'displayModeBar': True}),
            ], width=4),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("Straddle Analysis", className="mb-2"),
                html.Div(id='ol-straddle-analysis'),
            ], width=6),
            dbc.Col([
                html.H6("Historical Moves", className="mb-2"),
                dcc.Graph(id='ol-historical-moves-chart', config={'displayModeBar': True}),
            ], width=6),
        ]),
    ], fluid=True, className="p-3")


def _create_trade_journal_subtab():
    """Trade Journal - Track and analyze options trades."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "📝 Add Trade",
                    id='ol-journal-add-btn',
                    color="success",
                    className="me-2"
                ),
                dbc.Button(
                    "🔄 Refresh",
                    id='ol-journal-refresh-btn',
                    color="secondary",
                    className="me-2"
                ),
                dbc.Button(
                    "📥 Export",
                    id='ol-journal-export-btn',
                    color="info"
                ),
            ], width=12),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total P&L", className="text-muted mb-2"),
                        html.H4(id='ol-journal-total-pnl', children="--", className="text-success")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Win Rate", className="text-muted mb-2"),
                        html.H4(id='ol-journal-win-rate', children="--", className="text-info")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Profit Factor", className="text-muted mb-2"),
                        html.H4(id='ol-journal-profit-factor', children="--", className="text-primary")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Avg P&L", className="text-muted mb-2"),
                        html.H4(id='ol-journal-avg-pnl', children="--", className="text-warning")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Open Trades", className="text-muted mb-2"),
                        html.H4(id='ol-journal-open', children="--", className="text-secondary")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Trades", className="text-muted mb-2"),
                        html.H4(id='ol-journal-total', children="--", className="text-dark")
                    ])
                ])
            ], width=2),
        ], className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([
                html.H6("Cumulative P&L", className="mb-2"),
                dcc.Graph(id='ol-journal-pnl-chart', config={'displayModeBar': True}),
            ], width=6),
            dbc.Col([
                html.H6("Win Rate Gauge", className="mb-2"),
                dcc.Graph(id='ol-journal-gauge', config={'displayModeBar': False}),
            ], width=3),
            dbc.Col([
                html.H6("Monthly P&L", className="mb-2"),
                dcc.Graph(id='ol-journal-monthly', config={'displayModeBar': True}),
            ], width=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("P&L by Strategy", className="mb-2"),
                dcc.Graph(id='ol-journal-strategy-chart', config={'displayModeBar': True}),
            ], width=6),
            dbc.Col([
                html.H6("Trade History", className="mb-2"),
                html.Div(id='ol-journal-trades-table'),
            ], width=6),
        ]),

        dcc.Download(id='ol-journal-download'),
    ], fluid=True, className="p-3")


def _create_backtester_subtab():
    """
    Backtester - NEW subtab, uses ol-backtest-* IDs.
    Placeholder until callbacks are implemented.
    """
    return dbc.Container([
        dbc.Alert([
            html.H5("🎯 Options Strategy Backtester", className="alert-heading"),
            html.P([
                "Test options strategies against historical data. ",
                "Define entry/exit rules, run backtests, and analyze performance."
            ]),
        ], color="info", className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Strategy Template", className="fw-bold"),
                dcc.Dropdown(
                    id='ol-backtest-strategy',
                    options=[
                        {'label': 'Weekly Iron Condor', 'value': 'weekly_ic'},
                        {'label': 'Monthly Covered Call', 'value': 'monthly_cc'},
                        {'label': 'Delta-Neutral Straddle', 'value': 'delta_neutral'},
                        {'label': 'Custom Strategy', 'value': 'custom'},
                    ],
                    value='weekly_ic',
                    placeholder="Select a strategy template..."
                )
            ], width=6),
            dbc.Col([
                dbc.Label("Lookback Period (days)", className="fw-bold"),
                dbc.Input(
                    id='ol-backtest-lookback',
                    type='number',
                    value=90,
                    min=30,
                    max=365
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Starting Capital", className="fw-bold"),
                dbc.Input(
                    id='ol-backtest-capital',
                    type='number',
                    value=10000,
                    min=1000,
                    step=1000
                )
            ], width=3),
        ], className="mb-3 g-2"),

        dbc.Button(
            "▶️ Run Backtest",
            id='ol-backtest-run-btn',
            color="primary",
            size="lg",
            className="mb-3"
        ),

        html.Div(id='ol-backtest-results', className="mb-3"),

        dcc.Graph(
            id='ol-backtest-equity-chart',
            config={'displayModeBar': True},
            style={'height': '400px'}
        ),

        html.Hr(),

        html.H6("Trade History", className="mb-2"),
        html.Div(id='ol-backtest-trades-table', className="mb-3"),

        dbc.Button(
            "📥 Export Results",
            id='ol-backtest-export-btn',
            color="success",
            size="sm"
        ),
        dcc.Download(id='ol-backtest-download'),

    ], fluid=True, className="p-3")


def _create_settings_subtab():
    """
    Settings - NEW subtab, uses ol-settings-* IDs.
    Configuration for Options Lab behavior.
    """
    return dbc.Container([
        dbc.Alert([
            html.H5("⚙️ Options Lab Settings", className="alert-heading"),
            html.P("Configure data sources, update intervals, and trading parameters."),
        ], color="secondary", className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Data Source Priority", className="fw-bold"),
                dcc.Dropdown(
                    id='ol-settings-datasource',
                    options=[
                        {'label': 'Alpaca → yfinance → Mock', 'value': 'alpaca_first'},
                        {'label': 'yfinance → Alpaca → Mock', 'value': 'yfinance_first'},
                        {'label': 'Mock Only (Deterministic)', 'value': 'mock_only'},
                    ],
                    value='alpaca_first'
                )
            ], width=6),
            dbc.Col([
                dbc.Label("Auto-Refresh Interval (seconds)", className="fw-bold"),
                dbc.Input(
                    id='ol-settings-refresh-interval',
                    type='number',
                    value=60,
                    min=10,
                    max=300,
                    step=10
                )
            ], width=6),
        ], className="mb-3 g-2"),

        html.Hr(),

        dbc.Row([
            dbc.Col([
                dbc.Label("Paper Trading", className="fw-bold mb-2"),
                dbc.Checklist(
                    id='ol-settings-paper-enabled',
                    options=[
                        {'label': 'Enable Paper Trading Mode (All orders are simulated)', 'value': 'enabled'}
                    ],
                    value=['enabled']
                ),
                dbc.FormText("When enabled, all orders are paper-only. Disable to allow live orders (requires admin approval).")
            ], width=12),
        ], className="mb-4"),

        dbc.Button(
            "💾 Save Settings",
            id='ol-settings-save-btn',
            color="primary",
            size="lg"
        ),

    ], fluid=True, className="p-3")


def _error_fallback_layout(error):
    """
    Catastrophic failure fallback layout.
    Shown only if entire layout creation fails.
    """
    return dbc.Container([
        dbc.Alert([
            html.H4("⚠️ Options Lab Failed to Load", className="alert-heading"),
            html.P(f"Critical Error: {str(error)}"),
            html.Hr(),
            html.P([
                "The Options Lab tab could not be initialized. ",
                "Please check the browser console for details or contact support."
            ], className="mb-0"),
            html.Hr(),
            html.Pre(str(error), className="small text-muted")
        ], color="danger", className="m-5")
    ], fluid=True)
