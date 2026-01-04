"""
Event Queue Monitor Component

Visualizes the event-driven architecture event flow:
- MarketEvent → SignalEvent → OrderEvent → FillEvent
- Real-time event queue display
- Event statistics and throughput

Reference: Deep-Tech Stack Roadmap Section 2
"""
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import random


class EventType(Enum):
    """Event types in the trading system"""
    MARKET = "market"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"
    CANCEL = "cancel"
    EXPIRY = "expiry"
    RISK = "risk"


@dataclass
class TradingEvent:
    """Single event in the event queue"""
    id: str
    event_type: EventType
    timestamp: datetime
    symbol: str
    data: Dict
    processed: bool = False


def get_event_color(event_type: EventType) -> str:
    """Get color for event type"""
    colors = {
        EventType.MARKET: "#17a2b8",
        EventType.SIGNAL: "#ffc107",
        EventType.ORDER: "#0d6efd",
        EventType.FILL: "#28a745",
        EventType.CANCEL: "#dc3545",
        EventType.EXPIRY: "#6f42c1",
        EventType.RISK: "#fd7e14"
    }
    return colors.get(event_type, "#6c757d")


def get_event_icon(event_type: EventType) -> str:
    """Get icon for event type"""
    icons = {
        EventType.MARKET: "📊",
        EventType.SIGNAL: "📡",
        EventType.ORDER: "📝",
        EventType.FILL: "✅",
        EventType.CANCEL: "❌",
        EventType.EXPIRY: "⏰",
        EventType.RISK: "⚠️"
    }
    return icons.get(event_type, "❓")


def generate_mock_events(count: int = 20) -> List[TradingEvent]:
    """Generate mock events for demo"""
    events = []
    base_time = datetime.now()
    
    for i in range(count):
        event_type = random.choice(list(EventType))
        symbol = random.choice(["SPY", "AAPL", "TSLA", "QQQ"])
        
        data = {}
        if event_type == EventType.MARKET:
            data = {"price": round(random.uniform(100, 500), 2), "volume": random.randint(1000, 10000)}
        elif event_type == EventType.SIGNAL:
            data = {"direction": random.choice(["LONG", "SHORT"]), "confidence": round(random.uniform(0.5, 1.0), 2)}
        elif event_type == EventType.ORDER:
            data = {"side": random.choice(["BUY", "SELL"]), "qty": random.randint(1, 100), "price": round(random.uniform(100, 500), 2)}
        elif event_type == EventType.FILL:
            data = {"fill_price": round(random.uniform(100, 500), 2), "qty": random.randint(1, 100)}
        
        events.append(TradingEvent(
            id=f"evt_{i:04d}",
            event_type=event_type,
            timestamp=base_time,
            symbol=symbol,
            data=data,
            processed=i < count - 5
        ))
    
    return events


def create_event_flow_diagram() -> go.Figure:
    """Create a Sankey diagram showing event flow"""
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=["Market Data", "Signal Gen", "Risk Check", "Order Mgmt", "Execution", "Fill/Cancel"],
            color=["#17a2b8", "#ffc107", "#fd7e14", "#0d6efd", "#6f42c1", "#28a745"]
        ),
        link=dict(
            source=[0, 1, 1, 2, 3, 3],
            target=[1, 2, 3, 3, 4, 5],
            value=[100, 80, 20, 75, 70, 5],
            color=["rgba(23,162,184,0.4)", "rgba(255,193,7,0.4)", "rgba(255,193,7,0.4)",
                   "rgba(253,126,20,0.4)", "rgba(13,110,253,0.4)", "rgba(13,110,253,0.4)"]
        )
    )])
    
    fig.update_layout(
        title="Event Flow Pipeline",
        template="plotly_dark",
        height=200,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_event_throughput_chart(events: List[TradingEvent] = None) -> go.Figure:
    """Create throughput chart by event type"""
    if events is None:
        events = generate_mock_events(50)
    
    # Count by type
    counts = {}
    for event in events:
        counts[event.event_type.value] = counts.get(event.event_type.value, 0) + 1
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(counts.keys()),
            y=list(counts.values()),
            marker_color=[get_event_color(EventType(k)) for k in counts.keys()],
            text=list(counts.values()),
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Event Count by Type",
        template="plotly_dark",
        height=200,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis_title="Event Type",
        yaxis_title="Count"
    )
    
    return fig


