"""
Portfolio Analytics Tab - Advanced Analytics with Caching and Monte Carlo
Part of refactored Portfolio Tracker module

Features:
- Risk metrics (VaR, CVaR, Sharpe, Beta)
- Equity curve vs SPY benchmark
- Correlation heatmap
- Monte Carlo simulation (1,000 paths)
- Caching layer with 5-minute TTL
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
# Shared UI components for improvements
try:
    from financial_dashboard.components.shared_ui import (
        create_tab_toolbar, create_metric_card, create_summary_stats_row,
        create_loading_skeleton, create_date_range_filter, create_sector_filter,
        create_ticker_filter, create_last_updated_timestamp, create_notification_toast,
        create_refresh_button, create_export_button, create_historical_toggle,
        create_chart_container, create_empty_state
    )
    SHARED_UI_AVAILABLE = True
except ImportError:
    SHARED_UI_AVAILABLE = False

import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)

# Initialize caching
try:
    from diskcache import Cache
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cache', 'portfolio')
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = Cache(CACHE_DIR)
    CACHE_TTL = 300  # 5 minutes
    CACHING_ENABLED = True
    logger.info(f"Portfolio analytics caching enabled: {CACHE_DIR}")
except ImportError:
    logger.warning("diskcache not available - caching disabled")
    cache = None
    CACHING_ENABLED = False


def get_alpaca_client():
    """Get Alpaca trading client from environment."""
    try:
        from alpaca.trading.client import TradingClient
        
        key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
        secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
        if not key or not secret:
            return None
        
        paper = True
        return TradingClient(key, secret, paper=paper)
    except Exception as e:
        logger.warning(f"Alpaca not available: {e}")
        return None


def cached_historical_download(ticker, start_date, end_date):
    """Download stock data with caching using Alpaca/Finnhub."""
    cache_key = f"hist_{ticker}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    
    if CACHING_ENABLED:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT for {ticker}")
            return cached_data
    
    # Cache miss - download data using price_fetch
    try:
        from utils.price_fetch import fetch_historical_data
        
        data = fetch_historical_data([ticker], start_date, end_date, use_alpaca=True)
        
        # Convert to Series if single ticker (for compatibility)
        if not data.empty and ticker in data.columns:
            result = data[ticker].to_frame(name='Close')
            result['Adj Close'] = result['Close']  # Compatibility with existing code
        else:
            result = pd.DataFrame()
        
        if CACHING_ENABLED and not result.empty:
            cache.set(cache_key, result, expire=CACHE_TTL)
            logger.debug(f"Cached historical data for {ticker}")
        
        return result
    except Exception as e:
        logger.error(f"Error downloading {ticker}: {e}")
        return pd.DataFrame()


def cached_alpaca_portfolio_history(client, period_days):
    """Get Alpaca portfolio history with caching."""
    if not client:
        return None
    
    cache_key = f"alpaca_history_{period_days}"
    
    if CACHING_ENABLED:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT for Alpaca portfolio history")
            return cached_data
    
    # Cache miss - fetch from API
    try:
        from alpaca.data.timeframe import TimeFrame
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        
        request = GetPortfolioHistoryRequest(
            period=f"{period_days}D",
            timeframe=TimeFrame.Day
        )
        history = client.get_portfolio_history(request)
        
        if CACHING_ENABLED:
            cache.set(cache_key, history, expire=CACHE_TTL)
            logger.debug(f"Cached Alpaca portfolio history")
        
        return history
    except Exception as e:
        logger.error(f"Error fetching Alpaca history: {e}")
        return None


def layout():
    """Build analytics tab layout."""
    return dbc.Container([
        # === IMPROVEMENTS: Toolbar with filters ===
        html.Div([
            create_tab_toolbar(
                tab_name="portfolio_analytics",
                filters=[create_date_range_filter('analytics-date')] if SHARED_UI_AVAILABLE else [],
                show_refresh=True,
                show_export=True,
                show_help=True,
                help_text="Advanced portfolio analytics and risk metrics."
            ) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === IMPROVEMENTS: Summary Statistics ===
        html.Div([
            create_summary_stats_row([
                {'title': 'Sharpe Ratio', 'value': '--', 'icon': 'fa-chart-bar', 'color': 'primary'},
            {'title': 'Max Drawdown', 'value': '--%', 'icon': 'fa-arrow-down', 'color': 'danger'},
            {'title': 'Beta', 'value': '--', 'icon': 'fa-balance-scale', 'color': 'info'},
            {'title': 'Alpha', 'value': '--%', 'icon': 'fa-star', 'color': 'warning'}
            ]) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === IMPROVEMENTS: Notification Toast ===
        html.Div([
            create_notification_toast("portfolio_analytics-toast", "Portfolio Analytics Update") if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        html.H5("Portfolio Analytics", className="mt-3 mb-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Time Period:"),
                dcc.Dropdown(
                    id='analytics-period',
                    options=[
                        {'label': '1 Day', 'value': '1d'},
                        {'label': '1 Week', 'value': '1w'},
                        {'label': '1 Month', 'value': '1m'},
                        {'label': '3 Months', 'value': '3m'},
                        {'label': 'YTD', 'value': 'ytd'},
                        {'label': '1 Year', 'value': '1y'}
                    ],
                    value='1m'
                )
            ], width=4),
            dbc.Col([
                dbc.Button(
                    "Run Monte Carlo Simulation",
                    id='monte-carlo-btn',
                    color='primary',
                    className="mt-4"
                )
            ], width=4)
        ], className="mb-3"),
        
        # Risk Metrics Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Value at Risk (VaR 95%)", className="text-muted"),
                        html.H4(id='portfolio-var', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("CVaR (Expected Shortfall)", className="text-muted"),
                        html.H4(id='portfolio-cvar', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Sharpe Ratio", className="text-muted"),
                        html.H4(id='portfolio-sharpe', children="0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Beta to SPY", className="text-muted"),
                        html.H4(id='portfolio-beta', children="1.00")
                    ])
                ])
            ], width=3)
        ], className="mb-4"),
        
        dcc.Loading(
            id="analytics-loading",
            type="default",
            children=html.Div(id='portfolio-analytics-content')
        ),
        
        # Monte Carlo results
        dcc.Loading(
            id="monte-carlo-loading",
            type="default",
            children=html.Div(id='monte-carlo-results', className="mt-4")
        )
    ], fluid=True)


def register_callbacks(app):
    """Register callbacks for analytics tab."""
    
    @app.callback(
        [Output('portfolio-analytics-content', 'children'),
         Output('portfolio-var', 'children'),
         Output('portfolio-cvar', 'children'),
         Output('portfolio-sharpe', 'children'),
         Output('portfolio-beta', 'children')],
        [Input('analytics-period', 'value'),
         Input('portfolio-data-store', 'data'),
         Input('portfolio-tracker-subtabs', 'active_tab')]  # ADD: Trigger when Analytics tab is clicked
    )
    def update_analytics(period, portfolio_data, active_tab):
        """Update portfolio analytics with risk metrics, correlation heatmap, and equity curve.
        FIX: Uses database snapshot history for true portfolio equity curve.
        Uses caching to improve performance and avoid rate limiting.
        
        PHASE 0 FIX: Auto-calculate when Analytics subtab is activated.
        """
        # Only calculate when on Analytics tab (avoid unnecessary computation)
        if active_tab != 'analytics':
            raise PreventUpdate
        if not portfolio_data or not portfolio_data.get('positions'):
            empty_content = html.P("No data available for analytics.", className="text-muted")
            return empty_content, "$0.00", "$0.00", "0.00", "1.00"
        
        positions = portfolio_data['positions']
        df = pd.DataFrame(positions)
        
        # Calculate period days
        period_days = {'1d': 1, '1w': 7, '1m': 30, '3m': 90, 'ytd': 252, '1y': 365}.get(period, 30)
        
        # Fetch historical data for portfolio positions and SPY using CACHED function
        try:
            tickers = df['symbol'].tolist()
            weights = (df['market_value'] / df['market_value'].sum()).values
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days + 10)
            
            # Download data with caching
            portfolio_hist = {}
            for ticker in tickers:
                try:
                    data = cached_historical_download(ticker, start_date, end_date)
                    if not data.empty and 'Close' in data.columns:
                        close_data = data['Close']
                        # Ensure we have a Series, not a scalar
                        if isinstance(close_data, pd.Series) and len(close_data) > 0:
                            portfolio_hist[ticker] = close_data
                except Exception as e:
                    logger.warning(f"Failed to download {ticker}: {e}")
                    pass
            
            # Download SPY for benchmark with caching
            spy_data = cached_historical_download('SPY', start_date, end_date)
            spy_returns = spy_data['Close'].pct_change().dropna() if not spy_data.empty else pd.Series()
            
            # Calculate portfolio equity curve
            if portfolio_hist and len(portfolio_hist) > 0:
                # Ensure all values are Series before creating DataFrame
                valid_hist = {k: v for k, v in portfolio_hist.items() if isinstance(v, pd.Series) and len(v) > 0}
                
                if not valid_hist:
                    raise ValueError("No valid historical data available for portfolio positions")
                
                # Align all series
                portfolio_df = pd.DataFrame(valid_hist).ffill().dropna()
                
                if not portfolio_df.empty:
                    # Calculate portfolio returns
                    returns_df = portfolio_df.pct_change().dropna()
                    
                    # CRITICAL FIX: Filter weights to match only successfully downloaded tickers
                    # Create a mapping of ticker -> original weight
                    ticker_weight_map = dict(zip(tickers, weights))
                    
                    # Get weights for only the tickers that successfully downloaded (in same order as DataFrame columns)
                    valid_weights = np.array([ticker_weight_map[ticker] for ticker in portfolio_df.columns if ticker in ticker_weight_map])
                    
                    # Renormalize weights so they sum to 1.0
                    if valid_weights.sum() > 0:
                        valid_weights = valid_weights / valid_weights.sum()
                    else:
                        logger.warning("All valid weights sum to zero - using equal weights")
                        valid_weights = np.ones(len(portfolio_df.columns)) / len(portfolio_df.columns)
                    
                    # Weight returns
                    portfolio_returns = (returns_df * valid_weights).sum(axis=1)
                    
                    # Calculate metrics
                    portfolio_value = portfolio_data['account']['portfolio_value']
                    
                    # VaR (95% confidence)
                    var_95 = np.percentile(portfolio_returns, 5) * portfolio_value
                    
                    # CVaR (Expected Shortfall - average of worst 5%)
                    worst_returns = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)]
                    cvar = worst_returns.mean() * portfolio_value if len(worst_returns) > 0 else var_95
                    
                    # Sharpe Ratio (assuming 0% risk-free rate)
                    sharpe = (portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252)) if portfolio_returns.std() > 0 else 0.0
                    
                    # Beta to SPY
                    if len(spy_returns) > 0 and len(portfolio_returns) > 0:
                        aligned = pd.DataFrame({'portfolio': portfolio_returns, 'spy': spy_returns}).dropna()
                        if len(aligned) > 10:
                            covariance = aligned['portfolio'].cov(aligned['spy'])
                            spy_variance = aligned['spy'].var()
                            beta = covariance / spy_variance if spy_variance > 0 else 1.0
                        else:
                            beta = 1.0
                    else:
                        beta = 1.0
                    
                    # FIX: Build equity curve using database snapshot history for true portfolio values
                    fig_equity = go.Figure()
                    
                    # Try to get actual portfolio history from database
                    try:
                        from utils.db_utils import get_snapshot_history
                        snapshot_history = get_snapshot_history(days=period_days)
                        
                        if snapshot_history and len(snapshot_history['timestamps']) > 0:
                            # Use actual portfolio values from database
                            fig_equity.add_trace(go.Scatter(
                                x=snapshot_history['timestamps'],
                                y=snapshot_history['values'],
                                mode='lines',
                                name='Portfolio (Actual)',
                                line=dict(color='#10b981', width=2)
                            ))
                            logger.info(f"Using database history: {len(snapshot_history['timestamps'])} snapshots")
                        else:
                            # Fallback: use calculated returns
                            if len(portfolio_returns) > 0:
                                cumulative_returns = (1 + portfolio_returns).cumprod()
                                portfolio_equity = cumulative_returns * portfolio_data['account']['portfolio_value'] / cumulative_returns.iloc[-1]
                                fig_equity.add_trace(go.Scatter(
                                    x=portfolio_equity.index,
                                    y=portfolio_equity.values,
                                    mode='lines',
                                    name='Portfolio (Calculated)',
                                    line=dict(color='#10b981', width=2)
                                ))
                    except Exception as e:
                        logger.warning(f"Could not load database history, using calculated: {e}")
                        if len(portfolio_returns) > 0:
                            cumulative_returns = (1 + portfolio_returns).cumprod()
                            portfolio_equity = cumulative_returns * portfolio_data['account']['portfolio_value'] / cumulative_returns.iloc[-1]
                            fig_equity.add_trace(go.Scatter(
                                x=portfolio_equity.index,
                                y=portfolio_equity.values,
                                mode='lines',
                                name='Portfolio (Calculated)',
                                line=dict(color='#10b981', width=2)
                            ))
                    
                    # Add SPY benchmark
                    if not spy_returns.empty and len(spy_returns) > 0:
                        try:
                            # Align SPY returns with portfolio returns
                            aligned_spy = spy_returns[-len(portfolio_returns):]
                            if len(aligned_spy) > 0:
                                spy_equity = (1 + aligned_spy).cumprod() * 100000
                                fig_equity.add_trace(go.Scatter(
                                    x=spy_equity.index,
                                    y=spy_equity.values,
                                    mode='lines',
                                    name='SPY Benchmark',
                                    line=dict(color='#6366f1', width=2, dash='dash')
                                ))
                        except Exception as e:
                            logger.warning(f"Could not add SPY benchmark: {e}")
                    
                    fig_equity.update_layout(
                        title='Portfolio Performance vs SPY',
                        xaxis_title='Date',
                        yaxis_title='Portfolio Value ($)',
                        template='plotly_white',
                        hovermode='x unified',
                        height=400
                    )
                    
                    # Correlation heatmap (top 10 positions)
                    top_10 = df.nlargest(10, 'market_value')['symbol'].tolist()
                    corr_data = {ticker: portfolio_hist.get(ticker) for ticker in top_10 if ticker in portfolio_hist}
                    if len(corr_data) >= 2:
                        corr_df = pd.DataFrame(corr_data).pct_change().dropna().corr()
                        
                        fig_corr = go.Figure(data=go.Heatmap(
                            z=corr_df.values,
                            x=corr_df.columns,
                            y=corr_df.index,
                            colorscale='RdYlGn',
                            zmid=0,
                            text=corr_df.values.round(2),
                            texttemplate='%{text}',
                            textfont={"size": 10}
                        ))
                        fig_corr.update_layout(
                            title='Correlation Heatmap (Top 10 Positions)',
                            template='plotly_white',
                            height=500
                        )
                    else:
                        fig_corr = go.Figure()
                        fig_corr.add_annotation(text="Insufficient data for correlation analysis", showarrow=False)
                        fig_corr.update_layout(height=400)
                    
                else:
                    var_95, cvar, sharpe, beta = 0.0, 0.0, 0.0, 1.0
                    fig_equity = go.Figure()
                    fig_corr = go.Figure()
                    fig_equity.update_layout(height=400)
                    fig_corr.update_layout(height=400)
            else:
                var_95, cvar, sharpe, beta = 0.0, 0.0, 0.0, 1.0
                fig_equity = go.Figure()
                fig_corr = go.Figure()
                fig_equity.update_layout(height=400)
                fig_corr.update_layout(height=400)
        
        except Exception as e:
            import traceback
            logger.error(f"Error calculating advanced analytics: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            var_95, cvar, sharpe, beta = 0.0, 0.0, 0.0, 1.0
            fig_equity = go.Figure()
            fig_corr = go.Figure()
            
            # Add error message to equity chart
            fig_equity.add_annotation(
                text=f"Error loading analytics data:<br>{str(e)[:100]}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="red")
            )
            fig_equity.update_layout(height=400, title="Error Loading Data")
            fig_equity.update_layout(height=400)
            fig_corr.update_layout(height=400)
        
        # Create allocation pie chart
        fig_allocation = px.pie(
            df, 
            values='market_value', 
            names='symbol',
            title='Portfolio Allocation',
            height=400
        )
        
        # Create P/L bar chart
        fig_pl = go.Figure(data=[
            go.Bar(
                x=df['symbol'],
                y=df['unrealized_pl'],
                marker_color=['#10b981' if x >= 0 else '#ef4444' for x in df['unrealized_pl']]
            )
        ])
        fig_pl.update_layout(
            title='Unrealized P/L by Position',
            xaxis_title='Symbol',
            yaxis_title='Unrealized P/L ($)',
            template='plotly_white',
            height=400
        )
        
        content = html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_equity)
                ], width=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_allocation)
                ], width=6),
                dbc.Col([
                    dcc.Graph(figure=fig_pl)
                ], width=6)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_corr)
                ], width=12)
            ])
        ])
        
        return content, f"${abs(var_95):,.2f}", f"${abs(cvar):,.2f}", f"{sharpe:.2f}", f"{beta:.2f}"
    
    
    @app.callback(
        Output('monte-carlo-results', 'children'),
        [Input('monte-carlo-btn', 'n_clicks')],
        [State('portfolio-data-store', 'data'),
         State('analytics-period', 'value')]
    )
    def run_monte_carlo(n_clicks, portfolio_data, period):
        """Run Monte Carlo simulation with 1,000 paths and display distribution."""
        if not n_clicks or n_clicks == 0:
            raise PreventUpdate
        
        if not portfolio_data or not portfolio_data.get('positions'):
            return dbc.Alert("No portfolio data available for simulation.", color="warning")
        
        try:
            positions = portfolio_data['positions']
            df = pd.DataFrame(positions)
            
            # Fetch historical data for Monte Carlo
            tickers = df['symbol'].tolist()
            weights = (df['market_value'] / df['market_value'].sum()).values
            
            end_date = datetime.now()
            # FIX: Use the period from the dropdown instead of hardcoded 365 days
            period_map = {
                '1d': 5, '1w': 7, '1m': 30, '3m': 90, 
                'ytd': (datetime.now() - datetime(datetime.now().year, 1, 1)).days,
                '1y': 365
            }
            days_back = period_map.get(period, 365)
            start_date = end_date - timedelta(days=days_back)
            
            # Download historical data with caching
            portfolio_hist = {}
            for ticker in tickers:
                try:
                    data = cached_historical_download(ticker, start_date, end_date)
                    if not data.empty:
                        portfolio_hist[ticker] = data['Close']
                except Exception:
                    pass
            
            if not portfolio_hist:
                return dbc.Alert("Insufficient historical data for Monte Carlo simulation.", color="warning")
            
            # FIX: Handle single-ticker case where yfinance returns a Series instead of DataFrame
            if len(portfolio_hist) == 1:
                # Single ticker - create DataFrame explicitly with proper index
                ticker = list(portfolio_hist.keys())[0]
                series_data = portfolio_hist[ticker]
                
                # Ensure it's a Series with proper index
                if isinstance(series_data, pd.Series):
                    portfolio_df = pd.DataFrame({ticker: series_data}, index=series_data.index)
                else:
                    portfolio_df = pd.DataFrame(series_data)
                    
                logger.info(f"Single ticker portfolio detected: {ticker}")
            else:
                # Multiple tickers - use standard DataFrame constructor
                portfolio_df = pd.DataFrame(portfolio_hist)
            
            # Calculate portfolio returns
            portfolio_df = portfolio_df.ffill().dropna()
            returns_df = portfolio_df.pct_change().dropna()
            
            # Handle weighted returns calculation
            if len(tickers) == 1:
                # Single ticker - returns are already the portfolio returns
                portfolio_returns = returns_df.iloc[:, 0]
            else:
                # Multiple tickers - weighted sum
                portfolio_returns = (returns_df * weights).sum(axis=1)
            
            # Calculate mean and covariance for simulation
            mean_return = portfolio_returns.mean()
            std_return = portfolio_returns.std()
            
            # Run Monte Carlo simulation
            num_simulations = 1000
            num_days = 252  # 1 year forecast
            current_value = portfolio_data['account']['portfolio_value']
            
            # Generate random paths
            simulations = np.zeros((num_days, num_simulations))
            for sim in range(num_simulations):
                # Generate random returns using historical mean and std
                random_returns = np.random.normal(mean_return, std_return, num_days)
                # Calculate cumulative returns - FIX: Ensure proper array handling
                cumulative = np.cumprod(1 + random_returns)
                simulations[:, sim] = cumulative * current_value
            
            # Calculate percentiles
            percentile_95 = np.percentile(simulations[-1, :], 95)
            percentile_50 = np.percentile(simulations[-1, :], 50)
            percentile_5 = np.percentile(simulations[-1, :], 5)
            
            # Create visualization
            fig = go.Figure()
            
            # Plot a sample of paths (100 paths to avoid clutter)
            sample_indices = np.random.choice(num_simulations, size=min(100, num_simulations), replace=False)
            for idx in sample_indices:
                fig.add_trace(go.Scatter(
                    x=list(range(num_days)),
                    y=simulations[:, idx],
                    mode='lines',
                    line=dict(color='lightblue', width=0.5),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            # Add percentile lines
            fig.add_trace(go.Scatter(
                x=list(range(num_days)),
                y=np.percentile(simulations, 95, axis=1),
                mode='lines',
                name='95th Percentile',
                line=dict(color='green', width=2, dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=list(range(num_days)),
                y=np.percentile(simulations, 50, axis=1),
                mode='lines',
                name='Median (50th)',
                line=dict(color='blue', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=list(range(num_days)),
                y=np.percentile(simulations, 5, axis=1),
                mode='lines',
                name='5th Percentile',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            fig.update_layout(
                title='Monte Carlo Simulation (1,000 Paths, 1-Year Forecast)',
                xaxis_title='Trading Days',
                yaxis_title='Portfolio Value ($)',
                template='plotly_white',
                height=500,
                hovermode='x unified'
            )
            
            # Distribution histogram
            fig_dist = go.Figure(data=[
                go.Histogram(
                    x=simulations[-1, :],
                    nbinsx=50,
                    marker_color='steelblue',
                    name='Final Values'
                )
            ])
            fig_dist.update_layout(
                title='Distribution of Final Portfolio Values (End of Year)',
                xaxis_title='Portfolio Value ($)',
                yaxis_title='Frequency',
                template='plotly_white',
                height=400
            )
            
            # Summary stats
            summary = dbc.Card([
                dbc.CardBody([
                    html.H5("Monte Carlo Simulation Results", className="mb-3"),
                    html.P([
                        html.Strong("Current Portfolio Value: "),
                        f"${current_value:,.2f}"
                    ]),
                    html.P([
                        html.Strong("Median (50th Percentile) Value in 1 Year: "),
                        f"${percentile_50:,.2f}",
                        html.Span(f" ({((percentile_50 - current_value) / current_value * 100):.1f}%)", 
                                 className="text-muted")
                    ]),
                    html.P([
                        html.Strong("95th Percentile (Upside): "),
                        f"${percentile_95:,.2f}",
                        html.Span(f" (+{((percentile_95 - current_value) / current_value * 100):.1f}%)", 
                                 className="text-success")
                    ]),
                    html.P([
                        html.Strong("5th Percentile (Downside Risk): "),
                        f"${percentile_5:,.2f}",
                        html.Span(f" ({((percentile_5 - current_value) / current_value * 100):.1f}%)", 
                                 className="text-danger")
                    ]),
                    html.P([
                        html.Strong("Simulations: "),
                        f"{num_simulations:,} paths"
                    ], className="mb-0")
                ])
            ], className="mb-3", color="light")
            
            return html.Div([
                summary,
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure=fig)
                    ], width=12)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure=fig_dist)
                    ], width=12)
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error running Monte Carlo simulation: {e}")
            return dbc.Alert(f"Error running Monte Carlo simulation: {str(e)}", color="danger")
