"""
Portfolio Orders Tab - Order History with Date Filtering
Part of refactored Portfolio Tracker module
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from dash import dcc, html, Input, Output, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def get_alpaca_client():
    """Get Alpaca trading client from environment."""
    try:
        # Load environment variables from keys.env if not already in os.environ
        keys_env_path = os.path.join(os.path.dirname(__file__), '..', 'keys.env')
        if os.path.exists(keys_env_path):
            with open(keys_env_path) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key_name, key_value = line.split('=', 1)
                        if key_name.strip() and key_value.strip():
                            os.environ.setdefault(key_name.strip(), key_value.strip())
        
        from alpaca.trading.client import TradingClient
        
        key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
        secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
        if not key or not secret:
            logger.warning("Alpaca API keys not found in environment")
            return None
        
        # Default to paper trading
        paper = True
        return TradingClient(key, secret, paper=paper)
    except ImportError as e:
        logger.warning(f"Alpaca SDK not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"Alpaca client initialization failed: {e}")
        return None


def layout():
    """Build orders tab layout with date filtering."""
    return dbc.Container([
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


def register_callbacks(app):
    """Register callbacks for orders tab."""
    
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
                
                # FIX: Make ALL datetimes timezone-naive for proper comparison
                if order_dt is not None:
                    if hasattr(order_dt, 'tz') and order_dt.tz is not None:
                        order_dt = order_dt.tz_localize(None)
                
                # Ensure comparison dates are also timezone-naive
                safe_start_dt = start_dt
                safe_end_dt = end_dt
                if safe_start_dt is not None and hasattr(safe_start_dt, 'tz') and safe_start_dt.tz is not None:
                    safe_start_dt = safe_start_dt.tz_localize(None)
                if safe_end_dt is not None and hasattr(safe_end_dt, 'tz') and safe_end_dt.tz is not None:
                    safe_end_dt = safe_end_dt.tz_localize(None)
                
                # Apply date filter
                if safe_start_dt is not None and order_dt and order_dt < safe_start_dt:
                    continue
                if safe_end_dt is not None and order_dt and order_dt > safe_end_dt + timedelta(days=1):
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
