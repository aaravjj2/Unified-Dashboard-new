#!/usr/bin/env python3
"""
Server script for Enhanced Alpaca Options Lab.
Run this to start the enhanced options lab on port 8053.

Phase 1 Update: Hybrid Sentiment Engine
- Added Scanner Workspace with Hype Gauges
- Added News & Sentiment integration
- Added Pattern Detection overlays
"""

import sys
import os
sys.path.insert(0, '/home/aarav/Unified-Dashboard')

# Load all API keys from keys.env FIRST before any imports
from financial_dashboard.utils.load_keys_env import load_keys_env
loaded_keys = load_keys_env()
print(f"🔑 Loaded {len(loaded_keys)} API keys from keys.env")

# Phase 1: Log sentiment engine status
finnhub_configured = bool(os.getenv('FINNHUB_API_KEY'))
newsapi_configured = bool(os.getenv('NEWSAPI_KEY'))
print(f"📡 Sentiment Engine: Finnhub {'✅' if finnhub_configured else '❌ (mock)'} | NewsAPI {'✅' if newsapi_configured else '❌'} | FinViz ✅")

# Use ALPACA2 key for Options Lab (second key in keys.env)
alpaca2_key = os.getenv('ALPACA2_KEY')
alpaca2_secret = os.getenv('ALPACA2_SECRET')
if alpaca2_key and alpaca2_secret:
    os.environ['APCA_API_KEY_ID'] = alpaca2_key
    os.environ['APCA_API_SECRET_KEY'] = alpaca2_secret
    print(f"🔑 Using ALPACA2 key: {alpaca2_key[:8]}...")
else:
    print("⚠️ ALPACA2 key not found, using default APCA key")

from dash import Dash
import dash_bootstrap_components as dbc

# Check if using consolidated 4-tab layout (Phase 15)
USE_CONSOLIDATED_LAYOUT = os.getenv('UX_CONSOLIDATED', 'true').lower() == 'true'

if USE_CONSOLIDATED_LAYOUT:
    from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import create_consolidated_options_layout as create_layout
    print("🎛️ Using Phase 15 Consolidated 4-Tab Layout")
else:
    from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import create_enhanced_options_layout as create_layout
    print("📊 Using Original 12-Tab Layout")

# Create app with LIGHT theme (FLATLY = clean Bootstrap 5 light theme)
app = Dash(
    __name__, 
    external_stylesheets=[dbc.themes.FLATLY], 
    suppress_callback_exceptions=True,
    # Prevent async loading issues
    eager_loading=True,
    # Load assets from financial_dashboard/assets for hotkeys.js
    assets_folder='/home/aarav/Unified-Dashboard/financial_dashboard/assets',
)
app.layout = create_layout("SPY")

# Register base callbacks first (these use @callback decorator)
import financial_dashboard.tabs.options_lab.alpaca_callbacks

# Register enhanced callbacks
from financial_dashboard.tabs.options_lab.alpaca_callbacks_enhanced import register_enhanced_callbacks
register_enhanced_callbacks(app)

# Register system status callbacks (Phase 1 Data Fabric)
from financial_dashboard.tabs.options_lab.system_status_callbacks import register_system_status_callbacks
register_system_status_callbacks(app)

# Register strategy engine callbacks (Phase 3 - Iron Condor, Strategy Picker, Max Pain, Greeks Rollup)
from financial_dashboard.tabs.options_lab.strategy_engine_callbacks import register_strategy_engine_callbacks
register_strategy_engine_callbacks(app)

# Register ML Forecast callbacks (Phase 2 - Price & Volatility Forecast Engine)
from forecast_ui.tabs.forecast_callbacks import register_forecast_callbacks
register_forecast_callbacks(app)

# Register Trade Ops callbacks (Phase 4/5 - Execution Router, Risk Guards, Alert Watchdog)
from tradeops_ui.tabs.trade_ops_callbacks import register_tradeops_callbacks
register_tradeops_callbacks(app)

# Register Research Lab callbacks (Phase 7 - Historical Backtest Engine)
from research_ui.tabs.research import register_research_callbacks
register_research_callbacks(app)

# Register Market Viz UX callbacks (Phase 6 - Agent-Viz)
from financial_dashboard.callbacks.ux import register_ux_callbacks
try:
    register_ux_callbacks(app)
    print("📈 Market Viz: Phase 6 Active")
except Exception as e:
    print(f"⚠️ Market Viz callbacks skipped (components not in current view): {e}")

# Register Command Palette callbacks (Phase 17)
from financial_dashboard.components.command_palette.command_callbacks import register_command_palette_callbacks
try:
    register_command_palette_callbacks(app)
    print("⌘ Command Palette: Phase 17 Active")
except Exception as e:
    print(f"⚠️ Command Palette callbacks skipped: {e}")

# =============================================================================
# PHASE 1: HYBRID SENTIMENT ENGINE - Scanner Workspace
# =============================================================================
try:
    from financial_dashboard.dash.layouts.scanner_workspace import register_scanner_callbacks
    register_scanner_callbacks(app)
    print("📡 Scanner Workspace: Phase 1 Sentiment Engine Active")
except Exception as e:
    print(f"⚠️ Scanner Workspace callbacks skipped: {e}")

# Initialize sentiment engine (preload)
try:
    from financial_dashboard.engines.news import get_news_client
    news_client = get_news_client()
    print(f"📰 News Client initialized: {type(news_client).__name__}")
except Exception as e:
    print(f"⚠️ News Client init skipped: {e}")

if __name__ == '__main__':
    print("🚀 Starting Enhanced Alpaca Options Lab on port 8053...")
    print("📊 Features: Chain, Greeks & IV, Strategy Builder, Strategy Engine, AI, Forecast, Flow, Positions, Status, Trade Ops, Research, Market Viz, Scanner")
    print(f"🔐 Alpaca API: {'✅ Configured' if os.getenv('APCA_API_KEY_ID') else '❌ Not configured'}")
    print(f"📈 Data Sources: Alpaca → yfinance → mock")
    print("🔮 ML Forecast Engine: Phase 2 Active")
    print("⚙️ Trade Ops Engine: Phase 4/5 Active")
    print("📊 Research Lab: Phase 7 Active")
    print("📈 Market Viz: Phase 6 Active (GEX, Vol Surface, Flow Tape, Hotkeys)")
    print("⌘ Command Palette: Phase 17 Active (Ctrl+K)")
    print("📡 Scanner Workspace: Phase 1 Sentiment Engine (Hype Gauges, News Feed, Pattern Detection)")
    app.run(debug=False, port=8053, host='0.0.0.0')
