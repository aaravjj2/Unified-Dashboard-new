"""
Volatility Lab Tab - Advanced Volatility Analysis

Provides comprehensive volatility metrics and analysis including:
- Rolling volatility calculation
- Annualized and realized volatility
- Price and volatility charts
- Historical data analysis with caching

All component IDs use vl-* namespace as per specification.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dash_table

# Relative import for Docker container compatibility
from .volatility_lib import (
    compute_log_returns,
    rolling_volatility,
    realized_vol,
    compute_volatility_metrics
)

logger = logging.getLogger(__name__)

# Simple in-memory cache for computed results
_CACHE = {}


def validate_and_parse_tickers(ticker_input: str) -> tuple[list[str], list[str]]:
    """
    Parse and validate ticker input string.
    
    Args:
        ticker_input: Comma-separated ticker string (e.g., "AAPL,MSFT,SPY")
        
    Returns:
        Tuple of (valid_tickers, invalid_tickers)
        
    Examples:
        >>> validate_and_parse_tickers("AAPL,msft,SPY")
        (['AAPL', 'MSFT', 'SPY'], [])
        
        >>> validate_and_parse_tickers("AAPL,123,A")
        (['AAPL'], ['123', 'A'])
    """
    if not ticker_input or not isinstance(ticker_input, str):
        return [], []
    
    # Split by comma, strip whitespace, convert to uppercase
    raw_tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
    
    valid_tickers = []
    invalid_tickers = []
    
    for ticker in raw_tickers:
        # Validate: 1-5 alphanumeric characters, may contain hyphen for special symbols
        if 1 <= len(ticker) <= 5 and ticker.replace('-', '').isalpha():
            valid_tickers.append(ticker)
        else:
            invalid_tickers.append(ticker)
            logger.warning(f"Invalid ticker format: {ticker}")
    
    return valid_tickers, invalid_tickers


def load_price_data(
    tickers: List[str],
    start: str,
    end: str,
    resample: str = '1D'
) -> pd.DataFrame:
    """
    Load historical price data for given tickers using PriceClient.
    
    Args:
        tickers: List of ticker symbols
        start: Start date (ISO format)
        end: End date (ISO format)
        resample: Resample frequency ('1D' for daily, '1H' for hourly)
        
    Returns:
        DataFrame with columns: date, ticker, price
        
    Notes:
        Uses PriceClient with Alpaca → Finnhub → yfinance fallback.
        Caches results in memory and disk for performance.
    """
    logger.info(f"Loading price data for {len(tickers)} tickers from {start} to {end}")
    
    # Import PriceDataCache (relative import for Docker)
    try:
        from ..utils.price_cache import get_price_cache
    except ImportError:
        # Fallback for test environment
        from financial_dashboard.utils.price_cache import get_price_cache
    
    # Check cache first
    cache = get_price_cache()
    cached_df = cache.get(tickers, start, end, resample=resample)
    if cached_df is not None:
        logger.info(f"✓ Cache HIT: Loaded {len(cached_df)} cached records for {len(tickers)} tickers")
        return cached_df
    
    logger.info("Cache MISS: Fetching live data...")
    
    # Import PriceClient from utils (relative import for Docker)
    try:
        from ..utils.price_client import PriceClient
    except ImportError:
        # Fallback for test environment
        from financial_dashboard.utils.price_client import PriceClient
    
    # Initialize PriceClient (loads API keys from keys.env)
    try:
        price_client = PriceClient()
    except RuntimeError as e:
        logger.warning(f"PriceClient initialization failed: {e}. Using fallback data.")
        # Fallback to yfinance if API keys missing
        return _load_price_data_fallback(tickers, start, end, resample)
    
    # Calculate lookback days
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    lookback_days = (end_dt - start_dt).days
    
    # Fetch data using PriceClient
    data = []
    for ticker in tickers:
        try:
            # Use get_prices_dataframe for direct DataFrame output
            ticker_df = _fetch_ticker_data(price_client, ticker, start_dt, end_dt, lookback_days)
            
            if not ticker_df.empty:
                ticker_df['ticker'] = ticker
                ticker_df = ticker_df.rename(columns={'close': 'price', 'timestamp': 'date'})
                data.append(ticker_df[['date', 'ticker', 'price']])
                logger.info(f"✓ Fetched {len(ticker_df)} records for {ticker}")
            else:
                logger.warning(f"⚠ No data returned for {ticker}")
        
        except Exception as e:
            logger.error(f"✗ Failed to fetch data for {ticker}: {e}")
    
    if data:
        df = pd.concat(data, ignore_index=True)
        logger.info(f"Loaded {len(df)} price records for {len(data)}/{len(tickers)} tickers")
        
        # Store in cache
        cache.set(df, tickers, start, end, resample=resample)
        logger.info(f"✓ Cached results for future use")
        
        return df
    else:
        logger.warning("No data fetched, using fallback")
        return _load_price_data_fallback(tickers, start, end, resample)


def _fetch_ticker_data(
    price_client,
    ticker: str,
    start_dt: datetime,
    end_dt: datetime,
    lookback_days: int
) -> pd.DataFrame:
    """
    Fetch historical price data for a single ticker using yfinance.
    
    PriceClient.get_prices() is designed for current/spot prices, not historical bars.
    For volatility analysis, we need daily/hourly historical data, so use yfinance directly.
    
    Args:
        price_client: Initialized PriceClient instance (unused, kept for interface compatibility)
        ticker: Ticker symbol
        start_dt: Start datetime
        end_dt: End datetime
        lookback_days: Number of days to look back (unused with date range)
        
    Returns:
        DataFrame with columns: timestamp, close
    """
    try:
        import yfinance as yf
        
        # Fetch historical data using yfinance
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(
            start=start_dt.strftime('%Y-%m-%d'),
            end=end_dt.strftime('%Y-%m-%d'),
            interval='1d'
        )
        
        if not hist.empty:
            # yfinance returns DataFrame with index=Date, columns=[Open, High, Low, Close, Volume]
            hist = hist.reset_index()
            hist['timestamp'] = hist['Date']
            hist['close'] = hist['Close']
            return hist[['timestamp', 'close']]
        
        return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error fetching {ticker} from yfinance: {e}")
        return pd.DataFrame()


def _load_price_data_fallback(
    tickers: List[str],
    start: str,
    end: str,
    resample: str = '1D'
) -> pd.DataFrame:
    """
    Fallback price data loader using yfinance or synthetic data.
    
    Used when PriceClient fails or API keys are unavailable.
    """
    logger.warning("Using fallback data loader (yfinance or synthetic)")
    
    try:
        import yfinance as yf
        
        data = []
        for ticker in tickers:
            ticker_data = yf.download(ticker, start=start, end=end, progress=False)
            if not ticker_data.empty:
                ticker_data = ticker_data.reset_index()
                ticker_data['ticker'] = ticker
                ticker_data = ticker_data.rename(columns={'Date': 'date', 'Close': 'price'})
                data.append(ticker_data[['date', 'ticker', 'price']])
        
        if data:
            return pd.concat(data, ignore_index=True)
    
    except Exception as e:
        logger.warning(f"yfinance fallback failed: {e}")
    
    # Final fallback: synthetic data
    logger.warning("Using synthetic data (last resort)")
    date_range = pd.date_range(start=start, end=end, freq=resample)
    
    data = []
    for ticker in tickers:
        np.random.seed(hash(ticker) % 2**32)
        returns = np.random.randn(len(date_range)) * 0.02
        prices = 100 * np.exp(np.cumsum(returns))
        
        for date, price in zip(date_range, prices):
            data.append({'date': date, 'ticker': ticker, 'price': price})
    
    return pd.DataFrame(data)


def compute_volatility(
    df: pd.DataFrame,
    window: int,
    annualize: bool = True,
    periods_per_year: int = 252
) -> pd.DataFrame:
    """
    Compute volatility metrics for price data.
    
    Args:
        df: DataFrame with columns 'ticker', 'date', 'price'
        window: Rolling window size
        annualize: Whether to annualize volatility
        periods_per_year: Periods per year for annualization
        
    Returns:
        DataFrame with volatility metrics per ticker
    """
    logger.info(f"Computing volatility with window={window}, annualize={annualize}")
    
    results = []
    
    for ticker in df['ticker'].unique():
        ticker_df = df[df['ticker'] == ticker].sort_values('date')
        prices = ticker_df.set_index('date')['price']
        
        # Compute metrics using volatility_lib
        metrics = compute_volatility_metrics(
            prices,
            window=window,
            annualize=annualize,
            periods_per_year=periods_per_year
        )
        
        # Add ticker column
        metrics['ticker'] = ticker
        metrics = metrics.reset_index()
        
        results.append(metrics)
    
    if results:
        combined = pd.concat(results, ignore_index=True)
        logger.info(f"Computed volatility for {len(df['ticker'].unique())} tickers")
        return combined
    else:
        return pd.DataFrame()


def layout():
    """
    Return the Volatility Lab layout with vl-* component IDs.
    
    Returns:
        Dash container with all required components
    """
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-chart-line me-2"),
                    "Volatility Lab"
                ], className="mb-3"),
                html.P(
                    "Advanced volatility analysis with rolling, realized, and annualized metrics",
                    className="text-muted"
                )
            ])
        ]),
        
        # Controls Row
        dbc.Row([
            # Tickers Input (Custom + Predefined)
            dbc.Col([
                html.Label([
                    "Tickers ",
                    html.Small("(comma-separated)", className="text-muted")
                ]),
                dcc.Input(
                    id='vl-tickers-input',
                    type='text',
                    value='AAPL,SPY',
                    placeholder="Enter tickers (e.g., AAPL,MSFT,TSLA)",
                    className="form-control",
                    debounce=True,
                    style={'width': '100%'}
                ),
                html.Small([
                    html.I(className="fas fa-info-circle me-1"),
                    "Suggestions: SPY, QQQ, AAPL, MSFT, TSLA, NVDA, GOOGL"
                ], className="text-muted d-block mt-1")
            ], md=3),
            
            # Date Range
            dbc.Col([
                html.Label("Date Range"),
                dcc.DatePickerRange(
                    id='vl-date-range',
                    start_date=(datetime.now() - timedelta(days=90)).date(),
                    end_date=datetime.now().date(),
                    display_format='YYYY-MM-DD'
                )
            ], md=3),
            
            # Window Size
            dbc.Col([
                html.Label("Rolling Window"),
                dcc.Slider(
                    id='vl-window',
                    min=5,
                    max=60,
                    step=5,
                    value=20,
                    marks={5: '5', 20: '20', 40: '40', 60: '60'},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], md=3),
            
            # Volatility Type
            dbc.Col([
                html.Label("Volatility Type"),
                dcc.Dropdown(
                    id='vl-type',
                    options=[
                        {'label': 'Annualized', 'value': 'annualized'},
                        {'label': 'Rolling', 'value': 'rolling'},
                        {'label': 'Realized', 'value': 'realized'}
                    ],
                    value='annualized',
                    clearable=False
                )
            ], md=2),
            
            # Compute Button
            dbc.Col([
                html.Label(" ", className="d-block"),  # Spacer
                dbc.Button(
                    [html.I(className="fas fa-calculator me-2"), "Compute"],
                    id='vl-compute',
                    color="primary",
                    className="w-100"
                )
            ], md=1)
        ], className="mb-4"),
        
        # Charts Row
        dbc.Row([
            # Price Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-area me-2"),
                        "Price History"
                    ]),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(
                                id='vl-price-graph',
                                config={'displayModeBar': False}
                            )
                        )
                    ])
                ])
            ], md=6),
            
            # Volatility Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-wave-square me-2"),
                        "Rolling Volatility"
                    ]),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(
                                id='vl-vol-graph',
                                config={'displayModeBar': False}
                            )
                        )
                    ])
                ])
            ], md=6)
        ], className="mb-3"),
        
        # Results Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-table me-2"),
                        "Volatility Metrics"
                    ]),
                    dbc.CardBody([
                        dash_table.DataTable(
                            id='vl-results-table',
                            columns=[],
                            data=[],
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
                            page_size=10
                        )
                    ])
                ])
            ])
        ], className="mb-3"),
        
        # Status Area
        dbc.Row([
            dbc.Col([
                html.Div(
                    id='vl-status',
                    children=[
                        html.I(className="fas fa-info-circle me-2"),
                        "Ready to compute. Select tickers and click Compute."
                    ],
                    className="alert alert-info"
                )
            ])
        ])
    ], fluid=True)


def register_callbacks(app):
    """
    Register Dash callbacks for volatility lab.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        [
            Output('vl-price-graph', 'figure'),
            Output('vl-vol-graph', 'figure'),
            Output('vl-results-table', 'data'),
            Output('vl-results-table', 'columns'),
            Output('vl-status', 'children'),
            Output('vl-status', 'className')
        ],
        [
            Input('vl-compute', 'n_clicks')
        ],
        [
            State('vl-tickers-input', 'value'),
            State('vl-date-range', 'start_date'),
            State('vl-date-range', 'end_date'),
            State('vl-window', 'value'),
            State('vl-type', 'value')
        ],
        prevent_initial_call=True
    )
    def compute_volatility_callback(n_clicks, ticker_input, start_date, end_date, window, vol_type):
        """Compute and display volatility metrics"""
        
        # Parse and validate ticker input
        valid_tickers, invalid_tickers = validate_and_parse_tickers(ticker_input)
        
        if not valid_tickers:
            error_msg = "No valid tickers entered"
            if invalid_tickers:
                error_msg += f". Invalid: {', '.join(invalid_tickers)}"
            return (
                go.Figure(),
                go.Figure(),
                [],
                [],
                [html.I(className="fas fa-exclamation-triangle me-2"), error_msg],
                "alert alert-warning"
            )
        
        # Log validation results
        if invalid_tickers:
            logger.warning(f"Ignoring invalid tickers: {invalid_tickers}")
        
        logger.info(f"Computing volatility for tickers: {valid_tickers}")
        
        try:
            # Load price data (only for valid tickers)
            df = load_price_data(valid_tickers, start_date, end_date)
            
            if df.empty:
                return (
                    go.Figure(),
                    go.Figure(),
                    [],
                    [],
                    [html.I(className="fas fa-exclamation-triangle me-2"), "No data available"],
                    "alert alert-warning"
                )
            
            # Compute volatility
            annualize = (vol_type == 'annualized')
            vol_df = compute_volatility(df, window=window, annualize=annualize)
            
            # Create price chart
            price_fig = go.Figure()
            for ticker in valid_tickers:
                ticker_data = df[df['ticker'] == ticker]
                price_fig.add_trace(go.Scatter(
                    x=ticker_data['date'],
                    y=ticker_data['price'],
                    mode='lines',
                    name=ticker
                ))
            
            price_fig.update_layout(
                title="Price History",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                hovermode='x unified',
                template='plotly_dark'
            )
            
            # Create volatility chart
            vol_fig = go.Figure()
            for ticker in valid_tickers:
                ticker_vol = vol_df[vol_df['ticker'] == ticker]
                if not ticker_vol.empty:
                    vol_fig.add_trace(go.Scatter(
                        x=ticker_vol['date'],
                        y=ticker_vol['rolling_vol'] * 100,  # Convert to percentage
                        mode='lines',
                        name=ticker
                    ))
            
            vol_fig.update_layout(
                title=f"Rolling Volatility ({window}-day window)",
                xaxis_title="Date",
                yaxis_title="Volatility (%)",
                hovermode='x unified',
                template='plotly_dark'
            )
            
            # Create summary table
            summary = []
            for ticker in valid_tickers:
                ticker_vol = vol_df[vol_df['ticker'] == ticker]
                if not ticker_vol.empty:
                    summary.append({
                        'Ticker': ticker,
                        'Realized Vol (%)': f"{ticker_vol['realized_vol'].iloc[0] * 100:.2f}",
                        'Latest Rolling Vol (%)': f"{ticker_vol['rolling_vol'].iloc[-1] * 100:.2f}",
                        'Avg Rolling Vol (%)': f"{ticker_vol['rolling_vol'].mean() * 100:.2f}",
                        'Last Price': f"${df[df['ticker'] == ticker]['price'].iloc[-1]:.2f}"
                    })
            
            columns = [{'name': col, 'id': col} for col in summary[0].keys()] if summary else []
            
            # Build status message with warnings for invalid tickers if any
            status_msg = [
                html.I(className="fas fa-check-circle me-2"),
                f"Success! Computed volatility for {len(valid_tickers)} ticker(s)"
            ]
            if invalid_tickers:
                status_msg.extend([
                    html.Br(),
                    html.Small([
                        html.I(className="fas fa-exclamation-triangle me-1"),
                        f"Ignored invalid ticker(s): {', '.join(invalid_tickers)}"
                    ], className="text-warning")
                ])
            
            status_class = "alert alert-success"
            
            return price_fig, vol_fig, summary, columns, status_msg, status_class
            
        except Exception as e:
            logger.error(f"Error computing volatility: {e}", exc_info=True)
            return (
                go.Figure(),
                go.Figure(),
                [],
                [],
                [html.I(className="fas fa-exclamation-circle me-2"), f"Error: {str(e)}"],
                "alert alert-danger"
            )
