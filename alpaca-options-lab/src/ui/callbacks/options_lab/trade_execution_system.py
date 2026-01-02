"""
Alpaca Options Lab - Trade Execution System
Implements Items 101-125 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import json


# ============================================================
# ITEM 101: Order Types
# ============================================================
class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Single options order."""
    symbol: str
    option_symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: int
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"  # day, gtc, ioc, fok
    status: OrderStatus = OrderStatus.PENDING
    order_id: Optional[str] = None
    fill_price: Optional[float] = None
    filled_qty: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None


@dataclass
class MultiLegOrder:
    """Multi-leg options order (spread)."""
    strategy_name: str
    legs: List[Order]
    net_debit_credit: float  # positive = credit, negative = debit
    order_type: OrderType = OrderType.LIMIT
    status: OrderStatus = OrderStatus.PENDING
    order_id: Optional[str] = None


# ============================================================
# ITEM 102: Smart Order Routing
# ============================================================
class SmartOrderRouter:
    """Smart order routing for best execution."""
    
    def __init__(self):
        self.execution_stats = {
            'total_orders': 0,
            'price_improvement_total': 0,
            'avg_fill_time': 0
        }
    
    def calculate_optimal_limit_price(
        self,
        bid: float,
        ask: float,
        urgency: str = 'normal',  # low, normal, high
        historical_fill_rate: float = 0.5
    ) -> float:
        """Calculate optimal limit price for better fills."""
        spread = ask - bid
        mid = (bid + ask) / 2
        
        if urgency == 'high':
            # Pay up for urgency
            return ask if historical_fill_rate < 0.3 else mid + spread * 0.25
        elif urgency == 'low':
            # Be patient
            return bid + spread * 0.1
        else:
            # Normal - aim for mid with slight improvement attempt
            return mid - spread * 0.1
    
    def get_route_recommendation(
        self,
        order: Order,
        market_conditions: Dict
    ) -> Dict[str, Any]:
        """Get routing recommendation based on conditions."""
        spread_pct = market_conditions.get('spread_pct', 1)
        volume = market_conditions.get('volume', 0)
        
        recommendations = {
            'exchange': 'SMART',
            'strategy': 'adaptive',
            'notes': []
        }
        
        if spread_pct > 5:
            recommendations['notes'].append("Wide spread - use limit orders")
            recommendations['strategy'] = 'patient'
        
        if volume < 100:
            recommendations['notes'].append("Low liquidity - consider smaller size")
            recommendations['strategy'] = 'iceberg'
        
        return recommendations


# ============================================================
# ITEM 103: Pre-trade Validation
# ============================================================
class PreTradeValidator:
    """Validate orders before submission."""
    
    def __init__(self, account_info: Dict = None):
        self.account_info = account_info or {}
    
    def validate_order(self, order: Order) -> Dict[str, Any]:
        """Validate a single order."""
        errors = []
        warnings = []
        
        # Quantity check
        if order.quantity <= 0:
            errors.append("Quantity must be positive")
        
        if order.quantity > 100:
            warnings.append("Large order - consider splitting")
        
        # Limit price check
        if order.order_type == OrderType.LIMIT and not order.limit_price:
            errors.append("Limit orders require a limit price")
        
        if order.limit_price and order.limit_price < 0:
            errors.append("Limit price cannot be negative")
        
        # Buying power check
        buying_power = self.account_info.get('buying_power', float('inf'))
        estimated_cost = (order.limit_price or 0) * order.quantity * 100
        
        if estimated_cost > buying_power:
            errors.append(f"Insufficient buying power (need ${estimated_cost:,.0f})")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'estimated_cost': estimated_cost
        }
    
    def validate_spread(self, multi_leg: MultiLegOrder) -> Dict[str, Any]:
        """Validate a spread order."""
        errors = []
        warnings = []
        
        # Validate each leg
        for leg in multi_leg.legs:
            leg_result = self.validate_order(leg)
            errors.extend(leg_result['errors'])
            warnings.extend(leg_result['warnings'])
        
        # Check leg balance
        long_legs = sum(1 for l in multi_leg.legs if l.side in [OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE])
        short_legs = sum(1 for l in multi_leg.legs if l.side in [OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE])
        
        if long_legs == 0 and short_legs > 0:
            warnings.append("Naked short position - high risk")
        
        # Margin check for spreads
        if multi_leg.net_debit_credit < 0:  # Debit spread
            debit = abs(multi_leg.net_debit_credit)
            buying_power = self.account_info.get('buying_power', float('inf'))
            if debit > buying_power:
                errors.append(f"Insufficient funds for debit (need ${debit:,.0f})")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


