"""
Options Lab - Standalone Dash Application
Runs on port 8060 with integrated FastAPI backend for trading operations.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# Load environment variables
env_path = Path(__file__).parent / 'keys.env'
load_dotenv(env_path)
print(f"✓ Loaded environment variables from {env_path}")

# Import the Options Lab layout and callbacks
from tabs.options_lab import create_layout, register_callbacks

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
    title="Options Trading Lab"
)

# Set the layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("💹 Options Trading Lab", className="text-center my-4"),
            html.P(
                "Automated strategy monitoring, manual trading, and P&L analysis.",
                className="text-center text-muted mb-4"
            )
        ])
    ]),
    dbc.Row([
        dbc.Col([
            create_layout()
        ])
    ]),
    # Store for backend API integration
    dcc.Store(id='options-service-config', data={
        'api_url': 'http://localhost:8060',  # Self-referencing for API calls
        'paper_mode': True
    })
], fluid=True, style={'backgroundColor': '#1a1a1a', 'minHeight': '100vh'})

# Register all callbacks
register_callbacks(app)

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 Starting Options Trading Lab (Standalone)")
    print("=" * 70)
    print(f"📡 Server: http://localhost:8060")
    print(f"📊 Mode: PAPER TRADING")
    print(f"🔑 API Keys: Loaded from keys.env")
    print("=" * 70)
    
    # Run the Dash server
    app.run(
        host='0.0.0.0',
        port=8060,
        debug=True
    )
