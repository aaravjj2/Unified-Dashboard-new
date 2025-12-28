"""
Portfolio Tracker - Main Assembler (Refactored)
Coordinates modular portfolio components

Sub-modules:
- portfolio_positions.py: Current holdings with inspect modal
- portfolio_orders.py: Order history with date filtering
- portfolio_analytics.py: Advanced analytics with caching and Monte Carlo
- portfolio_factors.py: SHAP-based factor exposure
- portfolio_optimization.py: Portfolio optimization tool

This file acts as a lightweight coordinator that imports and assembles all sub-modules.
"""

import os
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

# Import modular components using package-relative imports so this module
# works when loaded as part of the `financial_dashboard` package.
try:
    from . import (
        portfolio_positions,
        portfolio_orders,
        portfolio_analytics,
        portfolio_factors,
        portfolio_optimization
    )
except Exception as e:
    # Fallback: if imports fail (import path issues in some runtimes), log
    # the error and synthesize minimal stub modules so the main layout
    # still renders and the tabs show helpful placeholders instead of
    # being empty.
    logger.exception(f"Failed to import portfolio submodules: {e}")

    class _MissingTab:
        def __init__(self, name):
            self._name = name

        def layout(self):
            return html.Div([
                html.H5(f"{self._name} (module missing)", className="text-muted"),
                html.P("This submodule failed to import. Check server logs for details.")
            ])

        def register_callbacks(self, app):
            # No-op: missing module can't register callbacks
            return None

    portfolio_positions = _MissingTab('Positions')
    portfolio_orders = _MissingTab('Order History')
    portfolio_analytics = _MissingTab('Analytics')
    portfolio_factors = _MissingTab('Factor Exposure')
    portfolio_optimization = _MissingTab('Optimization')

# Try to import database utilities
try:
    from utils import db_utils
    DB_AVAILABLE = True
except ImportError:
    logger.warning("Database utilities not available")
    DB_AVAILABLE = False

def get_alpaca_client():
    """Get Alpaca trading client from environment."""
    # Import TradingClient lazily so module import-time failures (or optional deps)
    # don't permanently disable Alpaca usage for this module.
    try:
        from alpaca.trading.client import TradingClient
    except Exception as e:
        logger.warning(f"Alpaca TradingClient import failed (will disable Alpaca here): {e}")
        return None

    # Accept multiple env var names as fallbacks. Prefer APCA_* canonical names.
    candidates = [
        ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY"),
        ("APCA_API_KEY", "APCA_API_SECRET"),
        ("ALPACA_KEY_WEEKLY", "ALPACA_SECRET_WEEKLY"),
        ("ALPACA_KEY_MONTHLY", "ALPACA_SECRET_MONTHLY"),
        ("APCA_EMERGENCY_KEY", "APCA_API_SECRET_KEY")
    ]

    key = None
    secret = None
    used_pair = None
    for kname, sname in candidates:
        k = os.getenv(kname)
        s = os.getenv(sname)
        if k and s:
            key = k
            secret = s
            used_pair = (kname, sname)
            break

    # If we still don't have both key/secret, give up
    if not key or not secret:
        logger.info("Alpaca credentials not found in environment (checked multiple names)")
        return None

    # Log which env var pair we used (helps debug CI/worker env differences)
    # Log which env var pair we used (helps debug CI/worker env differences)
    if used_pair:
        try:
            logger.info(f"Using Alpaca keys from env vars: {used_pair[0]} / {used_pair[1]}")
            logger.info(f"DEBUG: Key value starts with: {key[:5]}...")
        except Exception:
            pass

    # Default to paper trading unless overridden
    paper = True
    # If an explicit endpoint is provided, TradingClient may accept it via "base_url" or
    # the older clients may rely on paper flag — prefer the simple constructor used elsewhere.
    try:
        return TradingClient(key, secret, paper=paper)
    except Exception as e:
        logger.warning(f"Failed to construct Alpaca TradingClient: {e}")
        return None


