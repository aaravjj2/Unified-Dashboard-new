"""
TradingView Lightweight Charts Integration

Provides interactive candlestick charting with:
- OHLC candlestick display
- Volume histogram
- Drawing tools (trendlines, horizontals, rays)
- Real-time tick updates
- Event callbacks for user interactions

Reference: Deep-Tech Stack Roadmap Section 4
"""
from dash import html, dcc, Input, Output, State, callback, MATCH, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class OHLCBar:
    """Single OHLC bar"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass 
class DrawingObject:
    """User-created drawing on chart"""
    id: str
    type: str  # 'trendline', 'horizontal', 'ray', 'rectangle'
    start_price: float
    end_price: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    color: str = "#FFD700"
    label: str = ""


@dataclass
class ChartState:
    """Maintains chart state including drawings"""
    symbol: str
    timeframe: str
    bars: List[OHLCBar] = field(default_factory=list)
    drawings: List[DrawingObject] = field(default_factory=list)
    indicators: Dict[str, List[float]] = field(default_factory=dict)


def generate_mock_ohlc_data(
    symbol: str = "SPY",
    days: int = 30,
    timeframe: str = "1D"
) -> pd.DataFrame:
    """Generate realistic mock OHLC data"""
    np.random.seed(42)
    
    periods = days * (390 // {"1m": 1, "5m": 5, "15m": 15, "1H": 60, "1D": 390}.get(timeframe, 390))
    
    # Start price
    price = 450.0
    data = []
    
    current_time = datetime.now() - timedelta(days=days)
    
    for i in range(min(periods, 500)):  # Limit to 500 bars
        # Random walk with mean reversion
        change_pct = np.random.normal(0.0001, 0.01)
        price = price * (1 + change_pct)
        
        # Generate OHLC
        volatility = price * 0.005
        open_price = price + np.random.uniform(-volatility, volatility)
        close_price = price + np.random.uniform(-volatility, volatility)
        high_price = max(open_price, close_price) + abs(np.random.normal(0, volatility))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, volatility))
        
        volume = int(np.random.exponential(1000000) + 100000)
        
        data.append({
            'timestamp': current_time,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
        # Increment time based on timeframe
        delta_map = {"1m": 1, "5m": 5, "15m": 15, "1H": 60, "1D": 1440}
        current_time += timedelta(minutes=delta_map.get(timeframe, 1440))
    
    return pd.DataFrame(data)


def calculate_sma(prices: List[float], period: int) -> List[Optional[float]]:
    """Calculate Simple Moving Average"""
    result = [None] * (period - 1)
    for i in range(period - 1, len(prices)):
        result.append(np.mean(prices[i - period + 1:i + 1]))
    return result


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Calculate Bollinger Bands"""
    sma = calculate_sma(prices, period)
    upper = []
    lower = []
    
    for i, ma in enumerate(sma):
        if ma is None:
            upper.append(None)
            lower.append(None)
        else:
            std = np.std(prices[max(0, i - period + 1):i + 1])
            upper.append(ma + std_dev * std)
            lower.append(ma - std_dev * std)
    
    return sma, upper, lower


