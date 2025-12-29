"""
Strategy Lab - Trading Bots Subtab
Live trading bot management and automation

Features:
- AlphaBot: RSI/MACD strategy with real-time signals
- Alpaca Paper Trading integration
- Live price and account monitoring
- Trade execution logging
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback_context
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import bot engine components
try:
    from financial_dashboard.services.bot_engine import (
        get_bot_manager, BotConfig, BotStatus, SignalType
    )
    BOT_ENGINE_AVAILABLE = True
except ImportError:
    BOT_ENGINE_AVAILABLE = False


def create_connection_status_panel() -> dbc.Card:
    """Create Alpaca connection status panel with account info."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-plug me-2"),
                html.Strong("Broker Connection"),
            ], className="d-flex align-items-center")
        ], style={'backgroundColor': 'rgba(40, 167, 69, 0.15)'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Small("Status", className="text-muted d-block"),
                        html.Div(id="bot-connection-status", children=[
                            dbc.Spinner(size="sm", color="primary"),
                            html.Span(" Checking...", className="ms-2")
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Small("Account Type", className="text-muted d-block"),
                        html.Span(id="bot-account-type", children="--", className="fw-bold")
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Small("Buying Power", className="text-muted d-block"),
                        html.Span(id="bot-buying-power", children="$--", className="fw-bold text-success")
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Small("Portfolio Value", className="text-muted d-block"),
                        html.Span(id="bot-portfolio-value", children="$--", className="fw-bold")
                    ])
                ], width=3),
            ]),
            # Refresh button
            dbc.Button([
                html.I(className="fas fa-sync-alt me-1"),
                "Refresh"
            ], id="bot-refresh-connection", color="outline-secondary", size="sm", className="mt-2")
        ], className="py-2")
    ], className="mb-3", style={'border': '1px solid rgba(40, 167, 69, 0.3)'})


