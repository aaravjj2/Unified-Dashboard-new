"""
Chatbot Callbacks - RAG Chat Assistant UI Integration
Wires chatbot UI components to backend RAG API endpoints

Responsibilities:
- Handle chat message submission to /api/chat/query
- Display AI responses with sources
- Present action suggestions with confirmation flow
- Manage chat history and context
- Toggle chat visibility
"""

import logging
import json
import time
import uuid
from dash import Input, Output, State, html, no_update, callback_context
import dash_bootstrap_components as dbc

# Use internal RAG orchestrator and action executor to avoid HTTP calls
from financial_dashboard.services.chat.rag import get_rag
from financial_dashboard.services.chat.actions import get_executor

logger = logging.getLogger(__name__)

# We'll call internal orchestrator/executor directly to avoid HTTP requests


def create_action_suggestion_card(action_data):
    """
    Create action suggestion card with confirmation buttons
    
    Args:
        action_data: Dict with keys: action, payload, confidence
        
    Returns:
        dbc.Card component
    """
    if not action_data:
        return html.Div()
    
    action_type = action_data.get('action', 'unknown')
    payload = action_data.get('payload', {})
    confidence = action_data.get('confidence', 'N/A')
    
    # Format payload nicely
    payload_items = []
    for key, value in payload.items():
        payload_items.append(
            html.Li([
                html.Strong(f"{key}: "),
                html.Span(str(value))
            ])
        )
    
    return dbc.Card([
        dbc.CardHeader(
            html.Div([
                html.I(className="fas fa-robot", style={"marginRight": "8px"}),
                html.Strong("Action Suggestion")
            ]),
            style={"backgroundColor": "#fef3c7", "color": "#92400e"}
        ),
        dbc.CardBody([
            html.H5(action_type.replace('_', ' ').title(), className="card-title"),
            html.Hr(),
            html.Ul(payload_items, style={"listStyle": "none", "paddingLeft": "0"}),
            html.P([
                html.Small([
                    html.I(className="fas fa-chart-line", style={"marginRight": "4px"}),
                    f"Confidence: {confidence}"
                ])
            ], style={"color": "#6b7280", "marginTop": "8px"}),
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-check", style={"marginRight": "6px"}), "Confirm"],
                    id="chatbot-action-confirm",
                    color="success",
                    size="sm",
                    style={"marginRight": "8px"}
                ),
                dbc.Button(
                    [html.I(className="fas fa-times", style={"marginRight": "6px"}), "Cancel"],
                    id="chatbot-action-cancel",
                    color="danger",
                    size="sm",
                    outline=True
                )
            ], style={"marginTop": "12px"})
        ])
    ], style={
        "marginTop": "12px",
        "marginBottom": "12px",
        "border": "2px solid #fbbf24",
        "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
    }, id="chatbot-action-card")


def create_message_bubble(message: str, is_user: bool = False, sources: list = None):
    """
    Create a chat message bubble
    
    Args:
        message: The message text
        is_user: True if message is from user, False if from AI
        sources: Optional list of data sources used for the response
    """
    bubble_style = {
        "maxWidth": "85%",
        "marginBottom": "16px",
        "padding": "12px 16px",
        "borderRadius": "16px",
        "wordWrap": "break-word",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
    }
    
    if is_user:
        bubble_style.update({
            "marginLeft": "auto",
            "backgroundColor": "#667eea",
            "color": "white",
            "borderBottomRightRadius": "4px",
        })
    else:
        bubble_style.update({
            "marginRight": "auto",
            "backgroundColor": "white",
            "color": "#000000",  # BLACK TEXT per requirement
            "borderBottomLeftRadius": "4px",
        })
    
    bubble_content = [
        html.Div(message, style={"whiteSpace": "pre-wrap", "color": "#000000" if not is_user else "white"}),
    ]
    
    # Add sources if provided (for AI responses)
    if sources and not is_user:
        bubble_content.append(
            html.Div(
                style={"marginTop": "8px", "fontSize": "12px", "color": "#666", "fontStyle": "italic"},
                children=[
                    html.I(className="fas fa-info-circle", style={"marginRight": "4px"}),
                    f"Sources: {', '.join(sources[:3])}"  # Limit to 3 sources for readability
                ]
            )
        )
    
    return html.Div(
        style={"display": "flex", "justifyContent": "flex-end" if is_user else "flex-start"},
        children=[
            html.Div(
                style=bubble_style,
                children=bubble_content,
                **{'data-testid': 'chat-message', 'data-is-user': str(is_user)}
            )
        ]
    )


