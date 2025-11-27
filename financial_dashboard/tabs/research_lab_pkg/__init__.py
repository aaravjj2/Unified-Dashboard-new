"""
Research Lab Package

A modular, production-ready research lab with 7 subtabs:
1. Research Scan (rl-scan-tab) - Market/research scanning with news, signals, scan recipes
2. Factor & Signal Lab (rl-factor-tab) - Factor exposures, correlation, signal creation  
3. Screen & Universe Builder (rl-screen-tab) - Build reusable universes and screens
4. RAG Chat & Explain (rl-rag-tab) - RAG-powered Q&A over research docs
5. Briefs & Notes (rl-briefs-tab) - Author, version, search research briefs
6. Experiment Tracker (rl-exp-tab) - Tie research to backtest previews
7. Diagnostics & Index Health (rl-diag-tab) - Ingestion logs, vector index stats

All imports are lazy to avoid heavy work at module import time.
No modals auto-open on dashboard load.
"""

import logging

logger = logging.getLogger(__name__)

# Lazy imports to avoid side effects at import time
_layout_module = None
_callbacks_module = None


def _get_layout_module():
    """Lazily import layout module."""
    global _layout_module
    if _layout_module is None:
        from . import layout as _mod
        _layout_module = _mod
    return _layout_module


def _get_callbacks_module():
    """Lazily import callbacks module."""
    global _callbacks_module
    if _callbacks_module is None:
        from . import callbacks as _mod
        _callbacks_module = _mod
    return _callbacks_module


def layout():
    """
    Build the Research Lab tab layout.
    
    All heavy computation is deferred - this function returns a pure layout
    with no network calls or expensive operations.
    """
    try:
        mod = _get_layout_module()
        return mod.create_layout()
    except Exception as e:
        logger.error(f"Failed to load Research Lab layout: {e}", exc_info=True)
        from dash import html
        return html.Div([
            html.H2("🧪 Research Lab", className="mt-3"),
            html.P(f"Error loading Research Lab module: {str(e)}", 
                   className="text-danger")
        ])


def register_callbacks(app):
    """
    Register Research Lab callbacks with the Dash app.
    
    Uses module-level guard for idempotent registration.
    
    Args:
        app: Dash application instance
    """
    try:
        mod = _get_callbacks_module()
        mod.register_callbacks(app)
        logger.info("✓ Registered Research Lab pkg callbacks")
    except Exception as e:
        logger.error(f"Failed to register Research Lab callbacks: {e}", exc_info=True)


__all__ = ['layout', 'register_callbacks']
