"""
Market Forecast Tab - Phase 7C Implementation

Provides forward-looking market forecasts with:
- Ticker selection from portfolio
- Multiple forecast horizons (1-week, 1-month, 3-month)
- Expected return and volatility estimates
- Confidence intervals
- Probability metrics
- SHAP feature integration
- Interactive charts and summary cards
"""

from dash import html, dcc, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Import forecast engine
try:
    from utils.market_forecast import calculate_forecast, HORIZONS
    FORECAST_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Forecast engine not available: {e}")
    FORECAST_ENGINE_AVAILABLE = False
    HORIZONS = {'1_week': 7, '1_month': 30, '3_month': 90}

# Data paths
CACHE_DIR = Path("/app/cache")
EXPLAIN_DIR = Path("/app/explain")

# If running outside container (local dev), fall back to repository cache folders
if not CACHE_DIR.exists():
    repo_cache = Path(__file__).resolve().parents[2] / 'cache'
    if repo_cache.exists():
        CACHE_DIR = repo_cache
        logger.info(f"Using local repo cache dir: {CACHE_DIR}")
    else:
        # create cache folder locally so functions don't break
        try:
            repo_cache.mkdir(parents=True, exist_ok=True)
            CACHE_DIR = repo_cache
            logger.info(f"Created local repo cache dir: {CACHE_DIR}")
        except Exception:
            logger.warning(f"Cache dir not found and couldn't create repo cache: {repo_cache}")

if not EXPLAIN_DIR.exists():
    repo_explain = Path(__file__).resolve().parents[2] / 'explain'
    if repo_explain.exists():
        EXPLAIN_DIR = repo_explain
        logger.info(f"Using local repo explain dir: {EXPLAIN_DIR}")


def load_portfolio_tickers():
    """Load current portfolio tickers from cache"""
    try:
        portfolio_path = CACHE_DIR / "portfolio_data.json"
        if not portfolio_path.exists():
            logger.warning("Portfolio data not found")
            return []
        
        with open(portfolio_path) as f:
            data = json.load(f)
        # Support multiple possible schemas used historically
        positions = data.get("positions") or data.get("holdings") or data.get("items") or []
        tickers = []
        for p in positions:
            if isinstance(p, dict):
                t = p.get("ticker") or p.get("symbol") or p.get("ticker_symbol") or p.get("sym")
                if t:
                    tickers.append(str(t).upper())
            else:
                # If positions is a simple list of tickers
                tickers.append(str(p).upper())
        tickers = sorted(list({t for t in tickers if t}))
        return tickers
    except Exception as e:
        logger.error(f"Error loading portfolio tickers: {e}")
        return []


def load_market_signals():
    """Load market trend signals from cache"""
    try:
        market_path = CACHE_DIR / "market_brief.json"
        if not market_path.exists():
            return {}
        
        with open(market_path) as f:
            data = json.load(f)
        signals = {}
        detailed = data.get("detailed") or data.get("rows") or data.get("tickers") or []
        for item in detailed:
            if not isinstance(item, dict):
                continue
            # Support various casing/keys
            ticker = item.get("Ticker") or item.get("ticker") or item.get("symbol") or item.get("sym")
            if not ticker:
                continue
            ticker = str(ticker).upper()
            signals[ticker] = {
                "signal": item.get("Signal") or item.get("signal") or item.get("trend") or "NEUTRAL",
                "momentum": _safe_number(item.get("Momentum") or item.get("momentum") or item.get("mom"), default=0),
                "sentiment": _safe_number(item.get("Sentiment") or item.get("sentiment"), default=0),
                "volatility": _safe_number(item.get("Volatility") or item.get("volatility"), default=0.25)
            }
        return signals
    except Exception as e:
        logger.error(f"Error loading market signals: {e}")
        return {}


def _safe_number(v, default=0.0):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return float(v)
    except Exception:
        return default


def create_summary_card(title, value, subtitle="", icon="📊", color="primary"):
    """Create a summary metrics card"""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(icon, style={"fontSize": "32px", "marginRight": "12px"}),
                html.Div([
                    html.H6(title, className="mb-1", style={"fontSize": "12px", "color": "#000000"}),
                    html.H3(value, className="mb-0", style={"fontSize": "24px", "fontWeight": "600"}),
                    html.P(subtitle, className="mb-0", style={"fontSize": "11px", "color": "#000000"}) if subtitle else html.Div()
                ], style={"flex": "1"})
            ], style={"display": "flex", "alignItems": "center"})
        ])
    ], className=f"border-{color} shadow-sm mb-3", style={"borderLeft": f"4px solid"})


