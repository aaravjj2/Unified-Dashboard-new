"""
Market Forecast Tab - Complete Overhaul with Enhanced Visualization
=====================================================================

A professional-grade market forecasting dashboard featuring:
- Multi-model forecasting (Prophet, ARIMA, LSTM, Ensemble)
- Crystal-clear fan charts with confidence intervals
- Real-time price data via unified price fetching (Alpaca → yfinance fallback)
- Scenario analysis for what-if simulations
- Model performance comparison metrics
- Clean, intuitive UI with dark theme

Data Sources (priority order):
- Alpaca (requires API key)
- yfinance (fallback, no key needed)
"""

import logging
import os
import sys
import time
from dash import html, dcc, Input, Output, State, callback_context
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
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'keys.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Import FinGPT panel (safely)
try:
    from .market_forecast_fingpt import create_fingpt_panel, register_fingpt_callbacks
    FINGPT_AVAILABLE = True
except ImportError:
    FINGPT_AVAILABLE = False
    logger.info("FinGPT panel not available")


def _create_fingpt_panel_safe():
    """Safely create FinGPT panel with fallback."""
    if FINGPT_AVAILABLE:
        return create_fingpt_panel()
    else:
        import dash_bootstrap_components as dbc
        return dbc.Card([
            dbc.CardHeader("FinGPT Forecast (Not Available)"),
            dbc.CardBody("FinGPT module not loaded.")
        ], className="bg-dark border-secondary")


# Color scheme for dark theme
COLORS = {
    'background': '#1a1a2e',
    'card': '#16213e',
    'accent': '#0f3460',
    'primary': '#3b82f6',
    'success': '#10b981',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'text': '#e5e5e5',
    'muted': '#9ca3af',
    'prophet': '#3b82f6',
    'arima': '#8b5cf6',
    'lstm': '#06b6d4',
    'qlib': '#f97316',
    'neuralprophet': '#ec4899',
    'ensemble': '#10b981',
}

# Component IDs
COMPONENT_IDS = {
    'ticker_input': 'mf-ticker-input',
    'horizon_select': 'mf-horizon-select',
    'model_checklist': 'mf-model-checklist',
    'interval_checklist': 'mf-interval-checklist',
    'scenario_select': 'mf-scenario-select',
    'scenario_param': 'mf-scenario-param',
    'scenario_apply_btn': 'mf-scenario-apply-btn',
    'run_btn': 'mf-run-btn',
    'forecast_chart': 'mf-forecast-chart',
    'scenario_chart': 'mf-scenario-chart',
    'model_comparison_chart': 'mf-model-comparison-chart',
    'model_metrics': 'mf-model-metrics',
    'status_banner': 'mf-status-banner',
    'forecast_store': 'mf-forecast-store',
    'loading': 'mf-loading-overlay',
    'price_info': 'mf-price-info',
    'sentiment_display': 'mf-sentiment-display',
}


def fetch_historical_price_data(ticker: str, lookback_days: int = 365) -> tuple:
    """
    Unified historical data fetching with source tracking.
    
    Uses Alpaca → yfinance fallback chain via fetch_historical_data utility.
    Returns (DataFrame/None, metadata dict) with source and timing info.
    
    Args:
        ticker: Stock ticker symbol
        lookback_days: Number of days to look back
    
    Returns:
        Tuple of (pandas DataFrame with OHLCV data, metadata dict)
    """
    fetch_start = time.time()
    metadata = {
        'source': 'unknown',
        'fetch_duration_ms': 0,
        'data_timestamp': None,
        'ticker': ticker
    }
    
    try:
        # Try unified price fetching first
        from financial_dashboard.utils.price_fetch import fetch_historical_data
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 10)
        
        prices_df = fetch_historical_data(
            tickers=[ticker],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            use_alpaca=True
        )
        
        metadata['fetch_duration_ms'] = round((time.time() - fetch_start) * 1000, 2)
        
        if not prices_df.empty and ticker in prices_df.columns:
            # We need full OHLCV for forecast models, so if we only got close prices
            # we still use the close column for modeling
            close_prices = prices_df[ticker].dropna()
            
            # Create a synthetic OHLCV DataFrame
            hist = pd.DataFrame({
                'Open': close_prices,
                'High': close_prices * 1.001,  # Small offset for synthetic OHLCV
                'Low': close_prices * 0.999,
                'Close': close_prices,
                'Volume': 1000000
            }, index=close_prices.index)
            
            metadata['source'] = 'alpaca_or_yfinance'
            metadata['data_timestamp'] = close_prices.index[-1].isoformat() if hasattr(close_prices.index[-1], 'isoformat') else str(close_prices.index[-1])
            metadata['data_points'] = len(hist)
            
            logger.info(f"✅ Fetched {len(hist)} price points for {ticker} via unified fetcher ({metadata['fetch_duration_ms']}ms)")
            return hist, metadata
            
    except ImportError as e:
        logger.warning(f"Unified price fetch not available: {e}")
    except Exception as e:
        logger.warning(f"Unified price fetch failed for {ticker}: {e}")
    
    # Fallback to direct yfinance only when explicitly allowed by env flag
    allow_yf = os.getenv('ALLOW_YFINANCE_FALLBACK', '0') == '1'
    if allow_yf:
        try:
            import yfinance as yf

            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 10)

            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date, auto_adjust=True)

            metadata['fetch_duration_ms'] = round((time.time() - fetch_start) * 1000, 2)

            if not hist.empty:
                metadata['source'] = 'yfinance'
                metadata['data_timestamp'] = hist.index[-1].isoformat() if hasattr(hist.index[-1], 'isoformat') else str(hist.index[-1])
                metadata['data_points'] = len(hist)

                logger.info(f"✅ Fetched {len(hist)} price points for {ticker} via yfinance ({metadata['fetch_duration_ms']}ms)")
                return hist, metadata

        except Exception as e:
            logger.error(f"yfinance fallback failed for {ticker}: {e}")
            metadata['error'] = str(e)
    
    metadata['fetch_duration_ms'] = round((time.time() - fetch_start) * 1000, 2)
    return None, metadata


def create_header():
    """Create page header with title and description."""
    return html.Div([
        html.Div([
            html.I(className="bi bi-graph-up-arrow", style={'fontSize': '2rem', 'color': COLORS['primary']}),
            html.Div([
                html.H2("Market Forecast", className="mb-0 text-white fw-bold"),
                html.P("Multi-model price prediction with confidence intervals", 
                       className="mb-0 text-white-50 small")
            ], className="ms-3")
        ], className="d-flex align-items-center")
    ], className="mb-4")


