"""
Options Lab Layout Module

Provides the main layout with 4 interactive subtabs:
1. Chain Viewer - Live options chain with filtering
2. Greeks Dashboard - Real-time Greeks analysis
3. Vol Surface - 3D implied volatility visualization
4. Trade Simulator - Strategy P&L calculator
"""

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout():
    """
    Main layout for Options Lab tab.
    
    Returns:
        Dash component tree
    """
    return dbc.Container([
        # Header
        html.Div([
            html.H3("💹 Options Lab", className="mb-2"),
            html.P(
                "Comprehensive options analytics: live chains, Greeks, volatility surfaces, and trade simulation",
                className="mb-4", style={'color': '#000000'}
            )
        ]),
        
        # Ticker Input Row
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Ticker"),
                    dbc.Input(
                        id='options-ticker-input',
                        type='text',
                        value='AAPL',
                        placeholder='Enter ticker...',
                        style={'textTransform': 'uppercase'},
                        className='options-ticker-input'  # Use class for testing instead
                    ),
                    dbc.Button(
                        "Load Chain",
                        id='options-load-btn',
                        color='primary',
                        n_clicks=0,
                        className='options-load-btn'  # Use class for testing
                    ),
                    dbc.Button(
                        "Use Mock Data",
                        id='options-mock-btn',
                        color='secondary',
                        outline=True,
                        n_clicks=0,
                        className='options-mock-btn'  # Use class for testing
                    )
                ], className="mb-3")
            ], width=6),
            dbc.Col([
                html.Div(id='options-status-message', className="pt-2", style={'color': '#000000'})
            ], width=6)
        ]),
        
        # Subtabs Navigation
        dbc.Tabs(
            id="options-subtabs",
            active_tab="chain-viewer",
            className="mb-4 options-subtabs",
            children=[
                dbc.Tab(
                    label="📊 Chain Viewer",
                    tab_id="chain-viewer",
                    className="options-tab-chain-viewer",
                    children=[_create_chain_viewer_layout()]
                ),
                dbc.Tab(
                    label="🔢 Greeks Dashboard",
                    tab_id="greeks-dashboard",
                    className="options-tab-greeks",
                    children=[_create_greeks_layout()]
                ),
                dbc.Tab(
                    label="🌐 Vol Surface",
                    tab_id="vol-surface",
                    className="options-tab-vol-surface",
                    children=[_create_vol_surface_layout()]
                ),
                dbc.Tab(
                    label="🎯 Trade Simulator",
                    tab_id="trade-simulator",
                    className="options-tab-simulator",
                    children=[_create_trade_simulator_layout()]
                )
            ]
        ),
        
        # Hidden stores for data
        dcc.Store(id='options-chain-store'),
        dcc.Store(id='options-surface-store'),
        
        # Auto-refresh interval (30 seconds)
        dcc.Interval(
            id='options-refresh-interval',
            interval=30*1000,  # 30 seconds
            n_intervals=0,
            disabled=True  # Start disabled
        )
        
    ], fluid=True)


