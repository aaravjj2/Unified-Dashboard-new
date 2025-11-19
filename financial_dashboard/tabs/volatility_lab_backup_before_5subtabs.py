"""
Volatility Lab - Callback-Based Content Switching
Uses proper Dash pattern: tabs trigger callback that returns content
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import yfinance as yf

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_tickers(ticker_str):
    if not ticker_str or not ticker_str.strip():
        return []
    tickers = [t.strip().upper() for t in ticker_str.split(',') if t.strip()]
    return [t for t in tickers if 1 <= len(t) <= 5]

def fetch_price_data(ticker, days=252):
    try:
        stock = yf.Ticker(ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        df = stock.history(start=start_date, end=end_date)
        return df if not df.empty else None
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None

def calculate_historical_volatility(prices, window=30):
    returns = np.log(prices / prices.shift(1))
    rolling_std = returns.rolling(window=window).std()
    return rolling_std * np.sqrt(252) * 100

# ============================================================================
# SUBTAB UI CREATION FUNCTIONS
# ============================================================================

def create_hv_subtab():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Label("Tickers (comma-separated):"),
                dbc.Input(id='hv-tickers', value='SPY,QQQ,IWM', placeholder='SPY,AAPL'),
            ], width=6),
            dbc.Col([
                dbc.Label("Window:"),
                dbc.Input(id='hv-window', value='30', type='number'),
            ], width=3),
            dbc.Col([
                dbc.Button("Calculate", id='hv-calc-btn', color='primary', className='mt-4'),
            ], width=3),
        ], className='mb-3'),
        dcc.Loading(children=[dcc.Graph(id='hv-chart', style={'height': '500px'})]),
        html.Div(id='hv-stats', className='mt-2 p-3 border rounded')
    ], fluid=True, className='p-3')

def create_iv_subtab():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Label("Ticker:"),
                dbc.Input(id='iv-ticker', value='SPY'),
            ], width=4),
            dbc.Col([
                dbc.Button("Generate", id='iv-gen-btn', color='success', className='mt-4'),
            ], width=3),
        ], className='mb-3'),
        dcc.Loading(children=[dcc.Graph(id='iv-surface', style={'height': '600px'})]),
        html.Div(id='iv-status', className='mt-2')
    ], fluid=True, className='p-3')

def create_corr_subtab():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Label("Tickers:"),
                dbc.Input(id='corr-tickers', value='SPY,QQQ,IWM,DIA'),
            ], width=6),
            dbc.Col([
                dbc.Label("Days:"),
                dbc.Input(id='corr-days', value='252', type='number'),
            ], width=3),
            dbc.Col([
                dbc.Button("Calculate", id='corr-calc-btn', color='info', className='mt-4'),
            ], width=3),
        ], className='mb-3'),
        dcc.Loading(children=[dcc.Graph(id='corr-heatmap', style={'height': '500px'})]),
        html.Div(id='corr-stats', className='mt-2')
    ], fluid=True, className='p-3')

def create_placeholder(title, desc):
    return dbc.Container([
        dbc.Alert([
            html.H5(f"🚧 {title}"),
            html.P(desc),
            html.P("Implementation planned for future release.", className='text-muted small')
        ], color='info')
    ], fluid=True, className='p-3')

# ============================================================================
# MAIN LAYOUT
# ============================================================================

def layout():
    return dbc.Container([
        html.H3("⚡ Volatility Lab"),
        html.P("Comprehensive volatility analysis", className='text-muted mb-4'),
        
        dbc.Tabs(id='vl-tabs', active_tab='hv', children=[
            dbc.Tab(label="📊 Historical HV", tab_id='hv'),
            dbc.Tab(label="🌐 IV Surface", tab_id='iv'),
            dbc.Tab(label="🔗 Correlation", tab_id='corr'),
            dbc.Tab(label="📈 Factors", tab_id='factors'),
            dbc.Tab(label="📉 Charts", tab_id='charts'),
            dbc.Tab(label="📋 Metrics", tab_id='metrics'),
            dbc.Tab(label="🎯 Scenarios", tab_id='scenarios'),
            dbc.Tab(label="🔔 Alerts", tab_id='alerts')
        ]),
        
        html.Div(id='vl-content', className='mt-3')
    ], fluid=True)

# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    Output('vl-content', 'children'),
    Input('vl-tabs', 'active_tab')
)
def render_tab_content(active_tab):
    """Switch content based on active tab"""
    if active_tab == 'hv':
        return create_hv_subtab()
    elif active_tab == 'iv':
        return create_iv_subtab()
    elif active_tab == 'corr':
        return create_corr_subtab()
    elif active_tab == 'factors':
        return create_placeholder("Factor Analytics", "Beta, alpha, Sharpe analysis")
    elif active_tab == 'charts':
        return create_placeholder("Advanced Charts", "Volatility cones, RV vs IV")
    elif active_tab == 'metrics':
        return create_placeholder("Metrics Table", "Comprehensive volatility grid")
    elif active_tab == 'scenarios':
        return create_placeholder("Custom Scenarios", "Stress testing framework")
    elif active_tab == 'alerts':
        return create_placeholder("Alerts", "Volatility spike monitoring")
    return html.Div("Select a tab")

@callback(
    Output('hv-chart', 'figure'),
    Output('hv-stats', 'children'),
    Input('hv-calc-btn', 'n_clicks'),
    State('hv-tickers', 'value'),
    State('hv-window', 'value'),
    prevent_initial_call=True
)
def calculate_hv(n, tickers_str, window):
    tickers = validate_tickers(tickers_str)
    window = int(window) if window else 30
    
    fig = go.Figure()
    stats = []
    
    for ticker in tickers:
        df = fetch_price_data(ticker, days=500)
        if df is not None and not df.empty:
            hv = calculate_historical_volatility(df['Close'], window=window)
            fig.add_trace(go.Scatter(x=hv.index, y=hv, mode='lines', name=f'{ticker} HV-{window}'))
            
            current = hv.iloc[-1] if len(hv) > 0 else 0
            mean = hv.mean()
            stats.append(f"{ticker}: {current:.2f}% (mean: {mean:.2f}%)")
    
    fig.update_layout(
        title=f'Historical Volatility ({window}-day)',
        xaxis_title='Date',
        yaxis_title='Volatility (%)',
        template='plotly_dark',
        height=500
    )
    
    return fig, html.Div([html.P(s) for s in stats])

@callback(
    Output('iv-surface', 'figure'),
    Output('iv-status', 'children'),
    Input('iv-gen-btn', 'n_clicks'),
    State('iv-ticker', 'value'),
    prevent_initial_call=True
)
def generate_iv(n, ticker):
    strikes = np.linspace(85, 115, 25)
    exps = np.arange(7, 180, 7)
    strike_grid, exp_grid = np.meshgrid(strikes, exps)
    
    moneyness = (strike_grid - 100) / 100
    iv_surface = 20 + 15 * np.exp(-moneyness**2 * 8) + 0.06 * exp_grid
    
    fig = go.Figure(data=[go.Surface(x=strikes, y=exps, z=iv_surface, colorscale='Viridis')])
    fig.update_layout(
        title=f'{ticker} IV Surface (Simulated)',
        scene=dict(
            xaxis_title='Strike',
            yaxis_title='DTE',
            zaxis_title='IV %'
        ),
        height=600,
        template='plotly_dark'
    )
    
    return fig, f"✅ Generated surface for {ticker}"

@callback(
    Output('corr-heatmap', 'figure'),
    Output('corr-stats', 'children'),
    Input('corr-calc-btn', 'n_clicks'),
    State('corr-tickers', 'value'),
    State('corr-days', 'value'),
    prevent_initial_call=True
)
def calculate_corr(n, tickers_str, days):
    tickers = validate_tickers(tickers_str)
    days = int(days) if days else 252
    
    price_data = {}
    for ticker in tickers:
        df = fetch_price_data(ticker, days=days)
        if df is not None and not df.empty:
            price_data[ticker] = df['Close']
    
    prices_df = pd.DataFrame(price_data)
    returns = prices_df.pct_change().dropna()
    corr = returns.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        colorscale='RdBu',
        zmid=0,
        text=corr.values.round(3),
        texttemplate='%{text}'
    ))
    fig.update_layout(title=f'Correlation ({days}-day)', template='plotly_dark', height=500)
    
    avg = corr.values[np.triu_indices_from(corr.values, k=1)].mean()
    return fig, html.P(f"Average correlation: {avg:.3f}")