def _create_strategy_card(strategy):
    """Create a card for strategy recommendation"""
    confidence = strategy.get('confidence', 0)
    
    # Confidence color coding
    if confidence >= 0.8:
        badge_color = "success"
    elif confidence >= 0.6:
        badge_color = "info"
    else:
        badge_color = "warning"
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.H6(strategy.get('name', 'Unknown Strategy'), className="mb-1"),
                    dbc.Badge(f"{confidence:.0%} confidence", color=badge_color, className="mb-2")
                ], style={"flex": "1"}),
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"}),
            html.P(strategy.get('description', ''), className="mb-2 small"),
            html.P([
                html.Strong("Rationale: "),
                html.Span(strategy.get('rationale', ''), className="text-muted")
            ], className="mb-0 small")
        ])
    ], className="mb-2 border-left-primary", style={"borderLeft": "3px solid #3b82f6"})


def layout():
    """Create Market Forecast tab layout"""
    
    # Load portfolio tickers
    tickers = load_portfolio_tickers()
    
    if not tickers:
        return html.Div([
            dbc.Alert([
                html.H5("⚠️ No Portfolio Data", className="alert-heading"),
                html.P("Portfolio positions not found. Please ensure portfolio_data.json exists in the cache directory."),
                html.Hr(),
                html.P("Expected path: /app/cache/portfolio_data.json", className="mb-0 small", style={"color": "#000000"})
            ], color="warning")
        ], className="p-4")
    
    ticker_options = [{"label": ticker, "value": ticker} for ticker in tickers]
    
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="bi bi-graph-up-arrow me-2"),
                    "Market Forecast"
                ], className="mb-1"),
                html.P(
                    f"Forward-looking forecasts for {len(tickers)} portfolio tickers with ML-powered predictions",
                    className="mb-0 small",
                    style={"color": "#000000"}
                ),
                dcc.Markdown("""
**📊 What This Tab Does:**

This tool projects **expected price movements** based on:
- Recent volatility patterns
- Trend momentum analysis  
- Statistical regression modeling

**🎯 How to Use:**
1. Select tickers from your portfolio or enter custom symbols (comma-separated)
2. Choose forecast horizon (1 week, 1 month, or 3 months)
3. Set confidence level (90%, 95%, or 99%)
4. Click "Generate Forecast" to see predictions

**📈 Understanding the Results:**
- **Price Prediction**: Expected future price based on current trends
- **Confidence Intervals**: Shaded areas show uncertainty range (narrower = higher confidence)
- **Volatility Estimates**: How much price swings are expected
- **Last Updated**: When the underlying data was refreshed
                """, className="small", style={'backgroundColor': '#f8f9fa', 'padding': '12px', 'borderRadius': '8px', 'marginTop': '10px', 'color': '#000000'})
            ])
        ], className="mb-4"),
        
        # Controls Row
        dbc.Row([
            dbc.Col([
                html.Label("Select Tickers", className="fw-bold mb-2 small"),
                html.Div([
                    dcc.Dropdown(
                        id="mf-ticker-selector",
                        options=ticker_options,
                        value=tickers[:5] if len(tickers) >= 5 else tickers,
                        multi=True,
                        placeholder="Select tickers to forecast...",
                        className="mb-2"
                    ),
                    # Free text input to allow arbitrary tickers (comma separated)
                    dcc.Input(
                        id='mf-ticker-input',
                        type='text',
                        placeholder='Or enter comma-separated tickers (e.g. AAPL,TSLA,IBM)',
                        style={'width': '100%'},
                        debounce=True
                    ),
                    html.Div("Tip: use the input above to forecast any ticker. Values will be upper-cased and whitespace-trimmed.", className='small mt-1', style={"color": "#000000"})
                ])
            ], md=6),
            dbc.Col([
                html.Label("Forecast Horizon", className="fw-bold mb-2 small"),
                dcc.Dropdown(
                    id="mf-horizon-selector",
                    options=[
                        {"label": "1 Week (7 days)", "value": "1_week"},
                        {"label": "1 Month (30 days)", "value": "1_month"},
                        {"label": "3 Months (90 days)", "value": "3_month"}
                    ],
                    value="1_month",
                    clearable=False,
                    className="mb-3"
                )
            ], md=3),
            dbc.Col([
                html.Label("Confidence Level", className="fw-bold mb-2 small"),
                dcc.Dropdown(
                    id="mf-confidence-selector",
                    options=[
                        {"label": "90%", "value": 0.90},
                        {"label": "95%", "value": 0.95},
                        {"label": "99%", "value": 0.99}
                    ],
                    value=0.95,
                    clearable=False,
                    className="mb-3"
                )
            ], md=3)
        ], className="mb-3"),
        
        # Action Button
        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="bi bi-play-fill me-2"),
                    "Generate Forecast"
                ], id="mf-generate-btn", color="primary", size="lg", className="w-100")
            ], md=12)
        ], className="mb-4"),
        
        # Loading Spinner
        dcc.Loading(
            id="mf-loading",
            type="default",
            children=html.Div(id="mf-loading-output")
        ),
        

        # Phase 20B: Options Forecast moved to Options Lab

        html.Hr(className="my-4"),
        
        # Summary Cards Row
        dbc.Row([
            dbc.Col([
                html.Div(id="mf-summary-cards")
            ], md=12)
        ], className="mb-4"),
        
        # Charts Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="bi bi-graph-up me-2"),
                            "Expected Returns & Confidence Intervals"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        dcc.Markdown("""
**📊 How to Read This Chart:**
- **Bars**: Show expected return percentage for each ticker
- **Error bars**: Confidence interval range (wider = more uncertainty)
- **Green bars**: Positive expected returns (bullish forecast)
- **Red bars**: Negative expected returns (bearish forecast)

The confidence interval represents the statistical uncertainty in the prediction. Narrower bands indicate the model has higher confidence in its forecast.
                        """, className="small mb-3", style={'backgroundColor': '#f0f8ff', 'padding': '10px', 'borderRadius': '6px', 'color': '#000000'}),
                        dcc.Graph(id="mf-returns-chart", config={'displayModeBar': False})
                    ])
                ], className="shadow-sm mb-3")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="bi bi-speedometer2 me-2"),
                            "Volatility Estimates"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        dcc.Markdown("""
**📈 Understanding Volatility:**
- **Higher bars**: More price swings expected (riskier)
- **Lower bars**: More stable price movement expected
- **Annualized %**: Projected volatility over a full year

Volatility measures how much a stock's price fluctuates. High volatility = high risk but potentially high reward. Low volatility = more predictable, but potentially lower returns.
                        """, className="small mb-3", style={'backgroundColor': '#fff5f0', 'padding': '10px', 'borderRadius': '6px', 'color': '#000000'}),
                        dcc.Graph(id="mf-volatility-chart", config={'displayModeBar': False})
                    ])
                ], className="shadow-sm mb-3")
            ], md=6)
        ]),
        
        # Detailed Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="bi bi-table me-2"),
                            "Forecast Details"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="mf-details-table")
                    ])
                ], className="shadow-sm")
            ], md=12)
        ]),
        
        # Hidden stores
        dcc.Store(id="mf-forecast-store"),
        dcc.Store(id="mf-params-store")
        
    ], className="p-4")


