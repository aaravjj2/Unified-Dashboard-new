"""
Chatbot Callbacks - RAG Chat Assistant UI Integration
Wires chatbot UI components to backend RAG API endpoints

Responsibilities:
- Handle chat message submission to /api/chat/query
- Display AI responses with sources
- Present action suggestions with confirmation flow
- Manage chat history and context
- Toggle chat visibility
- Monitor service health
"""

import logging
import json
import time
import uuid
import httpx
from dash import Input, Output, State, html, no_update, callback_context
import dash_bootstrap_components as dbc

# Use internal RAG orchestrator and action executor to avoid HTTP calls
from financial_dashboard.services.chat.rag import get_rag
from financial_dashboard.services.chat.actions import get_executor

logger = logging.getLogger(__name__)

CHATBOT_SERVICE_URL = "http://localhost:8062"

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
    # CALLBACK 1: Toggle Chatbot Visibility (Client-side for speed/reliability)
    # ========================================================================
    app.clientside_callback(
        """
        function(toggle_clicks, close_clicks, current_style) {
            var ctx = dash_clientside.callback_context;
            if (!ctx.triggered || ctx.triggered.length === 0) {
                return window.dash_clientside.no_update;
            }
            
            var trigger_id = ctx.triggered[0].prop_id.split('.')[0];
            
            if (trigger_id === 'chatbot-toggle-btn') {
                return {'display': 'block'};
            } else if (trigger_id === 'chatbot-close-btn') {
                return {'display': 'none'};
            }
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('chatbot-container', 'style'),
        Input('chatbot-toggle-btn', 'n_clicks'),
        Input('chatbot-close-btn', 'n_clicks'),
        State('chatbot-container', 'style'),
        prevent_initial_call=True
    )
    
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
        
        try:
            # Try calling the GPU-accelerated chatbot service first
            service_available = False
            
            try:
                # INCREASED TIMEOUT to 120s for Mistral-7B (first run can be slow)
                response = httpx.post(
                    f"{CHATBOT_SERVICE_URL}/api/chat",
                    json={"message": message, "session_id": session_id or "default"},
                    timeout=120.0 
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
                fallback_message = """The AI chatbot service is currently unavailable or timed out.

If this is the first request, the model might still be loading into GPU memory. Please try again in a minute.

To ensure the service is running:
`python -m uvicorn financial_dashboard.services.chatbot_service:app --host 0.0.0.0 --port 8062`

For now, you can use the dashboard's other features:
• 📊 Market data and charts
• 💹 Options analysis in Volatility Lab
• 📈 Market forecasts
• 💼 Portfolio tracking"""
                
                # Add fallback response bubble
                ai_bubble = create_message_bubble(fallback_message, is_user=False, sources=["System"])
                current_messages.append(ai_bubble)
                
                logger.info("✅ Chatbot fallback response provided")
                return current_messages, "", None

        except Exception as e:
            logger.exception(f"Chat error: {e}")
            error_bubble = create_message_bubble(
                "Sorry, I'm having trouble right now. Please try again later.",
                is_user=False
            )
            current_messages.append(error_bubble)
            return current_messages, "", None
    
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
            }, 100);
            return window.dash_clientside.no_update;
        }
        """,
        Output('chatbot-loading-output', 'children'),
        Input('chatbot-messages', 'children'),
        prevent_initial_call=True
    )

    # ========================================================================
    # CALLBACK 5: Health Check (Status Indicator)
    # ========================================================================
    @app.callback(
        Output('chatbot-status-indicator', 'children'),
        Output('chatbot-status-indicator', 'style'),
        Input('interval-component', 'n_intervals')
    )
    def update_chatbot_status(n):
        """Check chatbot service health and update status indicator"""
        try:
            response = httpx.get(f"{CHATBOT_SERVICE_URL}/health", timeout=2.0)
            if response.status_code == 200:
                return "● Online", {
                    "fontSize": "12px",
                    "marginLeft": "10px",
                    "color": "#4ade80",  # Green
                    "backgroundColor": "rgba(0,0,0,0.2)",
                    "padding": "2px 8px",
                    "borderRadius": "10px",
                    "transition": "all 0.3s ease"
                }
        except Exception:
            pass
            
        return "● Offline", {
            "fontSize": "12px",
            "marginLeft": "10px",
            "color": "#ff6b6b",  # Red
            "backgroundColor": "rgba(0,0,0,0.2)",
            "padding": "2px 8px",
            "borderRadius": "10px",
            "transition": "all 0.3s ease"
        }
    
    setattr(app, "_chatbot_callbacks_registered", True)
    logger.info("✅ Chatbot callbacks registered successfully")
