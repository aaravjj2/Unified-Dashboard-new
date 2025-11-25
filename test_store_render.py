#!/usr/bin/env python
"""Minimal test: Do stores render in a simple Dash app?"""
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("Store Test"),
    html.Div([
        dcc.Store(id='test-store-1'),
        dcc.Store(id='test-store-2'),
        html.P("Stores should exist above this (hidden)"),
    ], id='container', style={'border': '1px solid red'}),
    html.Div(id='output')
])

if __name__ == '__main__':
    app.run(debug=True, port=8051)
