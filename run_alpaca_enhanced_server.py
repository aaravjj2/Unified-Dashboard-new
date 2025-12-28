#!/usr/bin/env python3
"""
Server script for Enhanced Alpaca Options Lab.
Run this to start the enhanced options lab on port 8053.
"""

import sys
import os
sys.path.insert(0, '/home/aarav/Unified-Dashboard')

# Load all API keys from keys.env FIRST before any imports
from financial_dashboard.utils.load_keys_env import load_keys_env
loaded_keys = load_keys_env()
print(f"🔑 Loaded {len(loaded_keys)} API keys from keys.env")

from dash import Dash
import dash_bootstrap_components as dbc

# Import the enhanced layout
from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import create_enhanced_options_layout

# Create app
app = Dash(
    __name__, 
    external_stylesheets=[dbc.themes.DARKLY], 
    suppress_callback_exceptions=True,
    # Prevent async loading issues
    eager_loading=True
)
app.layout = create_enhanced_options_layout("SPY")

# Register base callbacks first (these use @callback decorator)
import financial_dashboard.tabs.options_lab.alpaca_callbacks

# Register enhanced callbacks
from financial_dashboard.tabs.options_lab.alpaca_callbacks_enhanced import register_enhanced_callbacks
register_enhanced_callbacks(app)

if __name__ == '__main__':
    print("🚀 Starting Enhanced Alpaca Options Lab on port 8053...")
    print("📊 Features: Chain, Greeks & IV, Strategy Builder, AI, Flow, Positions")
    print(f"🔐 Alpaca API: {'✅ Configured' if os.getenv('APCA_API_KEY_ID') else '❌ Not configured'}")
    print(f"📈 Data Sources: Alpaca → yfinance → mock")
    app.run(debug=False, port=8053, host='0.0.0.0')