def create_live_price_panel() -> dbc.Card:
    """Create live price and indicator panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-chart-line me-2"),
                html.Strong("Live Market Data"),
                dbc.Badge("REAL-TIME", color="success", className="ms-auto", pill=True)
            ], className="d-flex align-items-center")
        ], style={'backgroundColor': 'rgba(0, 123, 255, 0.1)'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Small("Symbol", className="text-muted d-block"),
                        html.Span(id="live-ticker-display", children="AAPL", className="fs-4 fw-bold")
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("Last Price", className="text-muted d-block"),
                        html.Span(id="live-price-display", children="$--", className="fs-4 fw-bold text-info")
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("Change", className="text-muted d-block"),
                        html.Span(id="live-change-display", children="--", className="fs-5 fw-bold")
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("RSI (14)", className="text-muted d-block"),
                        html.Div([
                            html.Span(id="live-rsi-value", children="--", className="fs-4 fw-bold"),
                            html.Span(id="live-rsi-signal", className="ms-2")
                        ])
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("MACD", className="text-muted d-block"),
                        html.Span(id="live-macd-value", children="--", className="fs-5 fw-bold")
                    ])
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Small("Volume", className="text-muted d-block"),
                        html.Span(id="live-volume-display", children="--", className="fs-5")
                    ])
                ], width=2),
            ]),
            # RSI Gauge
            dcc.Graph(
                id="rsi-gauge-chart",
                config={'displayModeBar': False},
                style={'height': '120px', 'marginTop': '10px'}
            )
        ])
    ], className="mb-3", style={'border': '1px solid rgba(0, 123, 255, 0.3)'})


def create_alphabot_control_panel() -> dbc.Card:
    """
    Create AlphaBot Control Panel - RSI Strategy Bot with Alpaca.
    
    Features:
    - Single ticker RSI/MACD-based trading
    - Paper trading mode (Alpaca)
    - Real-time signal display
    - Trade log viewer
    """
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Span("🤖", className="me-2 fs-5"),
                html.Strong("AlphaBot Trading Engine", className="fs-5"),
                html.Div([
                    dbc.Badge("PAPER", color="warning", className="me-1"),
                    dbc.Badge("yfinance", color="info", pill=True),
                ], className="ms-auto")
            ], className="d-flex align-items-center")
        ], style={'backgroundColor': 'rgba(249, 115, 22, 0.2)', 'borderBottom': '2px solid #f97316'}),
        dbc.CardBody([
            # Top Status Row - Live Metrics
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Small("Bot Status", className="text-muted"),
                            html.Div(id="alphabot-status", children=[
                                dbc.Badge("STOPPED", color="secondary", className="fs-6")
                            ], className="mt-1")
                        ], className="text-center py-2")
                    ], style={'backgroundColor': 'rgba(0,0,0,0.2)'})
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Small("Signal", className="text-muted"),
                            html.Div(id="alphabot-signal", children=[
                                dbc.Badge("HOLD", color="info", className="fs-6")
                            ], className="mt-1")
                        ], className="text-center py-2")
                    ], style={'backgroundColor': 'rgba(0,0,0,0.2)'})
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Small("RSI", className="text-muted"),
                            html.Div(id="alphabot-rsi", children=[
                                html.Span("--", className="fs-4 fw-bold text-warning")
                            ], className="mt-1")
                        ], className="text-center py-2")
                    ], style={'backgroundColor': 'rgba(0,0,0,0.2)'})
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Small("Trades Today", className="text-muted"),
                            html.Div(id="alphabot-trade-count", children=[
                                html.Span("0", className="fs-4 fw-bold text-info")
                            ], className="mt-1")
                        ], className="text-center py-2")
                    ], style={'backgroundColor': 'rgba(0,0,0,0.2)'})
                ], width=3),
            ], className="mb-3"),
            
            html.Hr(className="my-2"),
            
            # Configuration Section
            html.Div([
                html.H6([
                    html.I(className="fas fa-cog me-2"),
                    "Bot Configuration"
                ], className="text-muted mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Ticker Symbol", className="fw-bold small"),
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fas fa-search")),
                            dbc.Input(
                                id="alphabot-ticker",
                                type="text",
                                value="AAPL",
                                placeholder="Enter ticker...",
                                className="text-uppercase",
                                style={'textTransform': 'uppercase'}
                            )
                        ], size="sm")
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Strategy", className="fw-bold small"),
                        dcc.Dropdown(
                            id="alphabot-strategy",
                            options=[
                                {'label': '📊 RSI Only', 'value': 'rsi'},
                                {'label': '📈 MACD Only', 'value': 'macd'},
                                {'label': '🔀 RSI + MACD', 'value': 'rsi_macd'},
                            ],
                            value='rsi',
                            clearable=False,
                            className="dash-dropdown-dark"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Shares per Trade", className="fw-bold small"),
                        dbc.Input(
                            id="alphabot-quantity",
                            type="number",
                            value=1,
                            min=1,
                            max=100,
                            size="sm"
                        )
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Interval (sec)", className="fw-bold small"),
                        dbc.Input(
                            id="alphabot-interval",
                            type="number",
                            value=60,
                            min=30,
                            max=3600,
                            size="sm"
                        )
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Max Daily Trades", className="fw-bold small"),
                        dbc.Input(
                            id="alphabot-max-trades",
                            type="number",
                            value=10,
                            min=1,
                            max=100,
                            size="sm"
                        )
                    ], width=2),
                ], className="mb-2"),
                
                # RSI Thresholds with visual indicator
                dbc.Row([
                    dbc.Col([
                        dbc.Label([
                            html.Span("RSI Oversold", className="me-2"),
                            dbc.Badge("BUY", color="success", className="small")
                        ], className="fw-bold small"),
                        dbc.Input(
                            id="alphabot-rsi-oversold",
                            type="number",
                            value=30,
                            min=10,
                            max=40,
                            size="sm"
                        ),
                        html.Small("Buy when RSI drops below this", className="text-muted")
                    ], width=4),
                    dbc.Col([
                        dbc.Label([
                            html.Span("RSI Overbought", className="me-2"),
                            dbc.Badge("SELL", color="danger", className="small")
                        ], className="fw-bold small"),
                        dbc.Input(
                            id="alphabot-rsi-overbought",
                            type="number",
                            value=70,
                            min=60,
                            max=90,
                            size="sm"
                        ),
                        html.Small("Sell when RSI rises above this", className="text-muted")
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Risk Per Trade ($)", className="fw-bold small"),
                        dbc.Input(
                            id="alphabot-risk-amount",
                            type="number",
                            value=100,
                            min=10,
                            max=10000,
                            size="sm"
                        ),
                        html.Small("Max loss per position", className="text-muted")
                    ], width=4),
                ], className="mb-3"),
            ]),
            
            html.Hr(className="my-2"),
            
            # Control Buttons - Larger and more prominent
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Button([
                            html.I(className="fas fa-play me-2"),
                            "Start Bot"
                        ], id="alphabot-start-btn", color="success", size="lg", className="w-100")
                    ], width=4),
                    dbc.Col([
                        dbc.Button([
                            html.I(className="fas fa-stop me-2"),
                            "Stop Bot"
                        ], id="alphabot-stop-btn", color="danger", outline=True, size="lg", className="w-100")
                    ], width=4),
                    dbc.Col([
                        dbc.Button([
                            html.I(className="fas fa-bolt me-2"),
                            "Run Single Tick"
                        ], id="alphabot-tick-btn", color="info", outline=True, size="lg", className="w-100")
                    ], width=4),
                ])
            ], className="mb-3"),
            
            # Live Trade Log
            html.Div([
                html.Div([
                    html.H6([
                        html.I(className="fas fa-list-alt me-2"),
                        "Activity Log"
                    ], className="text-muted mb-0 d-inline"),
                    dbc.Button([
                        html.I(className="fas fa-trash-alt")
                    ], id="alphabot-clear-log", color="link", size="sm", className="float-end text-muted")
                ], className="mb-2"),
                html.Div(
                    id="alphabot-trade-log",
                    children=[
                        html.Div([
                            html.I(className="fas fa-info-circle me-2 text-muted"),
                            "Click 'Run Single Tick' to fetch current RSI and generate a signal."
                        ], className="text-muted text-center py-4")
                    ],
                    style={
                        'maxHeight': '200px',
                        'overflowY': 'auto',
                        'backgroundColor': 'rgba(0,0,0,0.4)',
                        'padding': '12px',
                        'borderRadius': '8px',
                        'fontSize': '0.85rem',
                        'fontFamily': 'monospace'
                    }
                )
            ]),
            
            # Data Source Info
            dbc.Alert([
                html.I(className="fas fa-database me-2"),
                html.Strong("Data Source: "),
                "yfinance (free, real-time delayed 15min). RSI/MACD calculated locally.",
                html.Br(),
                html.I(className="fas fa-paper-plane me-2 mt-1"),
                html.Strong("Execution: "),
                "Alpaca Paper Trading API (no real money at risk)"
            ], color="info", className="mt-3 mb-0 py-2 small"),
        ])
    ], className="mb-3", style={
        'backgroundColor': 'rgba(249, 115, 22, 0.05)',
        'border': '1px solid rgba(249, 115, 22, 0.4)',
        'borderRadius': '10px'
    })


def create_strategy_guide_panel() -> dbc.Card:
    """Create a strategy guide and help panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-graduation-cap me-2"),
                html.Strong("RSI Strategy Guide"),
            ], className="d-flex align-items-center")
        ]),
        dbc.CardBody([
            dbc.Accordion([
                dbc.AccordionItem([
                    html.P([
                        html.Strong("RSI (Relative Strength Index)"),
                        " measures momentum on a 0-100 scale."
                    ]),
                    html.Ul([
                        html.Li([html.Strong("RSI < 30: "), "Oversold → Potential BUY signal"]),
                        html.Li([html.Strong("RSI > 70: "), "Overbought → Potential SELL signal"]),
                        html.Li([html.Strong("RSI 30-70: "), "Neutral zone → HOLD"]),
                    ]),
                    dbc.Alert([
                        html.I(className="fas fa-lightbulb me-2"),
                        "This is a mean-reversion strategy - it bets that extreme moves will reverse."
                    ], color="warning", className="small mb-0")
                ], title="How RSI Trading Works"),
                
                dbc.AccordionItem([
                    html.Ol([
                        html.Li("Set your ticker (e.g., AAPL, MSFT, SPY)"),
                        html.Li("Adjust RSI thresholds (default: 30/70)"),
                        html.Li("Set position size (shares per trade)"),
                        html.Li("Click 'Run Single Tick' to test"),
                        html.Li("Click 'Start Bot' for auto-trading"),
                    ]),
                    dbc.Alert([
                        html.I(className="fas fa-shield-alt me-2"),
                        "All trades execute in Alpaca PAPER mode - no real money!"
                    ], color="success", className="small mb-0")
                ], title="Quick Start"),
                
                dbc.AccordionItem([
                    html.Ul([
                        html.Li("Start with small position sizes (1-5 shares)"),
                        html.Li("Use on liquid stocks (high volume)"),
                        html.Li("Don't trade during major news events"),
                        html.Li("Set a maximum daily trade limit"),
                        html.Li("Monitor your paper P&L before going live"),
                    ])
                ], title="Best Practices"),
            ], start_collapsed=True)
        ])
    ], className="mb-3")


