"""
Portfolio Positions Tab - Current Holdings View with Inspect Modal
Part of refactored Portfolio Tracker module

PHASE 4: Integrated with Market Trends signals via sync_manifest.py
"""

import os
import logging
import json
from datetime import datetime, timedelta
import time
from pathlib import Path
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
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

# PHASE 4: Import sync manifest utilities for cross-tab coordination
from financial_dashboard.utils.sync_manifest import (
    read_sync_manifest,
    mark_dependency,
    is_data_stale,
)
from financial_dashboard.utils.normalize import normalize_positions_list

logger = logging.getLogger(__name__)


def _load_market_trends_signals():
    """
    Load Market Trends signals from cache/market_brief.json.
    
    Returns:
        dict: Mapping of ticker -> signal data, or empty dict if unavailable
    """
    try:
        cache_dir = Path(__file__).parent.parent / 'cache'
        market_brief_path = cache_dir / 'market_brief.json'
        
        if not market_brief_path.exists():
            logger.warning(f"Market brief cache not found: {market_brief_path}")
            return {}
        
        with open(market_brief_path, 'r') as f:
            brief_data = json.load(f)
        
        # Extract detailed signals
        detailed = brief_data.get('detailed', [])
        
        if not detailed:
            logger.warning("Market brief cache has no detailed data")
            return {}
        
        # Build ticker -> signal mapping
        signal_map = {}
        for signal in detailed:
            ticker = signal.get('Ticker') or signal.get('ticker')
            if ticker:
                signal_map[ticker] = {
                    'trend_signal': signal.get('Signal', signal.get('signal', 'N/A')),
                    'momentum': signal.get('Momentum', signal.get('momentum', 0.0)),
                    'sentiment': signal.get('Sentiment', signal.get('sentiment', 0.0)),
                    'volatility': signal.get('Volatility', signal.get('volatility', 0.0))
                }
        
        logger.info(f"✅ Loaded Market Trends signals for {len(signal_map)} tickers")
        return signal_map
        
    except Exception as e:
        logger.error(f"Failed to load Market Trends signals: {e}")
        return {}


# normalization helper moved to utils.normalize for lightweight imports and testing


