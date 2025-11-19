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

    # Sprint 7: AI Chatbot Callbacks
    if CHATBOT_AVAILABLE:
        import httpx
        from components.chatbot_ui import create_message_bubble
        
        @app.callback(
            Output("chatbot-container", "style"),
            Input("chatbot-toggle-btn", "n_clicks"),
            Input("chatbot-close-btn", "n_clicks"),
            State("chatbot-container", "style"),
            prevent_initial_call=True
        )
        def toggle_chatbot(toggle_clicks, close_clicks, current_style):
            """Toggle chatbot window visibility."""
            ctx = dash.callback_context
            if not ctx.triggered:
                return current_style or {"display": "none"}
            
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "chatbot-toggle-btn":
                is_hidden = current_style.get("display") == "none" if current_style else True
                return {"display": "block"} if is_hidden else {"display": "none"}
            elif trigger_id == "chatbot-close-btn":
                return {"display": "none"}
            
            return current_style or {"display": "none"}
        
        @app.callback(
            Output("chatbot-messages", "children"),
            Output("chatbot-input", "value"),
            Input("chatbot-send-btn", "n_clicks"),
            State("chatbot-input", "value"),
            State("chatbot-messages", "children"),
            State("chatbot-session-id", "data"),
            prevent_initial_call=True
        )
        def send_message(n_clicks, message, current_messages, session_id):
            """Send message to chatbot and display response."""
            if not message or not message.strip():
                return current_messages, ""
            
            from components.chatbot_ui import create_message_bubble
            user_bubble = create_message_bubble(message, is_user=True)
            current_messages.append(user_bubble)
            
            try:
                api_url = os.getenv("API_GATEWAY_URL", "http://localhost:8049")
                response = httpx.post(
                    f"{api_url}/api/chat/chat",
                    json={"message": message, "session_id": session_id},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ai_message = data.get("response", "Sorry, I couldn't process that request.")
                    sources = data.get("sources", [])
                    ai_bubble = create_message_bubble(ai_message, is_user=False, sources=sources)
                    current_messages.append(ai_bubble)
                else:
                    error_bubble = create_message_bubble(
                        f"Error: Unable to get response (Status {response.status_code})",
                        is_user=False
                    )
                    current_messages.append(error_bubble)
            except Exception as e:
                logger.error(f"Error calling chatbot service: {e}")
                error_bubble = create_message_bubble(f"Error: {str(e)}", is_user=False)
                current_messages.append(error_bubble)
            
            return current_messages, ""
    
    callback_count = 3 if CHATBOT_AVAILABLE else 2
    logger.info(f"✅ Registered {callback_count} global callbacks")
    return callback_count
