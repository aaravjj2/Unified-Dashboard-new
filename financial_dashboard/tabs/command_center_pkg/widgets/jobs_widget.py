"""
Jobs Widget - Background Jobs & Tasks Monitor
Displays running and completed background jobs
"""

import dash_bootstrap_components as dbc
from dash import html
import logging

logger = logging.getLogger(__name__)


def create_jobs_widget():
    """
    Create jobs monitoring widget
    
    Returns minimal Dash component structure
    """
    return dbc.Card([
        dbc.CardHeader("🔧 Jobs & Background Tasks"),
        dbc.CardBody(
            html.Div(id="cc-jobs-card", children=[
                html.P("Loading jobs status...", className="text-muted"),
            ])
        ),
    ], className="mb-3")
