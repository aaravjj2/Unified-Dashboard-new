"""
Picks Widget - Picks Pipeline Status & Execution
Shows last run status and allows dry-run execution
"""

import dash_bootstrap_components as dbc
from dash import html
import logging

logger = logging.getLogger(__name__)


def create_picks_widget():
    """
    Create picks status widget
    
    Returns minimal Dash component structure
    """
    return dbc.Card([
        dbc.CardHeader("📊 Picks Status"),
        dbc.CardBody([
            html.Div(id="cc-picks-card", children=[
                html.P("Loading picks status...", className="text-muted"),
            ]),
            dbc.Button(
                "Run Picks (Dry)",
                id="cc-picks-run-btn",
                color="success",
                size="sm",
                n_clicks=0,
                className="mt-2"
            ),
            html.Small(
                id="cc-picks-last-run-id",
                children="Last run: N/A",
                className="text-muted d-block mt-2"
            ),
        ]),
    ], className="mb-3")