def create_bot_card(bot_id: str, bot_type: str, status: str, performance: dict = None) -> dbc.Card:
    """Create a trading bot status card."""
    status_colors = {
        'running': 'success',
        'stopped': 'secondary',
        'error': 'danger',
        'paused': 'warning'
    }
    
    bot_icons = {
        'momentum': '🚀',
        'mean_reversion': '🔄',
        'pairs': '⚖️',
        'news_sentiment': '📰',
        'custom': '⚙️'
    }
    
    perf = performance or {'pnl': 0, 'trades': 0, 'win_rate': 0}
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Span(bot_icons.get(bot_type, '🤖'), className="me-2"),
                html.Strong(bot_id.replace('_', ' ').title()),
                dbc.Badge(
                    status.upper(),
                    color=status_colors.get(status, 'info'),
                    className="ms-auto"
                )
            ], className="d-flex align-items-center")
        ], style={'backgroundColor': 'rgba(40, 167, 69, 0.1)' if status == 'running' else 'rgba(108, 117, 125, 0.1)'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Small("P&L", className="text-muted"),
                    html.H5(
                        f"${perf['pnl']:,.2f}",
                        className="text-success" if perf['pnl'] >= 0 else "text-danger"
                    )
                ], width=4),
                dbc.Col([
                    html.Small("Trades", className="text-muted"),
                    html.H5(f"{perf['trades']}")
                ], width=4),
                dbc.Col([
                    html.Small("Win Rate", className="text-muted"),
                    html.H5(f"{perf['win_rate']:.1f}%")
                ], width=4),
            ]),
            html.Hr(),
            dbc.ButtonGroup([
                dbc.Button(
                    [html.I(className="fas fa-play me-1"), "Start"] if status != 'running' else [html.I(className="fas fa-pause me-1"), "Pause"],
                    color="success" if status != 'running' else "warning",
                    size="sm",
                    id={'type': 'bot-start-btn', 'index': bot_id}
                ),
                dbc.Button(
                    [html.I(className="fas fa-stop me-1"), "Stop"],
                    color="danger",
                    size="sm",
                    outline=True,
                    id={'type': 'bot-stop-btn', 'index': bot_id}
                ),
                dbc.Button(
                    [html.I(className="fas fa-cog me-1"), "Config"],
                    color="info",
                    size="sm",
                    outline=True,
                    id={'type': 'bot-config-btn', 'index': bot_id}
                ),
            ], size="sm", className="w-100")
        ])
    ], className="mb-3", style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})