def layout():
    """Build positions tab layout with inspect modal and SHAP regeneration button.
    
    PHASE 4D FIX: Renders positions table server-side when cache exists to avoid
    callback race and ensure E2E tests see table immediately on first render.
    """
    # Attempt server-side render from cache for deterministic first-render
    initial_table_content = html.P("Loading positions...", className="text-muted")
    
    try:
        cache_path = Path(__file__).parent.parent / 'cache' / 'portfolio_data.json'
        if cache_path.exists():
            import json
            with open(cache_path, 'r') as f:
                cached = json.load(f)
                positions = cached.get('positions', [])
            
            if positions:
                logger.info(f"✅ Server-side render: Loading {len(positions)} positions from cache into layout")
                # Build positions DataFrame for server-side render
                df = pd.DataFrame(positions)
                
                # Normalize columns (same logic as callback)
                if 'symbol' not in df.columns and 'ticker' in df.columns:
                    df['symbol'] = df['ticker']
                
                numeric_cols = ['qty', 'avg_entry_price', 'current_price', 'cost_basis', 'market_value', 'unrealized_pl', 'unrealized_plpc']
                for col in numeric_cols:
                    if col not in df.columns:
                        df[col] = 0.0
                    else:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
                # Calculate weight
                total_value = df['market_value'].sum() if 'market_value' in df.columns else 0.0
                if total_value and total_value != 0:
                    df['weight_pct'] = (df['market_value'] / total_value * 100).round(2)
                else:
                    df['weight_pct'] = 0.0
                
                # Add placeholder columns for Market Trends signals (will be updated by callback if available)
                df['trend_signal'] = 'N/A'
                df['momentum'] = 0.0
                df['sentiment'] = 0.0
                df['volatility'] = 0.0
                
                # Format for display
                df_display = df.copy()
                df_display['avg_entry_price'] = df['avg_entry_price'].apply(lambda x: f"${x:.2f}")
                df_display['current_price'] = df['current_price'].apply(lambda x: f"${x:.2f}")
                df_display['cost_basis'] = df['cost_basis'].apply(lambda x: f"${x:.2f}")
                df_display['market_value'] = df['market_value'].apply(lambda x: f"${x:.2f}")
                df_display['unrealized_pl'] = df['unrealized_pl'].apply(lambda x: f"${x:.2f}")
                df_display['unrealized_plpc'] = df['unrealized_plpc'].apply(lambda x: f"{x:.2f}%")
                df_display['weight_pct'] = df_display['weight_pct'].apply(lambda x: f"{x:.2f}%")
                df_display['actions'] = '🔍 Inspect'
                
                # Server-side render of DataTable
                initial_table_content = dash_table.DataTable(
                    id='positions-datatable',
                    data=df_display.to_dict('records'),
                    columns=[
                        {'name': 'Symbol', 'id': 'symbol'},
                        {'name': 'Quantity', 'id': 'qty'},
                        {'name': 'Weight %', 'id': 'weight_pct'},
                        {'name': 'Trend Signal', 'id': 'trend_signal'},
                        {'name': 'Momentum', 'id': 'momentum'},
                        {'name': 'Sentiment', 'id': 'sentiment'},
                        {'name': 'Volatility', 'id': 'volatility'},
                        {'name': 'Avg Entry', 'id': 'avg_entry_price'},
                        {'name': 'Current Price', 'id': 'current_price'},
                        {'name': 'Cost Basis', 'id': 'cost_basis'},
                        {'name': 'Market Value', 'id': 'market_value'},
                        {'name': 'Unrealized P/L', 'id': 'unrealized_pl'},
                        {'name': 'P/L %', 'id': 'unrealized_plpc'},
                        {'name': 'Action', 'id': 'actions', 'presentation': 'markdown'}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '14px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {'if': {'column_id': 'actions'}, 'cursor': 'pointer', 'color': '#1e88e5', 'textDecoration': 'underline', 'fontWeight': '600'},
                        {'if': {'column_id': 'weight_pct'}, 'fontWeight': '600'},
                        {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
                    ],
                    row_selectable='single',
                    selected_rows=[]
                )
                logger.info("✅ Server-side positions table rendered successfully")
    except Exception as e:
        logger.warning(f"Could not render positions table server-side: {e}")
        # Non-fatal: callback will populate on client interaction
    
    return dbc.Container([
        # === IMPROVEMENTS: Toolbar with filters ===
        html.Div([
            create_tab_toolbar(
                tab_name="portfolio_positions",
                filters=[create_sector_filter('portfolio-sector')] if SHARED_UI_AVAILABLE else [],
                show_refresh=True,
                show_export=True,
                show_help=True,
                help_text="View and manage your portfolio positions."
            ) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === IMPROVEMENTS: Summary Statistics ===
        html.Div([
            create_summary_stats_row([
                {'title': 'Total Value', 'value': '$--', 'icon': 'fa-wallet', 'color': 'primary'},
            {'title': 'Day P&L', 'value': '$--', 'icon': 'fa-chart-line', 'color': 'success'},
            {'title': 'Positions', 'value': '--', 'icon': 'fa-cubes', 'color': 'info'},
            {'title': 'Cash', 'value': '$--', 'icon': 'fa-money-bill', 'color': 'secondary'}
            ]) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === IMPROVEMENTS: Notification Toast ===
        html.Div([
            create_notification_toast("portfolio_positions-toast", "Portfolio Positions Update") if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        html.H5("Current Positions", className="mt-3 mb-3"),
        
        # PHASE 6: Add SHAP regeneration control
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-sync-alt me-2"), "Regenerate SHAP Data"],
                    id='regen-shap-btn',
                    color='primary',
                    size='sm',
                    className='mb-2'
                ),
                dbc.Button(
                    [html.I(className="fas fa-redo-alt me-2"), "Refresh Positions"],
                    id='portfolio-positions-refresh-btn',
                    color='secondary',
                    size='sm',
                    className='mb-2 ms-2'
                ),
                html.Small(
                    " Force regenerate SHAP explanations for all portfolio tickers",
                    className='text-muted ms-2'
                )
            ])
        ]),
        dbc.Row([
            dbc.Col([
                html.Div(id='shap-regen-status', className='mb-2')
            ])
        ]),
        dbc.Row([
            dbc.Col([
                html.Div(id='news-prefetch-status', className='mb-2 text-muted', children="News cache: unknown")
            ])
        ]),
        
        html.Div(initial_table_content, id='portfolio-positions-table'),
        
        # Inspect Position Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id='inspect-modal-title')),
            dbc.ModalBody(id='inspect-modal-body'),
            dbc.ModalFooter(
                dbc.Button("Close", id='inspect-modal-close', className="ms-auto", n_clicks=0)
            )
        ], id='inspect-modal', size='lg', is_open=False)
    ], fluid=True)


