#!/usr/bin/env python3
"""Absolute minimal Dash app to test if ANY callback works"""
from dash import Dash, html, Input, Output
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("Minimal Test"),
    html.Button("Click Me", id="test-btn", n_clicks=0),
    html.Div(id="output", children="Not clicked yet")
])

@app.callback(
    Output("output", "children"),
    Input("test-btn", "n_clicks"),
    prevent_initial_call=True
)
def update_output(n_clicks):
    return f"Clicked {n_clicks} times!"

if __name__ == "__main__":
    app.run_server(debug=True, port=8051)