def _create_chain_viewer_layout():
    """Create layout for Chain Viewer subtab."""
    return dbc.Container([
        html.Div([
            html.H5("Options Chain Viewer", className="mt-3 mb-3"),
            
            # Summary Cards
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Spot Price", className="mb-1", style={'color': '#000000'}),
                            html.H4(id='chain-spot-price', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Total Volume", className="mb-1", style={'color': '#000000'}),
                            html.H4(id='chain-total-volume', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Open Interest", className="mb-1", style={'color': '#000000'}),
                            html.H4(id='chain-total-oi', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Put/Call Ratio", className="mb-1", style={'color': '#000000'}),
                            html.H4(id='chain-pcr', children="--"),
                        ])
                    ])
                ], width=3)
            ], className="mb-4"),
            
            # Filter Controls
            dbc.Row([
                dbc.Col([
                    dbc.Label("Expiration Date", style={'color': '#000000', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id='chain-expiration-dropdown',
                        options=[],
                        value=None,
                        placeholder="Select expiration...",
                        style={
                            'backgroundColor': '#ffffff',
                            'color': '#000000'
                        },
                        className='custom-dropdown'
                    )
                ], width=4),
                dbc.Col([
                    dbc.Label("Option Type", style={'color': '#000000', 'fontWeight': '500'}),
                    dbc.RadioItems(
                        id='chain-type-radio',
                        options=[
                            {'label': 'Calls', 'value': 'calls'},
                            {'label': 'Puts', 'value': 'puts'},
                            {'label': 'Both', 'value': 'both'}
                        ],
                        value='both',
                        inline=True,
                        style={'color': '#ffffff'}
                    )
                ], width=4),
                dbc.Col([
                    dbc.Label("Moneyness Filter", style={'color': '#000000', 'fontWeight': '500'}),
                    dbc.RadioItems(
                        id='chain-moneyness-radio',
                        options=[
                            {'label': 'All', 'value': 'all'},
                            {'label': 'ITM', 'value': 'ITM'},
                            {'label': 'ATM', 'value': 'ATM'},
                            {'label': 'OTM', 'value': 'OTM'}
                        ],
                        value='all',
                        inline=True,
                        style={'color': '#ffffff'}
                    )
                ], width=4)
            ], className="mb-3"),
            
            # Chain Table
            html.Div([
                dbc.Spinner(
                    html.Div(id='chain-table-container'),
                    color="primary"
                )
            ]),
            
            # Export Button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "📥 Export to CSV",
                        id='chain-export-btn',
                        color='success',
                        outline=True,
                        className="mt-3 chain-export-btn",
                        n_clicks=0
                    )
                ])
            ]),
            
            dcc.Download(id='chain-download'),
            
            # Contract Selector & Analysis Card
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🎯 Contract Selector & Analysis", className="mb-0")),
                        dbc.CardBody([
                            # Selection Controls - Phase 22B Enhanced
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Ticker Symbol:", className="fw-bold mb-2"),
                                    dcc.Dropdown(
                                        id='contract-ticker-selector',
                                        options=[
                                            {'label': '🍎 AAPL - Apple', 'value': 'AAPL'},
                                            {'label': '📱 MSFT - Microsoft', 'value': 'MSFT'},
                                            {'label': '🔍 GOOGL - Google', 'value': 'GOOGL'},
                                            {'label': '🚗 TSLA - Tesla', 'value': 'TSLA'},
                                            {'label': '📦 AMZN - Amazon', 'value': 'AMZN'},
                                            {'label': '🎮 NVDA - Nvidia', 'value': 'NVDA'},
                                            {'label': '📘 META - Meta', 'value': 'META'},
                                            {'label': '📊 SPY - S&P 500 ETF', 'value': 'SPY'},
                                            {'label': '💎 QQQ - Nasdaq ETF', 'value': 'QQQ'}
                                        ],
                                        value='AAPL',
                                        placeholder='Select ticker...',
                                        className="mb-3",
                                        style={'backgroundColor': '#ffffff', 'color': '#000000'}
                                    )
                                ], md=3),
                                dbc.Col([
                                    html.Label("Option Type:", className="fw-bold mb-2"),
                                    dbc.RadioItems(
                                        id='contract-option-type',
                                        options=[
                                            {'label': '📈 Call', 'value': 'call'},
                                            {'label': '📉 Put', 'value': 'put'}
                                        ],
                                        value='call',
                                        inline=True,
                                        className="mb-3"
                                    )
                                ], md=3),
                                dbc.Col([
                                    html.Label("Strike Price:", className="fw-bold mb-2"),
                                    dcc.Dropdown(
                                        id='contract-strike-selector',
                                        options=[],
                                        placeholder='Select strike...',
                                        className="mb-3",
                                        style={'backgroundColor': '#ffffff', 'color': '#000000'}
                                    )
                                ], md=3),
                                dbc.Col([
                                    html.Label("Expiration:", className="fw-bold mb-2"),
                                    dcc.Dropdown(
                                        id='contract-expiration-selector',
                                        options=[],
                                        placeholder='Select expiration...',
                                        className="mb-3",
                                        style={'backgroundColor': '#ffffff', 'color': '#000000'}
                                    )
                                ], md=3)
                            ]),
                            
                            # Action Buttons
                            dbc.Row([
                                dbc.Col([
                                    dbc.ButtonGroup([
                                        dbc.Button(
                                            "🔮 Generate Forecast",
                                            id='options-forecast-btn',
                                            color='primary',
                                            n_clicks=0
                                        ),
                                        dbc.Button(
                                            "📡 Get TradingView Signals",
                                            id='tradingview-fetch-btn',
                                            color='info',
                                            outline=True,
                                            n_clicks=0
                                        )
                                    ], className="w-100")
                                ])
                            ], className="mb-3"),
                            
                            # Results Area
                            html.Div([
                                # Forecast Results
                                html.Div(id='options-forecast-results', className="mb-3"),
                                
                                # TradingView Signals (contextual - shows only when requested)
                                html.Div(id='tradingview-signals-container', className="mb-3")
                            ])
                        ])
                    ])
                ])
            ], className="mb-4")
        ])
    ], fluid=True)


