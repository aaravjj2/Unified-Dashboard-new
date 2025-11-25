#!/usr/bin/env python3
"""
Clean Financial Dashboard - React Error Free
Minimal implementation to avoid React errors for LambdaTest validation
"""

import dash
from dash import dcc, html, Input, Output, callback_context
import dash_bootstrap_components as dbc
from flask import Flask
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    prevent_initial_callbacks=True
)

server = app.server

# Clean layout without React error triggers
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Financial Dashboard", 
               style={"color": "#000000", "textAlign": "center", "marginBottom": "20px"}),
        html.P("Phase 24-25 Clean Implementation", 
              style={"color": "#666666", "textAlign": "center"})
    ], style={"backgroundColor": "#ffffff", "padding": "20px"}),
    
    # Navigation
    html.Div([
        html.A("Home", href="/", className="btn btn-outline-primary me-2", id="nav-home"),
        html.A("Command Center", href="/command-center", className="btn btn-outline-primary me-2", id="nav-command"),
        html.A("Strategy Lab", href="/strategy-lab", className="btn btn-outline-primary me-2", id="nav-strategy"),
        html.A("Options Lab", href="/options-lab", className="btn btn-outline-primary me-2", id="nav-options"),
        html.A("Weekly Picks", href="/weekly-picks", className="btn btn-outline-primary me-2", id="nav-weekly"),
        html.A("Monthly Picks", href="/monthly-picks", className="btn btn-outline-primary", id="nav-monthly"),
    ], style={"textAlign": "center", "padding": "20px", "backgroundColor": "#ffffff"}),
    
    # Main content
    html.Div([
        html.H2("Dashboard Content", style={"color": "#000000"}),
        html.P("This is a clean dashboard implementation for LambdaTest validation.", 
               style={"color": "#000000"}),
        
        # Test elements
        html.Div([
            html.H3("Test Elements", style={"color": "#000000"}),
            html.Button("Test Button 1", id="test-btn-1", className="btn btn-primary me-2"),
            html.Button("Test Button 2", id="test-btn-2", className="btn btn-success me-2"),
            html.Button("Test Button 3", id="test-btn-3", className="btn btn-warning"),
        ], style={"marginTop": "20px"}),
        
        html.Div([
            dcc.Dropdown(
                id="test-dropdown",
                options=[
                    {"label": "Option 1", "value": "opt1"},
                    {"label": "Option 2", "value": "opt2"},
                    {"label": "Option 3", "value": "opt3"}
                ],
                placeholder="Select an option...",
                style={"marginTop": "20px", "backgroundColor": "#ffffff", "color": "#000000"}
            )
        ]),
        
        html.Div([
            dcc.Input(
                id="test-input",
                type="text",
                placeholder="Type here...",
                className="form-control",
                style={"marginTop": "20px", "backgroundColor": "#ffffff", "color": "#000000"}
            )
        ]),
        
        html.Div(id="output-area", style={
            "marginTop": "20px", 
            "padding": "15px", 
            "backgroundColor": "#f8f9fa",
            "color": "#000000",
            "borderRadius": "5px"
        })
        
    ], id="page-content", style={
        "padding": "20px", 
        "backgroundColor": "#ffffff",
        "minHeight": "500px",
        "color": "#000000"
    })
    
], style={"backgroundColor": "#ffffff", "fontFamily": "Arial, sans-serif"})

# Simple callback
@app.callback(
    Output('output-area', 'children'),
    [Input('test-btn-1', 'n_clicks'),
     Input('test-btn-2', 'n_clicks'),
     Input('test-btn-3', 'n_clicks'),
     Input('test-dropdown', 'value'),
     Input('test-input', 'value')],
    prevent_initial_call=True
)
def update_output(btn1, btn2, btn3, dropdown, input_val):
    """Simple callback to test interactivity"""
    try:
        ctx = callback_context
        if not ctx.triggered:
            return "No interactions yet..."
        
        trigger = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger == 'test-btn-1':
            return f"Button 1 clicked {btn1} times"
        elif trigger == 'test-btn-2':
            return f"Button 2 clicked {btn2} times"
        elif trigger == 'test-btn-3':
            return f"Button 3 clicked {btn3} times"
        elif trigger == 'test-dropdown':
            return f"Dropdown selected: {dropdown}"
        elif trigger == 'test-input':
            return f"Input value: {input_val}"
        
        return "Interactive elements working!"
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return f"Error: {str(e)}"

if __name__ == '__main__':
    logger.info("🚀 Starting Clean Financial Dashboard...")
    logger.info("📍 Dashboard available at: http://0.0.0.0:8050")
    
    app.run(
        debug=False,
        host='0.0.0.0',
        port=8050,
        dev_tools_hot_reload=False
    )