def create_event_queue_display(events: List[TradingEvent] = None) -> html.Div:
    """Create scrollable event queue display"""
    if events is None:
        events = generate_mock_events(15)
    
    return html.Div([
        html.Div([
            html.Div([
                html.Span(get_event_icon(e.event_type), className="me-2"),
                dbc.Badge(
                    e.event_type.value.upper(),
                    style={"backgroundColor": get_event_color(e.event_type)},
                    className="me-2"
                ),
                html.Span(e.symbol, className="fw-bold me-2"),
                html.Small(str(e.data)[:50], className="text-muted"),
                dbc.Badge(
                    "✓" if e.processed else "⏳",
                    color="success" if e.processed else "warning",
                    className="ms-auto"
                )
            ], className="d-flex align-items-center p-2 mb-1 rounded",
               style={"backgroundColor": "rgba(255,255,255,0.05)"})
        for e in events[-10:]])
    ], id="event-queue-list", style={"maxHeight": "300px", "overflowY": "auto"})


def create_event_stats_row(events: List[TradingEvent] = None) -> dbc.Row:
    """Create event statistics row"""
    if events is None:
        events = generate_mock_events(100)
    
    total = len(events)
    processed = sum(1 for e in events if e.processed)
    pending = total - processed
    
    stats = [
        {"label": "Total Events", "value": total, "color": "primary"},
        {"label": "Processed", "value": processed, "color": "success"},
        {"label": "Pending", "value": pending, "color": "warning"},
        {"label": "Events/sec", "value": f"{random.randint(100, 500)}", "color": "info"},
    ]
    
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Small(s["label"], className="text-muted"),
                    html.H4(s["value"], className=f"text-{s['color']} mb-0")
                ], className="text-center p-2")
            ])
        ], width=3) for s in stats
    ], className="mb-3")


def create_event_queue_card() -> dbc.Card:
    """
    Main event queue visualization component.
    """
    events = generate_mock_events(30)
    
    return dbc.Card([
        dbc.CardHeader([
            html.Span("📨 Event Queue Monitor", className="fw-bold"),
            html.Small(" | Event-Driven Architecture", className="text-muted ms-2"),
            dbc.Badge(f"{len(events)} events", color="info", className="ms-auto")
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            # Stats row
            create_event_stats_row(events),
            
            # Flow diagram
            dcc.Graph(
                id="event-flow-diagram",
                figure=create_event_flow_diagram(),
                config={'displayModeBar': False}
            ),
            
            # Event queue
            html.H6("Live Event Queue", className="mt-3 mb-2"),
            create_event_queue_display(events),
            
            # Throughput chart
            dcc.Graph(
                id="event-throughput-chart",
                figure=create_event_throughput_chart(events),
                config={'displayModeBar': False}
            )
        ])
    ])


def create_event_type_legend() -> html.Div:
    """Create event type legend"""
    return html.Div([
        html.Small("Event Types:", className="text-muted me-3"),
        html.Span([
            dbc.Badge(
                f"{get_event_icon(et)} {et.value}",
                style={"backgroundColor": get_event_color(et)},
                className="me-1"
            )
        for et in EventType])
    ], className="mb-2")


def create_event_filter_controls() -> dbc.Card:
    """Create event filtering controls"""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Filter by Type"),
                    dbc.Checklist(
                        id="event-type-filter",
                        options=[
                            {"label": f"{get_event_icon(et)} {et.value}", "value": et.value}
                            for et in EventType
                        ],
                        value=[et.value for et in EventType],
                        inline=True
                    )
                ], width=8),
                dbc.Col([
                    dbc.Label("Filter by Symbol"),
                    dbc.Select(
                        id="event-symbol-filter",
                        options=[
                            {"label": "All Symbols", "value": "all"},
                            {"label": "SPY", "value": "SPY"},
                            {"label": "AAPL", "value": "AAPL"},
                            {"label": "TSLA", "value": "TSLA"},
                        ],
                        value="all"
                    )
                ], width=4)
            ])
        ], className="py-2")
    ], className="mb-2")