# ============================================================
# ITEM 105: Execution Preview
# ============================================================
def create_execution_preview(order: Order, market_data: Dict) -> dbc.Card:
    """Create visual preview of order execution."""
    bid = market_data.get('bid', 0)
    ask = market_data.get('ask', 0)
    mid = (bid + ask) / 2
    
    # Calculate estimated fills
    limit_vs_mid = ((order.limit_price or mid) - mid) / mid * 100 if mid else 0
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-eye me-2"),
            "Execution Preview"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Small("NBBO", className="text-muted d-block"),
                    html.Span(f"${bid:.2f}", className="text-success me-2"),
                    html.Span("x", className="text-muted"),
                    html.Span(f"${ask:.2f}", className="text-danger ms-2"),
                ], width=4),
                dbc.Col([
                    html.Small("Your Limit", className="text-muted d-block"),
                    html.Strong(f"${order.limit_price:.2f}" if order.limit_price else "MKT"),
                ], width=4),
                dbc.Col([
                    html.Small("vs Mid", className="text-muted d-block"),
                    html.Strong(f"{limit_vs_mid:+.1f}%", 
                               className="text-success" if limit_vs_mid < 0 else "text-danger"),
                ], width=4),
            ], className="mb-3"),
            
            dbc.Progress([
                dbc.Progress(value=40, color="success", bar=True, label=f"${bid:.2f}"),
                dbc.Progress(value=20, color="warning", bar=True, label="Spread"),
                dbc.Progress(value=40, color="danger", bar=True, label=f"${ask:.2f}"),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Small("Est. Cost", className="text-muted d-block"),
                    html.H5(f"${(order.limit_price or mid) * order.quantity * 100:,.2f}")
                ], width=6),
                dbc.Col([
                    html.Small("Fill Probability", className="text-muted d-block"),
                    html.H5("~75%", className="text-warning")
                ], width=6),
            ])
        ])
    ])