def register_callbacks(app):
    """Register callbacks for Market Forecast tab"""
    
    @app.callback(
        [
            Output("mf-forecast-store", "data"),
            Output("mf-loading-output", "children"),
            Output("mf-summary-cards", "children"),
            Output("mf-returns-chart", "figure"),
            Output("mf-volatility-chart", "figure"),
            Output("mf-details-table", "children")
        ],
        [Input("mf-generate-btn", "n_clicks")],
        [
            State("mf-ticker-selector", "value"),
            State("mf-ticker-input", "value"),
            State("mf-horizon-selector", "value"),
            State("mf-confidence-selector", "value")
        ],
        prevent_initial_call=True
    )
    def generate_forecast(n_clicks, tickers, tickers_input, horizon, confidence):
        """Generate forecasts for selected tickers"""
        if not n_clicks:
            raise PreventUpdate

        # Prefer free-text input if provided
        if tickers_input and isinstance(tickers_input, str) and tickers_input.strip():
            tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]

        if not tickers:
            return (None, dbc.Alert("No tickers provided. Select or enter one or more tickers.", color="warning"), html.Div(), go.Figure(), go.Figure(), html.Div())
        
        try:
            # Ensure tickers is a list
            if isinstance(tickers, str):
                tickers = [tickers]
            
            logger.info(f"Generating forecasts for {len(tickers)} tickers: {tickers}")
            
            # Load market signals
            signals = load_market_signals()
            
            # Generate forecasts
            forecasts = []
            for ticker in tickers:
                try:
                    if FORECAST_ENGINE_AVAILABLE:
                        forecast = calculate_forecast(ticker, horizon, confidence, use_cached=True)
                    else:
                        # Mock forecast if engine unavailable
                        forecast = generate_mock_forecast(ticker, horizon, confidence, signals.get(ticker, {}))
                    
                    # Sanitize forecast structure and defaults
                    forecast = _sanitize_forecast(forecast)
                    if forecast:
                        forecasts.append(forecast)
                except Exception as e:
                    logger.error(f"Error forecasting {ticker}: {e}")
                    # Generate mock forecast as fallback
                    forecast = generate_mock_forecast(ticker, horizon, confidence, signals.get(ticker, {}))
                    forecast = _sanitize_forecast(forecast)
                    if forecast:
                        forecasts.append(forecast)
            
            if not forecasts:
                return (
                    None,
                    dbc.Alert("No forecasts generated. Check logs for errors.", color="warning"),
                    html.Div(),
                    go.Figure(),
                    go.Figure(),
                    html.Div()
                )
            
            # Create summary cards
            avg_return = np.mean([f['expected_return_horizon'] for f in forecasts])
            avg_volatility = np.mean([f['volatility'] for f in forecasts])
            avg_prob = np.mean([f['probability_positive'] for f in forecasts])
            
            summary_cards = dbc.Row([
                dbc.Col([
                    create_summary_card(
                        "Avg Expected Return",
                        f"{avg_return:+.2%}",
                        f"Over {horizon.replace('_', ' ')}",
                        "📈",
                        "success" if avg_return > 0 else "danger"
                    )
                ], md=3),
                dbc.Col([
                    create_summary_card(
                        "Avg Volatility",
                        f"{avg_volatility:.2%}",
                        "Annualized",
                        "📊",
                        "info"
                    )
                ], md=3),
                dbc.Col([
                    create_summary_card(
                        "Probability Positive",
                        f"{avg_prob:.1%}",
                        "Across all tickers",
                        "🎯",
                        "primary"
                    )
                ], md=3),
                dbc.Col([
                    create_summary_card(
                        "Tickers Analyzed",
                        str(len(forecasts)),
                        f"Out of {len(tickers)} selected",
                        "✅",
                        "success"
                    )
                ], md=3)
            ])
            
            # Create returns chart
            returns_fig = create_returns_chart(forecasts, confidence)
            
            # Create volatility chart
            volatility_fig = create_volatility_chart(forecasts)
            
            # Create details table
            details_table = create_details_table(forecasts)
            
            # Helpful debug message explaining metrics
            help_msg = (
                "✅ Generated {n} forecasts.\n".format(n=len(forecasts)) +
                "Avg Expected Return = average of horizon returns shown above.\n" +
                "Avg Volatility = annualized volatility used for CI.\n" +
                "Probability Positive = model-estimated chance the return > 0 over the horizon.\n" +
                "See details table for per-ticker values and CI bounds."
            )
            logger.info(f"Forecast generation complete for {len(forecasts)} tickers. Summary: avg_return={avg_return}, avg_vol={avg_volatility}")
            return (
                forecasts,
                dbc.Alert(help_msg, color="success", duration=8000),
                summary_cards,
                returns_fig,
                volatility_fig,
                details_table
            )
            
        except Exception as e:
            logger.error(f"Error in forecast generation: {e}", exc_info=True)
            return (
                None,
                dbc.Alert(f"Error generating forecasts: {str(e)}", color="danger"),
                html.Div(),
                go.Figure(),
                go.Figure(),
                html.Div()
            )


