"""
Portfolio Tracker Tab
Real-time portfolio tracking with Alpaca integration
Shows positions, P/L, analytics, and order history
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)

# Try to import Alpaca client
ALPACA_AVAILABLE = False
try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except Exception as e:
    logger.warning(f"Alpaca not available: {e}")


def get_alpaca_client():
    """Get Alpaca trading client from environment."""
    if not ALPACA_AVAILABLE:
        return None
    
    key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
    secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
    if not key or not secret:
        return None
    
    # Default to paper trading
    paper = True
    return TradingClient(key, secret, paper=paper)


def layout():
    """Build portfolio tracker layout."""
    return dbc.Container([
        # Alpaca credential alert (hidden unless credentials missing)
        dbc.Alert(id='portfolio-alpaca-alert', is_open=False, color='warning'),

        html.H2("Portfolio Tracker", className="mt-3 mb-3"),
        
        # Summary cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Portfolio Value", className="text-muted"),
                        html.H3(id='portfolio-value', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Invested", className="text-muted"),
                        html.H3(id='portfolio-invested', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Unrealized P/L", className="text-muted"),
                        html.H3(id='portfolio-unrealized-pl', children="$0.00")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Buying Power", className="text-muted"),
                        html.H3(id='portfolio-buying-power', children="$0.00")
                    ])
                ])
            ], width=3)
        ], className="mb-4"),
        
        # Refresh button
        dbc.Row([
            dbc.Col([
                dbc.Button("🔄 Refresh", id='portfolio-refresh-btn', color='primary', size='sm')
            ])
        ], className="mb-3"),
        
        # Tabs for different views
        dbc.Tabs(id="portfolio-tracker-subtabs", children=[
            # Positions tab
            dbc.Tab(label="Positions", children=[
                dbc.Container([
                    html.H5("Current Positions", className="mt-3 mb-3"),
                    html.Div(id='portfolio-positions-table')
                ], fluid=True)
            ]),
            
            # Orders tab
            dbc.Tab(label="Order History", children=[
                dbc.Container([
                    html.H5("Order History", className="mt-3 mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.RadioItems(
                                id='order-filter',
                                options=[
                                    {'label': 'All Orders', 'value': 'all'},
                                    {'label': 'Open Orders', 'value': 'open'},
                                    {'label': 'Filled Orders', 'value': 'filled'}
                                ],
                                value='all',
                                inline=True
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Date Range:"),
                            dcc.DatePickerRange(
                                id='order-date-range',
                                start_date=(datetime.now() - timedelta(days=30)).date(),
                                end_date=datetime.now().date(),
                                display_format='YYYY-MM-DD'
                            )
                        ], width=6)
                    ], className="mb-3"),
                    html.Div(id='portfolio-orders-table')
                ], fluid=True)
            ]),
            
            # Analytics tab
            dbc.Tab(label="Analytics", children=[
                dbc.Container([
                    html.H5("Portfolio Analytics", className="mt-3 mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Time Period:"),
                            dcc.Dropdown(
                                id='analytics-period',
                                options=[
                                    {'label': '1 Day', 'value': '1d'},
                                    {'label': '1 Week', 'value': '1w'},
                                    {'label': '1 Month', 'value': '1m'},
                                    {'label': '3 Months', 'value': '3m'},
                                    {'label': 'YTD', 'value': 'ytd'},
                                    {'label': '1 Year', 'value': '1y'}
                                ],
                                value='1m'
                            )
                        ], width=4)
                    ], className="mb-3"),
                    
                    # Risk Metrics Cards
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Value at Risk (VaR 95%)", className="text-muted"),
                                    html.H4(id='portfolio-var', children="$0.00")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("CVaR (Expected Shortfall)", className="text-muted"),
                                    html.H4(id='portfolio-cvar', children="$0.00")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Sharpe Ratio", className="text-muted"),
                                    html.H4(id='portfolio-sharpe', children="0.00")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Beta to SPY", className="text-muted"),
                                    html.H4(id='portfolio-beta', children="1.00")
                                ])
                            ])
                        ], width=3)
                    ], className="mb-4"),
                    
                    html.Div(id='portfolio-analytics-content')
                ], fluid=True)
            ]),
            
            # Factor Exposure tab (NEW)
            dbc.Tab(label="Factor Exposure", children=[
                dbc.Container([
                    html.H5("Factor Exposure Analysis", className="mt-3 mb-3"),
                    html.P("SHAP-based factor attribution for current positions", className="text-muted"),
                    html.Div(id='portfolio-factor-exposure-content')
                ], fluid=True)
            ])
        ]),
        
        # Hidden interval for auto-refresh
        dcc.Interval(id='portfolio-interval', interval=30*1000, n_intervals=0),
        
        # Store for portfolio data
        dcc.Store(id='portfolio-data-store'),
        
        # Hidden trigger for initial load
        dcc.Store(id='portfolio-load-trigger', data=1)
        
    ], fluid=True)


def register_callbacks(app):
    """Register portfolio tracker callbacks."""
    
    @app.callback(
        [Output('portfolio-value', 'children'),
         Output('portfolio-invested', 'children'),
         Output('portfolio-unrealized-pl', 'children'),
         Output('portfolio-buying-power', 'children'),
         Output('portfolio-data-store', 'data'),
         Output('portfolio-alpaca-alert', 'children'),
         Output('portfolio-alpaca-alert', 'is_open')],
        [Input('portfolio-refresh-btn', 'n_clicks'),
         Input('portfolio-interval', 'n_intervals'),
         Input('portfolio-load-trigger', 'data')]
    )
    def update_portfolio_summary(n_clicks, n_intervals, load_trigger):
        """Update portfolio summary from Alpaca."""
        try:
            client = get_alpaca_client()
            if not client:
                msg = ("Alpaca client not available. Ensure the Alpaca SDK is installed and "
                       "set APCA_API_KEY_ID / APCA_API_SECRET_KEY (or APCA_API_KEY / APCA_API_SECRET) in the environment.")
                return "$0.00", "$0.00", "$0.00", "$0.00", None, msg, True
            
            account = client.get_account()
            positions = client.get_all_positions()
            
            portfolio_value = float(account.portfolio_value)
            equity = float(account.equity)
            buying_power = float(account.buying_power)
            
            # Calculate total cost basis and unrealized P/L
            total_cost = 0.0
            unrealized_pl = 0.0
            
            positions_data = []
            for pos in positions:
                cost_basis = float(pos.cost_basis)
                market_value = float(pos.market_value)
                unrealized = market_value - cost_basis
                
                total_cost += cost_basis
                unrealized_pl += unrealized
                
                positions_data.append({
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'cost_basis': cost_basis,
                    'market_value': market_value,
                    'unrealized_pl': unrealized,
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100
                })
            
            # Store data for other callbacks
            store_data = {
                'positions': positions_data,
                'account': {
                    'portfolio_value': portfolio_value,
                    'equity': equity,
                    'buying_power': buying_power,
                    'cash': float(account.cash)
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return (
                f"${portfolio_value:,.2f}",
                f"${total_cost:,.2f}",
                f"${unrealized_pl:,.2f}" + (" 📈" if unrealized_pl >= 0 else " 📉"),
                f"${buying_power:,.2f}",
                store_data,
                "",
                False
            )
            
        except Exception as e:
            logger.error(f"Error updating portfolio summary: {e}")
            return "$0.00", "$0.00", "$0.00", "$0.00", None, f"Error: {str(e)}", True
    
    
    @app.callback(
        Output('portfolio-positions-table', 'children'),
        [Input('portfolio-data-store', 'data')]
    )
    def update_positions_table(portfolio_data):
        """Update positions table with Weight % and enhanced formatting."""
        if not portfolio_data or not portfolio_data.get('positions'):
            return html.P("No positions found.", className="text-muted")
        
        positions = portfolio_data['positions']
        df = pd.DataFrame(positions)
        
        # Calculate portfolio weight %
        total_value = df['market_value'].sum()
        df['weight_pct'] = (df['market_value'] / total_value * 100).round(2)
        
        # Format columns for display
        df_display = df.copy()
        df_display['avg_entry_price'] = df['avg_entry_price'].apply(lambda x: f"${x:.2f}")
        df_display['current_price'] = df['current_price'].apply(lambda x: f"${x:.2f}")
        df_display['cost_basis'] = df['cost_basis'].apply(lambda x: f"${x:.2f}")
        df_display['market_value'] = df['market_value'].apply(lambda x: f"${x:.2f}")
        df_display['unrealized_pl'] = df['unrealized_pl'].apply(lambda x: f"${x:.2f}")
        df_display['unrealized_plpc'] = df['unrealized_plpc'].apply(lambda x: f"{x:.2f}%")
        df_display['weight_pct'] = df_display['weight_pct'].apply(lambda x: f"{x:.2f}%")
        
        return dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=[
                {'name': 'Symbol', 'id': 'symbol'},
                {'name': 'Quantity', 'id': 'qty'},
                {'name': 'Weight %', 'id': 'weight_pct'},
                {'name': 'Avg Entry', 'id': 'avg_entry_price'},
                {'name': 'Current Price', 'id': 'current_price'},
                {'name': 'Cost Basis', 'id': 'cost_basis'},
                {'name': 'Market Value', 'id': 'market_value'},
                {'name': 'Unrealized P/L', 'id': 'unrealized_pl'},
                {'name': 'P/L %', 'id': 'unrealized_plpc'}
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'column_id': 'unrealized_pl'},
                    'color': 'inherit'  # Will be styled by value in next update
                },
                {
                    'if': {'column_id': 'weight_pct'},
                    'fontWeight': '600'
                }
            ],
            tooltip_data=[
                {
                    'symbol': {'value': f"Click for detailed info about {row['symbol']}", 'type': 'markdown'}
                } for row in df_display.to_dict('records')
            ],
            tooltip_duration=None
        )
    
    
    @app.callback(
        Output('portfolio-orders-table', 'children'),
        [Input('portfolio-refresh-btn', 'n_clicks'),
         Input('order-filter', 'value'),
         Input('order-date-range', 'start_date'),
         Input('order-date-range', 'end_date')]
    )
    def update_orders_table(n_clicks, filter_type, start_date, end_date):
        """Update orders table with date filtering and transaction costs."""
        try:
            client = get_alpaca_client()
            if not client:
                return html.P("Alpaca client not available.", className="text-muted")
            
            # Get orders based on filter
            from alpaca.trading.enums import QueryOrderStatus
            from alpaca.trading.requests import GetOrdersRequest
            
            if filter_type == 'open':
                request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            elif filter_type == 'filled':
                request = GetOrdersRequest(status=QueryOrderStatus.CLOSED)
            else:
                request = GetOrdersRequest(status=QueryOrderStatus.ALL)
            
            orders = client.get_orders(filter=request)
            
            if not orders:
                return html.P("No orders found.", className="text-muted")
            
            # Parse date range
            start_dt = pd.to_datetime(start_date) if start_date else None
            end_dt = pd.to_datetime(end_date) if end_date else None
            
            orders_data = []
            for order in orders[:200]:  # Increased limit
                order_dt = pd.to_datetime(order.created_at) if order.created_at else None
                
                # Apply date filter
                if start_dt and order_dt and order_dt < start_dt:
                    continue
                if end_dt and order_dt and order_dt > end_dt + timedelta(days=1):
                    continue
                
                # Calculate estimated slippage and commissions
                filled_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
                limit_price = float(order.limit_price) if order.limit_price else filled_price
                filled_qty = float(order.filled_qty) if order.filled_qty else 0.0
                
                # Estimate slippage (difference from limit price)
                slippage = 0.0
                if filled_price > 0 and limit_price > 0 and filled_qty > 0:
                    if order.side.value == 'buy':
                        slippage = max(0, (filled_price - limit_price) * filled_qty)
                    else:
                        slippage = max(0, (limit_price - filled_price) * filled_qty)
                
                # Commissions (Alpaca is commission-free, but show placeholder)
                commission = 0.0
                
                orders_data.append({
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'qty': float(order.qty) if order.qty is not None else 0.0,
                    'type': order.type.value,
                    'status': order.status.value,
                    'filled_qty': filled_qty,
                    'filled_avg_price': f"${filled_price:.2f}" if filled_price > 0 else "N/A",
                    'slippage': f"${slippage:.2f}",
                    'commission': f"${commission:.2f}",
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else "N/A",
                    'order_id': str(order.id) if order.id else "N/A"
                })
            
            df = pd.DataFrame(orders_data)
            
            if df.empty:
                return html.P("No orders found in selected date range.", className="text-muted")
            
            return dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[
                    {'name': 'Symbol', 'id': 'symbol'},
                    {'name': 'Side', 'id': 'side'},
                    {'name': 'Qty', 'id': 'qty'},
                    {'name': 'Type', 'id': 'type'},
                    {'name': 'Status', 'id': 'status'},
                    {'name': 'Filled Qty', 'id': 'filled_qty'},
                    {'name': 'Avg Price', 'id': 'filled_avg_price'},
                    {'name': 'Slippage', 'id': 'slippage'},
                    {'name': 'Commission', 'id': 'commission'},
                    {'name': 'Created', 'id': 'created_at'}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '13px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{status} = filled'},
                        'backgroundColor': '#d4edda'
                    },
                    {
                        'if': {'filter_query': '{status} = pending_new'},
                        'backgroundColor': '#fff3cd'
                    },
                    {
                        'if': {'column_id': 'side', 'filter_query': '{side} = buy'},
                        'color': '#10b981',
                        'fontWeight': '600'
                    },
                    {
                        'if': {'column_id': 'side', 'filter_query': '{side} = sell'},
                        'color': '#ef4444',
                        'fontWeight': '600'
                    }
                ],
                page_size=25
            )
            
        except Exception as e:
            logger.error(f"Error updating orders table: {e}")
            return html.P(f"Error: {str(e)}", className="text-danger")
    
    
    @app.callback(
        [Output('portfolio-analytics-content', 'children'),
         Output('portfolio-var', 'children'),
         Output('portfolio-cvar', 'children'),
         Output('portfolio-sharpe', 'children'),
         Output('portfolio-beta', 'children')],
        [Input('analytics-period', 'value'),
         Input('portfolio-data-store', 'data')]
    )
    def update_analytics(period, portfolio_data):
        """Update portfolio analytics with risk metrics, correlation heatmap, and equity curve."""
        if not portfolio_data or not portfolio_data.get('positions'):
            empty_content = html.P("No data available for analytics.", className="text-muted")
            return empty_content, "$0.00", "$0.00", "0.00", "1.00"
        
        positions = portfolio_data['positions']
        df = pd.DataFrame(positions)
        
        # Calculate period days
        period_days = {'1d': 1, '1w': 7, '1m': 30, '3m': 90, 'ytd': 252, '1y': 365}.get(period, 30)
        
        # Fetch historical data for portfolio positions and SPY
        try:
            import yfinance as yf
            
            tickers = df['symbol'].tolist()
            weights = (df['market_value'] / df['market_value'].sum()).values
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days + 10)
            
            # Download data
            portfolio_hist = {}
            for ticker in tickers:
                try:
                    data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                    if not data.empty:
                        portfolio_hist[ticker] = data['Close']
                except Exception:
                    pass
            
            # Download SPY for benchmark
            spy_data = yf.download('SPY', start=start_date, end=end_date, progress=False)
            spy_returns = spy_data['Close'].pct_change().dropna() if not spy_data.empty else pd.Series()
            
            # Calculate portfolio equity curve
            if portfolio_hist:
                # Align all series
                portfolio_df = pd.DataFrame(portfolio_hist).ffill().dropna()
                
                if not portfolio_df.empty:
                    # Calculate portfolio returns
                    returns_df = portfolio_df.pct_change().dropna()
                    
                    # Weight returns
                    portfolio_returns = (returns_df * weights).sum(axis=1)
                    
                    # Calculate metrics
                    portfolio_value = portfolio_data['account']['portfolio_value']
                    
                    # VaR (95% confidence)
                    var_95 = np.percentile(portfolio_returns, 5) * portfolio_value
                    
                    # CVaR (Expected Shortfall - average of worst 5%)
                    worst_returns = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)]
                    cvar = worst_returns.mean() * portfolio_value if len(worst_returns) > 0 else var_95
                    
                    # Sharpe Ratio (assuming 0% risk-free rate)
                    sharpe = (portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252)) if portfolio_returns.std() > 0 else 0.0
                    
                    # Beta to SPY
                    if len(spy_returns) > 0 and len(portfolio_returns) > 0:
                        aligned = pd.DataFrame({'portfolio': portfolio_returns, 'spy': spy_returns}).dropna()
                        if len(aligned) > 10:
                            covariance = aligned['portfolio'].cov(aligned['spy'])
                            spy_variance = aligned['spy'].var()
                            beta = covariance / spy_variance if spy_variance > 0 else 1.0
                        else:
                            beta = 1.0
                    else:
                        beta = 1.0
                    
                    # Build equity curve
                    portfolio_equity = (1 + portfolio_returns).cumprod() * 100000  # Normalize to 100k start
                    spy_equity = (1 + spy_returns[-len(portfolio_returns):]).cumprod() * 100000 if len(spy_returns) > 0 else pd.Series()
                    
                    fig_equity = go.Figure()
                    fig_equity.add_trace(go.Scatter(
                        x=portfolio_equity.index,
                        y=portfolio_equity.values,
                        mode='lines',
                        name='Portfolio',
                        line=dict(color='#10b981', width=2)
                    ))
                    if not spy_equity.empty:
                        fig_equity.add_trace(go.Scatter(
                            x=spy_equity.index,
                            y=spy_equity.values,
                            mode='lines',
                            name='SPY Benchmark',
                            line=dict(color='#6366f1', width=2, dash='dash')
                        ))
                    fig_equity.update_layout(
                        title='Portfolio Performance vs SPY',
                        xaxis_title='Date',
                        yaxis_title='Value (Normalized)',
                        template='plotly_white',
                        hovermode='x unified'
                    )
                    
                    # Correlation heatmap (top 10 positions)
                    top_10 = df.nlargest(10, 'market_value')['symbol'].tolist()
                    corr_data = {ticker: portfolio_hist.get(ticker) for ticker in top_10 if ticker in portfolio_hist}
                    if len(corr_data) >= 2:
                        corr_df = pd.DataFrame(corr_data).pct_change().dropna().corr()
                        
                        fig_corr = go.Figure(data=go.Heatmap(
                            z=corr_df.values,
                            x=corr_df.columns,
                            y=corr_df.index,
                            colorscale='RdYlGn',
                            zmid=0,
                            text=corr_df.values.round(2),
                            texttemplate='%{text}',
                            textfont={"size": 10}
                        ))
                        fig_corr.update_layout(
                            title='Correlation Heatmap (Top 10 Positions)',
                            template='plotly_white',
                            height=500
                        )
                    else:
                        fig_corr = go.Figure()
                        fig_corr.add_annotation(text="Insufficient data for correlation analysis", showarrow=False)
                    
                else:
                    var_95, cvar, sharpe, beta = 0.0, 0.0, 0.0, 1.0
                    fig_equity = go.Figure()
                    fig_corr = go.Figure()
            else:
                var_95, cvar, sharpe, beta = 0.0, 0.0, 0.0, 1.0
                fig_equity = go.Figure()
                fig_corr = go.Figure()
        
        except Exception as e:
            logger.error(f"Error calculating advanced analytics: {e}")
            var_95, cvar, sharpe, beta = 0.0, 0.0, 0.0, 1.0
            fig_equity = go.Figure()
            fig_corr = go.Figure()
        
        # Create allocation pie chart
        fig_allocation = px.pie(
            df, 
            values='market_value', 
            names='symbol',
            title='Portfolio Allocation'
        )
        
        # Create P/L bar chart
        fig_pl = go.Figure(data=[
            go.Bar(
                x=df['symbol'],
                y=df['unrealized_pl'],
                marker_color=['#10b981' if x >= 0 else '#ef4444' for x in df['unrealized_pl']]
            )
        ])
        fig_pl.update_layout(
            title='Unrealized P/L by Position',
            xaxis_title='Symbol',
            yaxis_title='Unrealized P/L ($)',
            template='plotly_white'
        )
        
        content = html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_equity)
                ], width=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_allocation)
                ], width=6),
                dbc.Col([
                    dcc.Graph(figure=fig_pl)
                ], width=6)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_corr)
                ], width=12)
            ])
        ])
        
        return content, f"${abs(var_95):,.2f}", f"${abs(cvar):,.2f}", f"{sharpe:.2f}", f"{beta:.2f}"
    
    
    @app.callback(
        Output('portfolio-factor-exposure-content', 'children'),
        [Input('portfolio-data-store', 'data')]
    )
    def update_factor_exposure(portfolio_data):
        """Update factor exposure analysis using SHAP data."""
        if not portfolio_data or not portfolio_data.get('positions'):
            return html.P("No positions available for factor analysis.", className="text-muted")
        
        positions = portfolio_data['positions']
        df = pd.DataFrame(positions)
        
        try:
            # Try to load SHAP data for current positions
            from utils.explain import load_shap_explanations
            
            # Try multiple date patterns
            today = datetime.now()
            shap_data = None
            for days_back in [0, 1, 2, 3, 7]:
                check_date = (today - timedelta(days=days_back)).strftime('%Y%m%d')
                shap_data = load_shap_explanations(check_date)
                if shap_data:
                    break
            
            if not shap_data:
                return html.Div([
                    html.P("SHAP data not available for current positions.", className="text-muted"),
                    html.P("Run the model with SHAP explanations to see factor exposure.", className="text-muted small")
                ])
            
            # Define factor groupings
            factor_groups = {
                'Momentum': ['ret_5d', 'ret_21d', 'ret_63d', 'rsi', 'macd'],
                'Value': ['pb_ratio', 'pe_ratio', 'pcf_ratio', 'dividend_yield'],
                'Quality': ['roe', 'roa', 'debt_equity', 'current_ratio'],
                'Sentiment': ['sentiment_score', 'news_volume', 'social_sentiment'],
                'Growth': ['revenue_growth', 'earnings_growth', 'sales_growth'],
                'Size': ['market_cap', 'volume', 'float_shares']
            }
            
            # Aggregate SHAP values by factor for positions
            position_factors = []
            for ticker in df['symbol'].tolist():
                ticker_upper = ticker.upper()
                if ticker_upper in shap_data:
                    ticker_shap = shap_data[ticker_upper]
                    if isinstance(ticker_shap, dict):
                        factor_totals = {f: 0.0 for f in factor_groups.keys()}
                        top_features = ticker_shap.get('top_features', [])
                        
                        for feat in top_features:
                            feat_name = feat.get('feature', '').lower()
                            feat_value = feat.get('value', 0)
                            
                            for factor_name, feature_list in factor_groups.items():
                                if any(f in feat_name for f in feature_list):
                                    factor_totals[factor_name] += feat_value
                                    break
                        
                        # Get position weight
                        weight = df[df['symbol'] == ticker]['market_value'].values[0] / df['market_value'].sum()
                        
                        for factor_name, factor_val in factor_totals.items():
                            if factor_val != 0:
                                position_factors.append({
                                    'Ticker': ticker,
                                    'Factor': factor_name,
                                    'SHAP Value': factor_val,
                                    'Weighted Contribution': factor_val * weight
                                })
            
            if not position_factors:
                return html.P("No SHAP factor data found for current positions.", className="text-muted")
            
            # Create factor exposure bar chart
            factor_df = pd.DataFrame(position_factors)
            portfolio_factors = factor_df.groupby('Factor')['Weighted Contribution'].sum().reset_index()
            portfolio_factors = portfolio_factors.sort_values('Weighted Contribution', key=abs, ascending=False)
            
            fig_factors = px.bar(
                portfolio_factors,
                x='Factor',
                y='Weighted Contribution',
                title='Portfolio Factor Exposure (SHAP-based)',
                color='Weighted Contribution',
                color_continuous_scale=['#ef4444', '#fbbf24', '#10b981'],
                color_continuous_midpoint=0
            )
            fig_factors.update_layout(template='plotly_white')
            
            # Create per-ticker factor table
            top_factors = factor_df.nlargest(20, 'SHAP Value', keep='all')
            top_factors['SHAP Value'] = top_factors['SHAP Value'].round(4)
            top_factors['Weighted Contribution'] = top_factors['Weighted Contribution'].round(4)
            
            return html.Div([
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure=fig_factors)
                    ], width=12)
                ], className="mb-4"),
                dbc.Row([
                    dbc.Col([
                        html.H6("Top Factor Contributions by Position", className="mb-3"),
                        dash_table.DataTable(
                            data=top_factors.to_dict('records'),
                            columns=[{'name': c, 'id': c} for c in top_factors.columns],
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={'backgroundColor': '#e7f3ff', 'fontWeight': 'bold'},
                            page_size=10,
                            style_data_conditional=[
                                {
                                    'if': {'column_id': 'SHAP Value', 'filter_query': '{SHAP Value} > 0'},
                                    'color': '#10b981',
                                    'fontWeight': '600'
                                },
                                {
                                    'if': {'column_id': 'SHAP Value', 'filter_query': '{SHAP Value} < 0'},
                                    'color': '#ef4444',
                                    'fontWeight': '600'
                                }
                            ]
                        )
                    ], width=12)
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error loading factor exposure: {e}")
            return html.Div([
                html.P(f"Error loading factor exposure: {str(e)}", className="text-danger"),
                html.P("Ensure SHAP explanations are available in the explain/ directory.", className="text-muted small")
            ])
