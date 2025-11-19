"""
Fixed Callbacks for Market Trends Tab

This module contains refactored, working callbacks for all Market Trends buttons.
Import and use these to replace the broken callbacks in market_trends.py.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

import os
import json
import logging
import time
from datetime import datetime
from dash import html, dcc, no_update
from dash.exceptions import PreventUpdate
import pandas as pd

logger = logging.getLogger(__name__)


def create_safe_callback(callback_name):
    """
    Decorator to wrap callbacks with comprehensive error handling.
    
    Requirements: 4.1, 4.2
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PreventUpdate:
                raise
            except Exception as e:
                logger.exception(f"Callback {callback_name} failed: {e}")
                return html.Div(
                    f"Error in {callback_name}: {str(e)[:200]}",
                    style={
                        'padding': '16px',
                        'backgroundColor': '#fee2e2',
                        'color': '#991b1b',
                        'borderRadius': '6px',
                        'marginTop': '8px'
                    }
                )
        return wrapper
    return decorator


def register_fixed_callbacks(app, cache_manager, news_manager):
    """
    Register all fixed callbacks for Market Trends tab.
    
    Args:
        app: Dash app instance
        cache_manager: CacheManager instance
        news_manager: NewsManager instance
    """
    from dash import Input, Output, State, callback_context
    from financial_dashboard import _shared as SH
    
    # ================================================================
    # BUTTON 2: Reload Model
    # ================================================================
    @app.callback(
        Output('model-status', 'children'),
        Output('results-area', 'children', allow_duplicate=True),
        Input('reload-model', 'n_clicks'),
        prevent_initial_call=True
    )
    @create_safe_callback('reload_model')
    def reload_model(n_clicks):
        """
        Reload data from disk cache and update display.
        
        Requirements: 2.2, 6.2
        """
        if not n_clicks:
            raise PreventUpdate
        
        logger.info("Reload Model button clicked")
        
        # Load from disk using CacheManager
        data = cache_manager.load_from_disk()
        
        if not data or not data.get('detailed'):
            return (
                "⚠️ No cached data found. Run analysis first.",
                html.Div(
                    "No cached data available. Click 'Run Full Analysis' to generate data.",
                    style={'padding': '20px', 'textAlign': 'center', 'color': '#9ca3af'}
                )
            )
        
        # Update memory cache
        cache_manager.update_cache(data)
        
        # Render table
        from financial_dashboard.tabs.market_trends import _render_html_table_with_prices
        table = _render_html_table_with_prices(data['detailed'], include_prices=True)
        
        cache_info = cache_manager.get_cache_info()
        status_msg = f"✅ Reloaded {cache_info['record_count']} records from cache"
        
        logger.info(status_msg)
        
        return status_msg, table
    
    # ================================================================
    # BUTTON 3: Refresh Cached Display
    # ================================================================
    @app.callback(
        Output('results-area', 'children', allow_duplicate=True),
        Output('status', 'children', allow_duplicate=True),
        Output('status', 'style', allow_duplicate=True),
        Input('refresh-cached', 'n_clicks'),
        prevent_initial_call=True
    )
    @create_safe_callback('refresh_cached_display')
    def refresh_cached_display(n_clicks):
        """
        Refresh display from current cache without re-fetching.
        
        Requirements: 2.3, 5.1
        """
        if not n_clicks:
            raise PreventUpdate
        
        logger.info("Refresh Cached Display button clicked")
        
        # Get cached data
        data = cache_manager.get_cached_data()
        
        if not data or not data.get('detailed'):
            # Try loading from disk
            data = cache_manager.load_from_disk()
        
        if not data or not data.get('detailed'):
            return (
                html.Div(
                    "No cached data available.",
                    style={'padding': '20px', 'textAlign': 'center', 'color': '#9ca3af'}
                ),
                "No cached data found",
                {'display': 'block', 'backgroundColor': '#fef3c7', 'color': '#92400e'}
            )
        
        # Render table
        from financial_dashboard.tabs.market_trends import _render_html_table_with_prices
        table = _render_html_table_with_prices(data['detailed'], include_prices=True)
        
        cache_info = cache_manager.get_cache_info()
        age_minutes = int(cache_info['age_seconds'] / 60) if cache_info['age_seconds'] else 0
        
        return (
            table,
            f"✅ Refreshed display ({cache_info['record_count']} records, {age_minutes}min old)",
            {'display': 'block', 'backgroundColor': '#d1fae5', 'color': '#065f46'}
        )
    
    # ================================================================
    # BUTTON 6: Toggle Full Brief
    # ================================================================
    @app.callback(
        Output('full-brief', 'style'),
        Output('full-brief', 'children'),
        Input('toggle-brief', 'n_clicks'),
        State('full-brief', 'style'),
        prevent_initial_call=True
    )
    @create_safe_callback('toggle_full_brief')
    def toggle_full_brief(n_clicks, current_style):
        """
        Toggle visibility of full market brief.
        
        Requirements: 2.6
        """
        if not n_clicks:
            raise PreventUpdate
        
        logger.info("Toggle Full Brief button clicked")
        
        # Toggle display
        is_hidden = current_style.get('display') == 'none'
        
        if is_hidden:
            # Show brief - load from cache
            data = cache_manager.get_cached_data()
            if not data:
                data = cache_manager.load_from_disk()
            
            brief_text = data.get('brief_text', 'No brief available') if data else 'No brief available'
            
            return (
                {'display': 'block', 'marginTop': '8px', 'padding': '10px', 
                 'borderRadius': '6px', 'backgroundColor': '#071028', 
                 'color': '#e6eef8', 'border': '1px solid #123'},
                html.Pre(brief_text, style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace'})
            )
        else:
            # Hide brief
            return (
                {'display': 'none'},
                ""
            )
    
    # ================================================================
    # BUTTON 7: Download CSV
    # ================================================================
    @app.callback(
        Output('download-data', 'data'),
        Input('mt-download-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    @create_safe_callback('download_csv')
    def download_csv(n_clicks):
        """
        Download latest results as CSV file.
        
        Requirements: 2.7
        """
        if not n_clicks:
            raise PreventUpdate
        
        logger.info("Download CSV button clicked")
        
        # Get cached data
        data = cache_manager.get_cached_data()
        if not data:
            data = cache_manager.load_from_disk()
        
        if not data or not data.get('detailed'):
            logger.warning("No data available for CSV download")
            raise PreventUpdate
        
        # Convert to DataFrame
        df = pd.DataFrame(data['detailed'])
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"market_trends_{timestamp}.csv"
        
        logger.info(f"Generating CSV: {filename} ({len(df)} rows)")
        
        # Return download
        return dcc.send_data_frame(df.to_csv, filename, index=False)
    
    # ================================================================
    # NEWS AUTO-REFRESH CALLBACK
    # ================================================================
    @app.callback(
        Output('news-container', 'children', allow_duplicate=True),
        Input('news-poll-interval', 'n_intervals'),
        State('news-last-updated', 'data'),
        prevent_initial_call=True
    )
    @create_safe_callback('refresh_news')
    def refresh_news(n_intervals, last_updated):
        """
        Auto-refresh news if cache is stale.
        
        Requirements: 1.2, 1.4, 1.5
        """
        # Check if news is stale
        if not news_manager.is_news_stale():
            raise PreventUpdate
        
        logger.info("News cache stale, refreshing...")
        
        # Get tickers from cached data
        data = cache_manager.get_cached_data()
        if not data:
            data = cache_manager.load_from_disk()
        
        if not data or not data.get('detailed'):
            raise PreventUpdate
        
        # Get top 5 tickers
        tickers = [row.get('ticker') for row in data['detailed'][:5] if row.get('ticker')]
        
        if not tickers:
            raise PreventUpdate
        
        try:
            # Fetch fresh news
            news_data = news_manager.fetch_news(tickers, max_per_ticker=2)
            
            # Render news panel
            return news_manager.render_news_panel(news_data)
            
        except Exception as e:
            logger.error(f"Failed to refresh news: {e}")
            # Return error message
            return html.Div(
                f"Failed to fetch news: {str(e)[:100]}",
                **{
                    'data-testid': 'news-panel',
                    'style': {
                        'padding': '16px',
                        'color': '#ef4444',
                        'textAlign': 'center'
                    }
                }
            )
    
    logger.info("Fixed callbacks registered successfully")