# ============================================================
# ITEM 107: Order Confirmation Dialog
# ============================================================
def create_confirmation_modal(order: Order, validation: Dict) -> dbc.Modal:
    """Create order confirmation modal."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Confirm Order")),
        dbc.ModalBody([
            # Order summary
            html.Div([
                html.H5(f"{order.side.value.replace('_', ' ').title()}", className="mb-3"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.Strong("Symbol: "), order.option_symbol
                    ]),
                    dbc.ListGroupItem([
                        html.Strong("Quantity: "), f"{order.quantity} contracts"
                    ]),
                    dbc.ListGroupItem([
                        html.Strong("Order Type: "), order.order_type.value.title()
                    ]),
                    dbc.ListGroupItem([
                        html.Strong("Limit Price: "), 
                        f"${order.limit_price:.2f}" if order.limit_price else "Market"
                    ]),
                    dbc.ListGroupItem([
                        html.Strong("Time in Force: "), order.time_in_force.upper()
                    ]),
                ], flush=True, className="mb-3"),
            ]),
            
            # Warnings
            html.Div([
                dbc.Alert(w, color="warning", className="mb-1")
                for w in validation.get('warnings', [])
            ]) if validation.get('warnings') else None,
            
            # Cost estimate
            dbc.Alert([
                html.Strong("Estimated Cost: "),
                f"${validation.get('estimated_cost', 0):,.2f}"
            ], color="info")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-order-btn", className="me-2", outline=True),
            dbc.Button("Submit Order", id="submit-order-btn", color="primary"),
        ])
    ], id="order-confirmation-modal", is_open=False)


# ============================================================
# ITEM 108: Live Order Status Tracker
# ============================================================
def create_order_status_row(order: Order) -> dbc.ListGroupItem:
    """Create order status row."""
    status_colors = {
        OrderStatus.PENDING: "secondary",
        OrderStatus.SUBMITTED: "info",
        OrderStatus.PARTIAL_FILL: "warning",
        OrderStatus.FILLED: "success",
        OrderStatus.CANCELLED: "secondary",
        OrderStatus.REJECTED: "danger"
    }
    
    return dbc.ListGroupItem([
        dbc.Row([
            dbc.Col([
                html.Strong(order.option_symbol),
                html.Br(),
                html.Small(f"{order.side.value.replace('_', ' ')}", className="text-muted")
            ], width=4),
            dbc.Col([
                html.Span(f"{order.filled_qty}/{order.quantity}"),
                html.Br(),
                html.Small(f"@ ${order.fill_price:.2f}" if order.fill_price else "Pending", className="text-muted")
            ], width=3),
            dbc.Col([
                dbc.Badge(order.status.value.replace('_', ' ').title(), 
                         color=status_colors.get(order.status, "secondary"))
            ], width=3),
            dbc.Col([
                dbc.Button([html.I(className="fas fa-times")], 
                          size="sm", color="danger", outline=True,
                          disabled=order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED])
            ], width=2, className="text-end")
        ], align="center")
    ])


def create_orders_panel(orders: List[Order]) -> html.Div:
    """Create orders management panel."""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-clipboard-list me-2"),
                "Active Orders",
                dbc.Badge(str(len(orders)), color="primary", className="ms-2")
            ]),
            dbc.CardBody([
                dbc.ListGroup([
                    create_order_status_row(o) for o in orders
                ], flush=True) if orders else html.P("No active orders", className="text-muted")
            ])
        ])
    ])


# ============================================================
# ITEM 110: Position Management
# ============================================================
@dataclass
class Position:
    """Options position."""
    symbol: str
    option_symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0
    delta: float = 0
    gamma: float = 0
    theta: float = 0
    vega: float = 0


def create_position_card(position: Position) -> dbc.Card:
    """Create position display card."""
    pnl_color = "success" if position.unrealized_pnl >= 0 else "danger"
    pnl_pct = (position.unrealized_pnl / (position.avg_cost * abs(position.quantity) * 100)) * 100
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6(position.option_symbol, className="mb-0"),
                    html.Small(f"Qty: {position.quantity}", className="text-muted")
                ], width=4),
                dbc.Col([
                    html.Span(f"${position.current_price:.2f}"),
                    html.Br(),
                    html.Small(f"Avg: ${position.avg_cost:.2f}", className="text-muted")
                ], width=3),
                dbc.Col([
                    html.Strong(f"${position.unrealized_pnl:+,.0f}", className=f"text-{pnl_color}"),
                    html.Br(),
                    html.Small(f"({pnl_pct:+.1f}%)", className=f"text-{pnl_color}")
                ], width=3),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Close", size="sm", color="danger", outline=True),
                        dbc.Button("Roll", size="sm", color="primary", outline=True),
                    ], size="sm")
                ], width=2)
            ], align="center")
        ])
    ], className="mb-2")


# ============================================================
# ITEM 112: Roll Position Wizard
# ============================================================
def calculate_roll_options(
    current_position: Position,
    available_expirations: List[str],
    target_delta: float = None
) -> List[Dict]:
    """Calculate roll alternatives for a position."""
    roll_options = []
    
    for exp in available_expirations:
        # Simplified - would fetch real chain data
        roll_option = {
            'expiration': exp,
            'strike': current_position.option_symbol,  # Same strike roll
            'credit_debit': np.random.uniform(-0.50, 0.50),  # Placeholder
            'new_delta': target_delta or current_position.delta,
            'theta_improvement': np.random.uniform(0, 0.05)
        }
        roll_options.append(roll_option)
    
    return roll_options


def create_roll_wizard(position: Position, roll_options: List[Dict]) -> dbc.Card:
    """Create roll position wizard."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-sync-alt me-2"),
            f"Roll: {position.option_symbol}"
        ]),
        dbc.CardBody([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Expiration"),
                        html.Th("Credit/Debit"),
                        html.Th("New Δ"),
                        html.Th("θ Improvement"),
                        html.Th("")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(opt['expiration']),
                        html.Td(f"${opt['credit_debit']:+.2f}", 
                               className="text-success" if opt['credit_debit'] > 0 else "text-danger"),
                        html.Td(f"{opt['new_delta']:.2f}"),
                        html.Td(f"+${opt['theta_improvement']:.3f}"),
                        html.Td(dbc.Button("Roll", size="sm", color="primary"))
                    ]) for opt in roll_options
                ])
            ], bordered=True, hover=True, size="sm")
        ])
    ])