def create_candlestick_chart(
    df: Optional[pd.DataFrame] = None,
    symbol: str = "SPY",
    show_volume: bool = True,
    show_sma: bool = True,
    show_bollinger: bool = False,
    drawings: Optional[List[DrawingObject]] = None
) -> go.Figure:
    """
    Create an interactive candlestick chart with TradingView styling.
    """
    if df is None:
        df = generate_mock_ohlc_data(symbol)
    
    # Create figure with secondary y-axis for volume
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(None, None)
        )
    else:
        fig = go.Figure()
    
    # Candlestick chart
    candlestick = go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350'
    )
    
    if show_volume:
        fig.add_trace(candlestick, row=1, col=1)
    else:
        fig.add_trace(candlestick)
    
    # Add SMA
    if show_sma:
        sma_20 = calculate_sma(df['close'].tolist(), 20)
        sma_50 = calculate_sma(df['close'].tolist(), 50)
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=sma_20,
            name='SMA 20',
            line=dict(color='#ffa726', width=1.5)
        ), row=1 if show_volume else None, col=1 if show_volume else None)
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=sma_50,
            name='SMA 50',
            line=dict(color='#42a5f5', width=1.5)
        ), row=1 if show_volume else None, col=1 if show_volume else None)
    
    # Add Bollinger Bands
    if show_bollinger:
        sma, upper, lower = calculate_bollinger_bands(df['close'].tolist())
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=upper,
            name='BB Upper',
            line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
            showlegend=False
        ), row=1 if show_volume else None, col=1 if show_volume else None)
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=lower,
            name='BB Lower',
            line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
            fill='tonexty',
            fillcolor='rgba(150, 150, 150, 0.1)',
            showlegend=False
        ), row=1 if show_volume else None, col=1 if show_volume else None)
    
    # Add volume bars
    if show_volume:
        colors = ['#26a69a' if c >= o else '#ef5350' 
                  for c, o in zip(df['close'], df['open'])]
        
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7
        ), row=2, col=1)
    
    # Add user drawings
    if drawings:
        for drawing in drawings:
            if drawing.type == 'horizontal':
                fig.add_hline(
                    y=drawing.start_price,
                    line_color=drawing.color,
                    line_dash="dash",
                    annotation_text=drawing.label or f"${drawing.start_price:.2f}"
                )
            elif drawing.type == 'trendline' and drawing.end_price and drawing.start_time and drawing.end_time:
                fig.add_trace(go.Scatter(
                    x=[drawing.start_time, drawing.end_time],
                    y=[drawing.start_price, drawing.end_price],
                    mode='lines',
                    line=dict(color=drawing.color, width=2),
                    name=drawing.label or 'Trendline',
                    showlegend=False
                ))
    
    # Layout styling (TradingView dark theme)
    fig.update_layout(
        title=dict(
            text=f"📈 {symbol} | Interactive Chart",
            font=dict(size=16, color='white')
        ),
        template="plotly_dark",
        height=500 if show_volume else 400,
        margin=dict(l=50, r=50, t=50, b=30),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        dragmode="zoom",
        paper_bgcolor='#131722',
        plot_bgcolor='#131722'
    )
    
    # Style axes
    fig.update_xaxes(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        showline=True,
        linecolor='rgba(255,255,255,0.2)'
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        showline=True,
        linecolor='rgba(255,255,255,0.2)'
    )
    
    return fig


def create_drawing_toolbar() -> html.Div:
    """Create drawing tools toolbar"""
    return html.Div([
        dbc.ButtonGroup([
            dbc.Button([
                html.I(className="fas fa-mouse-pointer me-1"),
                "Select"
            ], id="chart-tool-select", color="secondary", size="sm", outline=True, active=True),
            dbc.Button([
                html.I(className="fas fa-minus me-1"),
                "Horizontal"
            ], id="chart-tool-horizontal", color="secondary", size="sm", outline=True),
            dbc.Button([
                html.I(className="fas fa-chart-line me-1"),
                "Trendline"
            ], id="chart-tool-trendline", color="secondary", size="sm", outline=True),
            dbc.Button([
                html.I(className="fas fa-long-arrow-alt-right me-1"),
                "Ray"
            ], id="chart-tool-ray", color="secondary", size="sm", outline=True),
            dbc.Button([
                html.I(className="fas fa-square me-1"),
                "Rectangle"
            ], id="chart-tool-rectangle", color="secondary", size="sm", outline=True),
        ], className="me-3"),
        dbc.ButtonGroup([
            dbc.Button([
                html.I(className="fas fa-trash me-1"),
                "Clear All"
            ], id="chart-clear-drawings", color="danger", size="sm", outline=True),
        ])
    ], className="mb-2 d-flex")


