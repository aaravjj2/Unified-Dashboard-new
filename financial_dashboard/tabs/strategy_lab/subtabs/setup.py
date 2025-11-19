"""
Strategy Lab - Setup Subtab

Defines strategy configuration interface:
- Strategy type selection (Momentum, Mean Reversion, Pairs, etc.)
- Universe selection (tickers, sectors, indices)
- Entry/exit rules
- Position sizing
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

def layout():
    """
    Strategy Setup subtab layout.
    
    Returns:
        dbc.Container: Setup configuration interface
    """
    return dbc.Container([
        # Beginner-Friendly Description
        dcc.Markdown("""
**📋 Strategy Setup:**

Define your quantitative trading strategy parameters. This is where you choose:
- **Strategy Type**: Momentum, mean reversion, pairs trading, or custom rules
- **Universe**: Which stocks/ETFs to trade (tickers or sectors)
- **Entry Rules**: When to buy (e.g., "SMA 20 > SMA 50")
- **Exit Rules**: When to sell (e.g., "Stop Loss -5%" or "Take Profit +10%")
- **Position Sizing**: How much capital per trade

**💡 Beginner Tip:**
Start with a simple momentum strategy using 3-5 liquid tickers (AAPL, SPY, QQQ).
Keep rules simple initially - you can add complexity later!
        """, className="small mb-3", style={
            'backgroundColor': '#f0f8ff',
            'padding': '15px',
            'borderRadius': '8px',
            'color': '#000000'
        }),
        
        # Strategy Type Selection
        dbc.Row([
            dbc.Col([
                html.Label("Strategy Type", className="fw-bold"),
                html.Div([
                    dcc.Dropdown(
                        id='sl-strategy-type',
                        options=[
                            {'label': '📈 Momentum (SMA Crossover)', 'value': 'momentum'},
                            {'label': '📉 Mean Reversion (RSI)', 'value': 'mean_reversion'},
                            {'label': '🔀 Pairs Trading (Z-Score)', 'value': 'pairs'},
                            {'label': '📊 Bollinger Bands', 'value': 'bollinger_bands'},
                            {'label': '📉 MACD Crossover', 'value': 'macd'},
                        ],
                        value='momentum',
                        clearable=False,
                        className="mb-2"
                    ),
                    html.Small("Choose your trading signal type", className="text-muted", style={'color': '#000000'})
                ])
            ], md=6),
            dbc.Col([
                html.Label("Universe Selection", className="fw-bold"),
                html.Div([
                    dcc.Dropdown(
                        id='sl-universe-type',
                        options=[
                            {'label': 'Specific Tickers', 'value': 'tickers'},
                            {'label': 'S&P 500', 'value': 'sp500'},
                            {'label': 'Technology Sector', 'value': 'tech'},
                            {'label': 'Weekly Picks', 'value': 'weekly_picks'},
                        ],
                        value='tickers',
                        clearable=False,
                        className="mb-2"
                    ),
                    html.Small("Select which stocks to trade", className="text-muted", style={'color': '#000000'})
                ])
            ], md=6),
        ], className="mb-3"),
        
        # Ticker Input (conditional on universe type)
        dbc.Row([
            dbc.Col([
                html.Label("Tickers (comma-separated)", className="fw-bold"),
                dcc.Input(
                    id='sl-tickers-input',
                    type='text',
                    placeholder='AAPL, MSFT, SPY, QQQ',
                    value='AAPL,SPY,QQQ',
                    style={'width': '100%'},
                    className="mb-2"
                ),
                html.Small("Enter ticker symbols separated by commas", className="text-muted", style={'color': '#000000'})
            ], md=12),
        ], className="mb-3"),
        
        # Entry/Exit Rules
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📈 Entry Rules", className="mb-0")),
                    dbc.CardBody([
                        html.Label("Entry Condition", className="fw-bold small"),
                        dcc.Dropdown(
                            id='sl-entry-condition',
                            options=[
                                {'label': 'SMA 20 > SMA 50 (Golden Cross)', 'value': 'sma_cross_up'},
                                {'label': 'RSI < 30 (Oversold)', 'value': 'rsi_oversold'},
                                {'label': 'Price > Upper Bollinger Band', 'value': 'bb_breakout'},
                                {'label': 'MACD Signal Crossover', 'value': 'macd_cross'},
                                {'label': 'Custom (Advanced)', 'value': 'custom'},
                            ],
                            value='sma_cross_up',
                            clearable=False,
                            className="mb-2"
                        ),
                        html.Small("When to enter a trade", className="text-muted", style={'color': '#000000'})
                    ])
                ], className="mb-3")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📉 Exit Rules", className="mb-0")),
                    dbc.CardBody([
                        html.Label("Exit Condition", className="fw-bold small"),
                        dcc.Dropdown(
                            id='sl-exit-condition',
                            options=[
                                {'label': 'SMA 20 < SMA 50 (Death Cross)', 'value': 'sma_cross_down'},
                                {'label': 'Stop Loss -5%', 'value': 'stop_loss_5'},
                                {'label': 'Take Profit +10%', 'value': 'take_profit_10'},
                                {'label': 'RSI > 70 (Overbought)', 'value': 'rsi_overbought'},
                                {'label': 'Custom (Advanced)', 'value': 'custom'},
                            ],
                            value='sma_cross_down',
                            clearable=False,
                            className="mb-2"
                        ),
                        html.Small("When to exit a trade", className="text-muted", style={'color': '#000000'})
                    ])
                ], className="mb-3")
            ], md=6),
        ], className="mb-3"),
        
        # Position Sizing
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("💰 Position Sizing", className="mb-0")),
                    dbc.CardBody([
                        html.Label("Position Size Method", className="fw-bold small"),
                        dcc.Dropdown(
                            id='sl-position-sizing',
                            options=[
                                {'label': 'Equal Weight (Divide capital equally)', 'value': 'equal_weight'},
                                {'label': 'Risk Parity (Adjust by volatility)', 'value': 'risk_parity'},
                                {'label': 'Fixed Dollar ($10k per position)', 'value': 'fixed_dollar'},
                                {'label': 'Percentage of Portfolio (10% each)', 'value': 'percentage'},
                            ],
                            value='equal_weight',
                            clearable=False,
                            className="mb-2"
                        ),
                        html.Small("How much to invest per trade", className="text-muted", style={'color': '#000000'})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Validation Button
        dbc.Row([
            dbc.Col([
                dbc.Button("Validate Strategy", id='sl-validate-btn', color="primary", className="w-100 mb-2"),
                html.Div(id='sl-validation-result', className="mt-2")
            ], md=12),
        ]),
        
    ], fluid=True, className="p-3")


logger.info("✓ Strategy Lab Setup subtab loaded")
