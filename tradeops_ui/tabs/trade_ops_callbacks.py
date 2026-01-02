"""
Trade Operations Callbacks - Phase 4/5 TradeOps

Wires the Trade Ops UI to the execution and monitoring engines:
- Order submission and cancellation
- Risk violation handling with toast notifications
- Alert feed updates
- Risk settings display
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import dash
from dash import Input, Output, State, callback, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from engines.execution.router import (
    get_order_router,
    OrderStatus,
    ExecutionResult
)
from engines.risk.guard import (
    get_risk_manager,
    RiskViolation,
    OrderRequest
)
from engines.monitor.watchdog import (
    get_watchdog,
    AlertType,
    AlertSeverity
)
from tradeops_ui.components.alerts import create_alert_card

logger = logging.getLogger(__name__)


def register_tradeops_callbacks(app: dash.Dash):
    """Register all Trade Operations callbacks."""
    
    @app.callback(
        [
            Output('tradeops-orders-store', 'data'),
            Output('tradeops-alerts-store', 'data'),
            Output('tradeops-risk-store', 'data'),
            Output('toast-reject', 'is_open'),
            Output('toast-reject', 'children'),
        ],
        [
            Input('btn-test-order', 'n_clicks'),
            Input('btn-test-risk-violation', 'n_clicks'),
            Input('btn-simulate-iv-spike', 'n_clicks'),
            Input('btn-refresh-orders', 'n_clicks'),
            Input('tradeops-refresh-interval', 'n_intervals'),
        ],
        [
            State('test-order-ticker', 'value'),
            State('test-order-qty', 'value'),
            State('test-order-side', 'value'),
            State('tradeops-orders-store', 'data'),
            State('tradeops-alerts-store', 'data'),
        ],
        prevent_initial_call=False
    )
    def handle_tradeops_actions(
        test_order_clicks,
        risk_violation_clicks,
        iv_spike_clicks,
        refresh_clicks,
        n_intervals,
        ticker,
        quantity,
        side,
        current_orders,
        current_alerts
    ):
        """Handle all Trade Ops button clicks and interval updates."""
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Get singletons
        router = get_order_router()
        risk_mgr = get_risk_manager()
        watchdog = get_watchdog()
        
        # Initialize state
        orders = current_orders or []
        alerts = current_alerts or []
        show_toast = False
        toast_message = ""
        
        # Handle test order submission
        if triggered_id == 'btn-test-order' and test_order_clicks:
            ticker = ticker or "SPY"
            quantity = quantity or 10
            side = side or "buy"
            
            result = router.submit_order(
                ticker=ticker,
                side=side,
                quantity=quantity,
                order_type="market",
                is_paper=True
            )
            
            if result.success:
                # Add info alert
                watchdog.add_alert(
                    alert_type=AlertType.ORDER_FILL,
                    severity=AlertSeverity.INFO,
                    title=f"Order Filled: {ticker}",
                    message=f"{side.upper()} {quantity} shares @ ${result.fill_price:.2f}",
                    ticker=ticker,
                    details={"order_id": result.order_id}
                )
            else:
                if result.status == OrderStatus.RISK_REJECTED:
                    show_toast = True
                    toast_message = f"❌ {result.message}"
                    
                    watchdog.add_alert(
                        alert_type=AlertType.ORDER_REJECT,
                        severity=AlertSeverity.WARNING,
                        title=f"Order Rejected: {ticker}",
                        message=result.message,
                        ticker=ticker
                    )
        
        # Handle risk violation test (150 shares > 100 max)
        elif triggered_id == 'btn-test-risk-violation' and risk_violation_clicks:
            ticker = ticker or "SPY"
            
            result = router.submit_order(
                ticker=ticker,
                side="buy",
                quantity=150,  # Exceeds MAX_POSITION_SIZE
                order_type="market",
                is_paper=True
            )
            
            show_toast = True
            toast_message = f"❌ Risk Rejected: Position size 150 exceeds max 100"
            
            watchdog.add_alert(
                alert_type=AlertType.RISK_WARNING,
                severity=AlertSeverity.CRITICAL,
                title="Risk Violation Test",
                message="Order rejected: Position size exceeds maximum allowed",
                ticker=ticker,
                details={"requested": 150, "max_allowed": 100}
            )
        
        # Handle IV spike simulation
        elif triggered_id == 'btn-simulate-iv-spike' and iv_spike_clicks:
            ticker = ticker or "SPY"
            spike_alerts = watchdog.simulate_iv_spike(ticker, iv_increase_pct=60.0)
            
            # The watchdog already created the alert, just refresh
            logger.info(f"Simulated IV spike for {ticker}, {len(spike_alerts)} alerts generated")
        
        # Refresh orders and alerts
        orders = router.get_order_history(limit=20)
        active = router.get_active_orders()
        orders = active + orders
        
        alerts = watchdog.get_alerts(limit=30)
        
        # Get risk settings
        risk_data = risk_mgr.get_risk_limits()
        risk_data.update(risk_mgr.get_portfolio_state())
        
        return orders, alerts, risk_data, show_toast, toast_message
    
    @app.callback(
        Output('table-active-orders', 'children'),
        Input('tradeops-orders-store', 'data'),
        prevent_initial_call=True
    )
    def update_orders_table(orders):
        """Update the orders table from store."""
        from dash import dash_table
        
        if not orders:
            return html.Div([
                html.Span("📭", style={"fontSize": "2rem", "opacity": "0.5"}),
                html.P("No orders", className="text-muted mt-2")
            ], style={"textAlign": "center", "padding": "40px"})
        
        # Format orders for table
        table_data = []
        for order in orders:
            table_data.append({
                "order_id": order.get("order_id", "")[:12],
                "ticker": order.get("ticker", ""),
                "side": order.get("side", ""),
                "quantity": order.get("quantity", 0),
                "order_type": order.get("order_type", ""),
                "price": f"${order.get('fill_price', order.get('price', 0)):.2f}",
                "status": order.get("status", ""),
                "created_at": order.get("created_at", "")[:19] if order.get("created_at") else ""
            })
        
        return dash_table.DataTable(
            id="orders-datatable",
            columns=[
                {"name": "Order ID", "id": "order_id"},
                {"name": "Ticker", "id": "ticker"},
                {"name": "Side", "id": "side"},
                {"name": "Qty", "id": "quantity"},
                {"name": "Type", "id": "order_type"},
                {"name": "Price", "id": "price"},
                {"name": "Status", "id": "status"},
                {"name": "Time", "id": "created_at"},
            ],
            data=table_data,
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#2a2d3a",
                "color": "#fff",
                "fontWeight": "bold",
                "border": "1px solid #333"
            },
            style_cell={
                "backgroundColor": "#1e2130",
                "color": "#ddd",
                "border": "1px solid #333",
                "textAlign": "left",
                "padding": "8px",
                "fontSize": "13px"
            },
            style_data_conditional=[
                {
                    "if": {"filter_query": "{side} = buy"},
                    "color": "#4caf50"
                },
                {
                    "if": {"filter_query": "{side} = sell"},
                    "color": "#f44336"
                },
                {
                    "if": {"filter_query": "{status} = filled"},
                    "backgroundColor": "rgba(76, 175, 80, 0.2)"
                },
                {
                    "if": {"filter_query": "{status} = risk_rejected"},
                    "backgroundColor": "rgba(244, 67, 54, 0.2)"
                }
            ],
            row_selectable="single",
            selected_rows=[],
            page_size=10,
        )
    
    @app.callback(
        Output('feed-alerts', 'children'),
        Input('tradeops-alerts-store', 'data'),
        prevent_initial_call=True
    )
    def update_alerts_feed(alerts):
        """Update the alerts feed from store."""
        if not alerts:
            return html.Div([
                html.Span("📭", style={"fontSize": "2rem", "opacity": "0.5"}),
                html.P("No alerts", className="text-muted mt-2")
            ], style={"textAlign": "center", "padding": "40px"})
        
        return [create_alert_card(alert) for alert in alerts]
    
    @app.callback(
        [
            Output('risk-max-drawdown', 'children'),
            Output('risk-max-position', 'children'),
            Output('risk-max-notional', 'children'),
            Output('risk-daily-loss', 'children'),
            Output('risk-max-positions', 'children'),
            Output('current-pnl', 'children'),
            Output('current-pnl', 'style'),
            Output('current-drawdown', 'children'),
            Output('current-drawdown', 'style'),
        ],
        Input('tradeops-risk-store', 'data'),
        prevent_initial_call=True
    )
    def update_risk_display(risk_data):
        """Update risk settings display from store."""
        if not risk_data:
            return no_update
        
        max_dd = f"{risk_data.get('max_drawdown_pct', 5.0):.1f}%"
        max_pos = f"{risk_data.get('max_position_size', 100)} shares"
        max_notional = f"${risk_data.get('max_position_notional', 50000):,.0f}"
        daily_loss = f"${risk_data.get('daily_loss_limit', 1000):,.0f}"
        max_positions = str(risk_data.get('max_open_positions', 10))
        
        pnl = risk_data.get('daily_pnl', 0)
        pnl_str = f"${pnl:+,.2f}"
        pnl_color = "#4caf50" if pnl >= 0 else "#f44336"
        pnl_style = {"color": pnl_color, "fontSize": "18px", "fontWeight": "bold"}
        
        dd = risk_data.get('current_drawdown_pct', 0)
        dd_str = f"{dd:.1f}%"
        dd_color = "#4caf50" if dd < 2 else ("#ff9800" if dd < 4 else "#f44336")
        dd_style = {"color": dd_color, "fontSize": "18px", "fontWeight": "bold"}
        
        return max_dd, max_pos, max_notional, daily_loss, max_positions, pnl_str, pnl_style, dd_str, dd_style
    
    @app.callback(
        Output('btn-cancel-order', 'disabled'),
        Input('orders-datatable', 'selected_rows'),
        prevent_initial_call=True
    )
    def toggle_cancel_button(selected_rows):
        """Enable/disable cancel button based on selection."""
        return not bool(selected_rows)
    
    @app.callback(
        Output('tradeops-orders-store', 'data', allow_duplicate=True),
        Input('btn-cancel-order', 'n_clicks'),
        [
            State('orders-datatable', 'selected_rows'),
            State('orders-datatable', 'data'),
        ],
        prevent_initial_call=True
    )
    def cancel_selected_order(n_clicks, selected_rows, table_data):
        """Cancel the selected order."""
        if not n_clicks or not selected_rows or not table_data:
            raise PreventUpdate
        
        row_idx = selected_rows[0]
        if row_idx >= len(table_data):
            raise PreventUpdate
        
        order_id = table_data[row_idx].get("order_id", "")
        
        router = get_order_router()
        # Find full order ID from prefix
        full_id = None
        for oid in router.orders:
            if oid.startswith(order_id) or order_id in oid:
                full_id = oid
                break
        
        if full_id:
            result = router.cancel_order(full_id)
            logger.info(f"Cancel order result: {result.message}")
        
        # Return updated orders
        return router.get_order_history(limit=20) + router.get_active_orders()
