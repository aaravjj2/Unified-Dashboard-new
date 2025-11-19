"""
Strategy Lab - Results Subtab

Performance results visualization:
- Equity curve
- Key metrics (CAGR, Sharpe, Max Drawdown)
- Trade statistics
- Monthly/yearly returns
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

def layout():
    """
    Results subtab layout.
    
    Returns:
        dbc.Container: Performance results display
    """
    return dbc.Container([
        # Description
        dcc.Markdown("""
**📊 Backtest Results:**

View comprehensive performance metrics for your strategy:
- **Equity Curve**: Portfolio value over time (your $100k → $XXXk journey)
- **CAGR**: Compound Annual Growth Rate (average yearly return)
- **Sharpe Ratio**: Risk-adjusted returns (>1.5 is excellent)
- **Max Drawdown**: Worst peak-to-trough decline (pain tolerance test)
- **Win Rate**: Percentage of profitable trades

**📈 How to Interpret:**
- Green equity curve = profitable strategy
- Sharpe > 1.5 = good risk-adjusted returns
- Max Drawdown < -20% = potentially risky
- Win rate > 55% = strong predictive signal
        """, className="small mb-4", style={
            'backgroundColor': '#fff5f5',
            'padding': '15px',
            'borderRadius': '8px',
            'color': '#000000'
        }),
        
        # Key Metrics Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📈 CAGR", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H3(id='sl-metric-cagr', children="--", className="mb-0"),
                        html.Small("Annualized Return", className="text-muted", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("⚡ Sharpe Ratio", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H3(id='sl-metric-sharpe', children="--", className="mb-0"),
                        html.Small("Risk-Adjusted Return", className="text-muted", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📉 Max Drawdown", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H3(id='sl-metric-maxdd', children="--", className="mb-0", style={'color': '#dc3545'}),
                        html.Small("Worst Decline", className="text-muted", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("🎯 Win Rate", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H3(id='sl-metric-winrate', children="--", className="mb-0"),
                        html.Small("Profitable Trades", className="text-muted", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
        ], className="mb-4"),
        
        # Equity Curve
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📈 Equity Curve", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-equity-curve', config={'displayModeBar': False})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Monthly Returns Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📅 Monthly Returns (%)", className="mb-0")),
                    dbc.CardBody([
                        html.Div(id='sl-monthly-returns-table')
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Trade Statistics
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📋 Trade Statistics", className="mb-0")),
                    dbc.CardBody([
                        html.Div(id='sl-trade-stats')
                    ])
                ])
            ], md=12),
        ]),
        
    ], fluid=True, className="p-3")


logger.info("✓ Strategy Lab Results subtab loaded")
