"""
Chat Widget - Quick Query Interface
Minimal chat interface for quick queries about picks, portfolio, market
"""

import dash_bootstrap_components as dbc
from dash import html
import logging

logger = logging.getLogger(__name__)


def create_chat_widget():
    """
    Create chat widget
    
    Returns minimal Dash component structure
    """
    return dbc.Card([
        dbc.CardHeader("💬 Quick Query"),
        dbc.CardBody([
            html.Div(id="cc-chat-card", children=[
                dbc.Input(
                    id="cc-chat-input",
                    placeholder="Ask about picks, portfolio, or market...",
                    type="text",
                    className="mb-2"
                ),
                dbc.Button(
                    "Send",
                    id="cc-chat-send",
                    color="primary",
                    size="sm",
                    n_clicks=0
                ),
                html.Div(
                    id="cc-chat-response",
                    className="mt-3",
                    style={"minHeight": "100px"}
                ),
            ]),
        ]),
    ])
