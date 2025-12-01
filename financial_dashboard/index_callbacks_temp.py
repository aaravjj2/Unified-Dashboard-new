"""
Temporary file to hold index.py global callbacks.
These will be moved into index.py's register_index_callbacks() function.
"""
import logging
import dash
from dash_extensions.enrich import Input, Output, State
import dash_bootstrap_components as dbc
from dash_extensions.enrich import html
import os

logger = logging.getLogger(__name__)

def register_global_callbacks(app, loaded_tabs, CHATBOT_AVAILABLE):
    """
    Register global callbacks for search and theme toggle.
    
    Args:
        app: Dash app instance
        loaded_tabs: Dict of loaded tab modules
        CHATBOT_AVAILABLE: Bool indicating if chatbot is enabled
    """
    logger.info("🔵 Registering global callbacks (search, theme, chatbot)...")
    
    @app.callback(
        Output("global-search-modal", "is_open"),
        Output("global-search-results", "children"),
        Input("global-search-button", "n_clicks"),
        Input("global-search-close", "n_clicks"),
        State("global-search-input", "value"),
        State("global-search-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_global_search(search_clicks, close_clicks, search_value, is_open):
        """Handle global search functionality."""
        ctx = dash.callback_context
        if not ctx.triggered:
            return False, []
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "global-search-close":
            return False, []
        
        if button_id == "global-search-button" and search_value:
            results = []
            
            # Search stocks
            if search_value.upper() in ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "META", "AMZN"]:
                results.append(
                    dbc.Card([
                        dbc.CardHeader("Stock Found"),
                        dbc.CardBody([
                            html.H5(f"${search_value.upper()}", className="card-title"),
                            html.P("Click to view in Market Trends"),
                            dbc.Button("Go to Market Trends", color="primary", size="sm")
                        ])
                    ], className="mb-2")
                )
            
            # Search tabs
            for tab_id, tab_info in loaded_tabs.items():
                if search_value.lower() in tab_info['name'].lower():
                    results.append(
                        dbc.Card([
                            dbc.CardHeader("Tab Found"),
                            dbc.CardBody([
                                html.H5(tab_info['name'], className="card-title"),
                                html.P(f"Navigate to {tab_info['name']} tab"),
                                dbc.Button(f"Go to {tab_info['name']}", color="info", size="sm")
                            ])
                        ], className="mb-2")
                    )
            
            if not results:
                results = [
                    dbc.Alert("No results found. Try searching for stocks (AAPL, TSLA, etc.) or tab names.", color="warning")
                ]
            
            return True, results
        
        return is_open, []

    @app.callback(
        Output("theme-store", "data"),
        Output("theme-icon", "className"),
        Input("theme-toggle-button", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True
    )
    def toggle_theme(n_clicks, theme_data):
        """Toggle between light and dark themes."""
        current_theme = theme_data.get("theme", "dark")
        new_theme = "light" if current_theme == "dark" else "dark"
        icon_class = "bi bi-sun-fill" if new_theme == "light" else "bi bi-moon-fill"
        return {"theme": new_theme}, icon_class

    # Sprint 7: AI Chatbot Callbacks - MOVED to callbacks/chatbot_callbacks.py
    # We do NOT register them here anymore to avoid DuplicateCallbackOutputError
    # and conflict with the full RAG implementation.
    
    callback_count = 2
    logger.info(f"✅ Registered {callback_count} global callbacks")
    return callback_count