def register_chatbot_callbacks(app):
    """
    Register all chatbot-related callbacks
    
    Args:
        app: Dash application instance
    """
    
    # Guard against duplicate registration
    if getattr(app, "_chatbot_callbacks_registered", False):
        logger.info("Chatbot callbacks already registered, skipping")
        return
    
    logger.info("🤖 Registering chatbot callbacks...")
    
    # ========================================================================
    # CALLBACK 1: Toggle Chatbot Visibility
    # ========================================================================
    @app.callback(
        Output('chatbot-container', 'style'),
        Input('chatbot-toggle-btn', 'n_clicks'),
        Input('chatbot-close-btn', 'n_clicks'),
        State('chatbot-container', 'style'),
        prevent_initial_call=True
    )
    def toggle_chatbot(toggle_clicks, close_clicks, current_style):
        """Show/hide chatbot window"""
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'chatbot-toggle-btn':
            # Show chatbot
            return {"display": "block"}
        elif trigger_id == 'chatbot-close-btn':
            # Hide chatbot
            return {"display": "none"}
        
        return no_update
    
    # ========================================================================
    # CALLBACK 2: Handle Chat Message Submission
    # ========================================================================
    @app.callback(
        Output('chatbot-messages', 'children'),
        Output('chatbot-input', 'value'),
        Output('chatbot-pending-action', 'data'),  # Store pending action for confirmation
        Input('chatbot-send-btn', 'n_clicks'),
        State('chatbot-input', 'value'),
        State('chatbot-messages', 'children'),
        State('chatbot-session-id', 'data'),
        State('dashboard-tabs', 'active_tab'),  # Get current tab for context
        prevent_initial_call=True
    )
    def handle_chat_message(send_clicks, message, current_messages, session_id, active_tab):
        """
        Send user message to RAG API and display response
        NOTE: dbc.Input doesn't fire n_submit events - only button click works
        """
        if not message or not message.strip():
            return no_update, no_update, no_update
        
        logger.info(f"🤖 Chat message: {message[:50]}...")
        
        # Add user message bubble
        user_bubble = create_message_bubble(message, is_user=True)
        current_messages = current_messages or []
        current_messages.append(user_bubble)
        
        # Build tab context for RAG
        tab_context = {
            "tab": active_tab or "unknown",
            "timestamp": time.time()
        }
        
        # TODO: Extract ticker from tab-specific stores if available
        # For now, tab context is minimal
        
        try:
            # Try calling the GPU-accelerated chatbot service first
            import httpx
            chatbot_url = "http://localhost:8062"
            service_available = False
            
            try:
                response = httpx.post(
                    f"{chatbot_url}/api/chat",
                    json={"message": message, "session_id": session_id or "default"},
                    timeout=5.0  # Short timeout for quick fallback
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get('response', 'Sorry, I could not generate a response.')
                    sources = data.get('sources', [])
                    service_available = True
                    
                    # Add AI response bubble
                    ai_bubble = create_message_bubble(answer, is_user=False, sources=sources)
                    current_messages.append(ai_bubble)
                    
                    logger.info(f"✅ Chatbot response received from service: {len(answer)} chars, {len(sources)} sources")
                    return current_messages, "", None
                    
            except (httpx.ConnectError, httpx.TimeoutException) as conn_err:
                logger.warning(f"Chatbot service unavailable on port 8062, using fallback response: {conn_err}")
                service_available = False
            
            # Fallback response when service unavailable
            if not service_available:
                fallback_message = """I'm currently offline. The AI chatbot service isn't running.

To enable full chatbot functionality, you can:
1. Start the chatbot service: `python -m uvicorn financial_dashboard.services.chatbot_service:app --host 0.0.0.0 --port 8062`
2. Or set up a Gemini API key in your environment

For now, you can use the dashboard's other features:
• 📊 Market data and charts
• 💹 Options analysis in Volatility Lab
• 📈 Market forecasts
• 💼 Portfolio tracking

Feel free to explore the tabs above!"""
                
                # Add fallback response bubble
                ai_bubble = create_message_bubble(fallback_message, is_user=False, sources=["System"])
                current_messages.append(ai_bubble)
                
                logger.info("✅ Chatbot fallback response provided")
                return current_messages, "", None

        except Exception as e:
            logger.exception(f"Chat error: {e}")
            error_bubble = create_message_bubble(
                "Sorry, I'm having trouble right now. Please try the dashboard's other features!",
                is_user=False
            )
            current_messages.append(error_bubble)
            return current_messages, "", None  # FIX: Must return all 3 outputs
    
    # ========================================================================
    # CALLBACK 3: Handle Action Confirmation/Cancellation
    # ========================================================================
    @app.callback(
        Output('chatbot-messages', 'children', allow_duplicate=True),
        Output('chatbot-pending-action', 'data', allow_duplicate=True),
        Input('chatbot-action-confirm', 'n_clicks'),
        Input('chatbot-action-cancel', 'n_clicks'),
        State('chatbot-pending-action', 'data'),
        State('chatbot-messages', 'children'),
        State('chatbot-session-id', 'data'),
        prevent_initial_call=True
    )
    def handle_action_confirmation(confirm_clicks, cancel_clicks, pending_action, current_messages, session_id):
        """
        Execute or cancel pending action suggestion
        """
        ctx = callback_context
        if not ctx.triggered or not pending_action:
            return no_update, no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        current_messages = current_messages or []
        
        if trigger_id == 'chatbot-action-cancel':
            # User cancelled action
            cancel_bubble = create_message_bubble(
                "Action cancelled.",
                is_user=False
            )
            current_messages.append(cancel_bubble)
            logger.info("❌ User cancelled action")
            return current_messages, None
        
        elif trigger_id == 'chatbot-action-confirm':
            # User confirmed - execute action
            logger.info(f"✅ Executing action: {pending_action.get('action')}")
            
            try:
                # Execute using internal ActionExecutor
                executor = get_executor()
                action_id = pending_action.get('action_id') or str(uuid.uuid4())
                action_type = pending_action.get('action')
                payload = pending_action.get('payload', {})

                result = executor.execute(
                    action_id=action_id,
                    action_type=action_type,
                    payload=payload,
                    confirmed=True,
                    user_id=session_id
                )

                if result.get('success'):
                    success_msg = result.get('result') or result.get('message', 'Action executed successfully!')
                    success_bubble = create_message_bubble(
                        f"✅ Action executed: {json.dumps(success_msg) if isinstance(success_msg, dict) else str(success_msg)}",
                        is_user=False
                    )
                    current_messages.append(success_bubble)
                else:
                    error_msg = result.get('error', 'Action failed')
                    error_bubble = create_message_bubble(
                        f"❌ {error_msg}",
                        is_user=False
                    )
                    current_messages.append(error_bubble)

            except Exception as e:
                logger.exception(f"Action execution error (internal): {e}")
                error_bubble = create_message_bubble(
                    f"❌ Error executing action: {str(e)[:200]}",
                    is_user=False
                )
                current_messages.append(error_bubble)

            return current_messages, None
        
        return no_update, no_update
    
    # ========================================================================
    # CALLBACK 4: Auto-scroll to latest message
    # ========================================================================
    app.clientside_callback(
        """
        function(messages) {
            // Auto-scroll chat to bottom when new messages appear
            setTimeout(function() {
                var container = document.getElementById('chatbot-messages-container');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }

                // Also expose a small diagnostic hook for E2E: write last response snippet
                try {
                    var diag = document.getElementById('chat-color-diagnostic');
                    if (diag && messages && messages.length > 0) {
                        var last = messages[messages.length - 1];
                        var text = '';
                        function extractText(node) {
                            if (!node) return '';
                            if (typeof node === 'string') return node;
                            if (Array.isArray(node)) return node.map(extractText).join('');
                            if (node && node.props && node.props.children) return extractText(node.props.children);
                            if (node && node.children) return extractText(node.children);
                            return '';
                        }
                        try { text = extractText(last).toString(); } catch(e){ text = '' }
                        diag.dataset.lastResponse = text.slice(0,200);
                        diag.dataset.lastResponseLen = text.length;
                    }
                } catch(e) { /* ignore diagnostics failures */ }

            }, 100);
            return window.dash_clientside.no_update;
        }
        """,
        Output('chatbot-loading-output', 'children'),
        Input('chatbot-messages', 'children'),
        prevent_initial_call=True
    )

    
    setattr(app, "_chatbot_callbacks_registered", True)
    logger.info("✅ Chatbot callbacks registered successfully")
