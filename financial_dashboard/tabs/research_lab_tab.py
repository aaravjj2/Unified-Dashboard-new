"""
Research Lab Tab - Integration Module

Integrates the Research Lab into the main dashboard.
Uses research_lab_pkg (new modular version) by DEFAULT.
Set USE_LEGACY_RESEARCH_LAB=1 to use the old version.
"""

import logging
import os
from dash import html

logger = logging.getLogger(__name__)

# Feature flag: USE_LEGACY_RESEARCH_LAB=1 forces the old module (default is NEW)
USE_LEGACY_RESEARCH_LAB = os.getenv("USE_LEGACY_RESEARCH_LAB", "0") == "1"

def layout():
    """Build the Research Lab tab layout."""
    # NEW research_lab_pkg is now the default
    if not USE_LEGACY_RESEARCH_LAB:
        try:
            from .research_lab_pkg import layout as new_layout
            logger.info("✅ Using NEW Research Lab package (research_lab_pkg)")
            return new_layout()
        except Exception as e:
            logger.error(f"Failed to load NEW Research Lab layout: {e}")
            # Fall through to legacy
    
    # Legacy fallback
    try:
        from .research_lab import layout as create_layout
        logger.info("📦 Using LEGACY Research Lab module")
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
    # NEW research_lab_pkg is now the default
    if not USE_LEGACY_RESEARCH_LAB:
        try:
            from .research_lab_pkg import register_callbacks as new_register
            new_register(app)
            logger.info("✅ Registered NEW Research Lab callbacks (research_lab_pkg)")
            return
        except Exception as e:
            logger.error(f"Failed to register NEW Research Lab callbacks: {e}")
            # Fall through to legacy
    
    # Legacy fallback
    try:
        from .research_lab import register_callbacks
        register_callbacks(app)
        logger.info("📦 Registered LEGACY Research Lab callbacks")
    except Exception as e:
        logger.error(f"Failed to register Research Lab callbacks: {e}")