def _create_greeks_layout():
    """Create layout for Greeks Dashboard subtab."""
    return dbc.Container([
        html.Div([
            html.H5("Greeks Dashboard", className="mt-3 mb-3"),
            html.P("Real-time Greeks analysis and risk metrics", className="mb-4", style={'color': '#000000'}),
            
            # Greeks Charts Row
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='greeks-delta-chart', config={'displayModeBar': False})
                ], width=6),
                dbc.Col([
                    dcc.Graph(id='greeks-gamma-chart', config={'displayModeBar': False})
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='greeks-theta-chart', config={'displayModeBar': False})
                ], width=6),
                dbc.Col([
                    dcc.Graph(id='greeks-vega-chart', config={'displayModeBar': False})
                ], width=6)
            ], className="mb-4"),
            
            # Implied Volatility Chart
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='greeks-iv-smile', config={'displayModeBar': True})
                ], width=12)
            ])
        ])
    ], fluid=True)


def _create_vol_surface_layout():
    """Create layout for Volatility Surface subtab."""
    return dbc.Container([
        html.Div([
            html.H5("3D Volatility Surface", className="mt-3 mb-3"),
            html.P("Interactive implied volatility surface across strikes and expirations", 
                   className="mb-4", style={'color': '#000000'}),
            
            # Surface Chart
            dbc.Row([
                dbc.Col([
                    dbc.Spinner(
                        dcc.Graph(
                            id='vol-surface-3d',
                            config={'displayModeBar': True},
                            style={'height': '600px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ]),
            
            # Surface Controls
            dbc.Row([
                dbc.Col([
                    dbc.Label("View Angle"),
                    dcc.Slider(
                        id='surface-angle-slider',
                        min=0,
                        max=360,
                        step=10,
                        value=45,
                        marks={0: '0°', 90: '90°', 180: '180°', 270: '270°', 360: '360°'},
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Color Scale"),
                    dcc.Dropdown(
                        id='surface-colorscale-dropdown',
                        options=[
                            {'label': 'Viridis', 'value': 'Viridis'},
                            {'label': 'Plasma', 'value': 'Plasma'},
                            {'label': 'Blues', 'value': 'Blues'},
                            {'label': 'Hot', 'value': 'Hot'}
                        ],
                        value='Viridis'
                    )
                ], width=6)
            ], className="mt-3")
        ])
    ], fluid=True)


def _create_trade_simulator_layout():
    """Create layout for Trade Simulator subtab."""
    return dbc.Container([
        html.Div([
            html.H5("Trade Simulator", className="mt-3 mb-3"),
            html.P("Calculate P&L and risk metrics for options strategies", 
                   className="mb-4", style={'color': '#000000'}),
            
            # Strategy Builder
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Strategy Builder"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Strategy Type"),
                                    dcc.Dropdown(
                                        id='sim-strategy-dropdown',
                                        options=[
                                            {'label': 'Long Call', 'value': 'long_call'},
                                            {'label': 'Long Put', 'value': 'long_put'},
                                            {'label': 'Covered Call', 'value': 'covered_call'},
                                            {'label': 'Bull Call Spread', 'value': 'bull_call_spread'},
                                            {'label': 'Bear Put Spread', 'value': 'bear_put_spread'},
                                            {'label': 'Iron Condor', 'value': 'iron_condor'},
                                            {'label': 'Straddle', 'value': 'straddle'}
                                        ],
                                        value='long_call'
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("Quantity"),
                                    dbc.Input(
                                        id='sim-quantity-input',
                                        type='number',
                                        value=1,
                                        min=1,
                                        max=100
                                    )
                                ], width=6)
                            ], className="mb-3"),
                            
                            dbc.Button(
                                "Calculate P&L",
                                id='sim-calculate-btn',
                                color='primary',
                                n_clicks=0,
                                className="w-100 sim-calculate-btn"
                            )
                        ])
                    ])
                ], width=4),
                
                # P&L Metrics
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("P&L Metrics"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.H6("Max Profit", className="mb-1", style={'color': '#000000'}),
                                    html.H5(id='sim-max-profit', children="$0.00", 
                                           className="text-success")
                                ], width=4),
                                dbc.Col([
                                    html.H6("Max Loss", className="mb-1", style={'color': '#000000'}),
                                    html.H5(id='sim-max-loss', children="$0.00", 
                                           className="text-danger")
                                ], width=4),
                                dbc.Col([
                                    html.H6("Breakeven", className="mb-1", style={'color': '#000000'}),
                                    html.H5(id='sim-breakeven', children="--")
                                ], width=4)
                            ])
                        ])
                    ])
                ], width=8)
            ], className="mb-4"),
            
            # P&L Chart
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='sim-pnl-chart', config={'displayModeBar': True})
                ], width=12)
            ])
        ])
    ], fluid=True)


# TradingView layout function removed - signals now shown contextually in Chain Viewer