def register_callbacks(app):
    """Register callbacks for positions tab."""
    
    # Use module-level normalize_positions_list(positions) helper

    
    # PHASE 6: SHAP Regeneration Callback
    @app.callback(
        Output('shap-regen-status', 'children'),
        Input('regen-shap-btn', 'n_clicks'),
        State('portfolio-data-store', 'data'),
        prevent_initial_call=True
    )
    def regenerate_shap_data(n_clicks, portfolio_data):
        """Force regeneration of SHAP data for all portfolio tickers."""
        if not n_clicks or n_clicks == 0:
            raise PreventUpdate
        
        if not portfolio_data or not portfolio_data.get('positions'):
            return dbc.Alert("No portfolio data available", color="warning", dismissable=True)
        
        try:
            from utils.explain import get_or_generate_shap_data
            from datetime import datetime
            
            # Extract portfolio tickers
            tickers = [p.get('symbol') for p in portfolio_data['positions']]
            tickers = [t for t in tickers if t]
            
            logger.info(f"🔄 Manual SHAP regeneration requested for {len(tickers)} tickers")
            
            # Force regeneration
            date = datetime.now().strftime('%Y%m%d')
            shap_data = get_or_generate_shap_data(date, tickers=tickers, force_regenerate=True)
            
            if shap_data:
                explanations = shap_data.get('explanations', {})
                covered = len(explanations)
                
                return dbc.Alert([
                    html.I(className="fas fa-check-circle me-2"),
                    html.Strong(f"Success! "),
                    f"Generated SHAP data for {covered}/{len(tickers)} tickers. ",
                    html.Small(f"Features: {shap_data.get('num_features', 0)} per ticker", className="text-muted")
                ], color="success", dismissable=True)
            else:
                return dbc.Alert("SHAP generation returned no data", color="warning", dismissable=True)
                
        except Exception as e:
            logger.error(f"SHAP regeneration failed: {e}")
            return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)
    
    @app.callback(
        Output('portfolio-positions-table', 'children'),
        [
            Input('portfolio-tracker-subtabs', 'active_tab'),     # only update when subtab changes
            Input('portfolio-positions-refresh-btn', 'n_clicks'),           # explicit refresh (heavy)
            Input('portfolio-interval', 'n_intervals')            # optional periodic update
        ],
        State('portfolio-data-store', 'data'),
        prevent_initial_call=True
    )
    def update_positions_table(active_subtab, refresh_clicks, n_intervals, portfolio_data):
        """
        Update positions table. Two modes:
        - Lightweight: when user activates the Positions subtab, render quickly using cached `portfolio-data-store` (no network calls).
        - Heavy: when user clicks Refresh (or interval triggers), perform fallbacks (Alpaca fetch / cache) and enrich data.

        This reduces perceived load time by avoiding expensive network calls when the user merely navigates to the tab.
        """
        t0 = time.time()
        ctx = callback_context
        triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ''
        triggered_id = triggered.split('.')[0] if triggered else None

        logger.info(f"🔥 Positions callback fired! triggered={triggered_id}, active_subtab={active_subtab}, store_present={'yes' if portfolio_data else 'no'}")

        # If user just activated a subtab other than 'positions', do nothing
        if active_subtab != 'positions':
            raise PreventUpdate

        # LIGHTWEIGHT PATH: user clicked into Positions tab -> render quickly from store if available
        if triggered_id == 'portfolio-tracker-subtabs' or triggered_id is None:
            if portfolio_data and portfolio_data.get('positions'):
                logger.info("Quick-rendering positions from store (lightweight path)")
                positions = portfolio_data['positions']
                elapsed_light = time.time() - t0
                logger.info(f"Positions lightweight render completed in {elapsed_light:.3f}s (from tab activation)")
            else:
                # No data in store: ask user to click Refresh to load from Alpaca/cache
                logger.info("No portfolio data in store during lightweight render - instructing user to refresh")
                return html.Div([
                    dbc.Alert([
                        html.I(className="fas fa-info-circle me-2"),
                        html.Strong("No portfolio data loaded"),
                        html.Br(),
                        "Click the 'Regenerate/Refresh' button to load positions from your broker or cache."
                    ], color="info")
                ])

        # HEAVY PATH: only on explicit refresh or interval trigger - perform fetch/fallbacks
        elif triggered_id in ('portfolio-positions-refresh-btn', 'portfolio-interval'):
            # Attempt to use store first; if empty, try heavy fetch logic
            heavy_start = time.time()
            if portfolio_data and portfolio_data.get('positions'):
                logger.info("Refresh requested but store already contains positions - using store to avoid extra fetch")
                positions = portfolio_data['positions']
            else:
                logger.info("Performing heavy fetch for portfolio positions (Alpaca/cache fallbacks)")
                # PHASE 6C heavy fallback: direct Alpaca -> cache
                try:
                    import sys
                    import os
                    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)

                    from tabs.portfolio_tracker_refactored import get_alpaca_client
                    client = get_alpaca_client()

                    if client:
                        logger.info("✅ Got Alpaca client - fetching positions directly")
                        positions_resp = client.get_all_positions()
                        positions = []
                        for pos in positions_resp:
                            try:
                                positions.append({
                                    'symbol': getattr(pos, 'symbol', None),
                                    'qty': float(getattr(pos, 'qty', 0) or 0),
                                    'avg_entry_price': float(getattr(pos, 'avg_entry_price', 0) or 0),
                                    'current_price': float(getattr(pos, 'current_price', 0) or 0),
                                    'cost_basis': float(getattr(pos, 'cost_basis', 0) or 0),
                                    'market_value': float(getattr(pos, 'market_value', 0) or 0),
                                    'unrealized_pl': float(getattr(pos, 'unrealized_pl', 0) or 0),
                                    'unrealized_plpc': float((getattr(pos, 'unrealized_plpc', 0) or 0) * 100)
                                })
                            except Exception:
                                # best-effort per position
                                logger.debug(f"Skipping malformed position: {pos}")

                        logger.info(f"✅ Fetched {len(positions)} positions directly from Alpaca")
                        portfolio_data = {'positions': positions}
                        logger.info(f"Alpaca fetch returned {len(positions)} positions")
                    else:
                        # Try loading from cache as last resort
                        logger.warning("❌ Alpaca client unavailable - trying cache")
                        cache_path = Path(__file__).parent.parent / 'cache' / 'portfolio_data.json'
                        if cache_path.exists():
                            import json
                            with open(cache_path, 'r') as f:
                                cached = json.load(f)
                                portfolio_data = cached
                                positions = portfolio_data.get('positions', [])
                            logger.info(f"✅ Loaded {len(positions)} positions from cache")
                        else:
                            logger.error("❌ No cache file available")
                            return html.Div([
                                dbc.Alert([
                                    html.I(className="fas fa-exclamation-triangle me-2"),
                                    html.Strong("No Portfolio Data Available"),
                                    html.Br(),
                                    "Click the refresh button at the top to load positions from Alpaca."
                                ], color="warning")
                            ])

                except Exception as e:
                    logger.error(f"Failed to fetch positions: {e}", exc_info=True)
                    # record heavy path error elapsed time
                    heavy_elapsed = time.time() - heavy_start
                    logger.info(f"Positions heavy path failed after {heavy_elapsed:.3f}s")
                    return html.Div([
                        dbc.Alert([
                            html.I(className="fas fa-exclamation-circle me-2"),
                            html.Strong("Error Loading Positions"),
                            html.Br(),
                            html.Small(str(e), className="text-muted"),
                            html.Br(),
                            html.Small("Try clicking the refresh button or check Alpaca credentials.", className="text-muted")
                        ], color="danger")
                    ])
        else:
            # Unknown trigger - be safe and prevent update
            logger.debug(f"Unknown trigger for positions callback: {triggered_id}")
            raise PreventUpdate
        
        # Validate we now have positions
        if not portfolio_data or not portfolio_data.get('positions'):
            logger.warning("No positions data available after fallback attempts")
            return html.P("No positions found.", className="text-muted")
        
        positions = portfolio_data['positions']
        
        # ===== FILTER OUT CLOSED POSITIONS (qty = 0) =====
        # Only show open positions in the Positions tab
        # Closed positions should appear in Order History instead
        open_positions = [p for p in positions if float(p.get('qty', 0)) > 0]
        
        if not open_positions:
            logger.info("All positions are closed (qty=0), showing empty state")
            return html.P("No open positions. Closed positions appear in Order History.", className="text-muted")
        
        logger.info(f"Filtered positions: {len(positions)} total → {len(open_positions)} open (excluded {len(positions) - len(open_positions)} closed)")
        
        df = pd.DataFrame(open_positions)

        # ===== Normalize column names and types to avoid empty columns =====
        # Support different source schemas: 'symbol' or 'ticker' etc.
        if 'symbol' not in df.columns and 'ticker' in df.columns:
            df['symbol'] = df['ticker']
        if 'symbol' not in df.columns and 'sym' in df.columns:
            df['symbol'] = df['sym']

        # Ensure numeric columns exist and are numeric (coerce errors to 0)
        numeric_cols = ['qty', 'avg_entry_price', 'current_price', 'cost_basis', 'market_value', 'unrealized_pl', 'unrealized_plpc']
        for col in numeric_cols:
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Calculate portfolio weight %, guard divide-by-zero
        total_value = df['market_value'].sum() if 'market_value' in df.columns else 0.0
        if total_value and total_value != 0:
            df['weight_pct'] = (df['market_value'] / total_value * 100).round(2)
        else:
            df['weight_pct'] = 0.0
        
        # PHASE 4: Load Market Trends signals
        signals_map = {}
        sync_metadata = None
        try:
            # Read sync manifest to check if Market Trends data exists
            manifest = read_sync_manifest()
            sync_metadata = manifest.get('market_trends')
            
            if sync_metadata:
                logger.info(f"📊 Market Trends manifest found: last_updated={sync_metadata.get('last_updated')}")
                
                # Load signals from cache
                signals_map = _load_market_trends_signals()
                
                # Mark dependency: Portfolio synced with Market Trends
                if signals_map:
                    mark_dependency('portfolio', 'market_trends', sync_metadata.get('job_id'))
                    logger.info(f"✅ Portfolio synced with Market Trends (job: {sync_metadata.get('job_id')})")
            else:
                logger.warning("⚠️  No Market Trends data in sync manifest - skipping signal merge")
        
        except Exception as e:
            logger.error(f"Error loading Market Trends signals: {e}")
        
        # PHASE 4: Merge Market Trends signals into positions
        if signals_map:
            df['trend_signal'] = df['symbol'].apply(lambda s: signals_map.get(s, {}).get('trend_signal', 'N/A'))
            df['momentum'] = df['symbol'].apply(lambda s: signals_map.get(s, {}).get('momentum', 0.0))
            df['sentiment'] = df['symbol'].apply(lambda s: signals_map.get(s, {}).get('sentiment', 0.0))
            df['volatility'] = df['symbol'].apply(lambda s: signals_map.get(s, {}).get('volatility', 0.0))
            
            logger.info(f"✅ Merged Market Trends signals: {sum(df['trend_signal'] != 'N/A')} tickers matched")
        else:
            # Add placeholder columns if no signals available
            df['trend_signal'] = 'N/A'
            df['momentum'] = 0.0
            df['sentiment'] = 0.0
            df['volatility'] = 0.0
        
        # Format columns for display
        df_display = df.copy()
        df_display['avg_entry_price'] = df['avg_entry_price'].apply(lambda x: f"${x:.2f}")
        df_display['current_price'] = df['current_price'].apply(lambda x: f"${x:.2f}")
        df_display['cost_basis'] = df['cost_basis'].apply(lambda x: f"${x:.2f}")
        df_display['market_value'] = df['market_value'].apply(lambda x: f"${x:.2f}")
        df_display['unrealized_pl'] = df['unrealized_pl'].apply(lambda x: f"${x:.2f}")
        df_display['unrealized_plpc'] = df['unrealized_plpc'].apply(lambda x: f"{x:.2f}%")
        df_display['weight_pct'] = df_display['weight_pct'].apply(lambda x: f"{x:.2f}%")
        
        # Format Market Trends columns
        df_display['momentum'] = df['momentum'].apply(lambda x: f"{x:.2f}" if x != 0 else "—")
        df_display['sentiment'] = df['sentiment'].apply(lambda x: f"{x:.2f}" if x != 0 else "—")
        df_display['volatility'] = df['volatility'].apply(lambda x: f"{x:.2f}" if x != 0 else "—")
        
        # Add event alerts (bell emoji) for tickers with recent negative news
        try:
            # Use cached news for lightweight renders and start a tracked prefetch job in background
            from utils.finnhub_news import get_high_severity_news, get_cached_news, start_prefetch_job

            tickers_for_news = df['symbol'].astype(str).tolist()
            news_map = {t: [] for t in tickers_for_news}

            # If this callback was triggered by a lightweight tab activation, avoid network calls
            try:
                trigger = triggered_id  # captured from outer scope
            except Exception:
                trigger = None

            if trigger in (None, 'portfolio-tracker-subtabs'):
                # Quick path: read cached news only and schedule background refresh
                for t in tickers_for_news:
                    try:
                        cached = get_cached_news(t, ttl_seconds=3600)
                        news_map[t] = cached or []
                    except Exception:
                        news_map[t] = []

                # Prefetch fresh news in background (tracked job) so subsequent opens show event badges
                try:
                    job_id = start_prefetch_job(tickers_for_news, days_back=7, ttl_seconds=3600)
                    logger.info(f"Started news prefetch job {job_id} in background")
                except Exception:
                    logger.debug("Failed to start background prefetch (non-fatal)")

            else:
                # Heavy path: fetch high-severity news (batched) synchronously (for Refresh/interval)
                import concurrent.futures
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, max(1, len(tickers_for_news)))) as ex:
                        futures = {ex.submit(get_high_severity_news, t, 2): t for t in tickers_for_news}
                        for fut in concurrent.futures.as_completed(futures, timeout=20):
                            t = futures.get(fut)
                            try:
                                res = fut.result(timeout=5)
                                news_map[t] = res or []
                            except Exception:
                                news_map[t] = []
                except Exception:
                    for t in tickers_for_news:
                        try:
                            news_map[t] = get_high_severity_news(t, days_back=2) or []
                        except Exception:
                            news_map[t] = []

            # Apply bell emoji where high-severity negative news exists
            def _mark_bell(sym):
                if not sym:
                    return sym
                items = news_map.get(sym, [])
                if items and any(it.get('severity') == 'HIGH' or it.get('sentiment') == 'negative' for it in items):
                    return f"🔔 {sym}"
                return sym

            df_display['symbol'] = df_display['symbol'].apply(_mark_bell)

        except ImportError:
            logger.debug("finnhub_news not available - skipping event alerts")
        except Exception as e:
            logger.warning(f"Error adding event alerts (non-fatal): {e}")
        
        # Add action column for inspect button
        df_display['actions'] = '🔍 Inspect'
        
        dt = dash_table.DataTable(
            id='positions-datatable',
            data=df_display.to_dict('records'),
            columns=[
                {'name': 'Symbol', 'id': 'symbol'},
                {'name': 'Quantity', 'id': 'qty'},
                {'name': 'Weight %', 'id': 'weight_pct'},
                {'name': 'Trend Signal', 'id': 'trend_signal'},  # PHASE 4: New column
                {'name': 'Momentum', 'id': 'momentum'},          # PHASE 4: New column
                {'name': 'Sentiment', 'id': 'sentiment'},        # PHASE 4: New column
                {'name': 'Volatility', 'id': 'volatility'},      # PHASE 4: New column
                {'name': 'Avg Entry', 'id': 'avg_entry_price'},
                {'name': 'Current Price', 'id': 'current_price'},
                {'name': 'Cost Basis', 'id': 'cost_basis'},
                {'name': 'Market Value', 'id': 'market_value'},
                {'name': 'Unrealized P/L', 'id': 'unrealized_pl'},
                {'name': 'P/L %', 'id': 'unrealized_plpc'},
                {'name': 'Action', 'id': 'actions', 'presentation': 'markdown'}
            ],
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left', 
                'padding': '10px',
                'fontSize': '14px'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)', 
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'actions'},
                    'cursor': 'pointer',
                    'color': '#1e88e5',
                    'textDecoration': 'underline',
                    'fontWeight': '600'
                },
                {
                    'if': {'column_id': 'weight_pct'},
                    'fontWeight': '600'
                },
                # PHASE 4: Highlight Market Trends columns
                {
                    'if': {'column_id': 'trend_signal'},
                    'backgroundColor': '#f0f9ff',
                    'fontWeight': '600'
                },
                {
                    'if': {'column_id': 'momentum'},
                    'backgroundColor': '#ecfdf5'
                },
                {
                    'if': {'column_id': 'sentiment'},
                    'backgroundColor': '#fef3c7'
                },
                {
                    'if': {'column_id': 'volatility'},
                    'backgroundColor': '#fee2e2'
                },
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ] + [
                # FIX: Add gradient backgrounds to Weight % column for visual representation
                {
                    'if': {'column_id': 'weight_pct', 'row_index': i},
                    'background': f'linear-gradient(90deg, rgba(16, 185, 129, 0.3) {float(df["weight_pct"].iloc[i]):.1f}%, transparent {float(df["weight_pct"].iloc[i]):.1f}%)'
                } for i in range(len(df))
            ],
            tooltip_data=[
                {
                    'symbol': {'value': f"Click Inspect to see detailed analysis for {row['symbol']}", 'type': 'markdown'},
                    'trend_signal': {'value': f"Market trend signal from latest analysis", 'type': 'markdown'},
                    'momentum': {'value': f"Momentum score from Market Trends", 'type': 'markdown'},
                    'sentiment': {'value': f"Sentiment score from Market Trends", 'type': 'markdown'},
                    'volatility': {'value': f"Volatility measure from Market Trends", 'type': 'markdown'}
                } for row in df_display.to_dict('records')
            ],
            tooltip_duration=None,
            row_selectable='single',
            selected_rows=[]
        )

        # log heavy path elapsed if we started heavy work
        try:
            if 'heavy_start' in locals():
                heavy_elapsed = time.time() - heavy_start
                logger.info(f"Positions heavy render completed in {heavy_elapsed:.3f}s (from refresh)")
        except Exception:
            pass

        return dt
    
    
    @app.callback(
        [Output('inspect-modal', 'is_open'),
         Output('inspect-modal-title', 'children'),
         Output('inspect-modal-body', 'children')],
        [Input('positions-datatable', 'active_cell'),
         Input('inspect-modal-close', 'n_clicks')],
        [State('positions-datatable', 'data'),
         State('portfolio-data-store', 'data'),  # PHASE 6: Added to get full ticker list
         State('inspect-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_inspect_modal(active_cell, close_clicks, table_data, portfolio_data, is_open):
        """Open/close inspect modal with position details."""
        ctx = callback_context
        
        if not ctx.triggered:
            raise PreventUpdate
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Close modal
        if trigger_id == 'inspect-modal-close':
            return False, "", ""
        
        # Open modal when clicking on a cell in the actions column
        if trigger_id == 'positions-datatable' and active_cell:
            if active_cell['column_id'] == 'actions':
                row_idx = active_cell['row']
                if table_data and row_idx < len(table_data):
                    row_data = table_data[row_idx]
                    ticker = row_data['symbol'].replace('🔔 ', '')  # Strip event bell if present
                    
                    # PHASE 6: Extract full portfolio ticker list
                    portfolio_tickers = []
                    if portfolio_data and portfolio_data.get('positions'):
                        portfolio_tickers = [p.get('symbol') for p in portfolio_data['positions']]
                        portfolio_tickers = [t for t in portfolio_tickers if t]  # Filter None
                    
                    # Load position details
                    modal_title = f"Position Analysis: {ticker}"
                    modal_body = _build_inspect_modal_body(ticker, portfolio_tickers)
                    
                    return True, modal_title, modal_body
        
        raise PreventUpdate
    
    
    def _build_inspect_modal_body(ticker, portfolio_tickers=None):
        """
        Build modal body with model score, SHAP features, and news events.
        
        PHASE 6: Accepts portfolio_tickers to ensure SHAP data generated for full portfolio.
        """
        components = []
        
                # Section 1: Model Score & Prediction
        components.append(html.H6("Model Score & Prediction", className="mt-3 mb-2"))
        try:
            # Try to load model score from picks file
            from financial_dashboard import _shared as SH
            picks_path = None
            try:
                dash_root = SH.DASH_ROOT
            except:
                dash_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            import glob
            patterns = ['models/**/picks_*.csv', 'picks/picks_*.csv']
            candidates = []
            for pattern in patterns:
                path = os.path.join(dash_root, pattern)
                found = glob.glob(path, recursive=True)
                candidates.extend(found)
            
            if candidates:
                # Sort by mtime, get most recent
                candidates.sort(key=os.path.getmtime, reverse=True)
                picks_path = candidates[0]
                
                picks_df = pd.read_csv(picks_path)
                if 'symbol' in picks_df.columns:
                    picks_df = picks_df.rename(columns={'symbol': 'ticker'})
                
                ticker_data = picks_df[picks_df['ticker'].str.upper() == ticker.upper()]
                if not ticker_data.empty:
                    # Extract score and prediction
                    score = ticker_data.iloc[0].get('model_score', ticker_data.iloc[0].get('score', 'N/A'))
                    prediction = ticker_data.iloc[0].get('prediction', ticker_data.iloc[0].get('pred', 'N/A'))
                    
                    components.append(dbc.Card([
                        dbc.CardBody([
                            html.P([
                                html.Strong("Model Score: "), 
                                html.Span(f"{score:.4f}" if isinstance(score, (int, float)) else str(score))
                            ]),
                            html.P([
                                html.Strong("Prediction: "),
                                html.Span(f"{prediction:.4f}" if isinstance(prediction, (int, float)) else str(prediction), 
                                         className="text-success" if (isinstance(prediction, (int, float)) and prediction > 0) else "text-danger")
                            ])
                        ])
                    ], className="mb-3"))
                else:
                    components.append(dbc.Alert(f"No model data found for {ticker} in latest picks file.", color="warning", className="mb-3"))
            else:
                components.append(dbc.Alert("No picks file found. Run model to generate predictions.", color="info", className="mb-3"))
        
        except Exception as e:
            logger.error(f"Error loading model score for {ticker}: {e}")
            components.append(dbc.Alert(f"Error loading model score: {str(e)}", color="warning", className="mb-3"))
        
        # Section 2: Top 3 SHAP Features
        components.append(html.H6("Top 3 SHAP Features", className="mt-4 mb-2"))
        try:
            from utils.explain import get_or_generate_shap_data
            
            # PHASE 6: Pass full portfolio ticker list to ensure comprehensive SHAP generation
            if not portfolio_tickers:
                logger.warning("No portfolio tickers provided - SHAP may be incomplete")
                portfolio_tickers = [ticker]  # At least include current ticker
            
            logger.info(f"Generating SHAP data for {len(portfolio_tickers)} portfolio tickers (viewing: {ticker})")
            
            # Try multiple dates using the new auto-generation function
            shap_data = None
            for days_back in [0, 1, 2, 3, 7]:
                check_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
                # PHASE 6 FIX: Pass portfolio_tickers to ensure all tickers are covered
                shap_data = get_or_generate_shap_data(check_date, tickers=portfolio_tickers)
                if shap_data and shap_data.get('explanations'):
                    logger.info(f"✅ Found SHAP data for date {check_date} with {len(shap_data.get('explanations', {}))} tickers")
                    break
            
            # Check if we got fallback data
            if shap_data and shap_data.get('status') == 'fallback':
                components.append(dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Strong("SHAP Data Unavailable"),
                    html.Br(),
                    html.Small(shap_data.get('message', 'Model or features not found')),
                    html.Br(),
                    html.Small("💡 Tip: Ensure model is trained and features are prepared for recent dates.", 
                              className="text-muted")
                ], color="info", className="mb-3"))
            elif shap_data and ticker.upper() in shap_data.get('explanations', {}):
                ticker_shap = shap_data['explanations'][ticker.upper()]
                top_features = ticker_shap.get('top_features', [])[:3]
                
                if top_features:
                    shap_items = []
                    for i, feat in enumerate(top_features, 1):
                        feat_name = feat.get('feature', 'Unknown')
                        feat_value = feat.get('shap_value', 0)  # Updated key name
                        feat_impact = "↑ Positive" if feat_value > 0 else "↓ Negative"
                        
                        shap_items.append(html.Li([
                            html.Strong(f"{i}. {feat_name}: "),
                            html.Span(f"{feat_value:.4f} ", 
                                     className="text-success" if feat_value > 0 else "text-danger"),
                            html.Span(f"({feat_impact})", className="text-muted small")
                        ]))
                    
                    components.append(dbc.Card([
                        dbc.CardBody([
                            html.Ul(shap_items, className="mb-0")
                        ])
                    ], className="mb-3"))
                    
                    # Show auto-generation notice if data was just created
                    if shap_data.get('generated_at'):
                        gen_time = datetime.fromisoformat(shap_data['generated_at'])
                        if (datetime.now() - gen_time).total_seconds() < 60:
                            components.append(dbc.Alert([
                                html.I(className="fas fa-check-circle me-2"),
                                "✅ SHAP explanation auto-generated just now"
                            ], color="success", className="mb-2", style={'fontSize': '0.85rem'}))
                else:
                    components.append(dbc.Alert("No SHAP features found for this ticker.", color="info", className="mb-3"))
            else:
                components.append(dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "SHAP data not available for this ticker. ",
                    html.Small("The model may not have generated predictions for this symbol recently.", className="text-muted")
                ], color="info", className="mb-3"))
        
        except Exception as e:
            logger.error(f"Error loading SHAP features for {ticker}: {e}", exc_info=True)
            components.append(dbc.Alert([
                html.I(className="fas fa-exclamation-circle me-2"),
                f"Error loading SHAP features: {str(e)}"
            ], color="warning", className="mb-3"))
        
        # Section 3: Recent Company News with Sentiment (via Finnhub)
        components.append(html.H6("Recent Company News (Finnhub)", className="mt-4 mb-2"))
        try:
            from utils.finnhub_news import get_ticker_news_parallel
            
            # Fetch real news from Finnhub (parallel with 2 keys)
            news_items = get_ticker_news_parallel(ticker, days_back=30, max_news=5)
            
            if news_items and len(news_items) > 0:
                news_list = []
                for news in news_items:
                    sentiment = news.get('sentiment', 'neutral')
                    date = news.get('date', 'Unknown date')
                    headline = news.get('headline', 'No headline')
                    summary = news.get('summary', '')
                    source = news.get('source', 'Unknown')
                    url = news.get('url', '')
                    
                    # Sentiment badge with color coding
                    if sentiment == 'positive':
                        sentiment_badge = dbc.Badge('POSITIVE', color='success', className="me-2")
                    elif sentiment == 'negative':
                        sentiment_badge = dbc.Badge('NEGATIVE', color='danger', className="me-2")
                    else:
                        sentiment_badge = dbc.Badge('NEUTRAL', color='secondary', className="me-2")
                    
                    # Build news item
                    news_item = html.Li([
                        sentiment_badge,
                        html.Strong(date + ": "),
                        html.A(headline, href=url, target="_blank") if url else html.Span(headline),
                        html.Br(),
                        html.Small(f"Source: {source}", className="text-muted"),
                        html.Br() if summary else "",
                        html.Small(summary, className="text-muted") if summary else ""
                    ], className="mb-3")
                    
                    news_list.append(news_item)
                
                components.append(dbc.Card([
                    dbc.CardBody([
                        html.Ul(news_list, className="mb-0", style={'list-style-type': 'none', 'padding-left': '0'})
                    ])
                ], className="mb-3"))
            else:
                components.append(dbc.Alert("No recent news found for this ticker.", color="info", className="mb-3"))
        
        except ImportError as e:
            logger.error(f"Finnhub news module not available: {e}")
            components.append(dbc.Alert(
                "Finnhub news integration not available. Install required packages.",
                color="warning", className="mb-3"
            ))
        
        except Exception as e:
            logger.error(f"Error fetching Finnhub news for {ticker}: {e}")
            components.append(dbc.Alert(
                f"Error loading news: {str(e)}. Check Finnhub API keys in keys.env",
                color="warning", className="mb-3"
            ))
        
        return html.Div(components)


    # Status indicator for background news prefetch jobs
    @app.callback(
        Output('news-prefetch-status', 'children'),
        [
            Input('portfolio-tracker-subtabs', 'active_tab'),
            Input('portfolio-refresh-btn', 'n_clicks'),
            Input('portfolio-interval', 'n_intervals')
        ],
        prevent_initial_call=False
    )
    def update_news_prefetch_status(active_tab, n_clicks, n_intervals):
        """Update a small status string showing when news cache was last prefetched and if a job is running."""
        try:
            from utils.finnhub_news import get_latest_prefetch_timestamp, PREFETCH_JOBS, PREFETCH_JOBS_LOCK

            latest = get_latest_prefetch_timestamp()
            status = "News cache: never prefetched"
            if latest and latest > 0:
                dt = datetime.fromtimestamp(latest)
                age = datetime.now() - dt
                secs = int(age.total_seconds())
                if secs < 60:
                    ago = "just now"
                elif secs < 3600:
                    ago = f"{int(secs/60)}m ago"
                else:
                    ago = f"{int(secs/3600)}h ago"
                status = f"News cache: last prefetched {ago}"

            # Check running jobs
            running = False
            with PREFETCH_JOBS_LOCK:
                for v in PREFETCH_JOBS.values():
                    if v.get('started') and not v.get('finished'):
                        running = True
                        break

            if running:
                status = status + " (prefetch running...)"

            return status
        except Exception:
            return "News cache: status unknown"
