"""
Hedge Finder for Sprint 6 - Portfolio Tab
Suggests negatively correlated assets and options strategies for hedging
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

def find_hedge_assets(portfolio_holdings, correlation_threshold=-0.3):
    """
    Find assets that are negatively correlated with portfolio
    
    Returns list of hedge candidates with:
    - ticker, correlation, description, hedge_ratio
    """
    # Placeholder - replace with actual correlation analysis
    hedge_candidates = [
        {
            'ticker': 'VXX',
            'name': 'iPath S&P 500 VIX ST Futures ETN',
            'correlation': -0.75,
            'hedge_ratio': 0.15,
            'type': 'ETF',
            'description': 'Spikes when market drops - classic hedge'
        },
        {
            'ticker': 'GLD',
            'name': 'SPDR Gold Trust',
            'correlation': -0.42,
            'hedge_ratio': 0.20,
            'type': 'ETF',
            'description': 'Gold as safe haven asset'
        },
        {
            'ticker': 'TLT',
            'name': 'iShares 20+ Year Treasury Bond ETF',
            'correlation': -0.38,
            'hedge_ratio': 0.25,
            'type': 'ETF',
            'description': 'Long-duration bonds inverse to stocks'
        },
        {
            'ticker': 'UUP',
            'name': 'Invesco DB US Dollar Index Bullish Fund',
            'correlation': -0.28,
            'hedge_ratio': 0.10,
            'type': 'ETF',
            'description': 'Dollar strength in market stress'
        }
    ]
    
    return [h for h in hedge_candidates if h['correlation'] <= correlation_threshold]

def find_options_hedges(portfolio_holdings):
    """
    Suggest options strategies for hedging
    
    Returns list of strategies with:
    - name, description, cost, protection_level
    """
    strategies = [
        {
            'name': 'Protective Put',
            'ticker': 'SPY',
            'description': 'Buy SPY puts 5% OTM, 90 days out',
            'cost': '$850',
            'protection': '95%',
            'max_loss_protected': '-5%',
            'complexity': 'Simple',
            'icon': 'fa-shield-alt',
            'color': 'success'
        },
        {
            'name': 'Collar',
            'ticker': 'Portfolio',
            'description': 'Buy puts, sell calls to finance protection',
            'cost': '$200',
            'protection': '90%',
            'max_loss_protected': '-10%',
            'complexity': 'Medium',
            'icon': 'fa-hands-helping',
            'color': 'info'
        },
        {
            'name': 'Put Spread',
            'ticker': 'SPY',
            'description': 'Buy SPY 440P / Sell SPY 420P (bull put spread)',
            'cost': '$450',
            'protection': '85%',
            'max_loss_protected': '-15%',
            'complexity': 'Medium',
            'icon': 'fa-compress',
            'color': 'warning'
        },
        {
            'name': 'VIX Call',
            'ticker': 'VIX',
            'description': 'Buy VIX calls for volatility spike',
            'cost': '$300',
            'protection': '70%',
            'max_loss_protected': 'Variable',
            'complexity': 'Advanced',
            'icon': 'fa-bolt',
            'color': 'danger'
        }
    ]
    
    return strategies

def create_correlation_chart(hedge_candidates):
    """Create correlation chart for hedge candidates"""
    tickers = [h['ticker'] for h in hedge_candidates]
    correlations = [h['correlation'] for h in hedge_candidates]
    colors = ['#10b981' if c < -0.5 else '#f59e0b' for c in correlations]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=tickers,
        y=correlations,
        marker_color=colors,
        text=[f"{c:.2f}" for c in correlations],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Correlation: %{y:.2f}<extra></extra>'
    ))
    
    fig.add_hline(y=-0.3, line_dash="dash", line_color="#94a3b8", 
                  annotation_text="Threshold")
    
    fig.update_layout(
        title="Hedge Candidates by Correlation",
        xaxis_title="Asset",
        yaxis_title="Correlation to Portfolio",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e6eef8',
        height=350,
        showlegend=False
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=True, 
                     zerolinecolor='rgba(255,255,255,0.3)')
    
    return fig

def create_hedge_finder_layout():
    """Create Hedge Finder layout"""
    hedge_assets = find_hedge_assets(None)
    options_hedges = find_options_hedges(None)
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-shield-alt me-2"),
                    "Hedge Finder"
                ], className="mb-3"),
                html.P(
                    "Discover assets and strategies that move inversely to your portfolio. "
                    "Protect against downside risk with smart hedging.",
                    className="text-muted"
                )
            ])
        ]),
        
        # Hedge Assets
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-line me-2"),
                        "Negatively Correlated Assets"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='hedge-correlation-chart',
                            figure=create_correlation_chart(hedge_assets),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=12)
        ], className="mb-3"),
        
        # Asset Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Hedge Asset Details"),
                    dbc.CardBody([
                        dbc.Table([
                            html.Thead(html.Tr([
                                html.Th("Ticker"),
                                html.Th("Name"),
                                html.Th("Correlation"),
                                html.Th("Suggested Allocation"),
                                html.Th("Description"),
                                html.Th("Action")
                            ])),
                            html.Tbody([
                                html.Tr([
                                    html.Td(html.Strong(h['ticker'])),
                                    html.Td(h['name']),
                                    html.Td(
                                        f"{h['correlation']:.2f}",
                                        style={'color': '#10b981' if h['correlation'] < -0.5 else '#f59e0b'}
                                    ),
                                    html.Td(f"{h['hedge_ratio']*100:.0f}%"),
                                    html.Td(h['description'], className="text-muted small"),
                                    html.Td(
                                        dbc.Button("Add", size="sm", color="success", outline=True)
                                    )
                                ])
                                for h in hedge_assets
                            ])
                        ], bordered=True, hover=True, responsive=True, className="mb-0")
                    ])
                ])
            ], md=12)
        ], className="mb-3"),
        
        # Options Hedging Strategies
        dbc.Row([
            dbc.Col([
                html.H5([
                    html.I(className="fas fa-chess me-2"),
                    "Options Hedging Strategies"
                ], className="mb-3")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className=f"fas {strat['icon']} me-2"),
                        strat['name']
                    ]),
                    dbc.CardBody([
                        html.P(strat['description'], className="text-muted mb-2"),
                        dbc.Row([
                            dbc.Col([
                                html.Small("Cost:", className="text-muted"),
                                html.Div(strat['cost'], className="fw-bold")
                            ], width=3),
                            dbc.Col([
                                html.Small("Protection:", className="text-muted"),
                                html.Div(strat['protection'], className="fw-bold text-success")
                            ], width=3),
                            dbc.Col([
                                html.Small("Max Loss:", className="text-muted"),
                                html.Div(strat['max_loss_protected'], className="fw-bold")
                            ], width=3),
                            dbc.Col([
                                html.Small("Complexity:", className="text-muted"),
                                html.Div(strat['complexity'], className="fw-bold")
                            ], width=3)
                        ]),
                        html.Hr(),
                        dbc.Button(
                            [html.I(className="fas fa-plus me-2"), "Deploy Strategy"],
                            color=strat['color'],
                            size="sm",
                            outline=True,
                            className="mt-2"
                        )
                    ])
                ], className="mb-3")
            ], md=6)
            for strat in options_hedges
        ]),
        
        # Hedge Effectiveness Note
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Strong("Hedging 101: "),
                    "Perfect hedges are rare. Most hedges cost money (insurance premium) and "
                    "reduce upside potential. The goal is to protect against catastrophic losses, "
                    "not eliminate all risk. Consider your risk tolerance and time horizon."
                ], color="info", className="mt-3")
            ])
        ])
    ], fluid=True)

def register_hedge_finder_callbacks(app):
    """Register Hedge Finder callbacks"""
    from dash import Output, Input, State
    
    @app.callback(
        Output('hedge-correlation-chart', 'figure'),
        [Input('hedge-refresh-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def refresh_hedge_candidates(n_clicks):
        """Refresh hedge candidates"""
        hedge_assets = find_hedge_assets(None)
        return create_correlation_chart(hedge_assets)
