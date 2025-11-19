"""
Factor DNA Component for Sprint 6 - Analysis Hub
Provides factor-level attribution analysis (Value, Growth, Momentum, Quality, Size)
"""
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

# Factor definitions
FACTORS = {
    'value': {
        'name': 'Value',
        'description': 'Returns from value stocks (low P/E, P/B ratios)',
        'color': '#10b981',
        'icon': 'fa-dollar-sign'
    },
    'growth': {
        'name': 'Growth',
        'description': 'Returns from high-growth stocks',
        'color': '#3b82f6',
        'icon': 'fa-chart-line'
    },
    'momentum': {
        'name': 'Momentum',
        'description': 'Returns from recent winners',
        'color': '#8b5cf6',
        'icon': 'fa-rocket'
    },
    'quality': {
        'name': 'Quality',
        'description': 'Returns from high-quality firms (ROE, low debt)',
        'color': '#f59e0b',
        'icon': 'fa-star'
    },
    'size': {
        'name': 'Size',
        'description': 'Returns from small-cap vs large-cap stocks',
        'color': '#ef4444',
        'icon': 'fa-balance-scale'
    }
}

def calculate_factor_attribution(returns_df, holdings_df=None):
    """
    Calculate factor attribution for a portfolio
    
    Parameters:
    - returns_df: DataFrame with columns [date, ticker, return, market_cap, ...]
    - holdings_df: DataFrame with current holdings [ticker, weight, ...]
    
    Returns:
    - factor_returns: Dict with factor contributions
    """
    # Placeholder implementation - replace with actual factor model
    # In production, this would use Fama-French factors or a proprietary model
    
    factor_returns = {
        'value': 0.015,      # 1.5% contribution from value
        'growth': 0.032,     # 3.2% from growth
        'momentum': 0.012,   # 1.2% from momentum
        'quality': 0.018,    # 1.8% from quality
        'size': -0.005,      # -0.5% from size (large-cap bias)
    }
    
    return factor_returns

def create_factor_dna_chart(factor_returns):
    """Create Factor DNA breakdown bar chart"""
    factors = list(factor_returns.keys())
    values = [factor_returns[f] * 100 for f in factors]  # Convert to percentages
    colors = [FACTORS[f]['color'] for f in factors]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=factors,
        y=values,
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in values],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Contribution: %{y:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title="Factor Attribution Breakdown",
        xaxis_title="Factor",
        yaxis_title="Contribution to Returns (%)",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e6eef8',
        showlegend=False,
        height=400,
        margin=dict(t=60, b=40, l=40, r=40)
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=True, zerolinecolor='rgba(255,255,255,0.3)')
    
    return fig

def create_factor_dna_table(factor_returns):
    """Create detailed factor breakdown table"""
    rows = []
    
    for factor_key, contribution in factor_returns.items():
        factor_info = FACTORS[factor_key]
        rows.append(html.Tr([
            html.Td([
                html.I(className=f"fas {factor_info['icon']} me-2", 
                      style={'color': factor_info['color']}),
                html.Span(factor_info['name'], className="fw-bold")
            ]),
            html.Td(factor_info['description'], className="text-muted"),
            html.Td(
                f"{contribution * 100:+.2f}%",
                className="fw-bold text-end",
                style={'color': '#10b981' if contribution > 0 else '#ef4444'}
            )
        ]))
    
    # Total row
    total = sum(factor_returns.values())
    rows.append(html.Tr([
        html.Td("Total Factor Contribution", className="fw-bold", colSpan=2),
        html.Td(
            f"{total * 100:+.2f}%",
            className="fw-bold text-end",
            style={'color': '#10b981' if total > 0 else '#ef4444'}
        )
    ], className="table-active"))
    
    return dbc.Table([
        html.Thead(html.Tr([
            html.Th("Factor"),
            html.Th("Description"),
            html.Th("Contribution", className="text-end")
        ])),
        html.Tbody(rows)
    ], bordered=True, hover=True, responsive=True, className="mt-3")

def create_factor_dna_layout():
    """Create the Factor DNA tab layout"""
    # Example data - in production this would come from callbacks
    factor_returns = calculate_factor_attribution(None, None)
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-dna me-2"),
                    "Factor DNA Analysis"
                ], className="mb-3"),
                html.P(
                    "Understand which investment factors drive your portfolio's returns. "
                    "Factor analysis decomposes performance into systematic risk factors.",
                    className="text-muted"
                )
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-bar me-2"),
                        "Factor Contribution Chart"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='factor-dna-chart',
                            figure=create_factor_dna_chart(factor_returns),
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-3")
            ], md=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-table me-2"),
                        "Detailed Factor Breakdown"
                    ]),
                    dbc.CardBody([
                        create_factor_dna_table(factor_returns)
                    ])
                ])
            ], md=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Strong("What are investment factors? "),
                    "Factors are characteristics that explain differences in stock returns. "
                    "The most common factors are Value (cheap stocks), Growth (high earnings growth), "
                    "Momentum (recent winners), Quality (profitable, stable firms), and Size (market cap)."
                ], color="info", className="mt-3")
            ])
        ])
    ], fluid=True)

def register_factor_dna_callbacks(app):
    """Register Factor DNA callbacks"""
    from dash import Output, Input, State
    
    @app.callback(
        Output('factor-dna-chart', 'figure'),
        [Input('factor-refresh-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def refresh_factor_analysis(n_clicks):
        """Refresh factor analysis with latest data"""
        factor_returns = calculate_factor_attribution(None, None)
        return create_factor_dna_chart(factor_returns)
