#!/usr/bin/env python3
"""
Application patch to fix 500 errors
Apply this patch to your main Dash application
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from dash_callback_fix import register_safe_callbacks, safe_callback_decorator
import dash
from dash import dcc, html

def patch_dash_app(app):
    """Patch existing Dash app with safe callbacks"""
    
    # Apply error handling to existing callbacks
    original_callback = app.callback
    
    def safe_callback(*args, **kwargs):
        def decorator(func):
            safe_func = safe_callback_decorator(func)
            return original_callback(*args, **kwargs)(safe_func)
        return decorator
    
    # Replace the callback decorator
    app.callback = safe_callback
    
    # Register additional safe callbacks
    register_safe_callbacks(app)
    
    print("✅ Dash app patched with safe callbacks")
    return app

# Example usage:
# from app_patch import patch_dash_app
# app = dash.Dash(__name__)
# app = patch_dash_app(app)
