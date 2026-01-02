#!/usr/bin/env python3
"""
Alpaca Options Lab - Standalone Entry Point
============================================

A production-ready options trading dashboard with:
- Real-time options chain viewer
- Greeks & IV analysis  
- Strategy builder (Iron Condors, Spreads, etc.)
- AI-powered recommendations
- ML price/volatility forecasting
- Risk management & trade execution
- Sentiment analysis & news feeds

Usage:
    python run.py
    
Then open: http://localhost:8053

Author: Alpaca Options Lab Team
License: MIT
"""

import sys
import os

# Set up path for standalone operation
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_ROOT)
sys.path.insert(0, os.path.join(APP_ROOT, 'src'))

# Also add parent path for backward compatibility during transition
PARENT_ROOT = os.path.dirname(APP_ROOT)
sys.path.insert(0, PARENT_ROOT)

# Load environment variables
def load_env():
    """Load API keys from .env or keys.env file."""
    env_files = [
        os.path.join(APP_ROOT, '.env'),
        os.path.join(APP_ROOT, 'keys.env'),
        os.path.join(PARENT_ROOT, '.env'),
        os.path.join(PARENT_ROOT, 'keys.env'),
    ]
    
    loaded = {}
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"📁 Loading environment from: {env_file}")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
                            loaded[key] = value[:8] + '...' if len(value) > 8 else value
            break
    
    return loaded

# Load environment first
loaded_keys = load_env()
print(f"🔑 Loaded {len(loaded_keys)} environment variables")

# Configure Alpaca API (prefer ALPACA2 for options lab)
alpaca2_key = os.getenv('ALPACA2_KEY')
alpaca2_secret = os.getenv('ALPACA2_SECRET')
if alpaca2_key and alpaca2_secret:
    os.environ['APCA_API_KEY_ID'] = alpaca2_key
    os.environ['APCA_API_SECRET_KEY'] = alpaca2_secret
    print(f"🔑 Using ALPACA2 key: {alpaca2_key[:8]}...")
else:
    alpaca_key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
    if alpaca_key:
        print(f"🔑 Using ALPACA key: {alpaca_key[:8]}...")
    else:
        print("⚠️ No Alpaca API key configured - using mock data")

# Check data sources
finnhub_configured = bool(os.getenv('FINNHUB_API_KEY'))
newsapi_configured = bool(os.getenv('NEWSAPI_KEY'))
print(f"📡 Data Sources: Finnhub {'✅' if finnhub_configured else '❌'} | NewsAPI {'✅' if newsapi_configured else '❌'} | FinViz ✅")

# Import Dash
from dash import Dash
import dash_bootstrap_components as dbc

# Import layout (using backward compatible imports during transition)
try:
    from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import create_consolidated_options_layout as create_layout
    print("🎛️ Using Consolidated 4-Tab Layout")
except ImportError:
    from src.ui.callbacks.options_lab.alpaca_ui_enhanced import create_consolidated_options_layout as create_layout
    print("🎛️ Using Local Consolidated Layout")

# Create Dash app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
    eager_loading=True,
    assets_folder=os.path.join(APP_ROOT, 'assets'),
)
app.title = "Alpaca Options Lab"
app.layout = create_layout("SPY")

