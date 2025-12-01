"""
Quick Dashboard Test - Minimal version to test chatbot without pandas hanging
"""
import os
import sys

# Setup paths
APP_DIR = os.path.dirname(os.path.abspath(__file__)) + '/financial_dashboard'
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

print("🔧 Starting minimal dashboard...", flush=True)

from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

# Import chatbot without pandas dependency
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from financial_dashboard.components.chatbot_ui import create_chatbot_ui

print("🔧 Creating Dash app...", flush=True)
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

print("🔧 Building layout...", flush=True)
app.layout = html.Div([
    html.H1("Minimal Dashboard - Chatbot Test", style={"textAlign": "center", "marginTop": "20px"}),
    html.Div(id="test-content", children=[
        html.P("Click the floating chat button in the bottom-right corner to test the chatbot."),
        html.P("The button should now be clickable (z-index fix applied)."),
    ], style={"padding": "20px"}),
    create_chatbot_ui()  # This should render the chatbot with the z-index fix
])

print("🔧 Layout created successfully", flush=True)

if __name__ == '__main__':
    print("✅ Starting dashboard on http://localhost:8050", flush=True)
    print("📱 Click the chat button in bottom-right to test", flush=True)
    app.run_server(debug=True, host='0.0.0.0', port=8050)
