"""
AI Picks Portfolio Tab - Automated trading for weekly/monthly picks
Uses Alpaca 2 keys for dedicated picks trading
Includes AI-powered backtesting and adaptive strategy adjustment
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dash import dcc, html, Input, Output, State, dash_table, no_update, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)

# Alpaca 2 API configuration
ALPACA2_KEY = os.getenv('ALPACA2_KEY', '')
ALPACA2_SECRET = os.getenv('ALPACA2_SECRET', '')
ALPACA_BASE_URL = os.getenv('APCA_ENDPOINT', 'https://paper-api.alpaca.markets')

# Default investment per pick
INVESTMENT_PER_PICK = 500.0
MAX_POSITIONS = 20


def get_alpaca2_client():
    """Get Alpaca trading client using Alpaca 2 keys."""
    try:
        from alpaca.trading.client import TradingClient
        return TradingClient(ALPACA2_KEY, ALPACA2_SECRET, paper=True)
    except Exception as e:
        logger.warning(f"Failed to create Alpaca 2 client: {e}")
        return None


def get_alpaca2_positions():
    """Get current positions from Alpaca 2 account."""
    client = get_alpaca2_client()
    if not client:
        return pd.DataFrame()
    
    try:
        positions = client.get_all_positions()
        if not positions:
            return pd.DataFrame()
        
        data = []
        for pos in positions:
            data.append({
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                'market_value': float(pos.market_value),
                'side': pos.side.name if hasattr(pos.side, 'name') else 'long'
            })
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error fetching Alpaca 2 positions: {e}")
        return pd.DataFrame()


def get_alpaca2_account():
    """Get Alpaca 2 account information."""
    client = get_alpaca2_client()
    if not client:
        return {'equity': 0, 'cash': 0, 'buying_power': 0}
    
    try:
        account = client.get_account()
        return {
            'equity': float(account.equity),
            'cash': float(account.cash),
            'buying_power': float(account.buying_power),
            'portfolio_value': float(account.portfolio_value)
        }
    except Exception as e:
        logger.error(f"Error fetching Alpaca 2 account: {e}")
        return {'equity': 0, 'cash': 0, 'buying_power': 0}


def submit_buy_order(symbol: str, qty: int = None, notional: float = None):
    """Submit a buy order via Alpaca 2."""
    client = get_alpaca2_client()
    if not client:
        return {'status': 'error', 'message': 'Alpaca client unavailable'}
    
    try:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        
        if qty:
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
        elif notional:
            order_data = MarketOrderRequest(
                symbol=symbol,
                notional=notional,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
        else:
            return {'status': 'error', 'message': 'Either qty or notional required'}
        
        order = client.submit_order(order_data)
        return {
            'status': 'success',
            'order_id': order.id,
            'symbol': symbol,
            'qty': str(order.qty) if order.qty else 'notional',
            'side': 'buy'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def submit_sell_order(symbol: str, qty: float):
    """Submit a sell order via Alpaca 2."""
    client = get_alpaca2_client()
    if not client:
        return {'status': 'error', 'message': 'Alpaca client unavailable'}
    
    try:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        order = client.submit_order(order_data)
        return {
            'status': 'success',
            'order_id': order.id,
            'symbol': symbol,
            'qty': str(order.qty),
            'side': 'sell'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_picks_performance_data():
    """Calculate performance metrics for picks."""
    try:
        # Try to load historical picks data
        from . import weekly_picks, monthly_picks
        
        # Get current picks
        weekly_df, _, _ = weekly_picks._load_and_enrich_picks()
        monthly_df, _, _ = monthly_picks._load_and_enrich_picks()
        
        performance = {
            'weekly': {
                'total_picks': len(weekly_df) if weekly_df is not None else 0,
                'total_pl': weekly_df['profit_loss'].sum() if weekly_df is not None and 'profit_loss' in weekly_df.columns else 0,
                'winners': len(weekly_df[weekly_df['profit_loss'] > 0]) if weekly_df is not None and 'profit_loss' in weekly_df.columns else 0,
                'losers': len(weekly_df[weekly_df['profit_loss'] < 0]) if weekly_df is not None and 'profit_loss' in weekly_df.columns else 0,
            },
            'monthly': {
                'total_picks': len(monthly_df) if monthly_df is not None else 0,
                'total_pl': monthly_df['profit_loss'].sum() if monthly_df is not None and 'profit_loss' in monthly_df.columns else 0,
                'winners': len(monthly_df[monthly_df['profit_loss'] > 0]) if monthly_df is not None and 'profit_loss' in monthly_df.columns else 0,
                'losers': len(monthly_df[monthly_df['profit_loss'] < 0]) if monthly_df is not None and 'profit_loss' in monthly_df.columns else 0,
            }
        }
        
        return performance
    except Exception as e:
        logger.error(f"Error calculating performance: {e}")
        return {'weekly': {}, 'monthly': {}}


def create_performance_chart(picks_type='weekly'):
    """Create a performance chart for picks."""
    try:
        if picks_type == 'weekly':
            from . import weekly_picks
            df, _, _ = weekly_picks._load_and_enrich_picks()
        else:
            from . import monthly_picks
            df, _, _ = monthly_picks._load_and_enrich_picks()
        
        if df is None or df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(22,33,62,0.8)')
            return fig
        
        # Sort by profit/loss
        if 'profit_loss' in df.columns and 'ticker' in df.columns:
            df_sorted = df.sort_values('profit_loss', ascending=True)
            
            colors = ['#ff6b6b' if x < 0 else '#4CAF50' for x in df_sorted['profit_loss']]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=df_sorted['profit_loss'],
                    y=df_sorted['ticker'],
                    orientation='h',
                    marker_color=colors,
                    text=[f"${x:+.2f}" for x in df_sorted['profit_loss']],
                    textposition='outside'
                )
            ])
            
            fig.update_layout(
                title=f"{picks_type.title()} Picks P/L",
                xaxis_title="Profit/Loss ($)",
                yaxis_title="Ticker",
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(22,33,62,0.8)',
                height=max(400, len(df_sorted) * 25),
                margin=dict(l=80, r=80, t=50, b=50)
            )
            
            return fig
        else:
            fig = go.Figure()
            fig.add_annotation(text="Insufficient data for chart", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(22,33,62,0.8)')
            return fig
            
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        fig = go.Figure()
        fig.add_annotation(text=f"Chart error: {str(e)[:50]}", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(22,33,62,0.8)')
        return fig


def create_equity_curve():
    """Create equity curve chart for AI picks portfolio."""
    positions_df = get_alpaca2_positions()
    account = get_alpaca2_account()
    
    # For now, show current state as a bar
    fig = go.Figure()
    
    if not positions_df.empty:
        # Show positions by value
        fig.add_trace(go.Bar(
            x=positions_df['symbol'],
            y=positions_df['market_value'],
            marker_color='#4CAF50',
            name='Market Value'
        ))
        
        fig.add_trace(go.Bar(
            x=positions_df['symbol'],
            y=positions_df['unrealized_pl'],
            marker_color=['#4CAF50' if x >= 0 else '#ff6b6b' for x in positions_df['unrealized_pl']],
            name='Unrealized P/L'
        ))
    else:
        fig.add_annotation(text="No positions", x=0.5, y=0.5, showarrow=False, font=dict(color='white'))
    
    fig.update_layout(
        title="AI Picks Portfolio - Current Holdings",
        xaxis_title="Symbol",
        yaxis_title="Value ($)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        barmode='group',
        height=350
    )
    
    return fig


def create_win_loss_pie():
    """Create win/loss distribution pie chart."""
    positions_df = get_alpaca2_positions()
    
    if positions_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No positions", x=0.5, y=0.5, showarrow=False, font=dict(color='white'))
    else:
        winners = len(positions_df[positions_df['unrealized_pl'] >= 0])
        losers = len(positions_df[positions_df['unrealized_pl'] < 0])
        
        fig = go.Figure(data=[go.Pie(
            labels=['Winners', 'Losers'],
            values=[winners, losers],
            marker_colors=['#4CAF50', '#ff6b6b'],
            hole=0.4
        )])
    
    fig.update_layout(
        title="Win/Loss Distribution",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=300
    )
    
    return fig


def run_ai_backtest(picks_df, strategy_params):
    """Run AI-powered backtest on picks with adaptive strategy."""
    results = {
        'total_return': 0,
        'sharpe_ratio': 0,
        'max_drawdown': 0,
        'win_rate': 0,
        'avg_win': 0,
        'avg_loss': 0,
        'trades': [],
        'recommendations': []
    }
    
    if picks_df is None or picks_df.empty:
        return results
    
    try:
        # Simulate backtest with the picks
        daily_returns = []
        trades = []
        
        for _, pick in picks_df.iterrows():
            ticker = pick.get('ticker', '')
            entry_price = pick.get('week_start_price', pick.get('month_start_price', 100))
            current_price = pick.get('current_price', entry_price)
            
            if pd.isna(entry_price) or pd.isna(current_price):
                continue
            
            pct_return = ((current_price - entry_price) / entry_price) * 100
            daily_returns.append(pct_return)
            
            trades.append({
                'ticker': ticker,
                'entry': entry_price,
                'exit': current_price,
                'return': pct_return,
                'is_winner': pct_return > 0
            })
        
        if not trades:
            return results
        
        returns = np.array(daily_returns)
        
        # Calculate metrics
        results['total_return'] = np.sum(returns)
        results['sharpe_ratio'] = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Calculate max drawdown
        cum_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdowns = cum_returns - running_max
        results['max_drawdown'] = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        # Win/loss stats
        winners = [t for t in trades if t['is_winner']]
        losers = [t for t in trades if not t['is_winner']]
        
        results['win_rate'] = len(winners) / len(trades) * 100 if trades else 0
        results['avg_win'] = np.mean([t['return'] for t in winners]) if winners else 0
        results['avg_loss'] = np.mean([t['return'] for t in losers]) if losers else 0
        results['trades'] = trades
        
        # AI Recommendations based on performance
        if results['win_rate'] < 40:
            results['recommendations'].append("⚠️ Low win rate - consider more conservative position sizing")
        if results['max_drawdown'] < -15:
            results['recommendations'].append("⚠️ High drawdown risk - implement tighter stop losses")
        if results['sharpe_ratio'] > 1.5:
            results['recommendations'].append("✅ Strong risk-adjusted returns - strategy performing well")
        if results['avg_loss'] < -10 and results['avg_win'] < abs(results['avg_loss']):
            results['recommendations'].append("⚠️ Asymmetric risk/reward - losses exceed average wins")
        
        if not results['recommendations']:
            results['recommendations'].append("✅ Strategy metrics look balanced")
            
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        results['recommendations'].append(f"❌ Backtest error: {str(e)[:50]}")
    
    return results


def layout():
    """Create AI Picks Portfolio layout."""
    return dbc.Container([
        # Header
        html.Div([
            html.H2([
                html.I(className="bi bi-robot me-2"),
                "AI Picks Portfolio"
            ], className="text-primary mb-2"),
            html.P([
                "Automated trading for weekly & monthly AI picks using ",
                html.Strong("Alpaca 2 Account", className="text-success"),
                " • AI-Powered Backtesting & Adaptive Strategy"
            ], className="text-muted mb-4")
        ]),
        
        # Account Summary
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("Portfolio Value", className="small text-muted mb-1"),
                        html.H3(id="ai-portfolio-value", children="Loading...", className="text-white mb-0")
                    ])
                ], className="shadow graph-card-dark")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("Cash Available", className="small text-muted mb-1"),
                        html.H3(id="ai-portfolio-cash", children="Loading...", className="text-white mb-0")
                    ])
                ], className="shadow graph-card-dark")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("Buying Power", className="small text-muted mb-1"),
                        html.H3(id="ai-portfolio-buying-power", children="Loading...", className="text-white mb-0")
                    ])
                ], className="shadow graph-card-dark")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("Positions", className="small text-muted mb-1"),
                        html.H3(id="ai-portfolio-positions-count", children="0", className="text-white mb-0")
                    ])
                ], className="shadow graph-card-dark")
            ], width=3),
        ], className="mb-4"),
        
        # Auto-Buy Controls
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-lightning-charge me-2"),
                "Auto-Buy Controls"
            ], className="fw-bold"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("📅 Weekly Picks", className="text-center mb-3"),
                                dbc.Input(
                                    id="weekly-investment-amount",
                                    type="number",
                                    value=500,
                                    min=100,
                                    max=5000,
                                    step=100,
                                    placeholder="$ per pick",
                                    className="mb-2"
                                ),
                                dbc.Button(
                                    [html.I(className="bi bi-cart-plus me-2"), "Buy All Weekly Picks"],
                                    id="buy-weekly-picks-btn",
                                    color="success",
                                    className="w-100 mb-2"
                                ),
                                html.Div(id="weekly-buy-status", className="small text-center")
                            ])
                        ], className="graph-card-dark")
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("📆 Monthly Picks", className="text-center mb-3"),
                                dbc.Input(
                                    id="monthly-investment-amount",
                                    type="number",
                                    value=1000,
                                    min=100,
                                    max=10000,
                                    step=100,
                                    placeholder="$ per pick",
                                    className="mb-2"
                                ),
                                dbc.Button(
                                    [html.I(className="bi bi-cart-plus me-2"), "Buy All Monthly Picks"],
                                    id="buy-monthly-picks-btn",
                                    color="primary",
                                    className="w-100 mb-2"
                                ),
                                html.Div(id="monthly-buy-status", className="small text-center")
                            ])
                        ], className="graph-card-dark")
                    ], width=6),
                ])
            ])
        ], className="mb-4 shadow"),
        
        # Charts Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Portfolio Holdings"),
                    dbc.CardBody([
                        dcc.Graph(id="ai-portfolio-chart", figure=create_equity_curve())
                    ])
                ], className="shadow graph-card-dark h-100")
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Win/Loss"),
                    dbc.CardBody([
                        dcc.Graph(id="ai-winloss-chart", figure=create_win_loss_pie())
                    ])
                ], className="shadow graph-card-dark h-100")
            ], width=4),
        ], className="mb-4"),
        
        # Picks Performance Charts
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Weekly Picks Performance"),
                    dbc.CardBody([
                        dcc.Graph(id="weekly-performance-chart", figure=create_performance_chart('weekly'))
                    ])
                ], className="shadow graph-card-dark")
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Monthly Picks Performance"),
                    dbc.CardBody([
                        dcc.Graph(id="monthly-performance-chart", figure=create_performance_chart('monthly'))
                    ])
                ], className="shadow graph-card-dark")
            ], width=6),
        ], className="mb-4"),
        
        # AI Backtest Section
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-cpu me-2"),
                "AI-Powered Backtesting & Strategy Analysis"
            ], className="fw-bold"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Strategy Type"),
                        dbc.Select(
                            id="backtest-strategy-type",
                            options=[
                                {"label": "Weekly Momentum", "value": "weekly"},
                                {"label": "Monthly Value", "value": "monthly"},
                                {"label": "Combined (Both)", "value": "combined"},
                            ],
                            value="combined"
                        ),
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Position Size ($)"),
                        dbc.Input(
                            id="backtest-position-size",
                            type="number",
                            value=500,
                            min=100,
                            max=5000
                        ),
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Stop Loss (%)"),
                        dbc.Input(
                            id="backtest-stop-loss",
                            type="number",
                            value=-10,
                            min=-50,
                            max=0
                        ),
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Take Profit (%)"),
                        dbc.Input(
                            id="backtest-take-profit",
                            type="number",
                            value=20,
                            min=5,
                            max=100
                        ),
                    ], width=3),
                ], className="mb-3"),
                
                dbc.Button(
                    [html.I(className="bi bi-play-fill me-2"), "Run AI Backtest"],
                    id="run-backtest-btn",
                    color="warning",
                    className="mb-3"
                ),
                
                html.Div(id="backtest-results", children=[
                    dbc.Alert("Click 'Run AI Backtest' to analyze strategy performance", color="info")
                ])
            ])
        ], className="mb-4 shadow"),
        
        # Positions Table
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-table me-2"),
                "Current Positions"
            ], className="fw-bold"),
            dbc.CardBody([
                html.Div(id="ai-positions-table", children=[
                    dbc.Alert("Loading positions...", color="info")
                ])
            ])
        ], className="mb-4 shadow"),
        
        # Emergency Controls
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-exclamation-triangle me-2"),
                "Emergency Controls"
            ], className="fw-bold text-danger"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-x-circle me-2"), "Close All Positions"],
                            id="ai-close-all-btn",
                            color="danger",
                            outline=True,
                            className="w-100"
                        ),
                    ], width=6),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-pause-circle me-2"), "Pause Auto-Trading"],
                            id="ai-pause-trading-btn",
                            color="warning",
                            outline=True,
                            className="w-100"
                        ),
                    ], width=6),
                ]),
                html.Div(id="ai-emergency-status", className="mt-3")
            ])
        ], className="shadow"),
        
        # Hidden stores and intervals
        dcc.Interval(id='ai-portfolio-refresh', interval=10000, n_intervals=0),
        dcc.Store(id='ai-backtest-store', data={}),
        
    ], fluid=True, className="p-4")


def register_callbacks(app):
    """Register callbacks for AI Picks Portfolio tab."""
    
    @app.callback(
        [Output("ai-portfolio-value", "children"),
         Output("ai-portfolio-cash", "children"),
         Output("ai-portfolio-buying-power", "children"),
         Output("ai-portfolio-positions-count", "children"),
         Output("ai-positions-table", "children"),
         Output("ai-portfolio-chart", "figure"),
         Output("ai-winloss-chart", "figure")],
        [Input("ai-portfolio-refresh", "n_intervals")],
        prevent_initial_call=False
    )
    def update_portfolio_data(n):
        """Update portfolio data from Alpaca 2."""
        account = get_alpaca2_account()
        positions_df = get_alpaca2_positions()
        
        # Format values
        portfolio_value = f"${account.get('portfolio_value', account.get('equity', 0)):,.2f}"
        cash = f"${account.get('cash', 0):,.2f}"
        buying_power = f"${account.get('buying_power', 0):,.2f}"
        positions_count = str(len(positions_df))
        
        # Build positions table
        if not positions_df.empty:
            positions_table = dash_table.DataTable(
                data=positions_df.to_dict('records'),
                columns=[
                    {'name': 'Symbol', 'id': 'symbol'},
                    {'name': 'Qty', 'id': 'qty', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                    {'name': 'Entry $', 'id': 'avg_entry_price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                    {'name': 'Current $', 'id': 'current_price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                    {'name': 'Value $', 'id': 'market_value', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                    {'name': 'P/L $', 'id': 'unrealized_pl', 'type': 'numeric', 'format': {'specifier': '+,.2f', 'prefix': '$'}},
                    {'name': 'P/L %', 'id': 'unrealized_plpc', 'type': 'numeric', 'format': {'specifier': '+.2f'}},
                ],
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#1a1a2e', 'color': '#e0e0e0', 'fontWeight': 'bold'},
                style_cell={'backgroundColor': '#16213e', 'color': '#e0e0e0', 'fontSize': '13px'},
                style_data_conditional=[
                    {'if': {'filter_query': '{unrealized_pl} > 0'}, 'color': '#4CAF50', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{unrealized_pl} < 0'}, 'color': '#ff6b6b', 'fontWeight': 'bold'}
                ]
            )
        else:
            positions_table = dbc.Alert(
                "No positions. Use Auto-Buy to purchase weekly or monthly picks.",
                color="info"
            )
        
        # Update charts
        portfolio_chart = create_equity_curve()
        winloss_chart = create_win_loss_pie()
        
        return portfolio_value, cash, buying_power, positions_count, positions_table, portfolio_chart, winloss_chart
    
    @app.callback(
        Output("weekly-buy-status", "children"),
        [Input("buy-weekly-picks-btn", "n_clicks")],
        [State("weekly-investment-amount", "value")],
        prevent_initial_call=True
    )
    def buy_weekly_picks(n_clicks, investment_amount):
        """Buy all weekly picks."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            from . import weekly_picks
            df, _, _ = weekly_picks._load_and_enrich_picks()
            
            if df is None or df.empty:
                return dbc.Alert("No weekly picks available", color="warning")
            
            results = []
            for _, row in df.iterrows():
                ticker = row.get('ticker', '')
                if not ticker:
                    continue
                
                result = submit_buy_order(ticker, notional=float(investment_amount or 500))
                results.append(f"{ticker}: {result.get('status')}")
            
            success_count = len([r for r in results if 'success' in r])
            return dbc.Alert(
                f"✅ Ordered {success_count}/{len(results)} weekly picks",
                color="success" if success_count > 0 else "warning"
            )
        except Exception as e:
            return dbc.Alert(f"❌ Error: {str(e)}", color="danger")
    
    @app.callback(
        Output("monthly-buy-status", "children"),
        [Input("buy-monthly-picks-btn", "n_clicks")],
        [State("monthly-investment-amount", "value")],
        prevent_initial_call=True
    )
    def buy_monthly_picks(n_clicks, investment_amount):
        """Buy all monthly picks."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            from . import monthly_picks
            df, _, _ = monthly_picks._load_and_enrich_picks()
            
            if df is None or df.empty:
                return dbc.Alert("No monthly picks available", color="warning")
            
            results = []
            for _, row in df.iterrows():
                ticker = row.get('ticker', '')
                if not ticker:
                    continue
                
                result = submit_buy_order(ticker, notional=float(investment_amount or 1000))
                results.append(f"{ticker}: {result.get('status')}")
            
            success_count = len([r for r in results if 'success' in r])
            return dbc.Alert(
                f"✅ Ordered {success_count}/{len(results)} monthly picks",
                color="success" if success_count > 0 else "warning"
            )
        except Exception as e:
            return dbc.Alert(f"❌ Error: {str(e)}", color="danger")
    
    @app.callback(
        Output("backtest-results", "children"),
        [Input("run-backtest-btn", "n_clicks")],
        [State("backtest-strategy-type", "value"),
         State("backtest-position-size", "value"),
         State("backtest-stop-loss", "value"),
         State("backtest-take-profit", "value")],
        prevent_initial_call=True
    )
    def run_backtest(n_clicks, strategy_type, position_size, stop_loss, take_profit):
        """Run AI backtest."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Load picks data based on strategy
            from . import weekly_picks, monthly_picks
            
            if strategy_type == 'weekly':
                df, _, _ = weekly_picks._load_and_enrich_picks()
            elif strategy_type == 'monthly':
                df, _, _ = monthly_picks._load_and_enrich_picks()
            else:  # combined
                w_df, _, _ = weekly_picks._load_and_enrich_picks()
                m_df, _, _ = monthly_picks._load_and_enrich_picks()
                df = pd.concat([w_df, m_df]) if w_df is not None and m_df is not None else (w_df or m_df)
            
            # Run backtest
            params = {
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            results = run_ai_backtest(df, params)
            
            # Build results display
            return dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H4("📊 Backtest Results", className="text-primary mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Div("Total Return", className="small text-muted"),
                                    html.H5(f"{results['total_return']:+.2f}%", 
                                           className="text-success" if results['total_return'] >= 0 else "text-danger")
                                ], width=3),
                                dbc.Col([
                                    html.Div("Sharpe Ratio", className="small text-muted"),
                                    html.H5(f"{results['sharpe_ratio']:.2f}")
                                ], width=3),
                                dbc.Col([
                                    html.Div("Max Drawdown", className="small text-muted"),
                                    html.H5(f"{results['max_drawdown']:.2f}%", className="text-danger")
                                ], width=3),
                                dbc.Col([
                                    html.Div("Win Rate", className="small text-muted"),
                                    html.H5(f"{results['win_rate']:.1f}%")
                                ], width=3),
                            ])
                        ], width=8),
                        dbc.Col([
                            html.H5("🤖 AI Recommendations", className="text-warning mb-2"),
                            html.Ul([
                                html.Li(rec, className="mb-1") for rec in results['recommendations']
                            ], className="small")
                        ], width=4),
                    ])
                ])
            ], className="bg-dark text-white")
            
        except Exception as e:
            return dbc.Alert(f"❌ Backtest error: {str(e)}", color="danger")
    
    @app.callback(
        Output("ai-emergency-status", "children"),
        [Input("ai-close-all-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def close_all_positions(n_clicks):
        """Close all AI picks positions."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            client = get_alpaca2_client()
            if not client:
                return dbc.Alert("Alpaca client unavailable", color="danger")
            
            client.close_all_positions(cancel_orders=True)
            return dbc.Alert("✅ All positions closed successfully", color="success")
        except Exception as e:
            return dbc.Alert(f"❌ Error: {str(e)}", color="danger")
    
    @app.callback(
        [Output("weekly-performance-chart", "figure"),
         Output("monthly-performance-chart", "figure")],
        [Input("ai-portfolio-refresh", "n_intervals")],
        prevent_initial_call=False
    )
    def update_performance_charts(n):
        """Update performance charts."""
        return create_performance_chart('weekly'), create_performance_chart('monthly')
    
    logger.info("✅ AI Picks Portfolio callbacks registered")