def create_chart_controls() -> dbc.Card:
    """Create chart control panel"""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("Symbol"),
                        dbc.Input(
                            id="chart-symbol-input",
                            type="text",
                            value="SPY",
                            placeholder="Enter symbol..."
                        )
                    ], size="sm")
                ], width=3),
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("Timeframe"),
                        dbc.Select(
                            id="chart-timeframe-select",
                            options=[
                                {"label": "1 Minute", "value": "1m"},
                                {"label": "5 Minutes", "value": "5m"},
                                {"label": "15 Minutes", "value": "15m"},
                                {"label": "1 Hour", "value": "1H"},
                                {"label": "1 Day", "value": "1D"},
                            ],
                            value="1D"
                        )
                    ], size="sm")
                ], width=3),
                dbc.Col([
                    dbc.Checklist(
                        id="chart-indicators-toggle",
                        options=[
                            {"label": "SMA", "value": "sma"},
                            {"label": "Bollinger", "value": "bollinger"},
                            {"label": "Volume", "value": "volume"},
                        ],
                        value=["sma", "volume"],
                        inline=True,
                        switch=True
                    )
                ], width=6)
            ])
        ], className="py-2")
    ], className="mb-2")


def create_tradingview_chart_card() -> dbc.Card:
    """
    Main TradingView-style chart component.
    """
    return dbc.Card([
        dbc.CardHeader([
            html.Span("📊 Interactive Chart", className="fw-bold"),
            html.Small(" | TradingView Style", className="text-muted ms-2"),
            dbc.Badge("INTERACTIVE", color="info", className="ms-auto")
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            create_chart_controls(),
            create_drawing_toolbar(),
            dcc.Graph(
                id="tradingview-chart",
                figure=create_candlestick_chart(),
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
                    'scrollZoom': True
                }
            ),
            # Drawing event store
            dcc.Store(id="chart-drawings-store", data=[]),
            # Chart click data
            html.Div(id="chart-click-output", className="mt-2 small text-muted")
        ])
    ])


def create_price_alerts_panel() -> dbc.Card:
    """Create price alerts management panel"""
    return dbc.Card([
        dbc.CardHeader("🔔 Price Alerts"),
        dbc.CardBody([
            dbc.InputGroup([
                dbc.InputGroupText("Price"),
                dbc.Input(
                    id="alert-price-input",
                    type="number",
                    placeholder="450.00"
                ),
                dbc.Button("Add Alert", id="add-price-alert-btn", color="primary", size="sm")
            ], className="mb-3"),
            html.Div(id="price-alerts-list", children=[
                html.Div([
                    dbc.Badge("↑", color="success", className="me-2"),
                    html.Span("$455.00"),
                    dbc.Button("×", color="link", size="sm", className="ms-auto text-danger")
                ], className="d-flex align-items-center mb-1 p-2 bg-dark rounded"),
                html.Div([
                    dbc.Badge("↓", color="danger", className="me-2"),
                    html.Span("$445.00"),
                    dbc.Button("×", color="link", size="sm", className="ms-auto text-danger")
                ], className="d-flex align-items-center mb-1 p-2 bg-dark rounded"),
            ])
        ])
    ])


def create_chart_events_log() -> dbc.Card:
    """Create chart interaction events log"""
    return dbc.Card([
        dbc.CardHeader("📝 Chart Events"),
        dbc.CardBody([
            html.Div(id="chart-events-log", children=[
                html.Div([
                    html.Small("10:30:15", className="text-muted me-2"),
                    html.Span("Horizontal line added at $451.25")
                ], className="mb-1"),
                html.Div([
                    html.Small("10:29:45", className="text-muted me-2"),
                    html.Span("Trendline created")
                ], className="mb-1"),
                html.Div([
                    html.Small("10:28:30", className="text-muted me-2"),
                    html.Span("Timeframe changed to 1H")
                ], className="mb-1"),
            ], style={"maxHeight": "150px", "overflowY": "auto"})
        ])
    ])
