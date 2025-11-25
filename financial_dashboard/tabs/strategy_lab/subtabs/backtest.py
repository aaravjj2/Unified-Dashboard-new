"""
Strategy Lab - Backtest Configuration Subtab

Defines backtest parameters:
- Date range
- Initial capital
- Transaction costs
- Slippage assumptions
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def layout():
    """
    Backtest Configuration subtab layout.
    
    Returns:
        dbc.Container: Backtest parameter configuration
    """
    return dbc.Container([
        # Description
        dcc.Markdown("""
**⚙️ Backtest Configuration:**

Set the parameters for your historical simulation:
- **Date Range**: How far back to test (1 year, 5 years, etc.)
- **Initial Capital**: Starting portfolio value ($10k, $100k, $1M)
- **Transaction Costs**: Commissions + fees (typically $0-$5 per trade)
- **Slippage**: Price impact (usually 0.1-0.5% for liquid stocks)

**💡 Realistic Settings:**
- Use at least 1 year of data (preferably 3-5 years)
- Set initial capital to match your actual account size
- Use $0 commissions for modern brokers (Robinhood, Webull)
- Set slippage to 0.1% for liquid large-caps, 0.5% for small-caps
        """, className="small mb-3", style={
            'backgroundColor': '#fff5f0',
            'padding': '15px',
            'borderRadius': '8px',
            'color': '#000000'
        }),
        
        # Date Range
        dbc.Row([
            dbc.Col([
                html.Label("Backtest Start Date", className="fw-bold"),
                dcc.DatePickerSingle(
                    id='sl-start-date',
                    date=datetime.now() - timedelta(days=365),
                    display_format='YYYY-MM-DD',
                    className="mb-2"
                ),
                html.Small("Backtest start date", className="text-muted", style={'color': '#000000'})
            ], md=6),
            dbc.Col([
                html.Label("Backtest End Date", className="fw-bold"),
                dcc.DatePickerSingle(
                    id='sl-end-date',
                    date=datetime.now(),
                    display_format='YYYY-MM-DD',
                    className="mb-2"
                ),
                html.Small("Backtest end date", className="text-muted", style={'color': '#000000'})
            ], md=6),
        ], className="mb-3"),
        
        # Capital & Costs
        dbc.Row([
            dbc.Col([
                html.Label("Initial Capital ($)", className="fw-bold"),
                dcc.Input(
                    id='sl-initial-capital',
                    type='number',
                    value=100000,
                    min=1000,
                    step=1000,
                    style={'width': '100%'},
                    className="mb-2"
                ),
                html.Small("Starting portfolio value", className="text-muted", style={'color': '#000000'})
            ], md=6),
            dbc.Col([
                html.Label("Commission per Trade ($)", className="fw-bold"),
                dcc.Input(
                    id='sl-transaction-cost',
                    type='number',
                    value=0,
                    min=0,
                    step=0.1,
                    style={'width': '100%'},
                    className="mb-2"
                ),
                html.Small("Set to $0 for modern brokers", className="text-muted", style={'color': '#000000'})
            ], md=6),
        ], className="mb-3"),
        
        # Slippage & Frequency
        dbc.Row([
            dbc.Col([
                html.Label("Slippage (%)", className="fw-bold"),
                dcc.Slider(
                    id='sl-slippage',
                    min=0,
                    max=1,
                    step=0.05,
                    value=0.1,
                    marks={0: '0%', 0.5: '0.5%', 1: '1%'},
                    className="mb-2"
                ),
                html.Small("Price impact when trading", className="text-muted", style={'color': '#000000'})
            ], md=6),
            dbc.Col([
                html.Label("Rebalance Frequency", className="fw-bold"),
                dcc.Dropdown(
                    id='sl-rebalance-freq',
                    options=[
                        {'label': 'Daily', 'value': 'daily'},
                        {'label': 'Weekly', 'value': 'weekly'},
                        {'label': 'Monthly', 'value': 'monthly'},
                    ],
                    value='daily',
                    clearable=False,
                    className="mb-2"
                ),
                html.Small("How often to check signals", className="text-muted", style={'color': '#000000'})
            ], md=6),
        ], className="mb-3"),
        
        # Position Sizing
        dbc.Row([
            dbc.Col([
                html.Label("Position Size (%)", className="fw-bold"),
                dcc.Input(
                    id='sl-position-size',
                    type='number',
                    value=10,
                    min=1,
                    max=100,
                    step=1,
                    style={'width': '100%'},
                    className="mb-2"
                ),
                html.Small("Percentage of portfolio per position", className="text-muted", style={'color': '#000000'})
            ], md=6),
            dbc.Col([
                html.Label("Max Positions", className="fw-bold"),
                dcc.Input(
                    id='sl-max-positions',
                    type='number',
                    value=5,
                    min=1,
                    max=20,
                    step=1,
                    style={'width': '100%'},
                    className="mb-2"
                ),
                html.Small("Maximum concurrent positions", className="text-muted", style={'color': '#000000'})
            ], md=6),
        ], className="mb-3"),
        
        # Reset Button
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "🔄 Reset to Defaults",
                    id='sl-reset-btn',
                    color='secondary',
                    outline=True,
                    className="w-100",
                    n_clicks=0
                ),
            ], md=12),
        ], className="mb-3"),
        
    ], fluid=True, className="p-3")


logger.info("✓ Strategy Lab Backtest Config subtab loaded")
