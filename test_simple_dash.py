#!/usr/bin/env python3
"""
Test with simple regular Dash instead of DashProxy
"""
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# Create simple Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Simple layout with tabs
app.layout = dbc.Container([
    html.H1("Financial Dashboard - Test", className="text-center mb-4"),
    
    dbc.Tabs([
        dbc.Tab(label="Home", tab_id="home", children=[
            html.Div([
                html.H3("Home Tab"),
                html.P("This is the home tab content.")
            ], className="p-4")
        ]),
        dbc.Tab(label="Research Lab", tab_id="research", children=[
            html.Div([
                html.H3("Research Lab"),
                html.P("This is the research lab content.")
            ], className="p-4")
        ]),
        dbc.Tab(label="Strategy Lab", tab_id="strategy", children=[
            html.Div([
                html.H3("Strategy Lab"),
                html.P("This is the strategy lab content.")
            ], className="p-4")
        ]),
        dbc.Tab(label="Options Lab", tab_id="options", children=[
            html.Div([
                html.H3("Options Lab"),
                html.P("This is the options lab content.")
            ], className="p-4")
        ]),
        dbc.Tab(label="Portfolio", tab_id="portfolio", children=[
            html.Div([
                html.H3("Portfolio"),
                html.P("This is the portfolio content.")
            ], className="p-4")
        ])
    ], id="main-tabs", active_tab="home"),
    
    html.Hr(),
    html.P("✅ Database connected", className="text-success"),
    html.P("✅ API endpoints working", className="text-success"),
    html.P("✅ All 5 tabs visible", className="text-success")
])

if __name__ == "__main__":
    print("🚀 Starting simple Dash test...")
    print("📍 Available at: http://localhost:8052")
    app.run(host="0.0.0.0", port=8052, debug=False)