def create_inputs_panel():
    """Enhanced inputs panel with model selection and scenarios."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-sliders", style={'color': COLORS['primary']}),
                html.Span(" Forecast Configuration", className="ms-2 fw-bold")
            ])
        ], className="bg-dark border-secondary"),
        dbc.CardBody([
            # Ticker Input with validation
            html.Div([
                html.Label([
                    html.I(className="bi bi-search me-1"),
                    "Stock Ticker"
                ], className="small fw-bold text-white mb-1"),
                dbc.InputGroup([
                    dcc.Input(
                        id=COMPONENT_IDS['ticker_input'],
                        type='text',
                        value='AAPL',
                        placeholder='Enter ticker (e.g., AAPL)',
                        className="form-control bg-dark text-white border-secondary",
                        style={'borderRadius': '0.375rem 0 0 0.375rem'}
                    ),
                    dbc.InputGroupText("US", className="bg-secondary border-secondary text-white")
                ], size="sm"),
                html.Div(id=COMPONENT_IDS['price_info'], className="mt-1")
            ], className="mb-3"),
            
            # Horizon Selection
            html.Div([
                html.Label([
                    html.I(className="bi bi-calendar-range me-1"),
                    "Forecast Horizon"
                ], className="small fw-bold text-white mb-1"),
                dcc.Dropdown(
                    id=COMPONENT_IDS['horizon_select'],
                    options=[
                        {'label': '📅 1 Week (7 days)', 'value': 7},
                        {'label': '📅 2 Weeks (14 days)', 'value': 14},
                        {'label': '📅 1 Month (30 days)', 'value': 30},
                        {'label': '📅 3 Months (90 days)', 'value': 90},
                    ],
                    value=14,
                    clearable=False,
                    className="dash-dropdown-dark",
                    style={'backgroundColor': COLORS['card']}
                )
            ], className="mb-3"),
            
            # Model Selection with icons
            html.Div([
                html.Label([
                    html.I(className="bi bi-cpu me-1"),
                    "Forecasting Models"
                ], className="small fw-bold text-white mb-2"),
                dcc.Checklist(
                    id=COMPONENT_IDS['model_checklist'],
                    options=[
                        {'label': html.Span([
                            html.Span("●", style={'color': COLORS['prophet']}),
                            " Prophet (Trend + Seasonality)"
                        ]), 'value': 'prophet'},
                        {'label': html.Span([
                            html.Span("●", style={'color': COLORS['arima']}),
                            " ARIMA (Autoregression)"
                        ]), 'value': 'arima'},
                        {'label': html.Span([
                            html.Span("●", style={'color': COLORS['lstm']}),
                            " LSTM (Deep Learning)"
                        ]), 'value': 'lstm'},
                        {'label': html.Span([
                            html.Span("●", style={'color': '#f97316'}),
                            " Qlib (Alpha + Deep)"
                        ]), 'value': 'qlib'},
                        {'label': html.Span([
                            html.Span("●", style={'color': '#ec4899'}),
                            " NeuralProphet (Neural + Trend)"
                        ]), 'value': 'neuralprophet'},
                        {'label': html.Span([
                            html.Span("●", style={'color': COLORS['ensemble']}),
                            " Ensemble (All Models)"
                        ]), 'value': 'ensemble'},
                    ],
                    value=['prophet', 'ensemble'],
                    className="text-white-50 small",
                    labelStyle={'display': 'block', 'marginBottom': '8px', 'cursor': 'pointer'},
                    inputStyle={'marginRight': '8px'}
                )
            ], className="mb-3"),
            
            # Confidence Intervals
            html.Div([
                html.Label([
                    html.I(className="bi bi-bounding-box me-1"),
                    "Confidence Intervals"
                ], className="small fw-bold text-white mb-2"),
                dcc.Checklist(
                    id=COMPONENT_IDS['interval_checklist'],
                    options=[
                        {'label': ' 50% (Inner band)', 'value': '50'},
                        {'label': ' 80% (Middle band)', 'value': '80'},
                        {'label': ' 95% (Outer band)', 'value': '95'},
                    ],
                    value=['80', '95'],
                    className="text-white-50 small",
                    labelStyle={'display': 'block', 'marginBottom': '6px', 'cursor': 'pointer'},
                    inputStyle={'marginRight': '8px'}
                )
            ], className="mb-4"),
            
            # Run Button - Large and prominent
            dbc.Button([
                html.I(className="bi bi-play-fill me-2"),
                "Generate Forecast"
            ],
                id=COMPONENT_IDS['run_btn'],
                color="success",
                size="lg",
                className="w-100 fw-bold",
                style={'borderRadius': '0.5rem'}
            ),
        ], className="bg-dark")
    ], className="h-100 bg-dark border-secondary")


def create_scenario_panel():
    """Scenario analysis ("What-If") panel."""
    # Try to import scenario simulator
    try:
        from ..utils.scenario_simulator import ScenarioSimulator
        scenario_options = ScenarioSimulator.get_scenario_options()
    except Exception:
        scenario_options = [
            {'label': 'Fed Rate Cut - Interest rate decrease', 'value': 'fed_rate_cut'},
            {'label': 'Fed Rate Hike - Interest rate increase', 'value': 'fed_rate_hike'},
            {'label': 'VIX Spike - Volatility increase', 'value': 'vix_spike'},
            {'label': 'Earnings Beat - Better than expected', 'value': 'earnings_beat'},
            {'label': 'Earnings Miss - Worse than expected', 'value': 'earnings_miss'},
        ]
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-lightning", style={'color': COLORS['warning']}),
                html.Span(" Scenario Analysis", className="ms-2 fw-bold")
            ])
        ], className="bg-dark border-secondary"),
        dbc.CardBody([
            html.P("Simulate market reactions to economic events", 
                   className="small text-white-50 mb-3"),
            
            # Scenario selector
            html.Div([
                html.Label([
                    html.I(className="bi bi-diagram-3 me-1"),
                    "Scenario Type"
                ], className="small fw-bold text-white mb-1"),
                dcc.Dropdown(
                    id=COMPONENT_IDS['scenario_select'],
                    options=scenario_options,
                    placeholder="Select a scenario...",
                    className="dash-dropdown-dark"
                )
            ], className="mb-3"),
            
            # Parameter slider
            html.Div([
                html.Label([
                    html.I(className="bi bi-sliders2 me-1"),
                    "Impact Intensity"
                ], className="small fw-bold text-white mb-2"),
                dcc.Slider(
                    id=COMPONENT_IDS['scenario_param'],
                    min=-50,
                    max=50,
                    step=5,
                    value=0,
                    marks={i: {'label': f"{i}", 'style': {'color': COLORS['muted']}} 
                           for i in [-50, -25, 0, 25, 50]},
                    className="mb-3"
                )
            ]),
            
            # Apply button
            dbc.Button([
                html.I(className="bi bi-arrow-right-circle me-2"),
                "Apply Scenario"
            ],
                id=COMPONENT_IDS['scenario_apply_btn'],
                color="warning",
                size="sm",
                className="w-100",
                disabled=True
            ),
        ], className="bg-dark")
    ], className="bg-dark border-secondary")


def create_forecast_chart_panel():
    """Main forecast visualization panel with fan chart."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-graph-up", style={'color': COLORS['success']}),
                html.Span(" Price Forecast", className="ms-2 fw-bold")
            ], className="d-flex align-items-center justify-content-between w-100")
        ], className="bg-dark border-secondary"),
        dbc.CardBody([
            dcc.Loading(
                id=COMPONENT_IDS['loading'],
                type="circle",
                color=COLORS['primary'],
                children=[
                    dcc.Graph(
                        id=COMPONENT_IDS['forecast_chart'],
                        figure=_empty_chart("Click 'Generate Forecast' to see predictions"),
                        config={
                            'displayModeBar': True,
                            'displaylogo': False,
                            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                            'toImageButtonOptions': {
                                'format': 'png',
                                'filename': 'market_forecast',
                                'height': 600,
                                'width': 1200,
                                'scale': 2
                            }
                        },
                        style={'height': '500px'}
                    )
                ]
            ),
        ], className="bg-dark p-2")
    ], className="h-100 bg-dark border-secondary")


