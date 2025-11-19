"""
AI Chatbot UI Component
Floating chat interface for the financial dashboard
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc


def create_chatbot_ui():
    """
    Create the chatbot UI layout with a floating window design
    """
    return html.Div(
        id="chatbot-container",
        style={"display": "none"},  # Hidden by default
        children=[
            # Chatbot Window
            dbc.Card(
                id="chatbot-window",
                style={
                    "position": "fixed",
                    "bottom": "100px",
                    "right": "30px",
                    "width": "400px",
                    "maxHeight": "600px",
                    "zIndex": "9999",
                    "boxShadow": "0 8px 32px rgba(0,0,0,0.3)",
                    "borderRadius": "16px",
                    "overflow": "hidden",
                },
                children=[
                    # Header
                    dbc.CardHeader(
                        style={
                            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                            "color": "white",
                            "padding": "16px",
                            "borderBottom": "none",
                        },
                        children=[
                            html.Div(
                                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                                children=[
                                    html.Div(
                                        children=[
                                            html.I(className="fas fa-robot", style={"marginRight": "10px", "fontSize": "20px"}),
                                            html.Span("AI Financial Assistant", style={"fontSize": "18px", "fontWeight": "600"}),
                                        ]
                                    ),
                                    html.Button(
                                        html.I(className="fas fa-times"),
                                        id="chatbot-close-btn",
                                        n_clicks=0,
                                        style={
                                            "background": "transparent",
                                            "border": "none",
                                            "color": "white",
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "padding": "0",
                                            "outline": "none",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # Chat Messages Area
                    dbc.CardBody(
                        id="chatbot-messages-container",
                        style={
                            "height": "400px",
                            "overflowY": "auto",
                            "padding": "20px",
                            "backgroundColor": "#f8f9fa",
                        },
                        children=[
                            html.Div(id="chatbot-messages", children=[
                                # Welcome message
                                create_message_bubble(
                                    "Hello! I'm your AI financial assistant. How can I help you today?",
                                    is_user=False
                                )
                            ])
                        ],
                    ),
                    # Input Area
                    dbc.CardFooter(
                        style={
                            "padding": "16px",
                            "backgroundColor": "white",
                            "borderTop": "1px solid #e0e0e0",
                        },
                        children=[
                            html.Div(
                                style={"display": "flex", "gap": "10px"},
                                children=[
                                    dbc.Input(
                                        id="chatbot-input",
                                        type="text",
                                        placeholder="Ask me anything about stocks, markets, or your portfolio...",
                                        style={
                                            "flex": "1",
                                            "borderRadius": "24px",
                                            "padding": "12px 20px",
                                            "border": "1px solid #ddd",
                                        },
                                        debounce=False,
                                    ),
                                    dbc.Button(
                                        html.I(className="fas fa-paper-plane"),
                                        id="chatbot-send-btn",
                                        n_clicks=0,
                                        color="primary",
                                        style={
                                            "borderRadius": "50%",
                                            "width": "48px",
                                            "height": "48px",
                                            "padding": "0",
                                            "display": "flex",
                                            "alignItems": "center",
                                            "justifyContent": "center",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # Loading indicator
            dcc.Loading(
                id="chatbot-loading",
                type="circle",
                children=html.Div(id="chatbot-loading-output"),
                style={"display": "none"}
            ),
            # Store for chat history
            dcc.Store(id="chatbot-session-id", data="session-" + str(hash("default"))),
        ],
    )


def create_floating_action_button():
    """
    Create the floating action button (FAB) that toggles the chatbot
    """
    return html.Div(
        id="chatbot-fab",
        children=[
            dbc.Button(
                [
                    html.I(
                        className="fas fa-comments",
                        style={"fontSize": "28px"}
                    ),
                ],
                id="chatbot-toggle-btn",
                n_clicks=0,
                color="primary",
                style={
                    "position": "fixed",
                    "bottom": "30px",
                    "right": "30px",
                    "width": "64px",
                    "height": "64px",
                    "borderRadius": "50%",
                    "zIndex": "9998",
                    "boxShadow": "0 4px 16px rgba(0,0,0,0.3)",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "border": "none",
                    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    "cursor": "pointer",
                    "transition": "transform 0.3s ease",
                },
            ),
        ],
    )


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
        "animation": "slideIn 0.3s ease",
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
            "color": "#333",
            "borderBottomLeftRadius": "4px",
        })
    
    bubble_content = [
        html.Div(message, style={"whiteSpace": "pre-wrap"}),
    ]
    
    # Add sources if provided (for AI responses)
    if sources and not is_user:
        bubble_content.append(
            html.Div(
                style={"marginTop": "8px", "fontSize": "12px", "color": "#666", "fontStyle": "italic"},
                children=[
                    html.I(className="fas fa-info-circle", style={"marginRight": "4px"}),
                    f"Sources: {', '.join(sources)}"
                ]
            )
        )
    
    return html.Div(
        style={"display": "flex", "justifyContent": "flex-end" if is_user else "flex-start"},
        children=[
            html.Div(
                style=bubble_style,
                children=bubble_content
            )
        ]
    )


# CSS for animations
CHATBOT_STYLES = """
@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

#chatbot-fab:hover button {
    transform: scale(1.1);
}

#chatbot-messages-container {
    scrollbar-width: thin;
    scrollbar-color: #667eea #f1f1f1;
}

#chatbot-messages-container::-webkit-scrollbar {
    width: 8px;
}

#chatbot-messages-container::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

#chatbot-messages-container::-webkit-scrollbar-thumb {
    background: #667eea;
    border-radius: 4px;
}

#chatbot-messages-container::-webkit-scrollbar-thumb:hover {
    background: #764ba2;
}
"""
