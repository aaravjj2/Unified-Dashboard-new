#!/usr/bin/env python3
"""
Portfolio Dashboard - Standalone Service

Standalone Dash app for portfolio management, positions tracking,
and P/L analysis. Designed to be embedded in the unified dashboard.

Port: 8056
Access: http://localhost:8056
"""

import os
import sys
import logging
from dash import Dash
import dash_bootstrap_components as dbc

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the portfolio tracker module with Analytics, Optimization, Factor Exposure tabs
from tabs import portfolio_tracker

# Create Dash app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    title="Portfolio Dashboard",
    suppress_callback_exceptions=True
)

# Enhanced CSS for visibility
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #222629 !important;
                color: #ffffff !important;
                min-height: 100vh;
            }
            .container-fluid, .container {
                min-height: 100vh;
                padding: 20px;
            }
            .card {
                background-color: #2b3035 !important;
                border: 1px solid #3a3f44 !important;
            }
            /* Scope tab content and subtab styles to portfolio pane to avoid global leakage */
            #tab-pane-portfolio .tab-content {
                min-height: 600px;
                display: block !important;
                visibility: visible !important;
            }
            #tab-pane-portfolio .nav-tabs {
                border-bottom: 1px solid #3a3f44 !important;
            }
            #tab-pane-portfolio .nav-tabs .nav-link {
                color: #ffffff !important;
                background-color: transparent !important;
                border: 1px solid transparent !important;
                padding: 10px 20px !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                display: inline-block !important;
                visibility: visible !important;
            }
            #tab-pane-portfolio .nav-tabs .nav-link:hover {
                color: #00bc8c !important;
                border-color: #3a3f44 !important;
            }
            #tab-pane-portfolio .nav-tabs .nav-link.active {
                color: #00bc8c !important;
                background-color: #2b3035 !important;
                border-color: #3a3f44 #3a3f44 #2b3035 !important;
                font-weight: 600 !important;
            }
            #tab-pane-portfolio .nav-item {
                display: inline-block !important;
                visibility: visible !important;
            }
            h1, h2, h3, h4, h5, h6, p, div, span, td, th {
                color: #ffffff !important;
            }
            .text-muted {
                color: #adb5bd !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Set layout from portfolio tracker (includes Analytics, Optimization, Factor Exposure tabs)
app.layout = portfolio_tracker.layout()

# Register callbacks from portfolio tracker
portfolio_tracker.register_callbacks(app)

# Server for deployment
server = app.server

if __name__ == '__main__':
    print("=" * 60)
    print("💼 Portfolio Dashboard - Standalone Service")
    print("=" * 60)
    print("Starting on http://0.0.0.0:8056")
    print()
    print("Features:")
    print("  • Position tracking and P/L analysis")
    print("  • Transaction upload and reconciliation")
    print("  • Performance attribution and charts")
    print("  • Portfolio alerts and risk metrics")
    print()
    print("This service is designed to be embedded in the unified dashboard")
    print("Access directly: http://localhost:8056")
    print("Or via unified dashboard: http://localhost:8055")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=8056, debug=False)