def create_model_comparison_panel():
    """Model comparison chart."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-bar-chart", style={'color': COLORS['primary']}),
                html.Span(" Model Comparison", className="ms-2 fw-bold")
            ])
        ], className="bg-dark border-secondary"),
        dbc.CardBody([
            dcc.Graph(
                id=COMPONENT_IDS['model_comparison_chart'],
                figure=_empty_chart("Run forecast to compare models", height=280),
                config={'displayModeBar': False},
                style={'height': '280px'}
            )
        ], className="bg-dark p-2")
    ], className="bg-dark border-secondary")


def create_metrics_panel():
    """Model performance metrics panel."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-speedometer2", style={'color': COLORS['success']}),
                html.Span(" Forecast Metrics", className="ms-2 fw-bold")
            ])
        ], className="bg-dark border-secondary"),
        dbc.CardBody([
            html.Div(id=COMPONENT_IDS['model_metrics'], children=[
                html.Div([
                    html.I(className="bi bi-hourglass", style={'fontSize': '2rem', 'color': COLORS['muted']}),
                    html.P("Run forecast to see metrics", className="text-white-50 small mt-2")
                ], className="text-center py-4")
            ])
        ], className="bg-dark")
    ], className="bg-dark border-secondary")


def create_scenario_results_panel():
    """Scenario comparison results."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-arrows-expand", style={'color': COLORS['warning']}),
                html.Span(" Scenario Impact", className="ms-2 fw-bold")
            ])
        ], className="bg-dark border-secondary"),
        dbc.CardBody([
            dcc.Graph(
                id=COMPONENT_IDS['scenario_chart'],
                figure=_empty_chart("Apply scenario to see impact", height=280),
                config={'displayModeBar': False},
                style={'height': '280px'}
            )
        ], className="bg-dark p-2")
    ], className="bg-dark border-secondary")


def _empty_chart(message: str, height: int = 500) -> go.Figure:
    """Create empty placeholder chart with dark theme."""
    fig = go.Figure()
    
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=COLORS['muted']),
        align='center'
    )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        margin=dict(l=40, r=40, t=40, b=40),
        height=height,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
    )
    
    return fig


def create_sentiment_panel():
    """AI-powered sentiment analysis panel using FinBERT."""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-robot", style={'color': COLORS['primary']}),
                html.Span(" AI Sentiment Analysis", className="ms-2 fw-bold"),
                dbc.Badge("FinBERT", color="info", className="ms-2", pill=True)
            ])
        ], className="bg-dark border-secondary"),
        dbc.CardBody([
            html.Div(id='mf-sentiment-display', children=[
                html.Div([
                    html.I(className="bi bi-info-circle me-2 text-muted"),
                    html.Span("Run forecast to analyze market sentiment", className="text-muted small")
                ])
            ])
        ], className="bg-dark p-3")
    ], className="bg-dark border-secondary")


def create_status_banner():
    """Status banner for notifications."""
    return html.Div(id=COMPONENT_IDS['status_banner'], className="mb-3")


def layout():
    """Main layout with responsive design."""
    return dbc.Container([
        # === IMPROVEMENTS: Toolbar with filters ===
        html.Div([
            create_tab_toolbar(
                tab_name="market_forecast",
                filters=[create_date_range_filter('forecast-date')] if SHARED_UI_AVAILABLE else [],
                show_refresh=True,
                show_export=True,
                show_help=True,
                help_text="AI-powered market forecasts and scenario analysis."
            ) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === IMPROVEMENTS: Summary Statistics ===
        html.Div([
            create_summary_stats_row([
                {'title': 'Bull Probability', 'value': '--%', 'icon': 'fa-arrow-up', 'color': 'success'},
            {'title': 'Bear Probability', 'value': '--%', 'icon': 'fa-arrow-down', 'color': 'danger'},
            {'title': 'Confidence', 'value': '--%', 'icon': 'fa-brain', 'color': 'info'},
            {'title': 'Scenarios', 'value': '--', 'icon': 'fa-chart-area', 'color': 'primary'}
            ]) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === IMPROVEMENTS: Notification Toast ===
        html.Div([
            create_notification_toast("market_forecast-toast", "Market Forecast Update") if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # Header
        create_header(),
        
        # Status banner
        create_status_banner(),
        
        # Main content: 3 columns
        dbc.Row([
            # Left column: Controls
            dbc.Col([
                create_inputs_panel(),
                html.Div(className="mb-3"),
                create_scenario_panel(),
            ], lg=3, md=4, sm=12, className="mb-3"),
            
            # Middle column: Main forecast chart
            dbc.Col([
                create_forecast_chart_panel(),
            ], lg=6, md=8, sm=12, className="mb-3"),
            
            # Right column: Metrics and secondary charts
            dbc.Col([
                create_sentiment_panel(),
                html.Div(className="mb-3"),
                _create_fingpt_panel_safe(),  # FinGPT LLM Forecaster Panel
                html.Div(className="mb-3"),
                create_metrics_panel(),
                html.Div(className="mb-3"),
                create_model_comparison_panel(),
                html.Div(className="mb-3"),
                create_scenario_results_panel(),
            ], lg=3, md=12, sm=12, className="mb-3"),
        ]),
        
        # Hidden stores
        dcc.Store(id=COMPONENT_IDS['forecast_store'], data=None),
        
        # Custom CSS (moved to assets for Dash compatibility)
        html.Link(rel='stylesheet', href='/assets/market_forecast_custom.css')
        
    ], fluid=True, className="p-3", style={'backgroundColor': COLORS['background'], 'minHeight': '100vh'})


def register_callbacks(app, SH=None):
    """Register all callbacks for Market Forecast tab."""
    logger.info("Registering Market Forecast callbacks")
    
    # Register FinGPT callbacks if available
    if FINGPT_AVAILABLE:
        try:
            register_fingpt_callbacks(app)
            logger.info("FinGPT callbacks registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register FinGPT callbacks: {e}")
    
    from dash.exceptions import PreventUpdate
    
    @app.callback(
        Output(COMPONENT_IDS['forecast_store'], 'data'),
        Output(COMPONENT_IDS['forecast_chart'], 'figure'),
        Output(COMPONENT_IDS['model_comparison_chart'], 'figure'),
        Output(COMPONENT_IDS['model_metrics'], 'children'),
        Output(COMPONENT_IDS['status_banner'], 'children'),
        Output(COMPONENT_IDS['scenario_apply_btn'], 'disabled'),
        Output(COMPONENT_IDS['price_info'], 'children'),
        Output(COMPONENT_IDS['sentiment_display'], 'children'),
        Input(COMPONENT_IDS['run_btn'], 'n_clicks'),
        State(COMPONENT_IDS['ticker_input'], 'value'),
        State(COMPONENT_IDS['horizon_select'], 'value'),
        State(COMPONENT_IDS['model_checklist'], 'value'),
        State(COMPONENT_IDS['interval_checklist'], 'value'),
        prevent_initial_call=True
    )
    def run_forecast(n_clicks, ticker, horizon, selected_models, selected_intervals):
        """Main forecast generation callback with AI sentiment."""
        if not n_clicks or not ticker:
            raise PreventUpdate
        
        ticker = ticker.strip().upper()
        sentiment_display = html.Div([
            html.I(className="bi bi-hourglass-split me-2 text-muted"),
            html.Span("Analyzing sentiment...", className="text-muted small")
        ])
        
        try:
            # Import models
            try:
                from ..models import ProphetForecaster, ARIMAForecaster, LSTMForecaster, EnsembleForecaster
                models_available = True
            except ImportError as e:
                logger.warning(f"Models import failed: {e}")
                models_available = False
            
            # Import AI sentiment analyzer
            try:
                from ..models import get_market_sentiment
                sentiment_available = True
            except ImportError:
                sentiment_available = False

            # Initialize optional ServingClient for sentinel and embeddings
            try:
                from financial_dashboard.serving.serving_client import ServingClient
                sc = ServingClient()
            except Exception:
                sc = None
            
            # Fetch historical data using unified price fetcher (Alpaca → yfinance fallback)
            logger.info(f"Fetching data for {ticker}...")
            hist, data_metadata = fetch_historical_price_data(ticker, lookback_days=365)
            
            if hist is None or len(hist) < 30:
                status = dbc.Alert([
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    f"No data available for {ticker}. Please check the ticker symbol."
                ], color="danger", dismissable=True)
                return None, _empty_chart(f"No data for {ticker}"), _empty_chart("No data", 280), [], status, True, "", sentiment_display
            
            # Get current price info
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            # Add data source indicator
            source_badge = dbc.Badge(
                f"via {data_metadata.get('source', 'unknown')}",
                color="secondary",
                className="ms-2",
                style={'fontSize': '0.65rem'}
            )
            
            price_info = html.Span([
                f"${current_price:.2f} ",
                html.Span(
                    f"{'▲' if change >= 0 else '▼'} {abs(change):.2f} ({abs(change_pct):.2f}%)",
                    className=f"{'text-success' if change >= 0 else 'text-danger'} small"
                ),
                source_badge
            ])
            
            # Get AI sentiment
            sentiment_data = None
            if sentiment_available:
                try:
                    # If ServingClient exists (bento/triton), use it to analyze fetched headlines
                    if sc and sc.mode in ['bento', 'triton']:
                        # Fetch headlines via NewsManager if available
                        try:
                            from financial_dashboard.utils.news_manager import NewsManager
                            nm = NewsManager(ttl_seconds=300)
                            news_df = nm.fetch_news([ticker], max_per_ticker=10)
                            # Flatten headlines
                            headlines = []
                            for hdf in news_df.values():
                                for r in hdf:
                                    if r.get('title'):
                                        headlines.append(r['title'])
                        except Exception:
                            headlines = []

                        if headlines:
                            sc_res = sc.analyze_sentiment(headlines, ticker=ticker)
                            if sc_res.get('status') == 'success':
                                # Aggregate simple signal from responses
                                try:
                                    preds = sc_res['data'].get('sentiments') if isinstance(sc_res['data'], dict) and 'sentiments' in sc_res['data'] else sc_res['data']
                                    # Convert to a structure akin to get_market_sentiment
                                    mean_score = 0
                                    count = len(preds)
                                    pos = 0
                                    neg = 0
                                    for p in preds:
                                        label = p.get('sentiment') if isinstance(p, dict) else p.get('label')
                                        score = p.get('score', 0) if isinstance(p, dict) else 0
                                        if label == 'positive':
                                            pos += 1
                                            mean_score += score
                                        elif label == 'negative':
                                            neg += 1
                                            mean_score -= score
                                    mean_score = mean_score / count if count > 0 else 0
                                    signal = 'bullish' if mean_score > 0.15 else 'bearish' if mean_score < -0.15 else 'neutral'
                                    sentiment_data = {
                                        'ticker': ticker,
                                        'sentiment_count': count,
                                        'sentiment_mean': float(mean_score),
                                        'signal': signal,
                                        'confidence': min(abs(mean_score) * 2, 1.0)
                                    }
                                except Exception:
                                    sentiment_data = None
                    else:
                        sentiment_data = get_market_sentiment(ticker, days=7)
                        logger.info(f"Sentiment for {ticker}: {sentiment_data.get('signal', 'N/A')}")
                except Exception as e:
                    logger.warning(f"Sentiment analysis failed: {e}")
            
            # Build sentiment display
            if sentiment_data and sentiment_data.get('sentiment_count', 0) > 0:
                signal = sentiment_data.get('signal', 'neutral')
                mean_score = sentiment_data.get('sentiment_mean', 0)
                count = sentiment_data.get('sentiment_count', 0)
                confidence = sentiment_data.get('confidence', 0)
                
                signal_color = {
                    'bullish': 'success',
                    'bearish': 'danger',
                    'neutral': 'secondary'
                }.get(signal, 'secondary')
                
                signal_icon = {
                    'bullish': 'bi-arrow-up-circle-fill',
                    'bearish': 'bi-arrow-down-circle-fill',
                    'neutral': 'bi-dash-circle-fill'
                }.get(signal, 'bi-dash-circle-fill')
                
                sentiment_display = html.Div([
                    html.Div([
                        html.I(className=f"bi {signal_icon} me-2", 
                               style={'color': COLORS.get(signal_color, '#6c757d'), 'fontSize': '1.5rem'}),
                        html.Div([
                            html.Span(signal.upper(), className=f"fw-bold text-{signal_color}"),
                            html.Div(f"Score: {mean_score:.3f}", className="small text-muted")
                        ])
                    ], className="d-flex align-items-center mb-2"),
                    html.Div([
                        html.Span(f"{count} articles analyzed", className="small text-muted me-2"),
                        dbc.Badge(f"{confidence*100:.0f}% confidence", color=signal_color, className="small")
                    ]),
                    html.Hr(className="my-2"),
                    html.Div([
                        html.I(className="bi bi-robot me-1", style={'color': COLORS['primary']}),
                        html.Span("FinBERT AI Analysis", className="small text-muted")
                    ])
                ])
            else:
                sentiment_display = html.Div([
                    html.I(className="bi bi-exclamation-circle me-2 text-warning"),
                    html.Span("No recent news found for sentiment analysis", className="text-muted small")
                ])
            
            # Prepare data for models
            data = pd.DataFrame({
                'ds': hist.index.tz_localize(None) if hist.index.tz is not None else hist.index,
                'y': hist['Close'].values
            })
            
            # Train selected models and generate forecasts with defensive handling
            forecasts = {}
            model_errors = {}
            inference_sources = {}  # Track which backend was used for each model
            
            # Try ServingClient first for supported models (Bento/Triton)
            if sc and sc.mode in ['bento', 'triton']:
                try:
                    # Use serving client for ensemble/forecast if available
                    if 'ensemble' in (selected_models or []):
                        sc_res = sc.predict_forecast(ticker, horizon, 'ensemble', confidence=0.95)
                        if sc_res.get('status') == 'success':
                            fc_data = sc_res.get('data', {})
                            if 'forecast' in fc_data:
                                forecast_vals = fc_data['forecast']
                                if isinstance(forecast_vals, list):
                                    if isinstance(forecast_vals[0], dict):
                                        vals = [f.get('yhat', f.get('value', 0)) for f in forecast_vals]
                                    else:
                                        vals = forecast_vals
                                    # Create forecast dict similar to local models
                                    forecast_arr = np.array(vals)
                                    std = np.std(forecast_arr) * np.sqrt(np.arange(1, len(vals) + 1))
                                    forecasts['ensemble'] = {
                                        'forecast': vals,
                                        'lower_50': (forecast_arr - 0.675 * std).tolist(),
                                        'upper_50': (forecast_arr + 0.675 * std).tolist(),
                                        'lower_80': (forecast_arr - 1.28 * std).tolist(),
                                        'upper_80': (forecast_arr + 1.28 * std).tolist(),
                                        'lower_95': (forecast_arr - 1.96 * std).tolist(),
                                        'upper_95': (forecast_arr + 1.96 * std).tolist(),
                                    }
                                    inference_sources['ensemble'] = f'serving_{sc.mode}'
                                    logger.info(f"✅ Ensemble forecast via {sc.mode}")
                except Exception as e:
                    logger.warning(f"ServingClient forecast failed: {e}")
            
            # Fall back to local models for any not handled by serving
            if models_available:
                if 'prophet' in (selected_models or []) and 'prophet' not in forecasts:
                    try:
                        prophet = ProphetForecaster()
                        prophet.fit(data)
                        forecasts['prophet'] = prophet.predict(horizon)
                        inference_sources['prophet'] = 'local'
                        logger.info("✅ Prophet forecast complete")
                    except Exception as e:
                        logger.error(f"Prophet error: {e}")
                        model_errors['prophet'] = str(e)
                
                if 'arima' in (selected_models or []) and 'arima' not in forecasts:
                    try:
                        arima = ARIMAForecaster()
                        arima.fit(data)
                        forecasts['arima'] = arima.predict(horizon)
                        inference_sources['arima'] = 'local'
                        logger.info("✅ ARIMA forecast complete")
                    except Exception as e:
                        logger.error(f"ARIMA error: {e}")
                        model_errors['arima'] = str(e)
                
                if 'lstm' in (selected_models or []) and 'lstm' not in forecasts:
                    try:
                        lstm = LSTMForecaster(epochs=30)
                        lstm.fit(data)
                        forecasts['lstm'] = lstm.predict(horizon)
                        inference_sources['lstm'] = 'local'
                        logger.info("✅ LSTM forecast complete")
                    except Exception as e:
                        logger.error(f"LSTM error: {e}")
                        model_errors['lstm'] = str(e)
                
                # Qlib-style forecaster (Alpha + Deep Learning)
                if 'qlib' in (selected_models or []) and 'qlib' not in forecasts:
                    try:
                        from financial_dashboard.engines.qlib_forecaster import QlibStyleForecaster
                        qlib_fc = QlibStyleForecaster(lookback=60)
                        
                        # Qlib needs OHLCV DataFrame - use hist which has that data
                        qlib_result = qlib_fc.forecast(hist, horizon=horizon, ticker=ticker)
                        
                        if qlib_result and hasattr(qlib_result, 'forecast_values'):
                            forecast_vals = qlib_result.forecast_values
                            lower = qlib_result.confidence_lower
                            upper = qlib_result.confidence_upper
                            
                            # Calculate spreads for different confidence bands
                            spread = upper - forecast_vals
                            
                            # Build standard forecast dict
                            forecasts['qlib'] = {
                                'forecast': forecast_vals.tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals),
                                'lower_50': (forecast_vals - 0.675 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals - 0.675 * spread),
                                'upper_50': (forecast_vals + 0.675 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals + 0.675 * spread),
                                'lower_80': (forecast_vals - 1.28 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals - 1.28 * spread),
                                'upper_80': (forecast_vals + 1.28 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals + 1.28 * spread),
                                'lower_95': lower.tolist() if hasattr(lower, 'tolist') else list(lower),
                                'upper_95': upper.tolist() if hasattr(upper, 'tolist') else list(upper),
                            }
                            inference_sources['qlib'] = 'local_qlib'
                            logger.info(f"✅ Qlib forecast complete (alpha: {qlib_result.alpha_score:.3f})")
                    except Exception as e:
                        logger.error(f"Qlib error: {e}")
                        model_errors['qlib'] = str(e)
                
                # NeuralProphet forecaster (Neural + Trend decomposition)
                if 'neuralprophet' in (selected_models or []) and 'neuralprophet' not in forecasts:
                    try:
                        from financial_dashboard.engines.neural_prophet_forecaster import NeuralProphetForecaster
                        np_fc = NeuralProphetForecaster(n_lags=5, yearly_seasonality=True, weekly_seasonality=True)
                        
                        # Fit and forecast
                        np_fc.fit(data)
                        np_result = np_fc.predict(horizon)
                        
                        if np_result and hasattr(np_result, 'yhat'):
                            forecast_vals = np_result.yhat
                            lower = np_result.yhat_lower
                            upper = np_result.yhat_upper
                            
                            # Calculate spread for different confidence bands
                            spread = (upper - lower) / (2 * 1.96)  # Convert 95% to ~1 std
                            
                            forecasts['neuralprophet'] = {
                                'forecast': forecast_vals.tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals),
                                'lower_50': (forecast_vals - 0.675 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals - 0.675 * spread),
                                'upper_50': (forecast_vals + 0.675 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals + 0.675 * spread),
                                'lower_80': (forecast_vals - 1.28 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals - 1.28 * spread),
                                'upper_80': (forecast_vals + 1.28 * spread).tolist() if hasattr(forecast_vals, 'tolist') else list(forecast_vals + 1.28 * spread),
                                'lower_95': lower.tolist() if hasattr(lower, 'tolist') else list(lower),
                                'upper_95': upper.tolist() if hasattr(upper, 'tolist') else list(upper),
                            }
                            inference_sources['neuralprophet'] = 'local_neuralprophet'
                            logger.info("✅ NeuralProphet forecast complete")
                    except Exception as e:
                        logger.error(f"NeuralProphet error: {e}")
                        model_errors['neuralprophet'] = str(e)
                
                if 'ensemble' in (selected_models or []) and 'ensemble' not in forecasts:
                    try:
                        ensemble = EnsembleForecaster()
                        ensemble.fit(data)
                        forecasts['ensemble'] = ensemble.predict(horizon)
                        inference_sources['ensemble'] = 'local'
                        logger.info("✅ Ensemble forecast complete")
                    except Exception as e:
                        logger.error(f"Ensemble error: {e}")
                        model_errors['ensemble'] = str(e)

            
            # Fallback: statistical forecast if no models succeeded
            if not forecasts:
                logger.warning("All models failed, using statistical fallback")
                forecasts['statistical'] = _statistical_forecast(data['y'].values, horizon)
                inference_sources['statistical'] = 'statistical_fallback'
            
            # Create forecast dates
            last_date = data['ds'].iloc[-1]
            if isinstance(last_date, pd.Timestamp):
                forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon)
            else:
                forecast_dates = pd.date_range(start=pd.Timestamp(last_date) + timedelta(days=1), periods=horizon)
            
            # Use primary forecast (ensemble if available, else first available)
            primary_forecast = forecasts.get('ensemble', list(forecasts.values())[0])
            
            # Create main fan chart
            historical_dates = data['ds'].tolist()[-60:]  # Last 60 days
            historical_values = data['y'].tolist()[-60:]
            
            main_fig = create_enhanced_fan_chart(
                historical_dates=historical_dates,
                historical_values=historical_values,
                forecast_dates=forecast_dates.tolist(),
                forecast_data=primary_forecast,
                all_forecasts=forecasts,
                ticker=ticker,
                show_intervals=selected_intervals or ['80', '95'],
                current_price=current_price
            )
            
            # Create model comparison chart
            comparison_fig = create_model_comparison_chart(
                forecasts=forecasts,
                forecast_dates=forecast_dates.tolist(),
                current_price=current_price,
                ticker=ticker
            )
            
            # Create metrics display
            metrics_children = create_metrics_display(
                forecasts=forecasts,
                current_price=current_price,
                horizon=horizon,
                model_errors=model_errors
            )
            
            # Store forecast data with enhanced metadata
            store_data = {
                'ticker': ticker,
                'horizon': horizon,
                'forecasts': {k: {kk: (vv if isinstance(vv, list) else vv.tolist()) 
                                  for kk, vv in v.items()} 
                              for k, v in forecasts.items()},
                'primary_forecast': {k: (v if isinstance(v, list) else v.tolist()) 
                                     for k, v in primary_forecast.items()},
                'forecast_dates': [str(d) for d in forecast_dates],
                'last_price': float(current_price),
                # Enhanced metadata
                'metadata': {
                    'data_source': data_metadata.get('source', 'unknown'),
                    'data_fetch_duration_ms': data_metadata.get('fetch_duration_ms', 0),
                    'data_timestamp': data_metadata.get('data_timestamp'),
                    'data_points': data_metadata.get('data_points', len(hist)),
                    'inference_sources': inference_sources,
                    'model_errors': model_errors,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
            # Status message with source info
            source_info = f" (data: {data_metadata.get('source', 'unknown')})" if data_metadata.get('source') else ""
            # Add inference info
            unique_sources = set(inference_sources.values())
            inference_info = f", inference: {', '.join(unique_sources)}" if unique_sources else ""
            status = dbc.Alert([
                html.I(className="bi bi-check-circle me-2"),
                f"Forecast generated for {ticker} • {len(forecasts)} model(s) • {horizon} days{source_info}{inference_info}"
            ], color="success", dismissable=True, duration=5000)
            
            return store_data, main_fig, comparison_fig, metrics_children, status, False, price_info, sentiment_display
            
        except Exception as e:
            logger.exception(f"Forecast error: {e}")
            status = dbc.Alert([
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Error: {str(e)}"
            ], color="danger", dismissable=True)
            error_sentiment = html.Div([
                html.I(className="bi bi-x-circle me-2 text-danger"),
                html.Span("Sentiment analysis unavailable", className="text-muted small")
            ])
            return None, _empty_chart(f"Error: {str(e)}"), _empty_chart("Error", 280), [], status, True, "", error_sentiment
    
    @app.callback(
        Output(COMPONENT_IDS['scenario_chart'], 'figure'),
        Output(COMPONENT_IDS['status_banner'], 'children', allow_duplicate=True),
        Input(COMPONENT_IDS['scenario_apply_btn'], 'n_clicks'),
        State(COMPONENT_IDS['forecast_store'], 'data'),
        State(COMPONENT_IDS['scenario_select'], 'value'),
        State(COMPONENT_IDS['scenario_param'], 'value'),
        prevent_initial_call=True
    )
    def apply_scenario(n_clicks, store_data, scenario_type, param_value):
        """Apply scenario to baseline forecast."""
        if not n_clicks or not store_data or not scenario_type:
            raise PreventUpdate
        
        try:
            from ..utils.scenario_simulator import ScenarioSimulator
            
            baseline_forecast = store_data['primary_forecast']['forecast']
            forecast_dates = pd.to_datetime(store_data['forecast_dates'])
            ticker = store_data['ticker']
            
            # Apply scenario
            result = ScenarioSimulator.apply_scenario(
                baseline_forecast=baseline_forecast,
                scenario_type=scenario_type,
                param_value=param_value,
                decay_rate=0.9
            )
            
            # Create comparison chart
            fig = create_scenario_comparison_chart(
                forecast_dates=forecast_dates.tolist(),
                baseline_forecast=baseline_forecast,
                scenario_forecast=result['adjusted_forecast'],
                scenario_name=result['scenario_info']['name'],
                ticker=ticker
            )
            
            status = dbc.Alert([
                html.I(className="bi bi-lightning me-2"),
                f"Scenario applied: {result['scenario_info']['name']} "
                f"(Initial impact: {result['scenario_info']['initial_impact_pct']:+.2f}%)"
            ], color="info", dismissable=True, duration=5000)
            
            return fig, status
            
        except Exception as e:
            logger.exception(f"Scenario error: {e}")
            status = dbc.Alert([
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Scenario error: {str(e)}"
            ], color="danger", dismissable=True)
            return _empty_chart(f"Error: {str(e)}", 280), status
    
    logger.info("✅ Market Forecast callbacks registered")


def _statistical_forecast(prices: np.ndarray, horizon: int) -> Dict[str, List[float]]:
    """Generate statistical forecast as fallback."""
    returns = np.diff(prices) / prices[:-1]
    mean_return = np.mean(returns)
    volatility = np.std(returns)
    
    current_price = prices[-1]
    forecast = np.zeros(horizon)
    
    np.random.seed(42)
    
    for i in range(horizon):
        if i == 0:
            forecast[i] = current_price * (1 + mean_return + volatility * 0.1 * np.random.randn())
        else:
            forecast[i] = forecast[i-1] * (1 + mean_return + volatility * 0.1 * np.random.randn())
    
    std = volatility * current_price * np.sqrt(np.arange(1, horizon + 1))
    
    return {
        'forecast': forecast.tolist(),
        'lower_50': (forecast - 0.675 * std).tolist(),
        'upper_50': (forecast + 0.675 * std).tolist(),
        'lower_80': (forecast - 1.28 * std).tolist(),
        'upper_80': (forecast + 1.28 * std).tolist(),
        'lower_95': (forecast - 1.96 * std).tolist(),
        'upper_95': (forecast + 1.96 * std).tolist(),
    }


def create_enhanced_fan_chart(
    historical_dates: List,
    historical_values: List[float],
    forecast_dates: List,
    forecast_data: Dict,
    all_forecasts: Dict,
    ticker: str,
    show_intervals: List[str],
    current_price: float
) -> go.Figure:
    """Create enhanced fan chart with multiple models."""
    fig = go.Figure()
    
    # Historical data
    fig.add_trace(go.Scatter(
        x=historical_dates,
        y=historical_values,
        mode='lines',
        name='Historical',
        line=dict(color=COLORS['primary'], width=2),
        hovertemplate='<b>%{x|%b %d}</b><br>$%{y:.2f}<extra>Historical</extra>'
    ))
    
    # Confidence intervals (fan effect)
    intervals_config = [
        ('95', COLORS['success'], 0.1, '95% Confidence'),
        ('80', COLORS['success'], 0.2, '80% Confidence'),
        ('50', COLORS['success'], 0.3, '50% Confidence'),
    ]
    
    for interval, color, opacity, label in intervals_config:
        if interval not in show_intervals:
            continue
        
        lower_key = f'lower_{interval}'
        upper_key = f'upper_{interval}'
        
        if lower_key not in forecast_data or upper_key not in forecast_data:
            continue
        
        # Upper bound
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=forecast_data[upper_key],
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Lower bound with fill
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=forecast_data[lower_key],
            mode='lines',
            name=label,
            line=dict(width=0),
            fillcolor=f'rgba(16, 185, 129, {opacity})',
            fill='tonexty',
            hovertemplate=f'<b>%{{x|%b %d}}</b><br>{label}<br>${{y:.2f}}<extra></extra>'
        ))
    
    # Main forecast line
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=forecast_data['forecast'],
        mode='lines+markers',
        name='Forecast',
        line=dict(color=COLORS['success'], width=3),
        marker=dict(size=4),
        hovertemplate='<b>%{x|%b %d}</b><br>Forecast: $%{y:.2f}<extra></extra>'
    ))
    
    # Add other model forecasts as dotted lines
    model_colors = {
        'prophet': COLORS['prophet'],
        'arima': COLORS['arima'],
        'lstm': COLORS['lstm'],
        'qlib': COLORS['qlib'],
        'neuralprophet': COLORS['neuralprophet'],
        'ensemble': COLORS['ensemble'],
        'statistical': '#9ca3af'
    }
    
    for model_name, model_forecast in all_forecasts.items():
        if model_name == 'ensemble':  # Already shown as main
            continue
        
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=model_forecast['forecast'],
            mode='lines',
            name=model_name.upper(),
            line=dict(color=model_colors.get(model_name, '#6b7280'), width=1.5, dash='dot'),
            opacity=0.7,
            hovertemplate=f'<b>%{{x|%b %d}}</b><br>{model_name.upper()}: $%{{y:.2f}}<extra></extra>'
        ))
    
    # Add current price marker
    fig.add_hline(
        y=current_price, 
        line_dash="dash", 
        line_color=COLORS['muted'],
        annotation_text=f"Current: ${current_price:.2f}",
        annotation_position="top right"
    )
    
    # Layout
    fig.update_layout(
        title=dict(
            text=f"<b>{ticker}</b> Price Forecast",
            font=dict(size=18, color=COLORS['text']),
            x=0.5
        ),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            tickformat="%b %d",
            tickfont=dict(color=COLORS['muted'])
        ),
        yaxis=dict(
            title="Price ($)",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            tickformat="$,.2f",
            tickfont=dict(color=COLORS['muted'])
        ),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.5)',
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(l=60, r=40, t=80, b=60)
    )
    
    return fig


def create_model_comparison_chart(
    forecasts: Dict,
    forecast_dates: List,
    current_price: float,
    ticker: str
) -> go.Figure:
    """Create bar chart comparing model predictions."""
    fig = go.Figure()
    
    model_colors = {
        'prophet': COLORS['prophet'],
        'arima': COLORS['arima'],
        'lstm': COLORS['lstm'],
        'qlib': COLORS['qlib'],
        'neuralprophet': COLORS['neuralprophet'],
        'ensemble': COLORS['ensemble'],
        'statistical': '#9ca3af'
    }
    
    model_names = []
    final_prices = []
    colors = []
    returns = []
    
    for model_name, forecast_data in forecasts.items():
        model_names.append(model_name.upper())
        final_price = forecast_data['forecast'][-1]
        final_prices.append(final_price)
        colors.append(model_colors.get(model_name, '#6b7280'))
        ret = ((final_price - current_price) / current_price) * 100
        returns.append(ret)
    
    # Create bar chart
    fig.add_trace(go.Bar(
        x=model_names,
        y=returns,
        marker_color=colors,
        text=[f"{r:+.1f}%" for r in returns],
        textposition='outside',
        textfont=dict(color=COLORS['text']),
        hovertemplate='<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_color=COLORS['muted'], line_dash='dash')
    
    fig.update_layout(
        title=dict(
            text="Model Comparison (Expected Return)",
            font=dict(size=12, color=COLORS['text']),
            x=0.5
        ),
        xaxis=dict(
            tickfont=dict(color=COLORS['muted'], size=10),
            showgrid=False
        ),
        yaxis=dict(
            title="Return (%)",
            tickfont=dict(color=COLORS['muted']),
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.5)',
        height=280,
        margin=dict(l=50, r=20, t=40, b=40),
        showlegend=False
    )
    
    return fig


def create_scenario_comparison_chart(
    forecast_dates: List,
    baseline_forecast: List[float],
    scenario_forecast: List[float],
    scenario_name: str,
    ticker: str
) -> go.Figure:
    """Create comparison chart for scenario analysis."""
    fig = go.Figure()
    
    # Baseline
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=baseline_forecast,
        mode='lines',
        name='Baseline',
        line=dict(color=COLORS['muted'], width=2, dash='dash'),
        hovertemplate='<b>Baseline</b><br>%{x|%b %d}<br>$%{y:.2f}<extra></extra>'
    ))
    
    # Scenario
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=scenario_forecast,
        mode='lines',
        name=scenario_name,
        line=dict(color=COLORS['warning'], width=2),
        fill='tonexty',
        fillcolor='rgba(245, 158, 11, 0.2)',
        hovertemplate=f'<b>{scenario_name}</b><br>%{{x|%b %d}}<br>${{y:.2f}}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Scenario: {scenario_name}",
            font=dict(size=12, color=COLORS['text']),
            x=0.5
        ),
        xaxis=dict(
            tickfont=dict(color=COLORS['muted'], size=9),
            showgrid=False,
            tickformat="%b %d"
        ),
        yaxis=dict(
            tickfont=dict(color=COLORS['muted']),
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            tickformat="$,.0f"
        ),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.5)',
        height=280,
        margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(size=9)
        )
    )
    
    return fig


def create_metrics_display(
    forecasts: Dict,
    current_price: float,
    horizon: int,
    model_errors: Dict
) -> List:
    """Create metrics display cards."""
    metrics = []
    
    # Summary metrics
    all_returns = []
    for model_name, forecast_data in forecasts.items():
        final_price = forecast_data['forecast'][-1]
        ret = ((final_price - current_price) / current_price) * 100
        all_returns.append(ret)
    
    avg_return = np.mean(all_returns)
    
    # Header card
    metrics.append(
        html.Div([
            html.Div([
                html.Span("Avg Expected Return", className="small text-white-50"),
                html.H4(f"{avg_return:+.2f}%", 
                       className=f"mb-0 {'text-success' if avg_return >= 0 else 'text-danger'} fw-bold")
            ], className="text-center")
        ], className="p-2 mb-3 rounded", style={'backgroundColor': COLORS['accent']})
    )
    
    # Individual model results
    for model_name, forecast_data in forecasts.items():
        final_price = forecast_data['forecast'][-1]
        change = final_price - current_price
        change_pct = (change / current_price) * 100
        
        color = 'success' if change >= 0 else 'danger'
        icon = '▲' if change >= 0 else '▼'
        
        model_colors = {
            'prophet': COLORS['prophet'],
            'arima': COLORS['arima'],
            'lstm': COLORS['lstm'],
            'qlib': COLORS['qlib'],
            'neuralprophet': COLORS['neuralprophet'],
            'ensemble': COLORS['ensemble'],
            'statistical': '#9ca3af'
        }
        
        metrics.append(
            html.Div([
                html.Div([
                    html.Span("●", style={'color': model_colors.get(model_name, '#6b7280')}),
                    html.Span(f" {model_name.upper()}", className="text-white small fw-bold ms-1"),
                ], className="d-flex align-items-center mb-1"),
                html.Div([
                    html.Span(f"${final_price:.2f}", className="text-white"),
                    html.Span(f" {icon} {abs(change_pct):.2f}%", className=f"text-{color} small ms-2")
                ])
            ], className="p-2 mb-2 rounded", style={'backgroundColor': 'rgba(255,255,255,0.05)'})
        )
    
    # Show errors if any
    if model_errors:
        metrics.append(
            html.Div([
                html.Span("⚠️ Some models had issues", className="text-warning small")
            ], className="mt-2")
        )
    
    return metrics


__all__ = ['layout', 'register_callbacks', 'COMPONENT_IDS']