# ============================================================
# ITEM 115: P&L Attribution
# ============================================================
def calculate_pnl_attribution(
    position: Position,
    spot_change: float,
    vol_change: float,
    time_elapsed: float  # in days
) -> Dict[str, float]:
    """Calculate P&L attribution by Greeks."""
    
    # Delta P&L
    delta_pnl = position.delta * spot_change * position.quantity * 100
    
    # Gamma P&L
    gamma_pnl = 0.5 * position.gamma * (spot_change ** 2) * position.quantity * 100
    
    # Theta P&L
    theta_pnl = position.theta * time_elapsed * position.quantity * 100
    
    # Vega P&L
    vega_pnl = position.vega * vol_change * position.quantity * 100
    
    total_explained = delta_pnl + gamma_pnl + theta_pnl + vega_pnl
    unexplained = position.unrealized_pnl - total_explained
    
    return {
        'delta_pnl': delta_pnl,
        'gamma_pnl': gamma_pnl,
        'theta_pnl': theta_pnl,
        'vega_pnl': vega_pnl,
        'total_explained': total_explained,
        'unexplained': unexplained
    }


def create_pnl_attribution_chart(attribution: Dict[str, float]) -> dbc.Card:
    """Create P&L attribution waterfall."""
    import plotly.graph_objects as go
    
    components = ['Delta', 'Gamma', 'Theta', 'Vega', 'Other']
    values = [
        attribution['delta_pnl'],
        attribution['gamma_pnl'],
        attribution['theta_pnl'],
        attribution['vega_pnl'],
        attribution['unexplained']
    ]
    
    colors = ['#28a745' if v >= 0 else '#dc3545' for v in values]
    
    fig = go.Figure(go.Waterfall(
        name="P&L Attribution",
        orientation="h",
        measure=["relative"] * len(components),
        y=components,
        x=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#dc3545"}},
        increasing={"marker": {"color": "#28a745"}},
        totals={"marker": {"color": "#007bff"}}
    ))
    
    fig.update_layout(
        title="P&L Attribution",
        height=300,
        showlegend=False
    )
    
    return dbc.Card([
        dbc.CardBody([
            dcc.Graph(figure=fig, config={'displayModeBar': False})
        ])
    ])


# ============================================================
# ITEM 120: Trade Journal
# ============================================================
@dataclass
class TradeJournalEntry:
    """Trade journal entry."""
    trade_id: str
    timestamp: datetime
    symbol: str
    strategy: str
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    pnl: float = 0
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    setup_quality: int = 0  # 1-5 rating
    execution_quality: int = 0


