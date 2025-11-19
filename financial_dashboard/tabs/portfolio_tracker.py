"""
Portfolio Tracker Tab
Real-time portfolio tracking with Alpaca integration
Shows positions, P/L, analytics, and order history
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)

# Import market hours utilities for caching when market is closed
try:
    from financial_dashboard.utils.market_hours import is_market_open, cache_portfolio_data, get_cached_portfolio_data
    MARKET_HOURS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Market hours utilities not available: {e}")
    MARKET_HOURS_AVAILABLE = False

# Import sub-modules for analytics, optimization, positions, orders, and factor analysis
SUBMODULES_AVAILABLE = False
try:
    from . import portfolio_analytics, portfolio_optimization, portfolio_positions, portfolio_orders, portfolio_factors
    SUBMODULES_AVAILABLE = True
    logger.info("✅ Portfolio sub-modules imported successfully")
except Exception as e:
    logger.warning(f"Portfolio sub-modules not available: {e}")

# Try to import Alpaca client
ALPACA_AVAILABLE = False
try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except Exception as e:
    logger.warning(f"Alpaca not available: {e}")


def get_alpaca_client():
    """Get Alpaca trading client from environment."""
    if not ALPACA_AVAILABLE:
        return None
    
    key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
    secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
    if not key or not secret:
        return None
    
    # Default to paper trading
    paper = True
    return TradingClient(key, secret, paper=paper)


def layout():
    """Build portfolio tracker layout."""
    return dbc.Container([
        # Alpaca credential alert (hidden unless credentials missing)
        dbc.Alert(id='portfolio-alpaca-alert', is_open=False, color='warning'),

        html.H2("Portfolio Tracker", className="mt-3 mb-3"),
        
        # Summary cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Portfolio Value", className="text-muted"),
                        html.H3(id='portfolio-value', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Invested", className="text-muted"),
                        html.H3(id='portfolio-invested', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Unrealized P/L", className="text-muted"),
                        html.H3(id='portfolio-unrealized-pl', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Buying Power", className="text-muted"),
                        html.H3(id='portfolio-buying-power', children="$0.00")
                    ])
                ])
            ], width=3)
        ], className="mb-4"),
        
        # Refresh button
        dbc.Row([
            dbc.Col([
                dbc.Button("🔄 Refresh", id='portfolio-refresh-btn', color='primary', size='sm')
            ])
        ], className="mb-3"),
        
        # Tabs for different views
        dbc.Tabs(id="portfolio-tracker-subtabs", active_tab="tab-positions", children=[
            # Positions tab
            dbc.Tab(label="Positions", tab_id="tab-positions", children=[
                dbc.Container([
                    html.H5("Current Positions", className="mt-3 mb-3"),
                    html.Div(id='portfolio-positions-table')
                ], fluid=True)
            ]),
            
            # Orders tab
            dbc.Tab(label="Order History", tab_id="tab-orders", children=[
                dbc.Container([
                    html.H5("Order History", className="mt-3 mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.RadioItems(
                                id='order-filter',
                                options=[
                                    {'label': 'All Orders', 'value': 'all'},
                                    {'label': 'Open Orders', 'value': 'open'},
                                    {'label': 'Filled Orders', 'value': 'filled'}
                                ],
                                value='all',
                                inline=True
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Date Range:"),
                            dcc.DatePickerRange(
                                id='order-date-range',
                                start_date=(datetime.now() - timedelta(days=30)).date(),
                                end_date=datetime.now().date(),
                                display_format='YYYY-MM-DD'
                            )
                        ], width=6)
                    ], className="mb-3"),
                    html.Div(id='portfolio-orders-table')
                ], fluid=True)
            ]),
            
            # Analytics tab
            dbc.Tab(label="Analytics", tab_id="tab-analytics", children=[
                dbc.Container([
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
                    
                    html.Div(id='portfolio-analytics-content'),
                    
                    # Monte Carlo results
                    html.Div(id='monte-carlo-results', className="mt-4")
                ], fluid=True)
            ]),
            
            # Factor Exposure tab
            dbc.Tab(label="Factor Exposure", tab_id="tab-factors", children=[
                dbc.Container([
                    html.H5("Factor Exposure Analysis", className="mt-3 mb-3"),
                    html.P("SHAP-based factor attribution for current positions", className="text-muted"),
                    html.Div(id='portfolio-factor-exposure-content')
                ], fluid=True)
            ]),
            
            # Optimization tab
            dbc.Tab(label="Optimization", tab_id="tab-optimization", children=[
                portfolio_optimization.layout() if SUBMODULES_AVAILABLE else html.P("Optimization module not available", className="text-muted p-3")
            ])
        ]),
        
        # Hidden interval for auto-refresh
        dcc.Interval(id='portfolio-interval', interval=30*1000, n_intervals=0),
        
        # Store for portfolio data - initialize with empty dict so callbacks fire
        dcc.Store(id='portfolio-data-store', data={'positions': []}),
        
        # Hidden trigger for initial load
        dcc.Store(id='portfolio-load-trigger', data=1),
        
        # Inspect Position Modal (must be at root level, not inside tabs)
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id='inspect-modal-title')),
            dbc.ModalBody(id='inspect-modal-body'),
            dbc.ModalFooter(
                dbc.Button("Close", id='inspect-modal-close', className="ms-auto", n_clicks=0)
            )
        ], id='inspect-modal', size='lg', is_open=False)
        
    ], fluid=True)


def register_callbacks(app):
    """Register portfolio tracker callbacks."""
    
    @app.callback(
        [Output('portfolio-value', 'children'),
         Output('portfolio-invested', 'children'),
         Output('portfolio-unrealized-pl', 'children'),
         Output('portfolio-buying-power', 'children'),
         Output('portfolio-data-store', 'data'),
         Output('portfolio-alpaca-alert', 'children'),
         Output('portfolio-alpaca-alert', 'is_open')],
        [Input('portfolio-refresh-btn', 'n_clicks'),
         Input('portfolio-interval', 'n_intervals'),
         Input('portfolio-load-trigger', 'data')],
        prevent_initial_call=False
    )
    def update_portfolio_summary(n_clicks, n_intervals, load_trigger):
        logger.info(f"🔥 Portfolio summary callback fired! n_clicks={n_clicks}, n_intervals={n_intervals}, load_trigger={load_trigger}")
        """Update portfolio summary from Alpaca with market hours caching."""
        try:
            # Check if market is closed and we have cached data
            if MARKET_HOURS_AVAILABLE and not is_market_open():
                cached = get_cached_portfolio_data()
                if cached:
                    logger.info("Market closed - using cached portfolio data")
                    # Extract values from cached data
                    portfolio_value = cached['account']['portfolio_value']
                    total_cost = sum(p['cost_basis'] for p in cached['positions'])
                    unrealized_pl = sum(p['unrealized_pl'] for p in cached['positions'])
                    buying_power = cached['account']['buying_power']
                    
                    return (
                        f"${portfolio_value:,.2f} 🌙",  # Moon emoji indicates cached data
                        f"${total_cost:,.2f}",
                        f"${unrealized_pl:,.2f}" + (" 📈" if unrealized_pl >= 0 else " 📉"),
                        f"${buying_power:,.2f}",
                        cached,
                        "",
                        False
                    )
            
            # Market is open or no cache - fetch live data
            client = get_alpaca_client()
            if not client:
                msg = ("Alpaca client not available. Ensure the Alpaca SDK is installed and "
                       "set APCA_API_KEY_ID / APCA_API_SECRET_KEY (or APCA_API_KEY / APCA_API_SECRET) in the environment.")
                return "$0.00", "$0.00", "$0.00", "$0.00", None, msg, True
            
            account = client.get_account()
            positions = client.get_all_positions()
            
            portfolio_value = float(account.portfolio_value)
            equity = float(account.equity)
            buying_power = float(account.buying_power)
            
            # Calculate total cost basis and unrealized P/L
            total_cost = 0.0
            unrealized_pl = 0.0
            
            positions_data = []
            for pos in positions:
                cost_basis = float(pos.cost_basis)
                market_value = float(pos.market_value)
                unrealized = market_value - cost_basis
                
                total_cost += cost_basis
                unrealized_pl += unrealized
                
                positions_data.append({
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'cost_basis': cost_basis,
                    'market_value': market_value,
                    'unrealized_pl': unrealized,
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100
                })
            
            # Store data for other callbacks
            store_data = {
                'positions': positions_data,
                'account': {
                    'portfolio_value': portfolio_value,
                    'equity': equity,
                    'buying_power': buying_power,
                    'cash': float(account.cash)
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache the data if market hours tracking is available
            if MARKET_HOURS_AVAILABLE:
                try:
                    cache_portfolio_data(store_data)
                    logger.debug("Cached portfolio data for after-hours use")
                except Exception as e:
                    logger.warning(f"Failed to cache portfolio data: {e}")
            
            return (
                f"${portfolio_value:,.2f}",
                f"${total_cost:,.2f}",
                f"${unrealized_pl:,.2f}" + (" 📈" if unrealized_pl >= 0 else " 📉"),
                f"${buying_power:,.2f}",
                store_data,
                "",
                False
            )
            
        except Exception as e:
            logger.error(f"Error updating portfolio summary: {e}")
            return "$0.00", "$0.00", "$0.00", "$0.00", None, f"Error: {str(e)}", True
    
    # Register sub-module callbacks for analytics, optimization, positions, orders, and factor analysis
    if SUBMODULES_AVAILABLE:
        logger.info("Registering portfolio sub-module callbacks...")
        try:
            portfolio_analytics.register_callbacks(app)
            logger.info("  ✅ Analytics callbacks registered")
        except Exception as e:
            logger.error(f"  ❌ Failed to register analytics callbacks: {e}")
        
        try:
            portfolio_optimization.register_callbacks(app)
            logger.info("  ✅ Optimization callbacks registered")
        except Exception as e:
            logger.error(f"  ❌ Failed to register optimization callbacks: {e}")
        
        try:
            portfolio_positions.register_callbacks(app)
            logger.info("  ✅ Positions callbacks registered")
        except Exception as e:
            logger.error(f"  ❌ Failed to register positions callbacks: {e}")
        
        try:
            portfolio_orders.register_callbacks(app)
            logger.info("  ✅ Orders callbacks registered")
        except Exception as e:
            logger.error(f"  ❌ Failed to register orders callbacks: {e}")
        
        try:
            portfolio_factors.register_callbacks(app)
            logger.info("  ✅ Factor analysis callbacks registered")
        except Exception as e:
            logger.error(f"  ❌ Failed to register factor callbacks: {e}")
        
        logger.info("✅ All portfolio sub-module callbacks registered successfully")
    else:
        logger.warning("⚠️  Portfolio sub-modules not available - some functionality may be limited")