def generate_mock_forecast(ticker, horizon, confidence, signal_data):
    """Generate mock forecast when forecast engine unavailable"""
    horizon_days = HORIZONS.get(horizon, 30)
    
    # Use signal data if available
    momentum = signal_data.get('momentum', np.random.uniform(-0.5, 0.5))
    volatility = signal_data.get('volatility', np.random.uniform(0.15, 0.35))
    
    # Generate mock metrics
    expected_return_annual = momentum * 0.1 + np.random.normal(0.08, 0.05)
    expected_return_horizon = expected_return_annual * (horizon_days / 252)
    
    # Confidence intervals
    z_score = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}[confidence]
    std_horizon = volatility * np.sqrt(horizon_days / 252)
    
    return {
        'ticker': ticker,
        'horizon': horizon,
        'horizon_days': horizon_days,
        'expected_return': expected_return_annual,
        'expected_return_horizon': expected_return_horizon,
        'volatility': volatility,
        'probability_positive': 0.5 + (expected_return_horizon / (2 * std_horizon)) if std_horizon > 0 else 0.5,
        'confidence_interval': {
            'lower': expected_return_horizon - z_score * std_horizon,
            'upper': expected_return_horizon + z_score * std_horizon,
            'confidence': confidence
        },
        'current_price': 100.0,
        'forecast_price_mean': 100.0 * (1 + expected_return_horizon),
        'forecast_price_lower': 100.0 * (1 + expected_return_horizon - z_score * std_horizon),
        'forecast_price_upper': 100.0 * (1 + expected_return_horizon + z_score * std_horizon),
        'generated_at': datetime.now().isoformat()
    }


