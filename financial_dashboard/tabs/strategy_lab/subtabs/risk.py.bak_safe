"""
Strategy Lab - Risk & Factor Analysis Subtab

Deep-dive into risk metrics and factor attribution:
- Drawdown analysis
- Value at Risk (VaR)
- Factor exposures (Fama-French)
- Risk-adjusted metrics
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

def layout():
    """
    Risk & Factor Analysis subtab layout.
    
    Returns:
        dbc.Container: Risk metrics and factor analysis
    """
    return dbc.Container([
        # Description
        dcc.Markdown("""
**⚠️ Risk & Factor Analysis:**

Understand the risk profile of your strategy:
- **Max Drawdown**: Worst peak-to-trough decline (how much pain?)
- **VaR (Value at Risk)**: Expected loss in worst 5% of outcomes
- **Factor Exposures**: Which market factors drive returns (Market, Size, Value, Momentum)
- **Volatility**: How much your portfolio swings day-to-day

**📊 Factor Attribution (Fama-French):**
- **Market (Mkt-RF)**: Overall market exposure (beta)
- **SMB (Size)**: Small-cap vs large-cap tilt
- **HML (Value)**: Value vs growth orientation
- **MOM (Momentum)**: Chasing winners vs contrarian

**💡 Healthy Risk Profile:**
- Max drawdown < -25%
- Sharpe ratio > 1.5
- Positive alpha (factor-adjusted excess return)
- Diversified factor exposures (not over-concentrated)
        """, className="small mb-4", style={
            'backgroundColor': '#fff0f0',
            'padding': '15px',
            'borderRadius': '8px',
            'color': '#000000'
        }),
        
        # Risk Metrics Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📉 Max Drawdown", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-risk-max-dd', children="--", className="mb-0 text-danger"),
                        html.Small("Worst decline from peak", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📊 Volatility (Ann.)", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-risk-volatility', children="--", className="mb-0"),
                        html.Small("Annual price swings", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("⚠️ VaR (95%)", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-risk-var', children="--", className="mb-0 text-warning"),
                        html.Small("Expected worst-case loss", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📈 Sortino Ratio", className="text-muted mb-1", style={'color': '#000000'}),
                        html.H4(id='sl-risk-sortino', children="--", className="mb-0"),
                        html.Small("Downside risk-adjusted", style={'color': '#000000'})
                    ])
                ], className="text-center mb-3")
            ], md=3),
        ], className="mb-4"),
        
        # Drawdown Chart
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📉 Drawdown Over Time", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='sl-risk-drawdown-chart', config={'displayModeBar': False})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Factor Exposures
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("🔍 Factor Attribution (Fama-French)", className="mb-0")),
                    dbc.CardBody([
                        dcc.Markdown("""
**Understanding Factor Exposures:**
- **Positive values**: Your strategy tilts toward that factor
- **Negative values**: Your strategy avoids that factor
- **Near-zero**: Neutral exposure

**Interpretation:**
- Market > 1.0 = more volatile than market
- SMB > 0 = small-cap tilt, < 0 = large-cap tilt
- HML > 0 = value tilt, < 0 = growth tilt
- MOM > 0 = momentum chaser, < 0 = contrarian
                        """, className="small mb-3", style={'color': '#000000'}),
                        dcc.Graph(id='sl-risk-factor-chart', config={'displayModeBar': False})
                    ])
                ])
            ], md=12),
        ], className="mb-3"),
        
        # Risk Decomposition Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📊 Risk Decomposition", className="mb-0")),
                    dbc.CardBody([
                        html.Div(id='sl-risk-decomposition-table')
                    ])
                ])
            ], md=12),
        ]),
        
    ], fluid=True, className="p-3")


logger.info("✓ Strategy Lab Risk & Factor Analysis subtab loaded")
