# Volatility Lab - 8 Subtab Architecture (Phase 0.9B)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple
import logging

from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from dash import dash_table

# Relative imports
try:
    from .volatility_lib import compute_volatility_metrics
    from ..services.options_connector import get_options_chain, OptionsConnector
    from ..volatility.iv_surface import calculate_iv_surface, interpolate_iv_surface
    from ..volatility.factor_analytics import calculate_correlation_matrix
except ImportError:
    from financial_dashboard.tabs.volatility_lib import compute_volatility_metrics
    from financial_dashboard.services.options_connector import get_options_chain, OptionsConnector
    from financial_dashboard.volatility.iv_surface import calculate_iv_surface, interpolate_iv_surface
    from financial_dashboard.volatility.factor_analytics import calculate_correlation_matrix

logger = logging.getLogger(__name__)


def validate_and_parse_tickers(ticker_input: str) -> Tuple[List[str], List[str]]:
    if not ticker_input or not isinstance(ticker_input, str):
        return [], []
    raw_tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
    valid, invalid = [], []
    for ticker in raw_tickers:
        if 1 <= len(ticker) <= 5 and ticker.replace('-', '').isalpha():
            valid.append(ticker)
        else:
            invalid.append(ticker)
    return valid, invalid


def load_price_data(tickers: List[str], start: str, end: str):
    try:
        from ..utils.price_cache import get_price_cache
    except ImportError:
        from financial_dashboard.utils.price_cache import get_price_cache
    
    cache = get_price_cache()
    cached = cache.get(tickers, start, end)
    if cached is not None:
        return cached
    
    import yfinance as yf
    data = []
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(start=start, end=end, interval='1d')
            if not hist.empty:
                hist = hist.reset_index()
                hist['ticker'] = ticker
                hist['date'] = hist['Date']
                hist['price'] = hist['Close']
                data.append(hist[['date', 'ticker', 'price']])
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
    
    if data:
        df = pd.concat(data, ignore_index=True)
        cache.set(df, tickers, start, end)
        return df
    return pd.DataFrame()


def compute_volatility(df: pd.DataFrame, window: int):
    results = []
    for ticker in df['ticker'].unique():
        ticker_df = df[df['ticker'] == ticker].sort_values('date')
        prices = ticker_df.set_index('date')['price']
        metrics = compute_volatility_metrics(prices, window=window, annualize=True)
        metrics['ticker'] = ticker
        metrics = metrics.reset_index()
        results.append(metrics)
    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()


def create_hv_subtab():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("1. Historical Volatility"),
                html.P("Rolling and realized volatility from price history", className="text-muted small"),
                dcc.Markdown("""
**📊 What This Shows:**

Historical Volatility (HV) tracks **past price volatility levels** to understand how stable or unstable the market has been.

**💡 Key Insights:**
- Shows **total market volatility** compared to historical averages
- Helps identify whether conditions are **calm or turbulent**
- Higher HV = More price swings (riskier period)
- Lower HV = More stability (calmer market)

**🎯 How to Use:**
1. Enter comma-separated tickers (e.g., AAPL,SPY,TSLA)
2. Select date range (default: last 90 days)
3. Adjust rolling window (5-60 days)
4. Click "Compute" to generate charts

The left chart shows price movements, the right chart shows rolling volatility over time.
                """, className="small", style={'backgroundColor': '#f0f8ff', 'padding': '10px', 'borderRadius': '6px', 'marginBottom': '15px'})
            ])
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Tickers"),
                dcc.Input(id='vl-hv-tickers', type='text', value='AAPL,SPY', className="form-control")
            ], md=3),
            dbc.Col([
                html.Label("Date Range"),
                dcc.DatePickerRange(
                    id='vl-hv-dates',
                    start_date=(datetime.now() - timedelta(days=90)).date(),
                    end_date=datetime.now().date()
                )
            ], md=3),
            dbc.Col([
                html.Label("Window"),
                dcc.Slider(id='vl-hv-window', min=5, max=60, step=5, value=20, marks={5:'5',20:'20',60:'60'})
            ], md=4),
            dbc.Col([
                html.Label(" "),
                dbc.Button("Compute", id='vl-hv-btn', color="primary", className="w-100")
            ], md=2)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col(dcc.Loading(dcc.Graph(id='vl-hv-price')), md=6),
            dbc.Col(dcc.Loading(dcc.Graph(id='vl-hv-vol')), md=6)
        ]),
        
        html.Div(id='vl-hv-status', className="alert alert-info mt-3")
    ], fluid=True)


