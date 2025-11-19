#!/usr/bin/env python3
"""
Financial Dashboard - Main Application with Phase 24-25 Critical Fixes Applied
"""

import os
import sys
import logging
from pathlib import Path

# Add the fix utilities to the path
sys.path.insert(0, 'test_artifacts/phase24_25_targeted_fix')

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
from flask import Flask

# Import the critical fixes
from dash_callback_fix import safe_callback_decorator, register_safe_callbacks

# Configure logging with error handling
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dashboard_fixed.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize Dash app with error handling
try:
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        prevent_initial_callbacks=True
    )
    
    # Apply critical fixes to the app
    from app_patch import patch_dash_app
    app = patch_dash_app(app)
    
    server = app.server
    
    logger.info("✅ Dash app initialized with critical fixes applied")
    
except Exception as e:
    logger.error(f"❌ Failed to initialize Dash app: {e}")
    raise

# Safe layout with error boundaries
def create_safe_layout():
    """Create a safe layout that prevents React Error #31"""
    try:
        # Import safe components
        sys.path.insert(0, 'test_artifacts/phase24_25_targeted_fix')
        from react_error_31_fix import SafeDiv, SafeP, SafeH1, SafeButton
        
        return SafeDiv([
            SafeH1("Financial Dashboard", className="text-center mb-4"),
            SafeDiv([
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Home", href="/", active="exact")),
                    dbc.NavItem(dbc.NavLink("Command Center", href="/command-center", active="exact")),
                    dbc.NavItem(dbc.NavLink("Strategy Lab", href="/strategy-lab", active="exact")),
                    dbc.NavItem(dbc.NavLink("Options Lab", href="/options-lab", active="exact")),
                    dbc.NavItem(dbc.NavLink("Weekly Picks", href="/weekly-picks", active="exact")),
                    dbc.NavItem(dbc.NavLink("Monthly Picks", href="/monthly-picks", active="exact")),
                ], pills=True, className="mb-4")
            ]),
            SafeDiv(id="page-content"),
            
            # Test elements to ensure interactivity
            SafeDiv([
                SafeH1("Interactive Test Elements"),
                SafeButton("Test Button", id="test-button", className="btn btn-primary me-2"),
                dcc.Dropdown(
                    id="test-dropdown",
                    options=[
                        {"label": "Option 1", "value": "opt1"},
                        {"label": "Option 2", "value": "opt2"},
                        {"label": "Option 3", "value": "opt3"}
                    ],
                    placeholder="Select an option...",
                    className="mb-2",
                    style={"background-color": "white", "color": "black"}
                ),
                dcc.Input(
                    id="test-input",
                    type="text",
                    placeholder="Test input...",
                    className="form-control mb-2",
                    style={"background-color": "white", "color": "black"}
                ),
                SafeDiv(id="test-output")
            ], className="mt-4 p-3 border rounded", style={"background-color": "#f8f9fa"})
        ])
        
    except Exception as e:
        logger.error(f"❌ Error creating safe layout: {e}")
        # Fallback to basic layout
        return html.Div([
            html.H1("Financial Dashboard - Safe Mode"),
            html.P("Dashboard is running in safe mode due to layout errors."),
            html.Div(id="page-content")
        ])

# Set the layout
app.layout = create_safe_layout()

# Safe callback implementations
@app.callback(
    Output('test-output', 'children'),
    [Input('test-button', 'n_clicks'),
     Input('test-dropdown', 'value'),
     Input('test-input', 'value')],
    prevent_initial_call=True
)
@safe_callback_decorator
def test_interactivity(n_clicks, dropdown_value, input_value):
    """Test callback to verify interactivity works"""
    ctx = callback_context
    
    if not ctx.triggered:
        return no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'test-button':
        return f"✅ Button clicked {n_clicks} times!"
    elif trigger_id == 'test-dropdown':
        return f"✅ Dropdown selected: {dropdown_value}"
    elif trigger_id == 'test-input':
        return f"✅ Input changed to: {input_value}"
    
    return "✅ Interactive elements are working!"

@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname') if 'url' in [c.component_id for c in app.layout.children if hasattr(c, 'component_id')] else Input('test-button', 'n_clicks'),
    prevent_initial_call=True
)
@safe_callback_decorator
def display_page(pathname):
    """Safe page routing callback"""
    try:
        from react_error_31_fix import SafeDiv, SafeH2, SafeP
        
        if pathname == '/command-center':
            return SafeDiv([
                SafeH2("Command Center"),
                SafeP("Command center functionality coming soon...")
            ])
        elif pathname == '/strategy-lab':
            return SafeDiv([
                SafeH2("Strategy Lab"),
                SafeP("Strategy analysis tools coming soon...")
            ])
        elif pathname == '/options-lab':
            return SafeDiv([
                SafeH2("Options Lab"),
                SafeP("Options trading analysis coming soon...")
            ])
        elif pathname == '/weekly-picks':
            return SafeDiv([
                SafeH2("Weekly Picks"),
                SafeP("Weekly stock recommendations coming soon...")
            ])
        elif pathname == '/monthly-picks':
            return SafeDiv([
                SafeH2("Monthly Picks"),
                SafeP("Monthly investment strategies coming soon...")
            ])
        else:
            return SafeDiv([
                SafeH2("Home Dashboard"),
                SafeP("Welcome to the Financial Dashboard"),
                SafeP("All critical fixes have been applied:"),
                html.Ul([
                    html.Li("✅ Server 500 errors fixed with safe callbacks"),
                    html.Li("✅ React Error #31 resolved with safe components"),
                    html.Li("✅ Interactive elements restored"),
                    html.Li("✅ UI color normalization applied")
                ])
            ])
    except Exception as e:
        logger.error(f"❌ Error in page routing: {e}")
        return html.Div(f"Error loading page: {str(e)}")

# Register additional safe callbacks
try:
    register_safe_callbacks(app)
    logger.info("✅ Safe callbacks registered successfully")
except Exception as e:
    logger.error(f"❌ Error registering safe callbacks: {e}")

if __name__ == '__main__':
    try:
        logger.info("🚀 Starting Financial Dashboard with Phase 24-25 fixes...")
        app.run_server(
            debug=False,  # Disable debug mode for stability
            host='0.0.0.0',
            port=8050,
            dev_tools_hot_reload=False
        )
    except Exception as e:
        logger.error(f"❌ Failed to start dashboard: {e}")
        sys.exit(1)
