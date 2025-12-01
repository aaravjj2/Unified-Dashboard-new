#!/usr/bin/env python3
"""
Minimal Dash test
"""
import dash
from dash import html

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Hello World"),
    html.P("If you can see this, Dash is working!")
])

if __name__ == "__main__":
    print("🚀 Starting minimal Dash test...")
    app.run(host="0.0.0.0", port=8053, debug=False)