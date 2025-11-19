"""
Volatility Lab for Sprint 6 - Market Forecast Tab
Advanced volatility analysis including VIX, implied volatility term structure,
volatility forecasting, and regime detection
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

def fetch_vix_data():
    """Fetch VIX (volatility index) data"""
    # Placeholder - replace with actual API call
    dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
    vix_data = pd.DataFrame({
        'date': dates,
        'vix': np.random.uniform(12, 25, len(dates))  # Placeholder VIX values
    })
    return vix_data

def calculate_implied_vol_term_structure(ticker='SPY'):
    """Calculate implied volatility term structure (vol smile)"""
    # Placeholder - replace with actual options data
    expirations = [7, 14, 30, 60, 90, 180, 365]  # Days to expiration
    ivs = [0.18, 0.19, 0.20, 0.21, 0.22, 0.23, 0.24]  # Implied volatilities
    
    return pd.DataFrame({
        'days_to_expiration': expirations,
        'implied_vol': ivs
    })

def detect_volatility_regime(vix_series):
    """
    Detect current volatility regime
    Returns: 'low', 'normal', 'high', 'crisis'
    """
    current_vix = vix_series.iloc[-1]
    
    if current_vix < 15:
        return 'low', '#10b981'
    elif current_vix < 20:
        return 'normal', '#3b82f6'
    elif current_vix < 30:
        return 'high', '#f59e0b'
    else:
        return 'crisis', '#ef4444'

def forecast_volatility(historical_vix, horizon_days=30):
    """Forecast future volatility using simple GARCH-like model"""
    # Placeholder - replace with actual GARCH or ML model
    current = historical_vix.iloc[-1]
    mean_reversion_level = 18.0  # Long-term VIX average
    
    forecast_dates = pd.date_range(
        start=datetime.now() + timedelta(days=1),
        periods=horizon_days,
        freq='D'
    )
    
    # Simple mean-reverting forecast
    forecast = []
    val = current
    for _ in range(horizon_days):
        val = val * 0.95 + mean_reversion_level * 0.05 + np.random.normal(0, 0.5)
        forecast.append(max(10, min(40, val)))
    
    return pd.DataFrame({
        'date': forecast_dates,
        'forecast_vix': forecast
    })

def create_vix_chart():
    """Create VIX historical chart with regime zones"""
    vix_data = fetch_vix_data()
    forecast_data = forecast_volatility(vix_data['vix'], horizon_days=30)
    
    fig = go.Figure()
    
    # Historical VIX
    fig.add_trace(go.Scatter(
        x=vix_data['date'],
        y=vix_data['vix'],
        mode='lines',
        name='Historical VIX',
        line=dict(color='#60a5fa', width=2),
        fill='tozeroy',
        fillcolor='rgba(96, 165, 250, 0.1)'
    ))
    
    # Forecast VIX
    fig.add_trace(go.Scatter(
        x=forecast_data['date'],
        y=forecast_data['forecast_vix'],
        mode='lines',
        name='Forecast',
        line=dict(color='#f59e0b', width=2, dash='dash')
    ))
    
    # Regime zones
    fig.add_hrect(y0=0, y1=15, fillcolor='rgba(16, 185, 129, 0.1)', 
                  annotation_text="Low Vol", annotation_position="right")
    fig.add_hrect(y0=15, y1=20, fillcolor='rgba(59, 130, 246, 0.1)', 
                  annotation_text="Normal", annotation_position="right")
    fig.add_hrect(y0=20, y1=30, fillcolor='rgba(245, 158, 11, 0.1)', 
                  annotation_text="High Vol", annotation_position="right")
    fig.add_hrect(y0=30, y1=50, fillcolor='rgba(239, 68, 68, 0.1)', 
                  annotation_text="Crisis", annotation_position="right")
    
    fig.update_layout(
        title="VIX Index with Volatility Regime Zones",
        xaxis_title="Date",
        yaxis_title="VIX Level",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e6eef8',
        hovermode='x unified',
        height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    
    return fig

def create_vol_term_structure_chart():
    """Create implied volatility term structure chart"""
    vol_data = calculate_implied_vol_term_structure()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=vol_data['days_to_expiration'],
        y=vol_data['implied_vol'] * 100,
        mode='lines+markers',
        name='Implied Volatility',
        line=dict(color='#8b5cf6', width=3),
        marker=dict(size=10, color='#8b5cf6')
    ))
    
    fig.update_layout(
        title="Implied Volatility Term Structure (SPY Options)",
        xaxis_title="Days to Expiration",
        yaxis_title="Implied Volatility (%)",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e6eef8',
        height=350,
        showlegend=False
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    
    return fig

def create_volatility_lab_layout():
    """Create Volatility Lab tab layout"""
    vix_data = fetch_vix_data()
    regime, regime_color = detect_volatility_regime(vix_data['vix'])
    current_vix = vix_data['vix'].iloc[-1]
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-flask me-2"),
                    "Volatility Lab"
                ], className="mb-3"),
                html.P(
                    "Advanced volatility analysis and forecasting. Monitor market fear, "
                    "detect volatility regimes, and forecast future turbulence.",
                    className="text-muted"
                )
            ])
        ]),
        
        # Current Status Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-tachometer-alt fa-2x text-primary mb-2"),
                            html.H3(f"{current_vix:.1f}", className="mb-0"),
                            html.P("Current VIX", className="text-muted small mb-0")
                        ], className="text-center")
                    ])
                ])
            ], md=3),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-thermometer-half fa-2x mb-2", 
                                  style={'color': regime_color}),
                            html.H3(regime.capitalize(), className="mb-0"),
                            html.P("Volatility Regime", className="text-muted small mb-0")
                        ], className="text-center")
                    ])
                ])
            ], md=3),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-chart-line fa-2x text-success mb-2"),
                            html.H3("↓ 2.3", className="mb-0 text-success"),
                            html.P("30-Day Forecast", className="text-muted small mb-0")
                        ], className="text-center")
                    ])
                ])
            ], md=3),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-wave-square fa-2x text-warning mb-2"),
                            html.H3("22.5%", className="mb-0"),
                            html.P("Implied Vol (SPY)", className="text-muted small mb-0")
                        ], className="text-center")
                    ])
                ])
            ], md=3)
        ], className="mb-4"),
        
        # VIX Chart
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-area me-2"),
                        "VIX Index & Forecast"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='vix-chart',
                            figure=create_vix_chart(),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=12)
        ], className="mb-3"),
        
        # Volatility Term Structure
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-line me-2"),
                        "Implied Volatility Term Structure"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='vol-term-structure',
                            figure=create_vol_term_structure_chart(),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=12)
        ]),
        
        # Insights and Recommendations
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.H6([html.I(className="fas fa-brain me-2"), "Volatility Insights"]),
                    html.Ul([
                        html.Li(f"Current regime: {regime.upper()} - VIX at {current_vix:.1f}"),
                        html.Li("Term structure shows normal contango (upward sloping)"),
                        html.Li("30-day forecast suggests mean reversion toward 18.0"),
                        html.Li("Consider: Selling volatility through credit spreads or iron condors")
                    ], className="mb-0")
                ], color="info", className="mt-3")
            ])
        ])
    ], fluid=True)

def register_volatility_lab_callbacks(app):
    """Register Volatility Lab callbacks"""
    from dash import Output, Input
    
    @app.callback(
        [Output('vix-chart', 'figure'),
         Output('vol-term-structure', 'figure')],
        [Input('vol-lab-refresh-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def refresh_volatility_data(n_clicks):
        """Refresh volatility charts"""
        return create_vix_chart(), create_vol_term_structure_chart()
