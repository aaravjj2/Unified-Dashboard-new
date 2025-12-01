"""
Portfolio Health Dashboard for Sprint 6
Comprehensive portfolio health metrics, risk analysis, and health score
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc
import dash_bootstrap_components as dbc

def calculate_portfolio_health(holdings_df, returns_df):
    """
    Calculate comprehensive portfolio health metrics
    
    Returns dict with:
    - health_score: 0-100 overall health score
    - risk_metrics: dict of risk measures
    - diversification_metrics: correlation, concentration
    - sector_exposure: sector breakdown
    """
    # Placeholder implementation - replace with actual calculations
    
    health_metrics = {
        'health_score': 78,  # 0-100 score
        'risk_metrics': {
            'sharpe_ratio': 1.45,
            'max_drawdown': -0.18,  # -18%
            'volatility': 0.15,      # 15% annual
            'var_95': -0.025,        # -2.5% daily VaR
            'beta': 1.12
        },
        'diversification': {
            'correlation_avg': 0.45,
            'herfindahl_index': 0.12,  # Concentration measure
            'effective_n': 15.3        # Effective number of positions
        },
        'sector_exposure': {
            'Technology': 0.35,
            'Healthcare': 0.20,
            'Finance': 0.15,
            'Consumer': 0.15,
            'Energy': 0.08,
            'Other': 0.07
        }
    }
    
    return health_metrics

def create_health_score_gauge(health_score):
    """Create health score gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=health_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Portfolio Health Score", 'font': {'size': 20, 'color': '#e6eef8'}},
        delta={'reference': 70, 'increasing': {'color': "#10b981"}, 'decreasing': {'color': "#ef4444"}},
        gauge={
            'axis': {'range': [None, 100], 'tickcolor': '#e6eef8'},
            'bar': {'color': "#60a5fa"},
            'bgcolor': "rgba(255,255,255,0.1)",
            'borderwidth': 2,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(239, 68, 68, 0.3)'},    # Poor
                {'range': [40, 70], 'color': 'rgba(245, 158, 11, 0.3)'},  # Fair
                {'range': [70, 85], 'color': 'rgba(16, 185, 129, 0.3)'},  # Good
                {'range': [85, 100], 'color': 'rgba(34, 197, 94, 0.3)'},  # Excellent
            ],
            'threshold': {
                'line': {'color': "#10b981", 'width': 4},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#e6eef8', 'family': 'Arial'},
        height=300,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_risk_metrics_cards(risk_metrics):
    """Create risk metric cards"""
    metrics = [
        {
            'name': 'Sharpe Ratio',
            'value': f"{risk_metrics['sharpe_ratio']:.2f}",
            'icon': 'fa-chart-line',
            'color': 'success' if risk_metrics['sharpe_ratio'] > 1.0 else 'warning'
        },
        {
            'name': 'Max Drawdown',
            'value': f"{risk_metrics['max_drawdown'] * 100:.1f}%",
            'icon': 'fa-arrow-down',
            'color': 'danger' if abs(risk_metrics['max_drawdown']) > 0.20 else 'warning'
        },
        {
            'name': 'Volatility',
            'value': f"{risk_metrics['volatility'] * 100:.1f}%",
            'icon': 'fa-wave-square',
            'color': 'info'
        },
        {
            'name': 'Beta',
            'value': f"{risk_metrics['beta']:.2f}",
            'icon': 'fa-exchange-alt',
            'color': 'primary'
        }
    ]
    
    cards = []
    for metric in metrics:
        cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className=f"fas {metric['icon']} fa-2x text-{metric['color']} mb-2"),
                            html.H5(metric['value'], className="mb-0"),
                            html.P(metric['name'], className="text-muted small mb-0")
                        ], className="text-center")
                    ])
                ], className="h-100")
            ], md=3, sm=6, className="mb-3")
        )
    
    return cards

def create_sector_exposure_chart(sector_exposure):
    """Create sector exposure pie chart"""
    labels = list(sector_exposure.keys())
    values = [sector_exposure[s] * 100 for s in labels]
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6b7280']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textinfo='label+percent',
        textfont_size=12,
        hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>'
    )])
    
    fig.update_layout(
        title="Sector Exposure",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e6eef8',
        height=350,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_correlation_heatmap(correlation_matrix=None):
    """Create correlation heatmap for top holdings"""
    # Placeholder data - replace with actual correlation matrix
    if correlation_matrix is None:
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        correlation_matrix = pd.DataFrame(
            np.random.uniform(0.3, 0.9, (5, 5)),
            index=tickers,
            columns=tickers
        )
        np.fill_diagonal(correlation_matrix.values, 1.0)
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdYlGn_r',
        zmid=0.5,
        text=correlation_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation")
    ))
    
    fig.update_layout(
        title="Top Holdings Correlation Matrix",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e6eef8',
        height=400,
        margin=dict(l=60, r=20, t=60, b=60)
    )
    
    return fig

def create_portfolio_health_layout():
    """Create Portfolio Health Dashboard layout"""
    # Get health metrics
    health_metrics = calculate_portfolio_health(None, None)
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-heartbeat me-2"),
                    "Portfolio Health Dashboard"
                ], className="mb-3"),
                html.P(
                    "Comprehensive portfolio health analysis including risk metrics, "
                    "diversification, and sector exposure.",
                    className="text-muted"
                )
            ])
        ]),
        
        # Health Score Gauge
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(
                            id='health-score-gauge',
                            figure=create_health_score_gauge(health_metrics['health_score']),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=4),
            
            # Risk Metrics Summary
            dbc.Col([
                html.H6("Risk Metrics", className="mb-3"),
                dbc.Row(create_risk_metrics_cards(health_metrics['risk_metrics']))
            ], md=8)
        ], className="mb-4"),
        
        # Sector Exposure and Correlation
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Sector Allocation"),
                    dbc.CardBody([
                        dcc.Graph(
                            id='sector-exposure-chart',
                            figure=create_sector_exposure_chart(health_metrics['sector_exposure']),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=6),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Correlation Analysis"),
                    dbc.CardBody([
                        dcc.Graph(
                            id='correlation-heatmap',
                            figure=create_correlation_heatmap(),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=6)
        ]),
        
        # Health Recommendations
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.H6([html.I(className="fas fa-lightbulb me-2"), "Health Recommendations"]),
                    html.Ul([
                        html.Li("✅ Good diversification with low correlation"),
                        html.Li("⚠️ Technology sector concentration at 35% - consider rebalancing"),
                        html.Li("✅ Sharpe ratio above 1.0 indicates good risk-adjusted returns"),
                        html.Li("⚠️ Consider adding defensive positions to reduce max drawdown")
                    ], className="mb-0")
                ], color="info", className="mt-3")
            ])
        ])
    ], fluid=True)

def register_health_callbacks(app):
    """Register Portfolio Health callbacks"""
    from dash import Output, Input
    
    @app.callback(
        [Output('health-score-gauge', 'figure'),
         Output('sector-exposure-chart', 'figure'),
         Output('correlation-heatmap', 'figure')],
        [Input('health-refresh-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def refresh_health_metrics(n_clicks):
        """Refresh all health metrics"""
        health_metrics = calculate_portfolio_health(None, None)
        return (
            create_health_score_gauge(health_metrics['health_score']),
            create_sector_exposure_chart(health_metrics['sector_exposure']),
            create_correlation_heatmap()
        )