def _sanitize_forecast(f):
    """Ensure forecast dict has expected keys and defaults"""
    if not isinstance(f, dict):
        return None
    out = {}
    out['ticker'] = str(f.get('ticker') or f.get('symbol') or '').upper()
    if not out['ticker']:
        return None
    out['horizon'] = f.get('horizon') or '1_month'
    out['horizon_days'] = int(f.get('horizon_days') or HORIZONS.get(out['horizon'], 30))
    out['expected_return'] = float(_safe_number(f.get('expected_return'), default=0.0))
    out['expected_return_horizon'] = float(_safe_number(f.get('expected_return_horizon'), default=0.0))
    out['volatility'] = float(_safe_number(f.get('volatility'), default=0.25))
    out['probability_positive'] = float(_safe_number(f.get('probability_positive'), default=0.5))
    ci = f.get('confidence_interval') or {}
    out['confidence_interval'] = {
        'lower': float(_safe_number(ci.get('lower'), default=out['expected_return_horizon'] - 0.01)),
        'upper': float(_safe_number(ci.get('upper'), default=out['expected_return_horizon'] + 0.01)),
        'confidence': float(_safe_number(ci.get('confidence'), default=0.95))
    }
    out['current_price'] = float(_safe_number(f.get('current_price'), default=100.0))
    out['forecast_price_mean'] = float(_safe_number(f.get('forecast_price_mean'), default=out['current_price'] * (1 + out['expected_return_horizon'])))
    out['forecast_price_lower'] = float(_safe_number(f.get('forecast_price_lower'), default=out['forecast_price_mean'] * 0.95))
    out['forecast_price_upper'] = float(_safe_number(f.get('forecast_price_upper'), default=out['forecast_price_mean'] * 1.05))
    out['generated_at'] = f.get('generated_at') or datetime.now().isoformat()
    return out


def create_returns_chart(forecasts, confidence):
    """Create expected returns chart with confidence intervals"""
    try:
        df = pd.DataFrame(forecasts).sort_values('expected_return_horizon', ascending=True)
        if df.empty:
            return go.Figure()
        fig = go.Figure()

        # Add confidence interval bars
        # Compute arrays safely
        errs_up = []
        errs_down = []
        for idx, row in df.iterrows():
            ci = row.get('confidence_interval') or {}
            lower = ci.get('lower', row.get('expected_return_horizon', 0) - 0.01)
            upper = ci.get('upper', row.get('expected_return_horizon', 0) + 0.01)
            er = row.get('expected_return_horizon', 0)
            errs_up.append(upper - er)
            errs_down.append(er - lower)

        fig.add_trace(go.Bar(
            x=df['ticker'],
            y=df['expected_return_horizon'],
            name='Expected Return',
            marker_color=['#10b981' if x > 0 else '#ef4444' for x in df['expected_return_horizon']],
            error_y=dict(
                type='data',
                symmetric=False,
                array=errs_up,
                arrayminus=errs_down,
                color='rgba(100, 100, 100, 0.3)'
            )
        ))
    except Exception as e:
        logger.error(f"Error building returns chart: {e}")
        return go.Figure()
    
    fig.update_layout(
        title=f"{int(confidence*100)}% Confidence Intervals",
        xaxis_title="Ticker",
        yaxis_title="Expected Return (%)",
        yaxis_tickformat='.1%',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=10),
        margin=dict(l=40, r=20, t=40, b=40),
        height=350
    )
    
    return fig


