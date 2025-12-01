#!/usr/bin/env python3
"""
Research Lab Dashboard - Standalone Service

Standalone Dash app for research experiments, feature testing, and model comparison.
Designed to be embedded in the unified dashboard.

Port: 8058
Access: http://localhost:8058
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

# Import the research_lab module
from modules import research_lab

# Create Dash app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    title="Research Lab",
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
            /* Scope subtab styling to the Research Lab pane to avoid global nav leakage */
            #tab-pane-research_lab .nav-tabs .nav-link {
                color: #adb5bd !important;
                background-color: transparent !important;
            }
            #tab-pane-research_lab .nav-tabs .nav-link.active {
                color: #00bc8c !important;
                background-color: #2b3035 !important;
                border-color: #3a3f44 #3a3f44 #2b3035 !important;
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

# Set layout
app.layout = research_lab.layout()

# Register callbacks
research_lab.register_callbacks(app)

# Optional: serve Scenario Lab directly at /scenario for test automation
@app.server.route('/scenario')
def serve_scenario():
        # Render minimal page that only contains the scenario tab layout for faster tests
        from flask import Response
        html = """
        <!doctype html>
        <html>
            <head><meta charset='utf-8'><title>Scenario Lab</title></head>
            <body>
                <div id='scenario-root'></div>
                <script>
                    // Client will fetch the full app and inject scenario content via fetch to the main Dash layout
                    window.location.href = '/';
                </script>
            </body>
        </html>
        """
        return Response(html, mimetype='text/html')

# Server for deployment
server = app.server

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Research Lab - Standalone Service")
    print("=" * 60)
    print("Starting on http://0.0.0.0:8058")
    print()
    print("Features:")
    print("  • Experiment sandbox for new features")
    print("  • Model comparison and ablation testing")
    print("  • Reproducible artifact tracking")
    print("  • Promotion to production pipeline")
    print()
    print("This service is designed to be embedded in the unified dashboard")
    print("Access directly: http://localhost:8058")
    print("Or via unified dashboard: http://localhost:8055")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=8058, debug=False)
