"""
Market Forecast Tab - Agent-1B Rebuild
Inline content with deterministic fixtures to avoid DashProxy callback issues
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json
import os
from pathlib import Path
import pandas as pd

# Load default AAPL fixture for display
def load_default_forecast():
    """Load AAPL fixture for default display"""
    fixture_path = Path(__file__).parents[2] / 'tests' / 'fixtures' / 'forecast' / 'forecast_fixture.json'
    
    if fixture_path.exists():
        with open(fixture_path) as f:
            data = json.load(f)
            # Fixture has 'forecast' not 'forecast_series' - normalize
            if 'forecast' in data:
                data['forecast_series'] = data['forecast']
            # Add metrics if missing
            data.setdefault('expected_return', 0.053)
            data.setdefault('volatility', 0.218)
            data.setdefault('sharpe_ratio', 0.72)
            data.setdefault('max_drawdown', -0.087)
            return data
    
    # Fallback if fixture not found
    return {
        'ticker': 'AAPL',
        'horizon': 30,
        'forecast_series': [
            {'date': '2025-11-20', 'price': 180.5, 'lower': 175.2, 'upper': 185.8},
            {'date': '2025-11-21', 'price': 181.2, 'lower': 175.5, 'upper': 186.9},
        ],
        'expected_return': 0.053,
        'volatility': 0.218,
        'sharpe_ratio': 0.72,
        'max_drawdown': -0.087,
        'confidence': 0.95
    }

def load_default_explanation():
    """Load AAPL explanation fixture"""
    fixture_path = Path(__file__).parents[2] / 'tests' / 'fixtures' / 'forecast' / 'explain_fixture.json'
    
    if fixture_path.exists():
        with open(fixture_path) as f:
            data = json.load(f)
            # Normalize: fixture has 'shap_values' not 'feature_importances'
            if 'shap_values' in data:
                data['feature_importances'] = data['shap_values']
            # Add ticker if missing
            data.setdefault('ticker', 'AAPL')
            return data
    
    return {
        'ticker': 'AAPL',
        'feature_importances': [
            {'feature': 'momentum_20d', 'importance': 0.34},
            {'feature': 'volatility_10d', 'importance': 0.22},
            {'feature': 'volume_ratio', 'importance': 0.18},
            {'feature': 'rsi_14', 'importance': 0.15},
            {'feature': 'ma_cross', 'importance': 0.11}
        ]
    }

# Load fixtures
default_forecast = load_default_forecast()
default_explain = load_default_explanation()

# Create forecast chart
def create_forecast_chart(forecast_data):
    """Create forecast chart with confidence bands"""
    df = pd.DataFrame(forecast_data['forecast_series'])
    
    # Normalize column names (fixture uses yhat/yhat_lower/yhat_upper)
    if 'yhat' in df.columns:
        df['price'] = df['yhat']
    if 'yhat_lower' in df.columns:
        df['lower'] = df['yhat_lower']
    if 'yhat_upper' in df.columns:
        df['upper'] = df['yhat_upper']
    
    fig = go.Figure()
    
    # Confidence band
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['upper'],
        fill=None,
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['lower'],
        fill='tonexty',
        mode='lines',
        line=dict(width=0),
        name='95% Confidence',
        fillcolor='rgba(68, 138, 255, 0.2)',
        hoverinfo='skip'
    ))
    
    # Forecast line
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['price'],
        mode='lines+markers',
        name='Forecast',
        line=dict(color='#448aff', width=2),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        height=400,
        margin=dict(l=40, r=20, t=40, b=40),
        title=f"{forecast_data['ticker']} Price Forecast - {forecast_data['horizon']} Days",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        hovermode='x unified'
    )
    
    return fig

# Create feature importance chart
def create_explain_chart(explain_data):
    """Create feature importance bar chart"""
    importances = explain_data['feature_importances']
    df = pd.DataFrame(importances)
    df = df.sort_values('importance', ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['importance'],
        y=df['feature'],
        orientation='h',
        marker=dict(color='#448aff')
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        height=350,
        margin=dict(l=120, r=20, t=40, b=40),
        title=f"{explain_data['ticker']} Feature Importances",
        xaxis_title="Importance",
        yaxis_title="Feature",
        showlegend=False
    )
    
    return fig

# Layout function (wraps static content for index.py compatibility)
def create_layout():
    """Create Market Forecast layout with default AAPL forecast"""
    return dbc.Container([
        html.H2("📈 Market Forecast", className="text-light mb-4 mt-3"),
        
        # Controls Panel
        dbc.Card([
            dbc.CardBody([
                html.H5("Forecast Controls", className="text-light mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Ticker", className="text-light"),
                        dcc.Dropdown(
                        id='mf-ticker-input',
                        options=[
                            {'label': 'AAPL', 'value': 'AAPL'},
                            {'label': 'MSFT', 'value': 'MSFT'},
                            {'label': 'GOOGL', 'value': 'GOOGL'},
                            {'label': 'NVDA', 'value': 'NVDA'}
                        ],
                        value='AAPL',
                        clearable=False,
                        className='mb-3'
                    )
                ], width=3),
                
                dbc.Col([
                    html.Label("Horizon", className="text-light"),
                    dcc.Dropdown(
                        id='mf-horizon-select',
                        options=[
                            {'label': '1 Week (7 days)', 'value': 7},
                            {'label': '2 Weeks (14 days)', 'value': 14},
                            {'label': '1 Month (30 days)', 'value': 30},
                            {'label': '3 Months (90 days)', 'value': 90}
                        ],
                        value=30,
                        clearable=False,
                        className='mb-3'
                    )
                ], width=3),
                
                dbc.Col([
                    html.Label("Confidence", className="text-light"),
                    dcc.Dropdown(
                        id='mf-confidence-select',
                        options=[
                            {'label': '90%', 'value': 0.90},
                            {'label': '95%', 'value': 0.95},
                            {'label': '99%', 'value': 0.99}
                        ],
                        value=0.95,
                        clearable=False,
                        className='mb-3'
                    )
                ], width=2),
                
                dbc.Col([
                    html.Label("Mode", className="text-light"),
                    dcc.Dropdown(
                        id='mf-mode-select',
                        options=[
                            {'label': 'Deterministic (fixtures)', 'value': 'deterministic'},
                            {'label': 'Live (Bento)', 'value': 'live'}
                        ],
                        value='deterministic',
                        clearable=False,
                        className='mb-3'
                    )
                ], width=2),
                
                dbc.Col([
                    html.Label(" ", className="text-light"),
                    dbc.Button(
                        "Run Forecast",
                        id='mf-run-btn',
                        color='primary',
                        className='w-100'
                    )
                ], width=2)
            ])
        ])
    ], className="mb-4 bg-dark border-secondary"),
    
    # Results Panel - Summary Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Expected Return", className="text-light"),
                    html.H4(f"{default_forecast.get('expected_return', 0)*100:.2f}%",
                           className="text-success", id='mf-return-card')
                ])
            ], className="bg-dark border-secondary")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Volatility", className="text-light"),
                    html.H4(f"{default_forecast.get('volatility', 0)*100:.2f}%",
                           className="text-warning", id='mf-vol-card')
                ])
            ], className="bg-dark border-secondary")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Sharpe Ratio", className="text-light"),
                    html.H4(f"{default_forecast.get('sharpe_ratio', 0):.2f}",
                           className="text-info", id='mf-sharpe-card')
                ])
            ], className="bg-dark border-secondary")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Max Drawdown", className="text-light"),
                    html.H4(f"{default_forecast.get('max_drawdown', 0)*100:.2f}%",
                           className="text-danger", id='mf-dd-card')
                ])
            ], className="bg-dark border-secondary")
        ], width=3)
    ], className="mb-4"),
    
    # Forecast Chart
    dbc.Card([
        dbc.CardBody([
            html.H5("Price Forecast", className="text-light mb-3"),
            dcc.Graph(
                id='mf-forecast-chart',
                figure=create_forecast_chart(default_forecast),
                config={'displayModeBar': False}
            )
        ])
    ], className="mb-4 bg-dark border-secondary"),
    
    # Explainability Panel
    dbc.Card([
        dbc.CardBody([
            html.H5("Feature Importance", className="text-light mb-3"),
            dcc.Graph(
                id='mf-explain-chart',
                figure=create_explain_chart(default_explain),
                config={'displayModeBar': False}
            ),
            dbc.Row([
                dbc.Col([
                    html.P(
                        "Feature importance shows which factors most influence the forecast. "
                        "Higher values indicate stronger predictive power.",
                        className="text-muted small mt-3"
                    )
                ], width=8),
                dbc.Col([
                    dbc.Button(
                        "Download SHAP",
                        id='mf-download-shap-btn',
                        color='secondary',
                        outline=True,
                        className='mt-2'
                    ),
                    dcc.Download(id='mf-shap-download')
                ], width=4, className="text-end")
            ])
        ])
    ], className="mb-4 bg-dark border-secondary"),
    
    # Hidden stores for state management (if callbacks are needed later)
    dcc.Store(id='mf-forecast-store'),
    dcc.Store(id='mf-explain-store'),
    
], fluid=True, className="py-4")

# Keep static layout for backwards compatibility
layout = create_layout()