def create_volatility_chart(forecasts):
    """Create volatility comparison chart"""
    try:
        df = pd.DataFrame(forecasts).sort_values('volatility', ascending=True)
        if df.empty:
            return go.Figure()
        fig = go.Figure()
        vol_vals = df['volatility'].fillna(0.0).tolist()
        fig.add_trace(go.Bar(
            x=df['ticker'],
            y=vol_vals,
            name='Annualized Volatility',
            marker_color='#3b82f6',
            text=[f"{v:.1%}" for v in vol_vals],
            textposition='outside'
        ))
    except Exception as e:
        logger.error(f"Error building volatility chart: {e}")
        return go.Figure()
    
    fig.update_layout(
        title="Annualized Volatility by Ticker",
        xaxis_title="Ticker",
        yaxis_title="Volatility (%)",
        yaxis_tickformat='.0%',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=10),
        margin=dict(l=40, r=20, t=40, b=40),
        height=350
    )
    
    return fig


def create_details_table(forecasts):
    """Create detailed forecast table"""
    try:
        df = pd.DataFrame(forecasts)
        if df.empty:
            return html.Div("No forecast details to display.")

        # Ensure nested keys are present
        df['expected_return_horizon'] = df.get('expected_return_horizon', pd.Series([0]*len(df))).apply(lambda x: _safe_number(x, 0.0))
        df['expected_return'] = df.get('expected_return', pd.Series([0]*len(df))).apply(lambda x: _safe_number(x, 0.0))
        df['volatility'] = df.get('volatility', pd.Series([0]*len(df))).apply(lambda x: _safe_number(x, 0.0))
        df['probability_positive'] = df.get('probability_positive', pd.Series([0.5]*len(df))).apply(lambda x: _safe_number(x, 0.5))

        df['Expected Return (Horizon)'] = df['expected_return_horizon'].apply(lambda x: f"{x:+.2%}")
        df['Expected Return (Annual)'] = df['expected_return'].apply(lambda x: f"{x:+.2%}")
        df['Volatility'] = df['volatility'].apply(lambda x: f"{x:.2%}")
        df['Prob. Positive'] = df['probability_positive'].apply(lambda x: f"{x:.1%}")

        def _ci_val(row, key, default=0.0):
            try:
                return f"{_safe_number(row.get('confidence_interval', {}).get(key), default):+.2%}"
            except Exception:
                return f"{default:+.2%}"

        df['CI Lower'] = df.apply(lambda row: _ci_val(row, 'lower', default=row.get('expected_return_horizon', 0)-0.01), axis=1)
        df['CI Upper'] = df.apply(lambda row: _ci_val(row, 'upper', default=row.get('expected_return_horizon', 0)+0.01), axis=1)

        # Select and rename columns
        table_df = df[['ticker', 'Expected Return (Horizon)', 'Expected Return (Annual)', 
                        'Volatility', 'Prob. Positive', 'CI Lower', 'CI Upper']].copy()
        table_df.columns = ['Ticker', 'Return (Horizon)', 'Return (Annual)', 
                            'Volatility', 'Prob+', 'CI Lower', 'CI Upper']

        # Create simple HTML table for robustness
        return dbc.Table.from_dataframe(
            table_df,
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            size='sm',
            className='text-center'
        )
    except Exception as e:
        logger.error(f"Error creating details table: {e}")
        # Fallback simple representation
        try:
            rows = [html.Tr([html.Td(f.get('ticker')), html.Td(str(f.get('expected_return_horizon')))]) for f in forecasts]
            return html.Table([html.Thead(html.Tr([html.Th('Ticker'), html.Th('Return (Horizon)')])), html.Tbody(rows)])
        except Exception:
            return html.Div('Unable to render forecast details.')


# Export layout function for index.py
__all__ = ['layout', 'register_callbacks']
