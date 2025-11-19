"""
Research Lab Tab - Integration Module

Integrates the Research Lab into the main dashboard.
Uses tabs/research_lab module for UI and callbacks.
"""

import logging
from dash import html

logger = logging.getLogger(__name__)

def layout():
    """Build the Research Lab tab layout."""
    try:
        from .research_lab import layout as create_layout
        return create_layout()
    except Exception as e:
        logger.error(f"Failed to load Research Lab layout: {e}")
        return html.Div([
            html.H2("🧪 Research Lab", className="mt-3"),
            html.P("Error loading Research Lab module. Check logs for details.", 
                   className="text-danger")
        ])

def register_callbacks(app):
    """Register Research Lab callbacks."""
    try:
        from .research_lab import register_callbacks
        register_callbacks(app)
        logger.info("✓ Registered Research Lab callbacks")
    except Exception as e:
        logger.error(f"Failed to register Research Lab callbacks: {e}")