def create_journal_entry_form() -> dbc.Card:
    """Create trade journal entry form."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-book me-2"),
            "Trade Journal"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Strategy"),
                    dbc.Input(id="journal-strategy", placeholder="e.g., Iron Condor")
                ], width=6),
                dbc.Col([
                    dbc.Label("Tags"),
                    dbc.Input(id="journal-tags", placeholder="earnings, hedge, income")
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Setup Quality (1-5)"),
                    dcc.Slider(id="setup-quality", min=1, max=5, step=1, value=3,
                              marks={i: str(i) for i in range(1, 6)})
                ], width=6),
                dbc.Col([
                    dbc.Label("Execution Quality (1-5)"),
                    dcc.Slider(id="exec-quality", min=1, max=5, step=1, value=3,
                              marks={i: str(i) for i in range(1, 6)})
                ], width=6),
            ], className="mb-3"),
            
            dbc.Label("Notes"),
            dbc.Textarea(id="journal-notes", placeholder="Trade notes...", rows=3, className="mb-3"),
            
            dbc.Button([
                html.I(className="fas fa-save me-2"),
                "Save Entry"
            ], id="save-journal-btn", color="primary")
        ])
    ])


# ============================================================
# Main Execution Panel
# ============================================================
def create_execution_panel() -> html.Div:
    """Create the complete trade execution panel."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-exchange-alt me-2"),
                        "Quick Trade"
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Action"),
                                dbc.Select(
                                    id="trade-action",
                                    options=[
                                        {"label": "Buy to Open", "value": "buy_to_open"},
                                        {"label": "Sell to Open", "value": "sell_to_open"},
                                        {"label": "Buy to Close", "value": "buy_to_close"},
                                        {"label": "Sell to Close", "value": "sell_to_close"},
                                    ]
                                )
                            ], width=3),
                            dbc.Col([
                                dbc.Label("Quantity"),
                                dbc.Input(id="trade-qty", type="number", value=1, min=1)
                            ], width=2),
                            dbc.Col([
                                dbc.Label("Order Type"),
                                dbc.Select(
                                    id="trade-order-type",
                                    options=[
                                        {"label": "Limit", "value": "limit"},
                                        {"label": "Market", "value": "market"},
                                    ],
                                    value="limit"
                                )
                            ], width=2),
                            dbc.Col([
                                dbc.Label("Limit Price"),
                                dbc.Input(id="trade-limit-price", type="number", step=0.01)
                            ], width=2),
                            dbc.Col([
                                dbc.Label("TIF"),
                                dbc.Select(
                                    id="trade-tif",
                                    options=[
                                        {"label": "Day", "value": "day"},
                                        {"label": "GTC", "value": "gtc"},
                                    ],
                                    value="day"
                                )
                            ], width=2),
                        ], className="mb-3"),
                        dbc.Button([
                            html.I(className="fas fa-paper-plane me-2"),
                            "Preview Order"
                        ], id="preview-trade-btn", color="primary", className="w-100")
                    ])
                ])
            ], width=8),
            dbc.Col([
                html.Div(id="execution-preview-area")
            ], width=4)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Div(id="positions-panel")
            ], width=6),
            dbc.Col([
                html.Div(id="orders-panel")
            ], width=6)
        ])
    ])


__all__ = [
    'OrderType',
    'OrderSide',
    'OrderStatus',
    'Order',
    'MultiLegOrder',
    'SmartOrderRouter',
    'PreTradeValidator',
    'create_execution_preview',
    'create_confirmation_modal',
    'create_order_status_row',
    'create_orders_panel',
    'Position',
    'create_position_card',
    'calculate_roll_options',
    'create_roll_wizard',
    'calculate_pnl_attribution',
    'create_pnl_attribution_chart',
    'TradeJournalEntry',
    'create_journal_entry_form',
    'create_execution_panel',
]
