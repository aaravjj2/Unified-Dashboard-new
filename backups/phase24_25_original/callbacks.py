"""
Callback Registration Module
Registers all tab callbacks with the Dash app instance.

CRITICAL: This module is imported AFTER app.py completes initialization
to avoid circular import issues.
"""
import logging

logger = logging.getLogger(__name__)

def register_all_callbacks(app, loaded_tabs, SH=None, CHATBOT_AVAILABLE=False):
    """
    Register all tab callbacks with the app.
    
    Args:
        app: The DashProxy app instance
        loaded_tabs: Dictionary of loaded tab modules
        SH: Shared helpers module (optional)
        CHATBOT_AVAILABLE: Whether chatbot UI is available
    """
    logger.info(f"[CALLBACK_REG] Starting callback registration. app object id: {id(app)}, type: {type(app)}")
    
    registered_count = 0
    
    for tab_id, tab_info in loaded_tabs.items():
        try:
            if hasattr(tab_info['module'], 'register_callbacks'):
                callback_func = tab_info['module'].register_callbacks
                logger.info(f"[CALLBACK_REG] Attempting to register callbacks for {tab_info['name']}")
                
                # Try different callback registration signatures
                try:
                    callback_func(app)
                    logger.info(f"✓ Registered callbacks for {tab_info['name']}")
                except TypeError:
                    try:
                        callback_func(app, SH)
                        logger.info(f"✓ Registered callbacks for {tab_info['name']} (with SH)")
                    except Exception as e:
                        logger.error(f"Failed to register callbacks for {tab_info['name']}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
                
                # Verify registration worked
                callback_count = len(getattr(app, 'callback_map', {}))
                logger.info(f"[CALLBACK_REG] Callback map now has {callback_count} entries after {tab_info['name']}")
                registered_count = callback_count
                
        except Exception as e:
            logger.error(f"Error registering callbacks for {tab_info['name']}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Sprint 7: AI Chatbot Callbacks
    if CHATBOT_AVAILABLE:
        from dash_extensions.enrich import Output, Input, State
        import httpx
        from components.chatbot_ui import create_message_bubble
        
        @app.callback(
            Output("chatbot-container", "style"),
            Input("chatbot-toggle-btn", "n_clicks"),
            State("chatbot-container", "style"),
            prevent_initial_call=True
        )
        def toggle_chatbot(n_clicks, current_style):
            """Toggle chatbot visibility."""
            if not current_style:
                current_style = {"display": "none"}
            
            if current_style.get("display") == "none":
                return {"display": "flex"}
            else:
                return {"display": "none"}
        
        @app.callback(
            Output("chatbot-messages", "children"),
            Output("chatbot-input", "value"),
            Input("chatbot-send-btn", "n_clicks"),
            Input("chatbot-input", "n_submit"),
            State("chatbot-input", "value"),
            State("chatbot-messages", "children"),
            prevent_initial_call=True
        )
        def send_message(send_clicks, n_submit, message, current_messages):
            """Send message to chatbot and get response."""
            if not message or not message.strip():
                return current_messages, ""
            
            # Add user message
            current_messages = current_messages or []
            user_bubble = create_message_bubble(message, is_user=True)
            current_messages.append(user_bubble)
            
            # Call chatbot service
            try:
                response = httpx.post(
                    'http://localhost:5000/chat',
                    json={'message': message},
                    timeout=30.0
                )
                response.raise_for_status()
                bot_response = response.json().get('response', 'No response')
                bot_bubble = create_message_bubble(bot_response, is_user=False)
                current_messages.append(bot_bubble)
            except Exception as e:
                logger.error(f"Error calling chatbot service: {e}")
                error_bubble = create_message_bubble(f"Error: {str(e)}", is_user=False)
                current_messages.append(error_bubble)
            
            return current_messages, ""
    
    final_callback_count = len(getattr(app, 'callback_map', {}))
    logger.info(f"[CALLBACK_REG] Registration complete. Total callbacks: {final_callback_count}")
    
    return final_callback_count