def create_iv_subtab():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("2. IV Surface"),
                html.P("3D implied volatility from options chain", className="text-muted small"),
                dcc.Markdown("""
**📊 What This Shows:**

Implied Volatility (IV) Surface displays **implied volatility for different strike prices and expirations** derived from live options pricing.

**💡 Key Insights:**
- **Traders use this to gauge market sentiment** and option pricing
- **Higher IV** = Options are more expensive (market expects big moves)
- **Lower IV** = Options are cheaper (market expects calm conditions)
- The "surface" shows how IV changes across strikes and time

**🎯 How to Use:**
1. Enter ticker symbol (e.g., SPY)
2. Select expiration date from dropdown
3. Click "Load" to fetch options data
4. Click "Generate" to create 3D surface visualization

The 3D surface helps visualize the **volatility smile** and identify unusual pricing patterns.
                """, className="small", style={'backgroundColor': '#fff5f0', 'padding': '10px', 'borderRadius': '6px', 'marginBottom': '15px'})
            ])
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Ticker"),
                dcc.Input(id='vl-iv-ticker', value='SPY', className="form-control")
            ], md=2),
            dbc.Col([
                html.Label("Expiration"),
                dcc.Dropdown(id='vl-iv-exp', options=[], placeholder="Select...")
            ], md=3),
            dbc.Col([
                html.Label(" "),
                dbc.Button("Load", id='vl-iv-load', color="primary")
            ], md=2),
            dbc.Col([
                html.Label(" "),
                dbc.Button("Generate", id='vl-iv-gen', color="success")
            ], md=2)
        ], className="mb-3"),
        
        dcc.Loading(dcc.Graph(id='vl-iv-surface', style={'height':'600px'})),
        html.Div(id='vl-iv-status', className="alert alert-info mt-3")
    ], fluid=True)


def create_corr_subtab():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("3. Correlation Heatmap"),
                html.P("Multi-ticker correlation matrix", className="text-muted small"),
                dcc.Markdown("""
**📊 What This Shows:**

Correlation Heatmap reveals **how asset volatilities move together** - critical for understanding portfolio risk and diversification.

**💡 Key Insights:**
- **High positive correlation (red)** = Assets move in same direction together
- **Negative correlation (blue)** = Assets move opposite directions
- **Zero correlation (white)** = No relationship
- **High correlations across portfolio = systemic risk** (all holdings affected by same events)

**🎯 How to Use:**
1. Enter comma-separated tickers (e.g., SPY,QQQ,AAPL)
2. Select date range (default: last 180 days)
3. Click "Compute" to generate correlation matrix

Use this to identify **diversification opportunities** - seek assets with low/negative correlations to reduce portfolio risk.
                """, className="small", style={'backgroundColor': '#f0fff0', 'padding': '10px', 'borderRadius': '6px', 'marginBottom': '15px'})
            ])
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Tickers"),
                dcc.Input(id='vl-corr-tickers', value='SPY,QQQ,AAPL', className="form-control")
            ], md=4),
            dbc.Col([
                html.Label("Date Range"),
                dcc.DatePickerRange(
                    id='vl-corr-dates',
                    start_date=(datetime.now() - timedelta(days=180)).date(),
                    end_date=datetime.now().date()
                )
            ], md=4),
            dbc.Col([
                html.Label(" "),
                dbc.Button("Compute", id='vl-corr-btn', color="primary", className="w-100")
            ], md=2)
        ], className="mb-3"),
        
        dcc.Loading(dcc.Graph(id='vl-corr-heat', style={'height':'600px'})),
        html.Div(id='vl-corr-status', className="alert alert-info mt-3")
    ], fluid=True)


