"""
Limit Order Book (LOB) Visualization Component

Provides real-time order book depth visualization with:
- Bid/Ask depth chart
- Spread indicator
- Order book imbalance metrics
- Microstructure analytics

Reference: Deep-Tech Stack Roadmap Section 3
"""
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LOBLevel:
    """Single price level in the order book"""
    price: float
    quantity: float
    order_count: int = 1


@dataclass
class LOBSnapshot:
    """Complete order book snapshot"""
    symbol: str
    timestamp: str
    bids: List[LOBLevel]
    asks: List[LOBLevel]
    
    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None
    
    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None
    
    @property
    def spread(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None
    
    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None
    
    @property
    def imbalance(self) -> float:
        """Order book imbalance: positive = more bids, negative = more asks"""
        total_bid_qty = sum(l.quantity for l in self.bids[:5])
        total_ask_qty = sum(l.quantity for l in self.asks[:5])
        total = total_bid_qty + total_ask_qty
        if total == 0:
            return 0.0
        return (total_bid_qty - total_ask_qty) / total


def generate_mock_lob_data(symbol: str = "SPY") -> LOBSnapshot:
    """Generate realistic mock LOB data for testing"""
    mid_price = 450.50
    
    # Generate bid levels (descending from mid)
    bids = []
    for i in range(10):
        price = mid_price - 0.01 * (i + 1)
        qty = int(np.random.exponential(500) + 100)
        bids.append(LOBLevel(price=round(price, 2), quantity=qty, order_count=np.random.randint(1, 20)))
    
    # Generate ask levels (ascending from mid)
    asks = []
    for i in range(10):
        price = mid_price + 0.01 * (i + 1)
        qty = int(np.random.exponential(500) + 100)
        asks.append(LOBLevel(price=round(price, 2), quantity=qty, order_count=np.random.randint(1, 20)))
    
    from datetime import datetime
    return LOBSnapshot(
        symbol=symbol,
        timestamp=datetime.now().isoformat(),
        bids=bids,
        asks=asks
    )


def create_lob_depth_chart(snapshot: Optional[LOBSnapshot] = None) -> go.Figure:
    """
    Create a depth chart visualization of the order book.
    
    Shows cumulative bid/ask volume at each price level.
    """
    if snapshot is None:
        snapshot = generate_mock_lob_data()
    
    # Calculate cumulative volumes
    bid_prices = [l.price for l in snapshot.bids]
    bid_volumes = [l.quantity for l in snapshot.bids]
    bid_cumulative = np.cumsum(bid_volumes)
    
    ask_prices = [l.price for l in snapshot.asks]
    ask_volumes = [l.quantity for l in snapshot.asks]
    ask_cumulative = np.cumsum(ask_volumes)
    
    fig = go.Figure()
    
    # Bid depth (green area)
    fig.add_trace(go.Scatter(
        x=bid_prices[::-1],  # Reverse for proper display
        y=bid_cumulative[::-1],
        fill='tozeroy',
        fillcolor='rgba(0, 200, 83, 0.3)',
        line=dict(color='rgb(0, 200, 83)', width=2),
        name='Bids',
        hovertemplate='Price: $%{x:.2f}<br>Cumulative: %{y:,.0f}<extra></extra>'
    ))
    
    # Ask depth (red area)
    fig.add_trace(go.Scatter(
        x=ask_prices,
        y=ask_cumulative,
        fill='tozeroy',
        fillcolor='rgba(255, 82, 82, 0.3)',
        line=dict(color='rgb(255, 82, 82)', width=2),
        name='Asks',
        hovertemplate='Price: $%{x:.2f}<br>Cumulative: %{y:,.0f}<extra></extra>'
    ))
    
    # Mid price line
    if snapshot.mid_price:
        fig.add_vline(
            x=snapshot.mid_price,
            line_dash="dash",
            line_color="yellow",
            annotation_text=f"Mid: ${snapshot.mid_price:.2f}"
        )
    
    fig.update_layout(
        title=dict(text=f"📊 {snapshot.symbol} Order Book Depth", font=dict(size=14)),
        xaxis_title="Price",
        yaxis_title="Cumulative Volume",
        template="plotly_dark",
        height=300,
        margin=dict(l=50, r=30, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    return fig


def create_lob_imbalance_gauge(imbalance: float = 0.0) -> go.Figure:
    """Create a gauge showing order book imbalance"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=imbalance * 100,
        title={'text': "LOB Imbalance", 'font': {'size': 14}},
        delta={'reference': 0, 'position': 'bottom'},
        gauge={
            'axis': {'range': [-100, 100], 'tickwidth': 1},
            'bar': {'color': "rgba(100, 100, 100, 0.8)"},
            'steps': [
                {'range': [-100, -50], 'color': 'rgba(255, 82, 82, 0.5)'},
                {'range': [-50, 0], 'color': 'rgba(255, 82, 82, 0.2)'},
                {'range': [0, 50], 'color': 'rgba(0, 200, 83, 0.2)'},
                {'range': [50, 100], 'color': 'rgba(0, 200, 83, 0.5)'}
            ],
            'threshold': {
                'line': {'color': 'white', 'width': 4},
                'thickness': 0.75,
                'value': imbalance * 100
            }
        },
        number={'suffix': '%', 'font': {'size': 20}}
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=30, r=30, t=50, b=20),
        template="plotly_dark"
    )
    
    return fig


def create_microstructure_metrics(snapshot: Optional[LOBSnapshot] = None) -> html.Div:
    """Create microstructure analytics display"""
    if snapshot is None:
        snapshot = generate_mock_lob_data()
    
    spread = snapshot.spread or 0
    spread_bps = (spread / snapshot.mid_price * 10000) if snapshot.mid_price else 0
    
    metrics = [
        {"label": "Best Bid", "value": f"${snapshot.best_bid:.2f}" if snapshot.best_bid else "N/A", "color": "success"},
        {"label": "Best Ask", "value": f"${snapshot.best_ask:.2f}" if snapshot.best_ask else "N/A", "color": "danger"},
        {"label": "Spread", "value": f"${spread:.4f}", "color": "warning"},
        {"label": "Spread (bps)", "value": f"{spread_bps:.2f}", "color": "info"},
        {"label": "Imbalance", "value": f"{snapshot.imbalance * 100:.1f}%", "color": "primary"},
    ]
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Small(m["label"], className="text-muted"),
                        html.H5(m["value"], className=f"text-{m['color']} mb-0")
                    ], className="p-2 text-center")
                ], className="h-100")
            ], width=True) for m in metrics
        ], className="g-2")
    ])


def create_lob_visualization_card() -> dbc.Card:
    """
    Main LOB visualization component for the dashboard.
    
    Includes:
    - Depth chart
    - Imbalance gauge
    - Microstructure metrics
    """
    snapshot = generate_mock_lob_data()
    
    return dbc.Card([
        dbc.CardHeader([
            html.Span("📈 Limit Order Book", className="fw-bold"),
            html.Small(" | Real-time Microstructure", className="text-muted ms-2"),
            dbc.Badge("LIVE", color="success", className="ms-auto")
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            # Symbol selector
            dbc.Row([
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("Symbol"),
                        dbc.Select(
                            id="lob-symbol-select",
                            options=[
                                {"label": "SPY", "value": "SPY"},
                                {"label": "QQQ", "value": "QQQ"},
                                {"label": "AAPL", "value": "AAPL"},
                                {"label": "TSLA", "value": "TSLA"},
                            ],
                            value="SPY"
                        )
                    ], size="sm")
                ], width=4),
                dbc.Col([
                    html.Div(id="lob-last-update", children=[
                        html.Small("Last: ", className="text-muted"),
                        html.Span(snapshot.timestamp[:19], className="text-info")
                    ])
                ], width=8, className="text-end")
            ], className="mb-3"),
            
            # Depth chart
            dcc.Graph(
                id="lob-depth-chart",
                figure=create_lob_depth_chart(snapshot),
                config={'displayModeBar': False}
            ),
            
            # Microstructure metrics
            html.Div(id="lob-metrics", children=create_microstructure_metrics(snapshot), className="mt-3"),
            
            # Imbalance gauge (smaller)
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id="lob-imbalance-gauge",
                        figure=create_lob_imbalance_gauge(snapshot.imbalance),
                        config={'displayModeBar': False}
                    )
                ], width=6),
                dbc.Col([
                    html.Div([
                        html.H6("Order Flow", className="text-muted"),
                        html.P([
                            "Top 5 Bid Volume: ",
                            html.Strong(f"{sum(l.quantity for l in snapshot.bids[:5]):,}", className="text-success")
                        ], className="mb-1"),
                        html.P([
                            "Top 5 Ask Volume: ",
                            html.Strong(f"{sum(l.quantity for l in snapshot.asks[:5]):,}", className="text-danger")
                        ], className="mb-1"),
                        html.P([
                            "Total Orders: ",
                            html.Strong(f"{sum(l.order_count for l in snapshot.bids + snapshot.asks):,}")
                        ], className="mb-0"),
                    ], className="mt-3")
                ], width=6)
            ])
        ])
    ], className="h-100")


def create_lob_event_feed() -> dbc.Card:
    """Create a live event feed showing LOB updates"""
    return dbc.Card([
        dbc.CardHeader("🔄 LOB Event Feed"),
        dbc.CardBody([
            html.Div(id="lob-event-feed", children=[
                html.Div([
                    html.Small("10:30:45.123", className="text-muted me-2"),
                    dbc.Badge("ADD", color="success", className="me-2"),
                    html.Span("BID $450.45 x 500")
                ], className="mb-1"),
                html.Div([
                    html.Small("10:30:45.125", className="text-muted me-2"),
                    dbc.Badge("CANCEL", color="warning", className="me-2"),
                    html.Span("ASK $450.52 x 200")
                ], className="mb-1"),
                html.Div([
                    html.Small("10:30:45.128", className="text-muted me-2"),
                    dbc.Badge("EXEC", color="info", className="me-2"),
                    html.Span("TRADE $450.50 x 100")
                ], className="mb-1"),
            ], style={"maxHeight": "200px", "overflowY": "auto"})
        ])
    ])