# Register callbacks (using backward compatible imports)
def register_all_callbacks(app):
    """Register all dashboard callbacks."""
    
    # Base callbacks
    try:
        import financial_dashboard.tabs.options_lab.alpaca_callbacks
        print("  ✅ Base callbacks registered")
    except Exception as e:
        print(f"  ⚠️ Base callbacks: {e}")
    
    # Enhanced callbacks
    try:
        from financial_dashboard.tabs.options_lab.alpaca_callbacks_enhanced import register_enhanced_callbacks
        register_enhanced_callbacks(app)
        print("  ✅ Enhanced callbacks registered")
    except Exception as e:
        print(f"  ⚠️ Enhanced callbacks: {e}")
    
    # System status callbacks
    try:
        from financial_dashboard.tabs.options_lab.system_status_callbacks import register_system_status_callbacks
        register_system_status_callbacks(app)
        print("  ✅ System status callbacks registered")
    except Exception as e:
        print(f"  ⚠️ System status: {e}")
    
    # Strategy engine callbacks
    try:
        from financial_dashboard.tabs.options_lab.strategy_engine_callbacks import register_strategy_engine_callbacks
        register_strategy_engine_callbacks(app)
        print("  ✅ Strategy engine callbacks registered")
    except Exception as e:
        print(f"  ⚠️ Strategy engine: {e}")
    
    # ML Forecast callbacks
    try:
        from forecast_ui.tabs.forecast_callbacks import register_forecast_callbacks
        register_forecast_callbacks(app)
        print("  ✅ ML Forecast callbacks registered")
    except Exception as e:
        print(f"  ⚠️ ML Forecast: {e}")
    
    # Trade Ops callbacks
    try:
        from tradeops_ui.tabs.trade_ops_callbacks import register_tradeops_callbacks
        register_tradeops_callbacks(app)
        print("  ✅ Trade Ops callbacks registered")
    except Exception as e:
        print(f"  ⚠️ Trade Ops: {e}")
    
    # Research Lab callbacks
    try:
        from research_ui.tabs.research import register_research_callbacks
        register_research_callbacks(app)
        print("  ✅ Research Lab callbacks registered")
    except Exception as e:
        print(f"  ⚠️ Research Lab: {e}")
    
    # UX callbacks
    try:
        from financial_dashboard.callbacks.ux import register_ux_callbacks
        register_ux_callbacks(app)
        print("  ✅ UX callbacks registered")
    except Exception as e:
        print(f"  ⚠️ UX callbacks: {e}")
    
    # Command Palette callbacks
    try:
        from financial_dashboard.components.command_palette.command_callbacks import register_command_palette_callbacks
        register_command_palette_callbacks(app)
        print("  ✅ Command Palette callbacks registered")
    except Exception as e:
        print(f"  ⚠️ Command Palette: {e}")
    
    # Scanner Workspace callbacks
    try:
        from financial_dashboard.dash.layouts.scanner_workspace import register_scanner_callbacks
        register_scanner_callbacks(app)
        print("  ✅ Scanner Workspace callbacks registered")
    except Exception as e:
        print(f"  ⚠️ Scanner Workspace: {e}")

print("\n📋 Registering Callbacks...")
register_all_callbacks(app)

# Initialize sentiment engine
try:
    from financial_dashboard.engines.news import get_news_client
    news_client = get_news_client()
    print(f"\n📰 News Client: {type(news_client).__name__}")
except Exception as e:
    print(f"\n⚠️ News Client: {e}")

# Run golden vector tests (math integrity check)
try:
    from financial_dashboard.tests.quality.golden_vectors import run_startup_checks
    print("\n🔬 Running Golden Vector Tests...")
    run_startup_checks(block_on_fail=False)  # Don't block, just warn
except Exception as e:
    print(f"⚠️ Golden Vector Tests skipped: {e}")

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8053))
    HOST = os.getenv('HOST', '0.0.0.0')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║            🦙 ALPACA OPTIONS LAB - STARTING UP 🦙              ║
╠══════════════════════════════════════════════════════════════╣
║  URL:     http://localhost:{PORT}                              ║
║  Host:    {HOST}                                            ║
║  Debug:   {DEBUG}                                            ║
╠══════════════════════════════════════════════════════════════╣
║  WORKSPACES:                                                 ║
║    📡 Scanner  - Sentiment & News Feeds                      ║
║    📊 Strategy - Options Chain & Greeks                      ║
║    ⚙️  Command  - Positions & Risk                           ║
║    🔧 Admin    - System Health & Logs                        ║
╠══════════════════════════════════════════════════════════════╣
║  FEATURES:                                                   ║
║    • Real-time Options Chain Viewer                          ║
║    • Greeks Calculator & IV Surface                          ║
║    • Strategy Builder (Iron Condor, Spreads)                 ║
║    • AI-Powered Recommendations                              ║
║    • ML Price & Volatility Forecasting                       ║
║    • Risk Management & Position Tracking                     ║
║    • Self-Healing Data Layer (Circuit Breakers)              ║
╠══════════════════════════════════════════════════════════════╣
║  KEYBOARD SHORTCUTS:                                         ║
║    Ctrl+K     - Command Palette                              ║
║    Ctrl+1-4   - Switch Workspaces                            ║
║    Ctrl+R     - Refresh Data                                 ║
║    ?          - Show Help                                    ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    app.run(debug=DEBUG, port=PORT, host=HOST)

