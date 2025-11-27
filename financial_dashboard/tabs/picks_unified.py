"""
Unified Picks Tab - Single tab with 3 subtabs:
1. Weekly Picks - Short-term stock picks (7-day holding)
2. Monthly Picks - Long-term stock picks (30-day holding)
3. Auto-Trading Portfolio - Live paper trading portfolio

This combines weekly_picks.py and monthly_picks.py into a unified interface
with automated portfolio management capabilities.
"""

import os
import logging
import pandas as pd
from datetime import datetime, date
from dash import dcc, html, Input, Output, State, dash_table, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

# Import existing picks logic
from . import weekly_picks
from . import monthly_picks


def layout():
    """Create unified picks tab with 3 subtabs."""
    return dbc.Container([
        # Header
        html.Div([
            html.H2([
                html.I(className="bi bi-stars me-2"),
                "Stock Picks - AI-Powered Selection"
            ], className="text-primary mb-2"),
            html.P("ML-driven stock recommendations with automated portfolio management", 
                   className="text-muted mb-4")
        ]),
        
        # Main tabs
        dbc.Tabs([
            # Tab 1: Weekly Picks
            dbc.Tab(
                weekly_picks.layout(),
                label="📅 Weekly Picks",
                tab_id="tab-weekly-picks",
                className="pt-4"
            ),
            
            # Tab 2: Monthly Picks
            dbc.Tab(
                monthly_picks.layout(),
                label="📆 Monthly Picks",
                tab_id="tab-monthly-picks",
                className="pt-4"
            ),
            
            # Tab 3: Auto-Trading Portfolio (NEW)
            dbc.Tab(
                create_portfolio_tab_layout(),
                label="💼 Auto-Trading Portfolio",
                tab_id="tab-portfolio",
                className="pt-4"
            ),
        ], id="picks-tabs", active_tab="tab-weekly-picks"),
        
    ], fluid=True, className="p-4")


def create_portfolio_tab_layout():
    """Create the auto-trading portfolio tab layout."""
    return html.Div([
        # Portfolio Summary Bar
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div("Total Value", className="small text-muted mb-1"),
                        html.H4("$10,000.00", id="portfolio-total-value", className="text-white mb-0")
                    ], width=3),
                    dbc.Col([
                        html.Div("Total P/L", className="small text-muted mb-1"),
                        html.H4("$0.00 (0.00%)", id="portfolio-total-pnl", className="text-muted mb-0")
                    ], width=3),
                    dbc.Col([
                        html.Div("Cash Available", className="small text-muted mb-1"),
                        html.H4("$10,000.00", id="portfolio-cash", className="text-white mb-0")
                    ], width=2),
                    dbc.Col([
                        html.Div("Active Positions", className="small text-muted mb-1"),
                        html.H4("0/20", id="portfolio-positions-count", className="text-white mb-0")
                    ], width=2),
                    dbc.Col([
                        html.Div("Win Rate", className="small text-muted mb-1"),
                        html.H4("--", id="portfolio-win-rate", className="text-muted mb-0")
                    ], width=2),
                ], align="center")
            ], className="py-3")
        ], className="mb-4 shadow border-primary", style={'borderWidth': '2px'}),
        
        # Active Positions Section
        html.Div([
            html.H5([
                html.I(className="bi bi-briefcase me-2"),
                "Active Positions"
            ], className="text-white mb-3"),
            
            # Positions table will go here
            html.Div(id="portfolio-positions-container", children=[
                dbc.Alert([
                    html.I(className="bi bi-info-circle me-2"),
                    "No active positions. Deploy picks from Weekly or Monthly tabs to start trading."
                ], color="info", className="text-center")
            ])
        ], className="mb-4"),
        
        # Recent Orders Section
        html.Div([
            html.H5([
                html.I(className="bi bi-clock-history me-2"),
                "Recent Orders"
            ], className="text-white mb-3"),
            
            html.Div(id="portfolio-orders-container", children=[
                dbc.Alert("No orders yet", color="dark", className="text-center text-muted")
            ])
        ], className="mb-4"),
        
        # Settings Section
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("⚙️ Portfolio Settings"),
                    dbc.CardBody([
                        # Position sizing
                        dbc.Row([
                            dbc.Col(html.Label("Position Size (% of capital)", className="small"), width=6),
                            dbc.Col(
                                dbc.Input(
                                    id="portfolio-position-size",
                                    type="number",
                                    value=5,
                                    min=1,
                                    max=20,
                                    step=1,
                                    style={'width': '80px'}
                                ),
                                width=6
                            )
                        ], className="mb-3 align-items-center"),
                        
                        # Stop loss
                        dbc.Row([
                            dbc.Col(html.Label("Stop Loss (%)", className="small"), width=6),
                            dbc.Col(
                                dbc.Input(
                                    id="portfolio-stop-loss",
                                    type="number",
                                    value=-10,
                                    min=-50,
                                    max=0,
                                    step=1,
                                    style={'width': '80px'}
                                ),
                                width=6
                            )
                        ], className="mb-3 align-items-center"),
                        
                        # Take profit
                        dbc.Row([
                            dbc.Col(html.Label("Take Profit (%)", className="small"), width=6),
                            dbc.Col(
                                dbc.Input(
                                    id="portfolio-take-profit",
                                    type="number",
                                    value=20,
                                    min=0,
                                    max=100,
                                    step=5,
                                    style={'width': '80px'}
                                ),
                                width=6
                            )
                        ], className="align-items-center"),
                    ])
                ], className="shadow")
            ], width=6),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🚨 Emergency Controls"),
                    dbc.CardBody([
                        dbc.Button(
                            "Close All Positions",
                            id="portfolio-close-all-btn",
                            color="danger",
                            className="w-100 mb-2",
                            n_clicks=0
                        ),
                        html.Small("⚠️ This will immediately close all open positions at market price", 
                                 className="text-muted d-block text-center")
                    ])
                ], className="shadow")
            ], width=6)
        ]),
        
        # Status message area
        html.Div(id="portfolio-status-message", className="mt-4"),
        
        # Auto-refresh interval
        dcc.Interval(id='portfolio-refresh-interval', interval=5000, n_intervals=0),
        
    ])


def register_callbacks(app):
    """Register all callbacks for unified picks tab."""
    
    # Register weekly picks callbacks
    weekly_picks.register_callbacks(app)
    
    # Register monthly picks callbacks
    monthly_picks.register_callbacks(app)
    
    # Portfolio-specific callbacks will be added here
    register_portfolio_callbacks(app)


def register_portfolio_callbacks(app):
    """Register callbacks for auto-trading portfolio tab."""
    
    # Placeholder for now - will implement in next phase
    @app.callback(
        Output("portfolio-status-message", "children"),
        Input("portfolio-close-all-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def close_all_positions(n_clicks):
        """Close all positions (placeholder for now)."""
        if not n_clicks:
            raise PreventUpdate
        
        return dbc.Alert(
            "⚠️ Auto-trading portfolio not yet connected. Coming soon!",
            color="warning"
        )
    
    logger.info("✓ Portfolio callbacks registered (placeholder)")
