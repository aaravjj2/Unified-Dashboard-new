"""
Trade Operations Tab - Phase 4/5 TradeOps Dashboard

Main UI for trade operations:
- Top Panel: Active Orders Table with Cancel buttons
- Bottom Panel: Live Alerts Feed (color-coded)
- Sidebar: Risk Settings (read-only view)
"""

from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from typing import List, Dict, Any, Optional
import sys
import os

# Import Week 2 enhancements
try:
    from src.ui.components.buttons import create_button
except ImportError:
    try:
        # Try importing with package prefix if src is not top-level
        from alpaca_options_lab.src.ui.components.buttons import create_button
    except ImportError:
        def create_button(button_id, text, **kwargs):
            # Convert variant to color for dbc.Button compatibility
            if 'variant' in kwargs:
                kwargs['color'] = kwargs.pop('variant')
            # Remove unsupported kwargs
            for unsupported in ['full_width', 'loading', 'tooltip']:
                kwargs.pop(unsupported, None)
            return dbc.Button(text, id=button_id, **kwargs)

from tradeops_ui.components.alerts import create_alerts_feed


def create_orders_table(orders: Optional[List[Dict[str, Any]]] = None) -> html.Div:
    """
    Create Active Orders Table with Cancel button per row.
    
    Args:
        orders: List of order dictionaries
        
    Returns:
        Div containing the orders table
    """
    if not orders:
        orders = []
    
    return html.Div([
        # Header
        html.Div([
            html.H5([
                html.Span("📋 ", style={"marginRight": "8px"}),
                "Active Orders"
            ], style={"margin": "0", "color": "#fff"}),
            html.Div([
                dbc.Badge(
                    f"{len(orders)} active",
                    color="primary" if orders else "secondary",
                    pill=True,
                    className="me-2"
                ),
                create_button(
                    button_id="btn-refresh-orders",
                    text=[html.Span("🔄 ", style={"marginRight": "5px"}), "Refresh"],
                    variant="secondary",
                    size="sm"
                )
            ], style={"display": "flex", "alignItems": "center"})
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "15px",
            "paddingBottom": "10px",
            "borderBottom": "1px solid #333"
        }),
        
        # Orders table
        html.Div(
            id="table-active-orders",
            children=[
                dash_table.DataTable(
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
                    data=orders,
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
            ] if orders else [
                html.Div([
                    html.Span("📭", style={"fontSize": "2rem", "opacity": "0.5"}),
                    html.P("No active orders", className="text-muted mt-2")
                ], style={"textAlign": "center", "padding": "40px"})
            ]
        ),
        
        # Cancel button
        html.Div([
            create_button(
                button_id="btn-cancel-order",
                text=[html.Span("❌ ", style={"marginRight": "5px"}), "Cancel Selected"],
                variant="danger",
                size="sm",
                disabled=True,
                className="me-2"
            ),
            create_button(
                button_id="btn-cancel-all",
                text=[html.Span("🗑️ ", style={"marginRight": "5px"}), "Cancel All"],
                variant="danger",
                size="sm"
            )
        ], style={"marginTop": "15px", "display": "flex"})
        
    ], style={
        "backgroundColor": "#1e2130",
        "padding": "15px",
        "borderRadius": "8px"
    })


def create_risk_settings_panel() -> html.Div:
    """
    Create Risk Settings sidebar (read-only view).
    
    Returns:
        Div containing risk settings display
    """
    return html.Div([
        # Header
        html.H5([
            html.Span("🛡️ ", style={"marginRight": "8px"}),
            "Risk Settings"
        ], style={"marginBottom": "15px", "color": "#fff"}),
        
        # Settings list
        html.Div([
            # Max Drawdown
            html.Div([
                html.Div("Max Drawdown", style={"color": "#9ca3af", "fontSize": "11px"}),
                html.Div(
                    id="risk-max-drawdown",
                    children="5.0%",
                    style={"color": "#f44336", "fontSize": "18px", "fontWeight": "bold"}
                )
            ], style={"marginBottom": "15px"}),
            
            # Max Position Size
            html.Div([
                html.Div("Max Position Size", style={"color": "#9ca3af", "fontSize": "11px"}),
                html.Div(
                    id="risk-max-position",
                    children="100 shares",
                    style={"color": "#ff9800", "fontSize": "18px", "fontWeight": "bold"}
                )
            ], style={"marginBottom": "15px"}),
            
            # Max Position Notional
            html.Div([
                html.Div("Max Notional", style={"color": "#9ca3af", "fontSize": "11px"}),
                html.Div(
                    id="risk-max-notional",
                    children="$50,000",
                    style={"color": "#ff9800", "fontSize": "18px", "fontWeight": "bold"}
                )
            ], style={"marginBottom": "15px"}),
            
            # Daily Loss Limit
            html.Div([
                html.Div("Daily Loss Limit", style={"color": "#9ca3af", "fontSize": "11px"}),
                html.Div(
                    id="risk-daily-loss",
                    children="$1,000",
                    style={"color": "#f44336", "fontSize": "18px", "fontWeight": "bold"}
                )
            ], style={"marginBottom": "15px"}),
            
            # Max Open Positions
            html.Div([
                html.Div("Max Positions", style={"color": "#9ca3af", "fontSize": "11px"}),
                html.Div(
                    id="risk-max-positions",
                    children="10",
                    style={"color": "#2196F3", "fontSize": "18px", "fontWeight": "bold"}
                )
            ], style={"marginBottom": "15px"}),
            
            # Restricted Tickers
            html.Div([
                html.Div("Restricted Tickers", style={"color": "#9ca3af", "fontSize": "11px", "marginBottom": "5px"}),
                html.Div(
                    id="risk-restricted",
                    children=[
                        dbc.Badge("GME", color="danger", className="me-1 mb-1"),
                        dbc.Badge("AMC", color="danger", className="me-1 mb-1"),
                        dbc.Badge("UVXY", color="danger", className="me-1 mb-1"),
                        dbc.Badge("TQQQ", color="danger", className="me-1 mb-1"),
                    ]
                )
            ])
        ]),
        
        # Status indicators
        html.Hr(style={"borderColor": "#333", "margin": "20px 0"}),
        
        html.Div([
            html.Div([
                html.Div("Trading Mode", style={"color": "#9ca3af", "fontSize": "11px"}),
                dbc.Badge(
                    id="trading-mode-badge",
                    children="📝 PAPER",
                    color="info",
                    className="mt-1"
                )
            ], style={"marginBottom": "15px"}),
            
            html.Div([
                html.Div("Current P&L", style={"color": "#9ca3af", "fontSize": "11px"}),
                html.Div(
                    id="current-pnl",
                    children="$0.00",
                    style={"color": "#4caf50", "fontSize": "18px", "fontWeight": "bold"}
                )
            ], style={"marginBottom": "15px"}),
            
            html.Div([
                html.Div("Drawdown", style={"color": "#9ca3af", "fontSize": "11px"}),
                html.Div(
                    id="current-drawdown",
                    children="0.0%",
                    style={"color": "#4caf50", "fontSize": "18px", "fontWeight": "bold"}
                )
            ])
        ])
        
    ], style={
        "backgroundColor": "#1e2130",
        "padding": "15px",
        "borderRadius": "8px",
        "height": "100%"
    })


def create_test_order_panel() -> html.Div:
    """
    Create Test Order Panel for simulating orders and risk violations.
    
    Returns:
        Div containing test order controls
    """
    return html.Div([
        html.H6([
            html.Span("🧪 ", style={"marginRight": "8px"}),
            "Test Order"
        ], style={"marginBottom": "15px", "color": "#00d4ff"}),
        
        # Ticker input
        html.Div([
            html.Label("Ticker", style={"color": "#9ca3af", "fontSize": "11px"}),
            dcc.Input(
                id="test-order-ticker",
                type="text",
                value="SPY",
                style={
                    "width": "100%",
                    "backgroundColor": "#2a2d3a",
                    "color": "#fff",
                    "border": "1px solid #444",
                    "borderRadius": "4px",
                    "padding": "8px"
                }
            )
        ], style={"marginBottom": "10px"}),
        
        # Quantity input
        html.Div([
            html.Label("Quantity", style={"color": "#9ca3af", "fontSize": "11px"}),
            dcc.Input(
                id="test-order-qty",
                type="number",
                value=10,
                min=1,
                style={
                    "width": "100%",
                    "backgroundColor": "#2a2d3a",
                    "color": "#fff",
                    "border": "1px solid #444",
                    "borderRadius": "4px",
                    "padding": "8px"
                }
            )
        ], style={"marginBottom": "10px"}),
        
        # Side selector
        html.Div([
            html.Label("Side", style={"color": "#9ca3af", "fontSize": "11px"}),
            dcc.Dropdown(
                id="test-order-side",
                options=[
                    {"label": "Buy", "value": "buy"},
                    {"label": "Sell", "value": "sell"}
                ],
                value="buy",
                style={"backgroundColor": "#2a2d3a"},
                className="dash-dropdown-dark"
            )
        ], style={"marginBottom": "15px"}),
        
        # Submit button
        create_button(
            button_id="btn-test-order",
            text=[html.Span("📤 ", style={"marginRight": "5px"}), "Submit Test Order"],
            variant="primary",
            full_width=True,
            className="mb-2"
        ),
        
        # Risk violation test
        create_button(
            button_id="btn-test-risk-violation",
            text=[html.Span("⚠️ ", style={"marginRight": "5px"}), "Test Risk Violation (150 shares)"],
            variant="secondary",
            full_width=True,
            className="mb-2"
        ),
        
        # IV Spike simulation
        dbc.Button(
            [html.Span("🔥 ", style={"marginRight": "5px"}), "Simulate IV Spike"],
            id="btn-simulate-iv-spike",
            color="danger",
            outline=True,
            className="w-100"
        )
        
    ], style={
        "backgroundColor": "#1e2130",
        "padding": "15px",
        "borderRadius": "8px",
        "marginBottom": "15px"
    })


def create_trade_ops_tab() -> html.Div:
    """
    Create the full Trade Operations Tab.
    
    Layout:
    - Top: Active Orders Table
    - Bottom Left: Live Alerts Feed
    - Right Sidebar: Risk Settings + Test Panel
    
    Returns:
        Complete Trade Ops tab layout
    """
    return html.Div([
        # Toast notification for risk rejections
        dbc.Toast(
            id="toast-reject",
            header="Risk Rejection",
            icon="danger",
            is_open=False,
            dismissable=True,
            duration=6000,
            style={
                "position": "fixed",
                "top": 66,
                "right": 10,
                "width": 350,
                "zIndex": 9999
            }
        ),
        
        # Data stores
        dcc.Store(id="tradeops-orders-store", data=[]),
        dcc.Store(id="tradeops-alerts-store", data=[]),
        dcc.Store(id="tradeops-risk-store", data={}),
        dcc.Interval(id="tradeops-refresh-interval", interval=5000, n_intervals=0),
        
        # Header
        html.Div([
            html.H4([
                html.Span("⚙️ Trade Operations", style={"marginRight": "10px"}),
                dbc.Badge("Phase 4/5", color="info", className="me-2"),
                dbc.Badge("PAPER", id="mode-badge-header", color="secondary")
            ], style={"color": "#ffffff", "marginBottom": "10px"}),
            html.P(
                "Order execution, risk management, and real-time monitoring",
                style={"color": "#888", "fontSize": "13px", "marginBottom": "15px"}
            )
        ]),
        
        # Main layout: 3 columns
        dbc.Row([
            # Left column: Orders + Alerts (2/3 width)
            dbc.Col([
                # Active Orders Table
                html.Div([
                    create_orders_table([])
                ], style={"marginBottom": "15px"}),
                
                # Live Alerts Feed
                create_alerts_feed([])
                
            ], md=8),
            
            # Right sidebar: Risk Settings + Test Panel (1/3 width)
            dbc.Col([
                # Test Order Panel
                create_test_order_panel(),
                
                # Risk Settings
                create_risk_settings_panel()
                
            ], md=4)
        ])
        
    ], style={
        "padding": "20px",
        "backgroundColor": "#0d1117",
        "minHeight": "800px"
    })