def create_placeholder(title, desc, subtab_num=None, explanation=None):
    """Create enhanced placeholder with user-friendly explanations"""
    
    # Map subtab names to descriptions
    descriptions = {
        "Factor Analytics": {
            "title": "4. Factor Analytics",
            "desc": "Beta, alpha, Sharpe ratio, and rolling performance metrics",
            "explanation": """
**📊 What This Shows:**

Factor Analytics reveals how your portfolio or individual stocks relate to market factors and risk-adjusted performance.

**💡 Key Metrics:**
- **Beta**: Sensitivity to market movements (1.0 = moves with market, >1.0 = more volatile)
- **Alpha**: Excess return vs benchmark (positive = outperformance)
- **Sharpe Ratio**: Risk-adjusted returns (higher = better reward per unit of risk)
- **Rolling Metrics**: How these metrics change over time

**🎯 Use Case:**

Identify which assets add systematic risk vs diversification benefit to your portfolio.
            """
        },
        "Advanced Charts": {
            "title": "5. Advanced Charts",
            "desc": "Multi-ticker HV/IV comparisons and volatility cones",
            "explanation": """
**📊 What This Shows:**

Advanced visualization tools for comparing volatility across multiple assets and time periods.

**💡 Features:**
- **HV/IV Overlays**: Compare historical vs implied volatility
- **Volatility Cones**: Show typical volatility ranges at different time horizons
- **Multi-ticker Comparison**: Side-by-side volatility analysis

**🎯 Use Case:**

Spot unusual volatility patterns and identify relative value opportunities in options pricing.
            """
        },
        "Metrics Table": {
            "title": "6. Metrics Table",
            "desc": "Comprehensive volatility metrics summary grid",
            "explanation": """
**📊 What This Shows:**

A comprehensive table displaying all key volatility metrics for your selected tickers in one view.

**💡 Metrics Included:**
- Current IV & HV levels
- IV Rank & IV Percentile
- Historical volatility ranges
- Volatility term structure summary
- Last update timestamp

**🎯 Use Case:**

Quickly scan multiple tickers to find the most/least volatile assets or identify mispriced options.
            """
        },
        "Custom Scenarios": {
            "title": "7. Custom Scenarios",
            "desc": "User-defined volatility stress testing",
            "explanation": """
**📊 What This Shows:**

Tools for running custom volatility scenarios and stress tests on your portfolio.

**💡 Capabilities:**
- **"What-if" Analysis**: Model portfolio behavior under different volatility regimes
- **Stress Tests**: See impact of volatility spikes (e.g., +50% IV shock)
- **Scenario Comparison**: Compare multiple custom scenarios side-by-side

**🎯 Use Case:**

Prepare for market turbulence by understanding how your portfolio reacts to volatility changes.
            """
        },
        "Alerts": {
            "title": "8. Alerts & Diagnostics",
            "desc": "Data quality warnings and system health monitoring",
            "explanation": """
**📊 What This Shows:**

System health monitoring, data quality alerts, and diagnostic information for the Volatility Lab.

**💡 Features:**
- **Data Freshness**: When was the last successful data fetch
- **Missing Data Alerts**: Identify gaps in historical or options data
- **API Status**: Connection health to data providers
- **Calculation Warnings**: Flags for incomplete or unreliable metrics

**🎯 Use Case:**

Ensure confidence in your analysis by verifying data quality and system integrity.
            """
        }
    }
    
    info = descriptions.get(title, {
        "title": title,
        "desc": desc,
        "explanation": explanation or "Details coming in Phase 2."
    })
    
    return dbc.Container([
        html.H5(info["title"]),
        html.P(info["desc"], className="text-muted small"),
        dcc.Markdown(info["explanation"], className="small", 
                    style={'backgroundColor': '#fffacd', 'padding': '10px', 'borderRadius': '6px', 'marginBottom': '15px'}),
        dbc.Alert([
            html.I(className="bi bi-wrench me-2"),
            "This subtab is under development. Core functionality coming in Phase 2."
        ], color="warning", className="mt-3")
    ], fluid=True)


def layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="bi bi-activity me-2"),
                    "⚡ Volatility Lab"
                ]),
                html.P("8-subtab advanced volatility analysis suite", className="text-muted"),
                dcc.Markdown("""
**🔬 Volatility Lab Overview:**

This comprehensive suite provides **8 specialized tools** for analyzing market volatility across historical, implied, and predictive dimensions.

**📈 What You Can Do:**
1. **Historical HV** - Analyze past volatility patterns
2. **IV Surface** - Visualize options-implied volatility in 3D
3. **Correlation** - Identify how assets move together
4. **Factor Analytics** - Calculate risk-adjusted performance metrics
5. **Advanced Charts** - Compare HV/IV across assets
6. **Metrics Table** - Scan all volatility metrics at a glance
7. **Custom Scenarios** - Stress test portfolio under volatility shocks
8. **Alerts** - Monitor data quality and system health

**💡 Quick Start:** Click any subtab above to begin. Each section includes detailed instructions and explanations.
                """, className="small", style={'backgroundColor': '#f5f5f5', 'padding': '12px', 'borderRadius': '8px', 'marginBottom': '10px'})
            ])
        ], className="mb-4"),
        
        dbc.Tabs(id="vl-tabs", active_tab='hv', children=[
            dbc.Tab(label="Historical HV", tab_id='hv', children=create_hv_subtab()),
            dbc.Tab(label="IV Surface", tab_id='iv', children=create_iv_subtab()),
            dbc.Tab(label="Correlation", tab_id='corr', children=create_corr_subtab()),
            dbc.Tab(label="Factor Analytics", tab_id='factors', children=create_placeholder("Factor Analytics", "Beta, alpha, Sharpe")),
            dbc.Tab(label="Advanced Charts", tab_id='charts', children=create_placeholder("Advanced Charts", "HV/IV overlays")),
            dbc.Tab(label="Metrics Table", tab_id='metrics', children=create_placeholder("Metrics Table", "Comprehensive summary")),
            dbc.Tab(label="Custom Scenarios", tab_id='scenarios', children=create_placeholder("Custom Scenarios", "User-defined analysis")),
            dbc.Tab(label="Alerts", tab_id='alerts', children=create_placeholder("Alerts", "Data quality warnings"))
        ])
    ], fluid=True)


