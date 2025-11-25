"""
Weekly Picks Tab - Rebuilt with robust architecture

Features:
- API-driven rendering (load via /api/weekly_picks)
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
FIXTURE_PATH = 'reports/picks/fixtures/weekly_fixture.json'
CACHE_PATH = 'data/picks/weekly_cache.json'
DB_TABLE = 'weekly_picks'
TTL_SECONDS = 300  # 5 minutes

# Initialize cache manager
_weekly_cache = {}
_cache_manager = CacheManager(
    cache_file_path=CACHE_PATH,
    memory_cache=_weekly_cache,
    ttl_seconds=TTL_SECONDS
)


def create_layout():
    """
    Create weekly picks layout with tab_shell wrapper for safety.
    
    Returns:
        Dash component tree
    """
    try:
        layout = html.Div([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H3("📈 Weekly Picks", className="text-primary mb-0"),
                    html.P("Top 20 stock recommendations for the week", 
                           className="text-muted small mb-3")
                ], width=8),
                dbc.Col([
                    html.Div([
                        dbc.Button(
                            "↻ Refresh",
                            id="wp-refresh-btn",
                            color="primary",
                            size="sm",
                            className="me-2"
                        ),
                        dbc.Button(
                            "⬇ Download CSV",
                            id="wp-download-btn",
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
                    html.Div(id="wp-status-message", children=[
                        dbc.Badge("Loading...", color="secondary", className="me-2")
                    ])
                ])
            ], className="mb-3"),
            
            # Main content area
            dbc.Row([
                dbc.Col([
                    html.Div(id="wp-content", children=[
                        dbc.Spinner(html.Div("Loading picks..."), color="primary")
                    ])
                ])
            ]),
            
            # Hidden stores
            dcc.Store(id="wp-data-store", data=None),
            dcc.Download(id="wp-csv-download"),
            
            # Auto-refresh interval (disabled by default)
            dcc.Interval(
                id="wp-auto-refresh",
                interval=TTL_SECONDS * 1000,  # milliseconds
                disabled=True
            )
        ], className="container-fluid p-4")
        
        return tab_shell(layout, tab_name="Weekly Picks")
        
    except Exception as e:
        logger.error(f"Failed to create weekly picks layout: {e}")
        return tab_shell(
            html.Div([
                dbc.Alert([
                    html.H5("⚠️ Layout Error"),
                    html.P(f"Failed to create layout: {str(e)}")
                ], color="danger")
            ]),
            tab_name="Weekly Picks",
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
    
    # Map API field names to display names (curated subset)
    field_map = {
        'ticker': 'Symbol',
        'rank': 'Rank',
        'combined_score': 'Score',
        'momentum_score': 'Momentum',
        'fundamental_score': 'Fundamentals',
        'sentiment_score': 'Sentiment',
        'last_price': 'Price',
        'last_price_timestamp': 'Price Time',
        'rationale': 'Analysis',
        'week_start_date': 'Week'
    }

    def _build_display_df(src_df: pd.DataFrame) -> pd.DataFrame:
        """Return a curated display DataFrame containing only fields in field_map."""
        df_out = pd.DataFrame()
        for api_field, display_name in field_map.items():
            if api_field in src_df.columns:
                df_out[display_name] = src_df[api_field]

        # Numeric formatting
        if 'Score' in df_out.columns:
            df_out['Score'] = df_out['Score'].round(1)
        for col in ['Momentum', 'Fundamentals', 'Sentiment']:
            if col in df_out.columns:
                df_out[col] = df_out[col].round(1)

        # Price formatting
        if 'Price' in df_out.columns:
            df_out['Price'] = df_out['Price'].map(lambda v: f"${v:,.2f}" if pd.notnull(v) else "N/A")

        return df_out

    # Build display dataframe with available columns
    df_display = _build_display_df(picks_df)
    
    # Create DataTable
    return dash_table.DataTable(
        id="wp-table",
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
    Load weekly picks from source (DB, JSON, or fixture).
    
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
            import os
            json_path = 'data/picks/weekly_picks.json'
            
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                picks_df = pd.DataFrame(data.get('data', []))
                logger.info(f"Loaded {len(picks_df)} picks from JSON fallback")
            else:
                # Try DB
                picks_df = fetcher.load_from_db(DB_TABLE)
                logger.info(f"Loaded {len(picks_df)} picks from database")
        
        # Weekly picks already include chart_array with prices, no enrichment needed
        
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
    Register all callbacks for weekly picks tab.
    
    Args:
        app: Dash app instance
    """
    
    @app.callback(
        Output('wp-content', 'children'),
        Output('wp-status-message', 'children'),
        Output('wp-data-store', 'data'),
        Input('wp-refresh-btn', 'n_clicks'),
        Input('wp-auto-refresh', 'n_intervals'),
        prevent_initial_call=False
    )
    def load_picks_content(refresh_clicks, auto_intervals):
        """Load and display picks data."""
        try:
            # Force reload on manual refresh
            if ctx.triggered_id == 'wp-refresh-btn':
                logger.info("Manual refresh triggered")
                # Clear cache to force reload
                _weekly_cache.clear()
            
            # Load picks
            picks_df = _load_picks_data()
            
            if picks_df.empty:
                status = dbc.Badge("⚠️ No data available", color="warning")
                content = dbc.Alert(
                    "No weekly picks data found. Try refreshing or check data source.",
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
                                f"{picks_df['combined_score'].mean():.1f}" if 'combined_score' in picks_df.columns else "N/A",
                                className="mb-0 text-success"
                            ),
                            html.P("Avg Score", className="text-muted small mb-0")
                        ])
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.H5(
                                str(picks_df['week_start_date'].nunique() if 'week_start_date' in picks_df.columns else 1),
                                className="mb-0 text-info"
                            ),
                            html.P("Weeks", className="text-muted small mb-0")
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
        Output('wp-csv-download', 'data'),
        Input('wp-download-btn', 'n_clicks'),
        State('wp-data-store', 'data'),
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

            # Build curated display DataFrame (same columns as UI table)
            field_map = {
                'ticker': 'Symbol',
                'rank': 'Rank',
                'combined_score': 'Score',
                'momentum_score': 'Momentum',
                'fundamental_score': 'Fundamentals',
                'sentiment_score': 'Sentiment',
                'last_price': 'Price',
                'last_price_timestamp': 'Price Time',
                'rationale': 'Analysis',
                'week_start_date': 'Week'
            }

            df_out = pd.DataFrame()
            for api_field, display_name in field_map.items():
                if api_field in picks_df.columns:
                    df_out[display_name] = picks_df[api_field]

            # Format numeric and price columns for CSV
            if 'Score' in df_out.columns:
                df_out['Score'] = df_out['Score'].round(1)
            for col in ['Momentum', 'Fundamentals', 'Sentiment']:
                if col in df_out.columns:
                    df_out[col] = df_out[col].round(1)
            if 'Price' in df_out.columns:
                df_out['Price'] = df_out['Price'].map(lambda v: f"{v:.2f}" if pd.notnull(v) else "")

            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"weekly_picks_{timestamp}.csv"

            return dcc.send_data_frame(df_out.to_csv, filename, index=False)
            
        except Exception as e:
            logger.error(f"CSV download failed: {e}")
            raise PreventUpdate
    
    logger.info("✅ Weekly picks callbacks registered")


# Module exports
__all__ = ['create_layout', 'register_callbacks']
