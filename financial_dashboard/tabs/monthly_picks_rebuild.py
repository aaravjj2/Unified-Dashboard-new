"""
Monthly Picks Tab - Rebuilt with robust architecture

Features:
- API-driven rendering
- Deterministic fixtures support
- Provenance tracking
- Manual refresh
- CSV download
- Clean separation of layout and callbacks

Author: Agent-1B (Rebuild)
Date: 2025-11-21
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime
from dash import dcc, html, Input, Output, State, dash_table, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from utils.picks_fetcher import PicksFetcher, is_deterministic_mode
from utils.tab_shell import tab_shell
from utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# Configuration
FIXTURE_PATH = 'reports/picks/fixtures/monthly_fixture.json'
CACHE_PATH = 'data/picks/monthly_cache.json'
DB_TABLE = 'monthly_picks'
TTL_SECONDS = 300  # 5 minutes

# Initialize cache manager
_monthly_cache = {}
_cache_manager = CacheManager(
    cache_file_path=CACHE_PATH,
    memory_cache=_monthly_cache,
    ttl_seconds=TTL_SECONDS
)


def create_layout():
    """
    Create monthly picks layout with tab_shell wrapper for safety.
    
    Returns:
        Dash component tree
    """
    try:
        layout = html.Div([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H3("📊 Monthly Picks", className="text-primary mb-0"),
                    html.P("Top 20 stock recommendations for the month", 
                           className="text-muted small mb-3")
                ], width=8),
                dbc.Col([
                    html.Div([
                        dbc.Button(
                            "↻ Refresh",
                            id="mp-refresh-btn",
                            color="primary",
                            size="sm",
                            className="me-2"
                        ),
                        dbc.Button(
                            "⬇ Download CSV",
                            id="mp-download-btn",
                            color="success",
                            size="sm",
                            outline=True
                        ),
                    ], className="d-flex justify-content-end")
                ], width=4)
            ], className="mb-3"),
            
            # Status indicators
            dbc.Row([
                dbc.Col([
                    html.Div(id="mp-status-message", children=[
                        dbc.Badge("Loading...", color="secondary", className="me-2")
                    ])
                ])
            ], className="mb-3"),
            
            # Main content area
            dbc.Row([
                dbc.Col([
                    html.Div(id="mp-content", children=[
                        dbc.Spinner(html.Div("Loading picks..."), color="primary")
                    ])
                ])
            ]),
            
            # Hidden stores
            dcc.Store(id="mp-data-store", data=None),
            dcc.Download(id="mp-csv-download"),
            
            # Auto-refresh interval (disabled by default)
            dcc.Interval(
                id="mp-auto-refresh",
                interval=TTL_SECONDS * 1000,
                disabled=True
            )
        ], className="container-fluid p-4")
        
        return tab_shell(layout, tab_name="Monthly Picks")
        
    except Exception as e:
        logger.error(f"Failed to create monthly picks layout: {e}")
        return tab_shell(
            html.Div([
                dbc.Alert([
                    html.H5("⚠️ Layout Error"),
                    html.P(f"Failed to create layout: {str(e)}")
                ], color="danger")
            ]),
            tab_name="Monthly Picks",
            collapsed_on_error=True
        )


def _create_picks_table(picks_df: pd.DataFrame) -> dash_table.DataTable:
    """
    Create DataTable from picks DataFrame.
    
    Args:
        picks_df: DataFrame with picks data
        
    Returns:
        DataTable component
    """
    if picks_df.empty:
        return html.Div([
            dbc.Alert("No picks data available", color="warning")
        ])
    
    # Map API field names to display names
    # Monthly picks API returns: ticker, rank, combined_score, current_price, profit_loss, label, etc.
    field_map = {
        'ticker': 'Symbol',
        'rank': 'Rank',
        'combined_score': 'Score',
        'current_price': 'Price',
        'month_start_price': 'Start Price',
        'profit_loss': 'P/L %',
        'momentum_score': 'Momentum',
        'fundamental_score': 'Fundamentals',
        'sentiment_score': 'Sentiment',
        'label': 'Signal'
    }
    
    # Build display dataframe with available columns
    df_display = pd.DataFrame()
    for api_field, display_name in field_map.items():
        if api_field in picks_df.columns:
            df_display[display_name] = picks_df[api_field]
    
    # Round numeric columns
    for col in ['Score', 'Price', 'Start Price', 'P/L %', 'Momentum', 'Fundamentals', 'Sentiment']:
        if col in df_display.columns:
            df_display[col] = df_display[col].round(2)
    
    # Create DataTable
    return dash_table.DataTable(
        id="mp-table",
        data=df_display.to_dict('records'),
        columns=[{"name": col, "id": col} for col in df_display.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'borderBottom': '2px solid #dee2e6'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        page_size=20,
        sort_action='native',
        filter_action='native'
    )


def _load_picks_data() -> pd.DataFrame:
    """
    Load monthly picks from source (DB, JSON, or fixture).
    
    Returns:
        DataFrame with picks data (may be empty on error)
    """
    try:
        # Check cache freshness first
        if _cache_manager.is_cache_fresh():
            cached_data = _cache_manager.get_cached_data()
            if cached_data and not cached_data.get('empty', True):
                logger.info("Using fresh cached picks data")
                picks_list = cached_data.get('picks', [])
                return pd.DataFrame(picks_list)
        
        # Load from source
        fetcher = PicksFetcher(fixture_path=FIXTURE_PATH)
        
        if is_deterministic_mode():
            # Use deterministic fixtures
            picks_df = fetcher.load_from_fixture()
            logger.info(f"Loaded {len(picks_df)} picks from deterministic fixture")
        else:
            # Try JSON fallback first, then DB
            json_path = 'data/picks/monthly_picks.json'
            
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                picks_df = pd.DataFrame(data.get('data', []))
                logger.info(f"Loaded {len(picks_df)} picks from JSON fallback")
            else:
                # Try DB
                picks_df = fetcher.load_from_db(DB_TABLE)
                logger.info(f"Loaded {len(picks_df)} picks from database")
        
        # Monthly picks already include current_price in API response
        
        # Update cache
        cache_data = {
            'picks': picks_df.to_dict('records') if not picks_df.empty else [],
            'count': len(picks_df),
            'empty': picks_df.empty,
            'generated_at': datetime.now().isoformat()
        }
        _cache_manager.update_cache(cache_data)
        
        return picks_df
        
    except Exception as e:
        logger.error(f"Failed to load picks data: {e}")
        return pd.DataFrame()


def register_callbacks(app):
    """
    Register all callbacks for monthly picks tab.
    
    Args:
        app: Dash app instance
    """
    
    @app.callback(
        Output('mp-content', 'children'),
        Output('mp-status-message', 'children'),
        Output('mp-data-store', 'data'),
        Input('mp-refresh-btn', 'n_clicks'),
        Input('mp-auto-refresh', 'n_intervals'),
        prevent_initial_call=False
    )
    def load_picks_content(refresh_clicks, auto_intervals):
        """Load and display picks data."""
        try:
            # Force reload on manual refresh
            if ctx.triggered_id == 'mp-refresh-btn':
                logger.info("Manual refresh triggered")
                _monthly_cache.clear()
            
            # Load picks
            picks_df = _load_picks_data()
            
            if picks_df.empty:
                status = dbc.Badge("⚠️ No data available", color="warning")
                content = dbc.Alert(
                    "No monthly picks data found. Try refreshing or check data source.",
                    color="warning"
                )
                return content, status, None
            
            # Create table
            table = _create_picks_table(picks_df)
            
            # Create status badge
            cache_info = _cache_manager.get_cache_info()
            age_sec = cache_info.get('age_seconds', 0)
            is_fresh = cache_info.get('is_fresh', False)
            
            if is_fresh:
                status = [
                    dbc.Badge(f"✓ {len(picks_df)} picks", color="success", className="me-2"),
                    dbc.Badge(f"Updated {int(age_sec)}s ago", color="info")
                ]
            else:
                status = [
                    dbc.Badge(f"⚠ {len(picks_df)} picks", color="warning", className="me-2"),
                    dbc.Badge(f"Stale ({int(age_sec)}s old)", color="secondary")
                ]
            
            # Prepare store data
            store_data = {
                'picks': picks_df.to_dict('records'),
                'count': len(picks_df),
                'timestamp': datetime.now().isoformat()
            }
            
            # Create summary stats
            summary = html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H5(str(len(picks_df)), className="mb-0 text-primary"),
                            html.P("Total Picks", className="text-muted small mb-0")
                        ])
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.H5(
                                f"{picks_df['profit_loss'].mean():.1f}%" if 'profit_loss' in picks_df.columns else "N/A",
                                className="mb-0 text-success"
                            ),
                            html.P("Avg P/L", className="text-muted small mb-0")
                        ])
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.H5(
                                f"{picks_df['combined_score'].mean():.1f}" if 'combined_score' in picks_df.columns else "N/A",
                                className="mb-0 text-info"
                            ),
                            html.P("Avg Score", className="text-muted small mb-0")
                        ])
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.H5(
                                "Deterministic" if is_deterministic_mode() else "Live",
                                className="mb-0 text-warning"
                            ),
                            html.P("Data Mode", className="text-muted small mb-0")
                        ])
                    ], width=3)
                ], className="mb-3"),
                table
            ])
            
            return summary, status, store_data
            
        except Exception as e:
            logger.error(f"Error loading picks content: {e}")
            error_content = dbc.Alert([
                html.H5("⚠️ Error Loading Picks"),
                html.P(str(e))
            ], color="danger")
            error_status = dbc.Badge("❌ Error", color="danger")
            return error_content, error_status, None
    
    @app.callback(
        Output('mp-csv-download', 'data'),
        Input('mp-download-btn', 'n_clicks'),
        State('mp-data-store', 'data'),
        prevent_initial_call=True
    )
    def download_csv(n_clicks, store_data):
        """Download picks as CSV."""
        if not n_clicks or not store_data:
            raise PreventUpdate
        
        try:
            picks_df = pd.DataFrame(store_data.get('picks', []))
            
            if picks_df.empty:
                raise PreventUpdate
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"monthly_picks_{timestamp}.csv"
            
            return dcc.send_data_frame(picks_df.to_csv, filename, index=False)
            
        except Exception as e:
            logger.error(f"CSV download failed: {e}")
            raise PreventUpdate
    
    logger.info("✅ Monthly picks callbacks registered")


# Module exports
__all__ = ['create_layout', 'register_callbacks']
