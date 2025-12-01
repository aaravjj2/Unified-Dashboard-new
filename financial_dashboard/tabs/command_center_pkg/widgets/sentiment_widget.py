"""
Sentiment Widget - Market Sentiment Display
Real-time market sentiment indicator with historical trend
"""

import dash_bootstrap_components as dbc
from dash import html
import logging

logger = logging.getLogger(__name__)


def create_sentiment_widget():
    """
    Create market sentiment widget
    
    Returns minimal Dash component structure
    Loaded dynamically via callback to avoid import overhead
    """
    return dbc.Card([
        dbc.CardHeader("📈 Market Sentiment"),
        dbc.CardBody([
            html.Div([
                html.H4(
                    "Neutral",
                    id="cc-sentiment-indicator",
                    className="text-muted"
                ),
                html.Small(
                    "Score: 0.0",
                    id="cc-sentiment-score",
                    className="d-block"
                ),
                html.Small(
                    "Last updated: N/A",
                    id="cc-sentiment-last-updated",
                    className="text-muted d-block mt-1"
                ),
            ]),
            dbc.Button(
                "View Details",
                id="cc-sentiment-details-btn",
                color="info",
                size="sm",
                className="mt-2",
                n_clicks=0
            ),
        ]),
    ], className="mb-3")
