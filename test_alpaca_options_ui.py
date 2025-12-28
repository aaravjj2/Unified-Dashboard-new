"""
Test Alpaca-Style Options Lab UI

Standalone test to verify the new Alpaca-style interface works correctly.
"""

import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(__file__)
sys.path.insert(0, PROJECT_ROOT)

# Load environment variables from keys.env FIRST
from dotenv import load_dotenv
keys_env_path = os.path.join(PROJECT_ROOT, 'keys.env')
if os.path.exists(keys_env_path):
    load_dotenv(keys_env_path)
    print(f"✅ Loaded environment from {keys_env_path}")
else:
    print(f"⚠️ keys.env not found at {keys_env_path}")

# Also try financial_dashboard/utils/load_keys_env.py
try:
    from financial_dashboard.utils.load_keys_env import load_keys_env
    load_keys_env()
    print("✅ Loaded keys via load_keys_env()")
except Exception as e:
    print(f"⚠️ Could not load via load_keys_env: {e}")

# Verify Alpaca keys are loaded
apca_key = os.environ.get('APCA_API_KEY_ID', '')
apca_secret = os.environ.get('APCA_API_SECRET_KEY', '')
print(f"📊 APCA_API_KEY_ID: {'Set (' + apca_key[:8] + '...)' if apca_key else 'NOT SET'}")
print(f"📊 APCA_API_SECRET_KEY: {'Set (' + apca_secret[:8] + '...)' if apca_secret else 'NOT SET'}")

import dash
from dash import html
import dash_bootstrap_components as dbc
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import Alpaca components
from financial_dashboard.tabs.options_lab.alpaca_ui import create_alpaca_layout
import financial_dashboard.tabs.options_lab.alpaca_callbacks  # Register callbacks

# Create Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True
)

# Set layout
app.layout = html.Div([
    html.H1("Alpaca-Style Options Lab Test", style={
        'textAlign': 'center',
        'padding': '20px',
        'color': '#ffffff',
        'backgroundColor': '#1e2130'
    }),
    create_alpaca_layout("SPY")
])

if __name__ == '__main__':
    import sys
    port = 8053  # Use different port to avoid conflicts
    logger.info(f"🚀 Starting Alpaca Options Lab test on http://localhost:{port}")
    logger.info("📝 Make sure APCA_API_KEY_ID and APCA_API_SECRET_KEY are set in environment")
    
    try:
        app.run(
            debug=False,  # Disable debug to prevent reloader
            host='0.0.0.0',
            port=port
        )
    except KeyboardInterrupt:
        logger.info("👋 Server stopped")
        sys.exit(0)
