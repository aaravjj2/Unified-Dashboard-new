#!/usr/bin/env python3
"""
Standalone Quant Platform Dashboard Server
For testing with Chromium clicker tests
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import sys
import os

# Add paths
sys.path.insert(0, '/home/aarav/Unified-Dashboard')
sys.path.insert(0, '/home/aarav/Unified-Dashboard/services')

# Import dashboard integration
from services.quant_platform.dashboard_integration import (
    create_quant_platform_layout,
    register_quant_callbacks
)

# Create Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True
)

# Set layout directly
app.layout = create_quant_platform_layout()

# Register callbacks
register_quant_callbacks(app)

if __name__ == '__main__':
    print("🚀 Starting Quant Platform Dashboard on port 8053...")
    app.run(debug=False, host='0.0.0.0', port=8053)
