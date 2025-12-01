#!/usr/bin/env python3
"""
Launcher for the standalone Portfolio Dashboard
Run: python run_portfolio.py
"""
from pathlib import Path
import os
import sys

# Ensure repo root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Load keys.env into environment if present (so Alpaca keys are available)
keys_file = ROOT / 'keys.env'
if keys_file.exists():
    try:
        for line in keys_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            # Don't overwrite existing env vars
            if k and v and os.environ.get(k) is None:
                os.environ[k] = v
        print(f"Loaded environment variables from {keys_file}")
    except Exception as e:
        print(f"Could not load keys.env: {e}")

# FORCE use of the refactored modular portfolio (tabs/portfolio_tracker.py)
from tabs import portfolio_tracker as portfolio

print("✅ Using refactored portfolio_tracker with modular architecture")
print(f"   - Loaded from: {portfolio.__file__}")

from dash import Dash
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    title="Portfolio Dashboard",
    suppress_callback_exceptions=True,
)

app.layout = portfolio.layout()
portfolio.register_callbacks(app)

server = app.server

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8056))
    print(f"Starting Portfolio Dashboard on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