def layout():
    """Build portfolio tracker layout by assembling sub-modules."""
    # Try to pre-load portfolio cache so the client-side store is populated on first render
    preload_store = None
    try:
        cache_path = Path(__file__).parent.parent / 'cache' / 'portfolio_data.json'
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                preload_store = json.load(f)
            logger.info(f"Loaded portfolio cache for layout preload: {cache_path}")
    except Exception as e:
        logger.debug(f"Failed to preload portfolio cache: {e}")

    # If no cache present, attempt a best-effort live fetch (non-blocking fallback)
    # This makes the UI show live values on first render when Alpaca creds are available.
    if not preload_store:
        try:
            logger.info("Attempting live alpaca preload for portfolio layout")
            client = get_alpaca_client()
            if client:
                try:
                    account = client.get_account()
                    positions = client.get_all_positions()

                    positions_data = []
                    for pos in positions:
                        positions_data.append({
                            'symbol': pos.symbol,
                            'qty': float(pos.qty),
                            'avg_entry_price': float(getattr(pos, 'avg_entry_price', 0.0) or 0.0),
                            'current_price': float(getattr(pos, 'current_price', 0.0) or 0.0),
                            'cost_basis': float(getattr(pos, 'cost_basis', 0.0) or 0.0),
                            'market_value': float(getattr(pos, 'market_value', 0.0) or 0.0),
                            'unrealized_pl': float(getattr(pos, 'unrealized_pl', 0.0) or 0.0),
                            'unrealized_plpc': float(getattr(pos, 'unrealized_plpc', 0.0) or 0.0) * 100
                        })

                    preload_store = {
                        'positions': positions_data,
                        'account': {
                            'portfolio_value': float(getattr(account, 'equity', 0.0) or 0.0),
                            'equity': float(getattr(account, 'equity', 0.0) or 0.0),
                            'buying_power': float(getattr(account, 'buying_power', 0.0) or 0.0),
                            'cash': float(getattr(account, 'cash', 0.0) or 0.0)
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info("Live alpaca preload succeeded for portfolio layout")
                except Exception as e:
                    logger.warning(f"Live alpaca preload failed: {e}")
            else:
                # As a fallback to the TradingClient approach, try the local API endpoint
                # using a short HTTP request. This avoids importing alpaca-py here and
                # helps in cases where the endpoint (which has its own env-loading
                # and client wiring) can return the live summary.
                try:
                    import json as _json
                    import urllib.request as _ur
                    import urllib.error as _ue
                    _url = os.getenv('PORTFOLIO_SUMMARY_URL', 'http://127.0.0.1:8050/api/portfolio_summary')
                    _req = _ur.Request(_url, headers={'User-Agent': 'unified-dashboard/1.0'})
                    with _ur.urlopen(_req, timeout=1) as _resp:
                        try:
                            _data = _json.load(_resp)
                            if _data and _data.get('status') == 'success' and _data.get('summary'):
                                s = _data['summary']
                                preload_store = {
                                    'positions': _data.get('data') or [],
                                    'account': {
                                        'portfolio_value': float(s.get('portfolio_value', 0.0) or 0.0),
                                        'equity': float(s.get('portfolio_value', 0.0) or 0.0),
                                        'buying_power': float(s.get('buying_power', 0.0) or 0.0),
                                        'cash': float(s.get('cash', 0.0) or 0.0)
                                    },
                                    'timestamp': datetime.now().isoformat()
                                }
                                logger.info('Preload from local /api/portfolio_summary succeeded')
                        except Exception:
                            pass
                except Exception:
                    # Non-fatal fallback; continue to let layout render with $0.00
                    pass
        except Exception:
            # Non-fatal: any errors here should not prevent layout from rendering
            pass

    # Prepare initial display strings so server-rendered HTML reflects preload_store when available
    def _fmt_money(x):
        try:
            return f"${float(x):,.2f}"
        except Exception:
            return "$0.00"

    if preload_store and isinstance(preload_store, dict):
        account = preload_store.get('account', {}) or {}
        positions = preload_store.get('positions', []) or []
        init_portfolio_value = _fmt_money(account.get('portfolio_value', 0.0))
        init_total_invested = _fmt_money(sum([p.get('cost_basis', 0.0) for p in positions]))
        init_unrealized_pl = _fmt_money(sum([p.get('unrealized_pl', 0.0) for p in positions]))
        init_buying_power = _fmt_money(account.get('buying_power', 0.0))
    else:
        init_portfolio_value = "$0.00"
        init_total_invested = "$0.00"
        init_unrealized_pl = "$0.00"
        init_buying_power = "$0.00"

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
                        html.H3(id='portfolio-value', children=init_portfolio_value)
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Invested", className="text-muted"),
                        html.H3(id='portfolio-invested', children=init_total_invested)
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Unrealized P/L", className="text-muted"),
                        html.H3(id='portfolio-unrealized-pl', children=init_unrealized_pl)
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Buying Power", className="text-muted"),
                        html.H3(id='portfolio-buying-power', children=init_buying_power)
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
        
        # Tabs for different views - assembled from sub-modules
        # Assign explicit tab_id values so callbacks can react only when 'positions' is active
        dbc.Tabs(id="portfolio-tracker-subtabs", children=[
            # Positions tab
            dbc.Tab(label="Positions", tab_id='positions', children=[
                portfolio_positions.layout()
            ]),
            
            # Orders tab
            dbc.Tab(label="Order History", tab_id='orders', children=[
                portfolio_orders.layout()
            ]),
            
            # Analytics tab
            dbc.Tab(label="Analytics", tab_id='analytics', children=[
                portfolio_analytics.layout()
            ]),
            
            # Factor Exposure tab
            dbc.Tab(label="Factor Exposure", tab_id='factors', children=[
                portfolio_factors.layout()
            ]),
            
            # Optimization tab (NEW)
            dbc.Tab(label="Optimization", tab_id='optimization', children=[
                portfolio_optimization.layout()
            ])
        ], active_tab='positions'),
        
        # Hidden interval for auto-refresh
        dcc.Interval(id='portfolio-interval', interval=30*1000, n_intervals=0),
        
    # Store for portfolio data (preloaded from cache when available)
    dcc.Store(id='portfolio-data-store', data=preload_store),
        
        # Hidden trigger for initial load
        dcc.Store(id='portfolio-load-trigger', data=1)
        
    ], fluid=True)


