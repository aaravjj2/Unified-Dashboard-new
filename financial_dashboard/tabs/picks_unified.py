"""
Unified Picks Tab - Single tab with 4 subtabs:
1. Weekly Picks - Short-term stock picks (7-day holding)
2. Monthly Picks - Long-term stock picks (30-day holding)
3. Auto-Trading Portfolio - Live paper trading portfolio
4. AI Picks Portfolio - AI-powered auto-trading with Alpaca 2 keys

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
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# Import existing picks logic
from . import weekly_picks
from . import monthly_picks
from . import ai_picks_portfolio


def create_picks_performance_chart(picks_type='weekly'):
    """Create a performance chart for picks to add to Weekly/Monthly tabs."""
    try:
        if picks_type == 'weekly':
            df, _, _ = weekly_picks._load_and_enrich_picks()
        else:
            df, _, _ = monthly_picks._load_and_enrich_picks()
        
        if df is None or df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No picks data available", x=0.5, y=0.5, showarrow=False, font=dict(color='white'))
            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(22,33,62,0.8)', height=300)
            return fig
        
        # Create P/L bar chart
        if 'profit_loss' in df.columns and 'ticker' in df.columns:
            df_sorted = df.sort_values('profit_loss', ascending=True)
            colors = ['#ff6b6b' if x < 0 else '#4CAF50' for x in df_sorted['profit_loss']]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=df_sorted['profit_loss'],
                    y=df_sorted['ticker'],
                    orientation='h',
                    marker_color=colors,
                    text=[f"${x:+.2f}" if pd.notna(x) else "N/A" for x in df_sorted['profit_loss']],
                    textposition='outside'
                )
            ])
            
            fig.update_layout(
                title=f"{picks_type.title()} Picks Profit/Loss",
                xaxis_title="P/L ($)",
                yaxis_title="",
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(22,33,62,0.8)',
                height=max(300, len(df_sorted) * 22),
                margin=dict(l=60, r=60, t=40, b=40)
            )
            return fig
        else:
            fig = go.Figure()
            fig.add_annotation(text="Insufficient data", x=0.5, y=0.5, showarrow=False, font=dict(color='white'))
            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(22,33,62,0.8)', height=300)
            return fig
    except Exception as e:
        logger.error(f"Chart error: {e}")
        fig = go.Figure()
        fig.add_annotation(text="Chart unavailable", x=0.5, y=0.5, showarrow=False, font=dict(color='white'))
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(22,33,62,0.8)', height=300)
        return fig


def layout():
    """Create unified picks tab with 4 subtabs."""
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
            # Tab 1: Weekly Picks with Graph
            dbc.Tab(
                html.Div([
                    # Performance Chart
                    dbc.Card([
                        dbc.CardHeader("📊 Weekly Picks Performance"),
                        dbc.CardBody([
                            dcc.Graph(
                                id="weekly-picks-chart",
                                figure=create_picks_performance_chart('weekly')
                            )
                        ])
                    ], className="mb-4 shadow graph-card-dark"),
                    # Original weekly picks layout
                    weekly_picks.layout()
                ]),
                label="📅 Weekly Picks",
                tab_id="tab-weekly-picks",
                className="pt-4"
            ),
            
            # Tab 2: Monthly Picks with Graph
            dbc.Tab(
                html.Div([
                    # Performance Chart
                    dbc.Card([
                        dbc.CardHeader("📊 Monthly Picks Performance"),
                        dbc.CardBody([
                            dcc.Graph(
                                id="monthly-picks-chart",
                                figure=create_picks_performance_chart('monthly')
                            )
                        ])
                    ], className="mb-4 shadow graph-card-dark"),
                    # Original monthly picks layout
                    monthly_picks.layout()
                ]),
                label="📆 Monthly Picks",
                tab_id="tab-monthly-picks",
                className="pt-4"
            ),
            
            # Tab 3: Auto-Trading Portfolio
            dbc.Tab(
                create_portfolio_tab_layout(),
                label="💼 Auto-Trading Portfolio",
                tab_id="tab-portfolio",
                className="pt-4"
            ),
            
            # Tab 4: AI Picks Portfolio (NEW - uses Alpaca 2)
            dbc.Tab(
                ai_picks_portfolio.layout(),
                label="🤖 AI Picks Portfolio",
                tab_id="tab-ai-picks",
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
    
    # Register AI Picks Portfolio callbacks
    ai_picks_portfolio.register_callbacks(app)
    
    logger.info("✅ Unified picks callbacks registered (including AI Picks Portfolio)")


def register_portfolio_callbacks(app):
    """Register callbacks for auto-trading portfolio tab."""
    
    # Update portfolio summary and positions
    @app.callback(
        Output("portfolio-total-value", "children"),
        Output("portfolio-total-pnl", "children"),
        Output("portfolio-cash", "children"),
        Output("portfolio-positions-count", "children"),
        Output("portfolio-win-rate", "children"),
        Output("portfolio-positions-container", "children"),
        Output("portfolio-orders-container", "children"),
        Input("portfolio-refresh-interval", "n_intervals"),
        prevent_initial_call=False
    )
    def update_portfolio_data(n_intervals):
        """Update portfolio data from Alpaca."""
        try:
            from utils.picks_portfolio_manager import PicksPortfolioManager
            
            # Initialize manager
            manager = PicksPortfolioManager()
            
            # Get account info
            account = manager.get_account_info()
            total_value = account.get('total_value', 0)
            cash = account.get('cash', 0)
            equity = account.get('equity', 0)
            
            # Calculate P/L (assuming starting capital of $10k)
            starting_capital = 10000
            total_pnl = total_value - starting_capital
            total_pnl_pct = (total_pnl / starting_capital) * 100 if starting_capital > 0 else 0
            
            # Get positions
            positions_df = manager.get_positions()
            num_positions = len(positions_df) if not positions_df.empty else 0
            
            # Calculate win rate (positions with positive P/L)
            if not positions_df.empty and 'unrealized_plpc' in positions_df.columns:
                winning = len(positions_df[positions_df['unrealized_plpc'] > 0])
                win_rate = (winning / num_positions) * 100 if num_positions > 0 else 0
                win_rate_str = f"{win_rate:.0f}%"
            else:
                win_rate_str = "--"
            
            # Format summary values
            total_value_str = f"${total_value:,.2f}"
            pnl_color = "text-success" if total_pnl >= 0 else "text-danger"
            pnl_str = f"${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)"
            cash_str = f"${cash:,.2f}"
            positions_str = f"{num_positions}/20"
            
            # Build positions table
            if not positions_df.empty:
                positions_table = dash_table.DataTable(
                    data=positions_df.to_dict('records'),
                    columns=[
                        {'name': 'Ticker', 'id': 'ticker'},
                        {'name': 'Qty', 'id': 'quantity'},
                        {'name': 'Entry $', 'id': 'entry_price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                        {'name': 'Current $', 'id': 'current_price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                        {'name': 'P/L $', 'id': 'unrealized_pl', 'type': 'numeric', 'format': {'specifier': '+,.2f', 'prefix': '$'}},
                        {'name': 'P/L %', 'id': 'unrealized_plpc', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                    ],
                    style_table={'overflowX': 'auto'},
                    style_header={
                        'backgroundColor': '#333',
                        'color': '#e0e0e0',
                        'fontWeight': 'bold',
                        'fontSize': '12px'
                    },
                    style_cell={
                        'backgroundColor': '#2c2c2c',
                        'color': '#e0e0e0',
                        'fontSize': '13px',
                        'textAlign': 'left'
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{unrealized_plpc} > 0'},
                            'color': '#4CAF50',
                            'fontWeight': 'bold'
                        },
                        {
                            'if': {'filter_query': '{unrealized_plpc} < 0'},
                            'color': '#ff6b6b',
                            'fontWeight': 'bold'
                        }
                    ]
                )
            else:
                positions_table = dbc.Alert([
                    html.I(className="bi bi-info-circle me-2"),
                    "No active positions. Deploy picks from Weekly or Monthly tabs to start trading."
                ], color="info", className="text-center")
            
            # Get recent orders
            orders_df = manager.get_orders(limit=20)
            
            if not orders_df.empty:
                orders_df['date'] = pd.to_datetime(orders_df['date']).dt.strftime('%Y-%m-%d %H:%M')
                orders_table = dash_table.DataTable(
                    data=orders_df.head(10).to_dict('records'),
                    columns=[
                        {'name': 'Date', 'id': 'date'},
                        {'name': 'Ticker', 'id': 'ticker'},
                        {'name': 'Side', 'id': 'side'},
                        {'name': 'Qty', 'id': 'quantity'},
                        {'name': 'Filled', 'id': 'filled_qty'},
                        {'name': 'Status', 'id': 'status'},
                    ],
                    style_table={'overflowX': 'auto'},
                    style_header={
                        'backgroundColor': '#333',
                        'color': '#e0e0e0',
                        'fontWeight': 'bold',
                        'fontSize': '12px'
                    },
                    style_cell={
                        'backgroundColor': '#2c2c2c',
                        'color': '#e0e0e0',
                        'fontSize': '13px',
                        'textAlign': 'left'
                    }
                )
            else:
                orders_table = dbc.Alert("No orders yet", color="dark", className="text-center text-muted")
            
            return (
                total_value_str,
                html.Span(pnl_str, className=f"{pnl_color} mb-0"),
                cash_str,
                positions_str,
                win_rate_str,
                positions_table,
                orders_table
            )
            
        except Exception as e:
            logger.exception(f"Error updating portfolio: {e}")
            return (
                "$10,000.00",
                html.Span("$0.00 (0.00%)", className="text-muted mb-0"),
                "$10,000.00",
                "0/20",
                "--",
                dbc.Alert(f"Error loading portfolio: {str(e)}", color="danger"),
                dbc.Alert("Error loading orders", color="danger")
            )
    
    # Close all positions callback
    @app.callback(
        Output("portfolio-status-message", "children"),
        Input("portfolio-close-all-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def close_all_positions(n_clicks):
        """Close all positions."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            from utils.picks_portfolio_manager import PicksPortfolioManager
            
            manager = PicksPortfolioManager()
            result = manager.close_all_positions()
            
            if result['status'] == 'success':
                return dbc.Alert(
                    "✅ All positions closed successfully!",
                    color="success"
                )
            else:
                return dbc.Alert(
                    f"⚠️ Error: {result['message']}",
                    color="warning"
                )
                
        except Exception as e:
            return dbc.Alert(
                f"❌ Error closing positions: {str(e)}",
                color="danger"
            )
    
    logger.info("✓ Portfolio callbacks registered")
