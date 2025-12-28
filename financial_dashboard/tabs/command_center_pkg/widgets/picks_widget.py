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
            dbc.Button(
                "Run Picks (Live)",
                id="cc-picks-run-live-btn",
                color="danger",
                size="sm",
                n_clicks=0,
                className="mt-2 ms-2"
            ),
            html.Small(
                id="cc-picks-last-run-id",
                children="Last run: N/A",
                className="text-muted d-block mt-2"
            ),
        ]),
    ], className="mb-3")


def create_picks_live_confirm_modal():
    from dash import html
    return dbc.Modal([
        dbc.ModalHeader("Confirm Live Picks Execution"),
        dbc.ModalBody(html.Div([
            html.P("You are about to execute live market orders. This will place real trades (paper/live depending on Alpaca config)."),
            html.P("Ensure ALLOW_AUTO_BUY=1 and Alpaca keys are configured."),
            html.Small("This action is auditable and will be logged.", className="text-muted")
        ])),
        dbc.ModalFooter([
            dbc.Button("Confirm Execute", id="cc-picks-live-confirm-btn", color="danger", n_clicks=0),
            dbc.Button("Cancel", id="cc-picks-live-cancel-btn", color="secondary", n_clicks=0, className="ms-2")
        ])
    ], id="cc-picks-live-confirm-modal", is_open=False)