def register_callbacks(app):
    
    @app.callback(
        [Output('vl-hv-price', 'figure'), Output('vl-hv-vol', 'figure'), Output('vl-hv-status', 'children')],
        [Input('vl-hv-btn', 'n_clicks')],
        [State('vl-hv-tickers', 'value'), State('vl-hv-dates', 'start_date'), 
         State('vl-hv-dates', 'end_date'), State('vl-hv-window', 'value')],
        prevent_initial_call=True
    )
    def compute_hv(n, tickers, start, end, window):
        valid, invalid = validate_and_parse_tickers(tickers)
        if not valid:
            return go.Figure(), go.Figure(), "No valid tickers"
        
        df = load_price_data(valid, start, end)
        if df.empty:
            return go.Figure(), go.Figure(), "No data"
        
        vol_df = compute_volatility(df, window)
        
        price_fig = go.Figure()
        for ticker in valid:
            td = df[df['ticker'] == ticker]
            price_fig.add_trace(go.Scatter(x=td['date'], y=td['price'], name=ticker))
        price_fig.update_layout(title="Price", template='plotly_white', height=400)
        
        vol_fig = go.Figure()
        for ticker in valid:
            tv = vol_df[vol_df['ticker'] == ticker]
            if not tv.empty:
                vol_fig.add_trace(go.Scatter(x=tv['date'], y=tv['rolling_vol']*100, name=ticker))
        vol_fig.update_layout(title="Volatility (%)", template='plotly_white', height=400)
        
        return price_fig, vol_fig, f"Computed for {len(valid)} tickers"
    
    @app.callback(
        [Output('vl-iv-exp', 'options'), Output('vl-iv-exp', 'value'), Output('vl-iv-status', 'children')],
        [Input('vl-iv-load', 'n_clicks')],
        [State('vl-iv-ticker', 'value')],
        prevent_initial_call=True
    )
    def load_exps(n, ticker):
        if not ticker:
            return [], None, "Enter ticker"
        try:
            connector = OptionsConnector()
            exps = connector.get_available_expirations(ticker.upper())
            if not exps:
                return [], None, f"No options for {ticker}"
            opts = [{'label': e, 'value': e} for e in exps[:10]]
            return opts, exps[0], f"Found {len(exps)} expirations"
        except Exception as e:
            return [], None, f"Error: {e}"
    
    @app.callback(
        Output('vl-iv-surface', 'figure'),
        [Input('vl-iv-gen', 'n_clicks')],
        [State('vl-iv-ticker', 'value'), State('vl-iv-exp', 'value')],
        prevent_initial_call=True
    )
    def gen_surface(n, ticker, exp):
        if not ticker or not exp:
            return go.Figure()
        
        try:
            import yfinance as yf
            calls, puts, src = get_options_chain(ticker.upper(), exp)
            price = yf.Ticker(ticker.upper()).history(period='1d')['Close'].iloc[-1]
            
            all_opts = pd.concat([calls, puts], ignore_index=True)
            iv_df = calculate_iv_surface(all_opts, price)
            valid = iv_df[iv_df['implied_vol'].notna()].copy()
            
            if len(valid) < 4:
                return go.Figure()
            
            strike_mesh, tte_mesh, iv_mesh = interpolate_iv_surface(valid, grid_size=30)
            if strike_mesh is not None:
                fig = go.Figure(data=[go.Surface(x=strike_mesh, y=tte_mesh, z=iv_mesh*100, colorscale='Viridis')])
                fig.update_layout(title=f"IV Surface - {ticker}", scene=dict(xaxis_title="Strike", yaxis_title="TTE", zaxis_title="IV (%)"), height=600)
                return fig
            return go.Figure()
        except Exception as e:
            logger.error(f"IV surface error: {e}")
            return go.Figure()
    
    @app.callback(
        [Output('vl-corr-heat', 'figure'), Output('vl-corr-status', 'children')],
        [Input('vl-corr-btn', 'n_clicks')],
        [State('vl-corr-tickers', 'value'), State('vl-corr-dates', 'start_date'), State('vl-corr-dates', 'end_date')],
        prevent_initial_call=True
    )
    def compute_corr(n, tickers, start, end):
        valid, invalid = validate_and_parse_tickers(tickers)
        if len(valid) < 2:
            return go.Figure(), "Need 2+ tickers"
        
        df = load_price_data(valid, start, end)
        if df.empty:
            return go.Figure(), "No data"
        
        prices = df.pivot(index='date', columns='ticker', values='price')
        returns = prices.pct_change().dropna()
        corr = calculate_correlation_matrix({t: returns[t] for t in valid})
        
        fig = px.imshow(corr, labels=dict(color="Correlation"), color_continuous_scale='RdBu_r', zmin=-1, zmax=1, text_auto='.2f')
        fig.update_layout(title="Correlation Matrix", template='plotly_white', height=600)
        
        return fig, f"Computed for {len(valid)} tickers"