def create_bot_config_modal() -> dbc.Modal:
    """Create bot configuration modal."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Configure Trading Bot")),
        dbc.ModalBody([
            dbc.Form([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Bot Name"),
                        dbc.Input(
                            id="bot-config-name",
                            type="text",
                            placeholder="My Momentum Bot"
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Bot Type"),
                        dcc.Dropdown(
                            id="bot-config-type",
                            options=[
                                {'label': '🚀 Momentum', 'value': 'momentum'},
                                {'label': '🔄 Mean Reversion', 'value': 'mean_reversion'},
                                {'label': '⚖️ Pairs Trading', 'value': 'pairs'},
                                {'label': '📰 News Sentiment', 'value': 'news_sentiment'},
                                {'label': '⚙️ Custom Schedule', 'value': 'custom'}
                            ],
                            value='momentum',
                            clearable=False,
                            style={'backgroundColor': '#2d2d2d', 'color': 'white'}
                        )
                    ], width=6),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Symbols (comma-separated)"),
                        dbc.Input(
                            id="bot-config-symbols",
                            type="text",
                            placeholder="AAPL, MSFT, GOOGL, NVDA"
                        )
                    ], width=12),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Position Size ($)"),
                        dbc.Input(
                            id="bot-config-position-size",
                            type="number",
                            value=1000,
                            min=100,
                            max=100000
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Max Positions"),
                        dbc.Input(
                            id="bot-config-max-positions",
                            type="number",
                            value=5,
                            min=1,
                            max=20
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Daily Loss Limit ($)"),
                        dbc.Input(
                            id="bot-config-loss-limit",
                            type="number",
                            value=500,
                            min=50,
                            max=10000
                        )
                    ], width=4),
                ], className="mb-3"),
                
                html.Hr(),
                html.H6("Strategy Parameters", className="text-info"),
                
                # Momentum Parameters
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("RSI Oversold"),
                            dbc.Input(id="bot-config-rsi-oversold", type="number", value=30, min=10, max=40)
                        ], width=4),
                        dbc.Col([
                            dbc.Label("RSI Overbought"),
                            dbc.Input(id="bot-config-rsi-overbought", type="number", value=70, min=60, max=90)
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Momentum Lookback"),
                            dbc.Input(id="bot-config-momentum-lookback", type="number", value=14, min=5, max=50)
                        ], width=4),
                    ]),
                ], id="momentum-params", className="mb-3"),
                
                # Mean Reversion Parameters
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Bollinger Period"),
                            dbc.Input(id="bot-config-bb-period", type="number", value=20, min=10, max=50)
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Bollinger Std Dev"),
                            dbc.Input(id="bot-config-bb-std", type="number", value=2, min=1, max=4, step=0.5)
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Mean Period"),
                            dbc.Input(id="bot-config-mean-period", type="number", value=20, min=5, max=100)
                        ], width=4),
                    ]),
                ], id="mean-reversion-params", className="mb-3", style={'display': 'none'}),
                
                html.Hr(),
                html.H6("Risk Management", className="text-warning"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Stop Loss %"),
                        dbc.Input(id="bot-config-stop-loss", type="number", value=2, min=0.5, max=10, step=0.5)
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Take Profit %"),
                        dbc.Input(id="bot-config-take-profit", type="number", value=5, min=1, max=20, step=0.5)
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Trailing Stop %"),
                        dbc.Input(id="bot-config-trailing-stop", type="number", value=1.5, min=0.5, max=5, step=0.5)
                    ], width=4),
                ], className="mb-3"),
                
                html.Hr(),
                html.H6("Schedule", className="text-success"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Trading Hours"),
                        dcc.RangeSlider(
                            id="bot-config-trading-hours",
                            min=0,
                            max=24,
                            step=1,
                            value=[9, 16],
                            marks={i: f"{i}:00" for i in range(0, 25, 3)}
                        )
                    ], width=12),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Checklist(
                            id="bot-config-days",
                            options=[
                                {'label': 'Mon', 'value': 0},
                                {'label': 'Tue', 'value': 1},
                                {'label': 'Wed', 'value': 2},
                                {'label': 'Thu', 'value': 3},
                                {'label': 'Fri', 'value': 4},
                            ],
                            value=[0, 1, 2, 3, 4],
                            inline=True
                        )
                    ], width=12),
                ]),
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="bot-config-cancel", color="secondary"),
            dbc.Button("Save Bot", id="bot-config-save", color="success"),
        ])
    ], id="bot-config-modal", size="lg", is_open=False)


def create_bot_performance_chart() -> dcc.Graph:
    """Create bot performance chart."""
    fig = go.Figure()
    
    # Sample data - will be replaced with real data
    hours = list(range(9, 17))
    bot1_pnl = [0, 50, 75, 60, 120, 180, 150, 200]
    bot2_pnl = [0, -20, 10, 30, 50, 80, 100, 130]
    
    fig.add_trace(go.Scatter(
        x=hours,
        y=bot1_pnl,
        mode='lines+markers',
        name='Momentum Bot',
        line=dict(color='#00d4aa', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 170, 0.1)'
    ))
    
    fig.add_trace(go.Scatter(
        x=hours,
        y=bot2_pnl,
        mode='lines+markers',
        name='Mean Reversion Bot',
        line=dict(color='#ffc107', width=2),
        fill='tozeroy',
        fillcolor='rgba(255, 193, 7, 0.1)'
    ))
    
    fig.update_layout(
        title="Bot P&L Today",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis_title="Hour",
        yaxis_title="P&L ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


def create_active_trades_table() -> html.Div:
    """Create active trades table."""
    return html.Div([
        dbc.Table([
            html.Thead([
                html.Tr([
                    html.Th("Bot"),
                    html.Th("Symbol"),
                    html.Th("Side"),
                    html.Th("Qty"),
                    html.Th("Entry"),
                    html.Th("Current"),
                    html.Th("P&L"),
                    html.Th("Actions"),
                ])
            ]),
            html.Tbody(id="active-trades-tbody", children=[
                html.Tr([
                    html.Td("Momentum Bot"),
                    html.Td("NVDA"),
                    html.Td(dbc.Badge("BUY", color="success")),
                    html.Td("10"),
                    html.Td("$130.50"),
                    html.Td("$132.80"),
                    html.Td(html.Span("+$23.00", className="text-success")),
                    html.Td(dbc.Button("Close", color="danger", size="sm")),
                ]),
                html.Tr([
                    html.Td("Mean Reversion"),
                    html.Td("AAPL"),
                    html.Td(dbc.Badge("SELL", color="danger")),
                    html.Td("15"),
                    html.Td("$178.20"),
                    html.Td("$177.50"),
                    html.Td(html.Span("+$10.50", className="text-success")),
                    html.Td(dbc.Button("Close", color="danger", size="sm")),
                ]),
            ])
        ], bordered=True, hover=True, responsive=True, 
           className="table-dark", style={'fontSize': '0.9rem'})
    ])


def create_bot_logs() -> html.Div:
    """Create bot activity logs."""
    return html.Div([
        html.Div([
            html.Div([
                html.Span("10:45:32", className="text-muted me-2"),
                dbc.Badge("BUY", color="success", className="me-2"),
                html.Span("Momentum Bot: Bought 10 NVDA @ $130.50")
            ], className="mb-1"),
            html.Div([
                html.Span("10:42:15", className="text-muted me-2"),
                dbc.Badge("SIGNAL", color="info", className="me-2"),
                html.Span("Momentum Bot: RSI oversold signal on NVDA")
            ], className="mb-1"),
            html.Div([
                html.Span("10:30:00", className="text-muted me-2"),
                dbc.Badge("START", color="primary", className="me-2"),
                html.Span("All bots started for trading session")
            ], className="mb-1"),
            html.Div([
                html.Span("10:15:22", className="text-muted me-2"),
                dbc.Badge("SELL", color="danger", className="me-2"),
                html.Span("Mean Reversion: Sold 15 AAPL @ $178.20 (short)")
            ], className="mb-1"),
            html.Div([
                html.Span("09:30:00", className="text-muted me-2"),
                dbc.Badge("INIT", color="secondary", className="me-2"),
                html.Span("Trading bots initialized, waiting for market open")
            ], className="mb-1"),
        ], id="bot-logs-content", style={
            'maxHeight': '200px',
            'overflowY': 'auto',
            'fontSize': '0.85rem',
            'backgroundColor': 'rgba(0,0,0,0.3)',
            'padding': '10px',
            'borderRadius': '5px'
        })
    ])


def create_quick_stats() -> dbc.Row:
    """Create quick stats row."""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total P&L Today", className="text-muted mb-1"),
                    html.H3("+$330.00", className="text-success mb-0"),
                    html.Small("↑ 2.1% from yesterday", className="text-success")
                ])
            ], style={'backgroundColor': 'rgba(40, 167, 69, 0.1)', 'border': '1px solid rgba(40, 167, 69, 0.3)'})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Active Bots", className="text-muted mb-1"),
                    html.H3("2 / 4", className="text-info mb-0"),
                    html.Small("2 running, 2 stopped", className="text-muted")
                ])
            ], style={'backgroundColor': 'rgba(23, 162, 184, 0.1)', 'border': '1px solid rgba(23, 162, 184, 0.3)'})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Trades Today", className="text-muted mb-1"),
                    html.H3("12", className="text-warning mb-0"),
                    html.Small("8 wins, 4 losses", className="text-muted")
                ])
            ], style={'backgroundColor': 'rgba(255, 193, 7, 0.1)', 'border': '1px solid rgba(255, 193, 7, 0.3)'})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Win Rate", className="text-muted mb-1"),
                    html.H3("66.7%", className="text-success mb-0"),
                    html.Small("Above target (60%)", className="text-success")
                ])
            ], style={'backgroundColor': 'rgba(40, 167, 69, 0.1)', 'border': '1px solid rgba(40, 167, 69, 0.3)'})
        ], width=3),
    ], className="mb-4")


def create_bots_layout() -> html.Div:
    """Create the main Trading Bots layout."""
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-robot me-2"),
                    "Trading Bots"
                ], className="mb-0"),
                html.Small("Automated trading strategies powered by Alpaca Paper Trading", className="text-muted")
            ], width=8),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-plus me-1"),
                        "New Bot"
                    ], id="btn-new-bot", color="success", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-play me-1"),
                        "Start All"
                    ], id="btn-start-all-bots", color="primary", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-stop me-1"),
                        "Stop All"
                    ], id="btn-stop-all-bots", color="danger", size="sm", outline=True),
                ])
            ], width=4, className="text-end"),
        ], className="mb-4"),
        
        # Connection Status Panel - Shows Alpaca connection state
        create_connection_status_panel(),
        
        # Live Price Panel - Shows real-time data
        create_live_price_panel(),
        
        # Quick Stats
        create_quick_stats(),
        
        # AlphaBot Control Panel - RSI Strategy Bot
        dbc.Row([
            dbc.Col([
                create_alphabot_control_panel()
            ], width=8),
            dbc.Col([
                create_strategy_guide_panel()
            ], width=4),
        ], className="mb-3"),
        
        # Main Content
        dbc.Row([
            # Bot Cards Column
            dbc.Col([
                html.H5("Your Bots", className="mb-3"),
                html.Div(id="bot-cards-container", children=[
                    create_bot_card(
                        "momentum_bot_1",
                        "momentum",
                        "running",
                        {'pnl': 200.50, 'trades': 8, 'win_rate': 75.0}
                    ),
                    create_bot_card(
                        "mean_reversion_bot",
                        "mean_reversion",
                        "running",
                        {'pnl': 129.50, 'trades': 4, 'win_rate': 50.0}
                    ),
                    create_bot_card(
                        "pairs_trading_bot",
                        "pairs",
                        "stopped",
                        {'pnl': 0, 'trades': 0, 'win_rate': 0}
                    ),
                    create_bot_card(
                        "news_sentiment_bot",
                        "news_sentiment",
                        "stopped",
                        {'pnl': 0, 'trades': 0, 'win_rate': 0}
                    ),
                ])
            ], width=4),
            
            # Performance & Trades Column
            dbc.Col([
                # Performance Chart
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-line me-2"),
                        "Performance"
                    ]),
                    dbc.CardBody([
                        create_bot_performance_chart()
                    ])
                ], className="mb-3", style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'}),
                
                # Active Trades
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-exchange-alt me-2"),
                        "Active Positions"
                    ]),
                    dbc.CardBody([
                        create_active_trades_table()
                    ])
                ], className="mb-3", style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'}),
            ], width=8),
        ]),
        
        # Activity Logs
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-list me-2"),
                        "Activity Log",
                        dbc.Button(
                            [html.I(className="fas fa-sync-alt")],
                            id="btn-refresh-logs",
                            color="link",
                            size="sm",
                            className="float-end"
                        )
                    ]),
                    dbc.CardBody([
                        create_bot_logs()
                    ])
                ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})
            ], width=12),
        ], className="mt-3"),
        
        # Store for bot state
        dcc.Store(id="bot-state-store", data={}),
        
        # AlphaBot state store
        dcc.Store(id="alphabot-state-store", data={
            'status': 'stopped',
            'ticker': 'AAPL',
            'strategy': 'rsi',
            'last_signal': 'hold',
            'last_rsi': None,
            'trade_logs': []
        }),
        
        # Refresh interval
        dcc.Interval(
            id="bot-refresh-interval",
            interval=5000,  # 5 seconds
            n_intervals=0
        ),
        
        # AlphaBot refresh interval (matches tick interval)
        dcc.Interval(
            id="alphabot-refresh-interval",
            interval=60000,  # 60 seconds default
            n_intervals=0,
            disabled=True  # Enabled when bot starts
        ),
        
        # Configuration Modal
        create_bot_config_modal(),
        
        # Alert container
        html.Div(id="bot-alerts-container"),
    ], className="p-3")


def get_layout():
    """Return the Trading Bots subtab layout."""
    return create_bots_layout()