def register_callbacks(app):
    """Register callbacks - main coordinator and sub-module callbacks."""
    # Idempotency guard: prevent duplicate registration
    if getattr(app, '_portfolio_callbacks_registered', False):
        logger.info("⚠️  Portfolio callbacks already registered, skipping")
        return
    setattr(app, '_portfolio_callbacks_registered', True)
    
    # Initialize database on startup
    if DB_AVAILABLE:
        try:
            db_utils.initialize_database()
            logger.info("Portfolio database initialized")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    # Main portfolio summary callback
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
         Input('portfolio-load-trigger', 'data')]
    )
    def update_portfolio_summary(n_clicks, n_intervals, load_trigger):
        """Update portfolio summary from Alpaca and save snapshot to database."""
        try:
            client = get_alpaca_client()
            # Debug: log whether Alpaca client was obtained in this process
            try:
                logger.info(f"DEBUG [portfolio] Alpaca client available: {bool(client)}")
            except Exception:
                # Fallback in case logger formatting fails for any reason
                logger.info("DEBUG [portfolio] Alpaca client availability checked")
            if not client:
                # Fallback: try to populate store from on-disk cache so the UI can show positions
                cache_path = Path(__file__).parent.parent / 'cache' / 'portfolio_data.json'
                if cache_path.exists():
                    try:
                        with open(cache_path, 'r') as f:
                            cached = json.load(f)
                        positions = cached.get('positions', [])
                        account = cached.get('account', {})
                        portfolio_value = account.get('portfolio_value', 0.0) if account else 0.0
                        total_cost = sum([p.get('cost_basis', 0.0) for p in positions])
                        unrealized_pl = sum([p.get('unrealized_pl', 0.0) for p in positions])

                        store_data = {
                            'positions': positions,
                            'account': account,
                            'timestamp': cached.get('timestamp') or datetime.now().isoformat()
                        }

                        return (
                            f"${portfolio_value:,.2f}",
                            f"${total_cost:,.2f}",
                            f"${unrealized_pl:,.2f}",
                            f"${account.get('buying_power', 0.0):,.2f}",
                            store_data,
                            "",
                            False
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load portfolio cache: {e}")

                msg = ("Alpaca client not available. Ensure the Alpaca SDK is installed and "
                       "set APCA_API_KEY_ID / APCA_API_SECRET_KEY (or APCA_API_KEY / APCA_API_SECRET) in the environment.")
                return "$0.00", "$0.00", "$0.00", "$0.00", None, msg, True
            
            # Attempt to call Alpaca account endpoints and log lightweight diagnostics
            try:
                account = client.get_account()
                positions = client.get_all_positions()
                try:
                    logger.info(f"DEBUG [portfolio] Alpaca account fetched: portfolio_value={getattr(account, 'portfolio_value', 'N/A')}")
                except Exception:
                    logger.info("DEBUG [portfolio] Alpaca account fetched (value unreadable)")
            except Exception as alp_e:
                logger.error(f"DEBUG [portfolio] Alpaca client call failed: {alp_e}")
                # If Alpaca call fails, fall back to cache as below
                account = None
                positions = []
            
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
            
            # Save snapshot to database
            if DB_AVAILABLE:
                try:
                    db_utils.save_daily_snapshot(store_data['account'], positions_data)
                except Exception as e:
                    logger.error(f"Error saving snapshot: {e}")
            
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
            # Attempt to recover by reading the on-disk cache before failing
            try:
                cache_path = Path(__file__).parent.parent / 'cache' / 'portfolio_data.json'
                if cache_path.exists():
                    with open(cache_path, 'r') as f:
                        cached = json.load(f)
                    positions = cached.get('positions', [])
                    account = cached.get('account', {})
                    portfolio_value = account.get('portfolio_value', 0.0) if account else 0.0
                    total_cost = sum([p.get('cost_basis', 0.0) for p in positions])
                    unrealized_pl = sum([p.get('unrealized_pl', 0.0) for p in positions])

                    store_data = {
                        'positions': positions,
                        'account': account,
                        'timestamp': cached.get('timestamp') or datetime.now().isoformat()
                    }

                    return (
                        f"${portfolio_value:,.2f}",
                        f"${total_cost:,.2f}",
                        f"${unrealized_pl:,.2f}",
                        f"${account.get('buying_power', 0.0):,.2f}",
                        store_data,
                        "",
                        False
                    )
            except Exception as e2:
                logger.error(f"Failed to recover portfolio from cache: {e2}")

            return "$0.00", "$0.00", "$0.00", "$0.00", None, f"Error: {str(e)}", True
    
    # Register all sub-module callbacks
    portfolio_positions.register_callbacks(app)
    portfolio_orders.register_callbacks(app)
    portfolio_analytics.register_callbacks(app)
    portfolio_factors.register_callbacks(app)
    portfolio_optimization.register_callbacks(app)
    
    logger.info("Portfolio tracker callbacks registered (modular architecture)")
