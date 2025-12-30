"""
ML Forecast Tab - Phase 2 Forecast Engine UI

Provides:
- Signal Strength Gauge
- Predicted Price Path Line Chart
- Regime Classification Badge (Bull/Bear/Crab)
- Smart Hint Integration
- Refresh Forecast Button

Port: 8053 (Alpaca Options Dashboard)
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime


def create_signal_gauge(signal_strength: float = 0, direction: str = "NEUTRAL") -> go.Figure:
    """
    Create Signal Strength Gauge Chart.
    
    Args:
        signal_strength: 0-100 signal strength value
        direction: BULLISH, BEARISH, or NEUTRAL
    """
    # Color based on direction
    if direction == "BULLISH":
        bar_color = "#4caf50"
    elif direction == "BEARISH":
        bar_color = "#f44336"
    else:
        bar_color = "#ff9800"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=signal_strength,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Signal Strength", 'font': {'color': '#fff', 'size': 16}},
        number={'font': {'color': bar_color, 'size': 36}, 'suffix': '%'},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#555', 'tickfont': {'color': '#aaa'}},
            'bar': {'color': bar_color, 'thickness': 0.75},
            'bgcolor': '#2a2a2a',
            'borderwidth': 2,
            'bordercolor': '#444',
            'steps': [
                {'range': [0, 30], 'color': '#1a2d1a'},
                {'range': [30, 70], 'color': '#2d2d1a'},
                {'range': [70, 100], 'color': '#2d1a1a'}
            ],
            'threshold': {
                'line': {'color': bar_color, 'width': 4},
                'thickness': 0.75,
                'value': signal_strength
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#fff'},
        height=220,
        margin=dict(l=30, r=30, t=50, b=30)
    )
    
    return fig


def create_price_path_chart(
    timestamps: list = None,
    price_path: list = None,
    current_price: float = 0,
    target_price: float = 0,
    ticker: str = "SPY"
) -> go.Figure:
    """
    Create Predicted Price Path Line Chart.
    
    Args:
        timestamps: List of date strings
        price_path: List of predicted prices
        current_price: Current stock price
        target_price: Target price at horizon
        ticker: Stock ticker symbol
    """
    if timestamps is None:
        timestamps = ["Day 0", "Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]
    if price_path is None:
        price_path = [100] * len(timestamps)
    
    # Determine color based on direction
    color = "#4caf50" if target_price >= current_price else "#f44336"
    
    fig = go.Figure()
    
    # Add price path line
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=price_path,
        mode='lines+markers',
        name='Predicted Path',
        line=dict(color=color, width=3),
        marker=dict(size=8, color=color),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)'
    ))
    
    # Add current price line
    fig.add_hline(
        y=current_price,
        line_dash="dash",
        line_color="#fff",
        annotation_text=f"Current: ${current_price:.2f}",
        annotation_position="right",
        annotation_font_color="#fff"
    )
    
    # Add target price marker
    fig.add_trace(go.Scatter(
        x=[timestamps[-1]],
        y=[target_price],
        mode='markers+text',
        marker=dict(size=15, color=color, symbol='star'),
        text=[f"${target_price:.2f}"],
        textposition='top center',
        textfont=dict(color=color, size=12),
        name='Target',
        showlegend=False
    ))
    
    fig.update_layout(
        title=dict(
            text=f"📈 {ticker} Price Forecast (7-Day)",
            font=dict(color='#fff', size=14)
        ),
        xaxis=dict(
            title="Date",
            gridcolor='#333',
            tickfont=dict(color='#aaa'),
            titlefont=dict(color='#aaa')
        ),
        yaxis=dict(
            title="Price ($)",
            gridcolor='#333',
            tickfont=dict(color='#aaa'),
            titlefont=dict(color='#aaa'),
            tickprefix='$'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,33,48,0.8)',
        font=dict(color='#fff'),
        height=300,
        margin=dict(l=50, r=30, t=50, b=40),
        showlegend=False
    )
    
    return fig


def create_regime_badge(regime: str = "CRAB") -> dbc.Badge:
    """
    Create Regime Classification Badge.
    
    Args:
        regime: BULL, BEAR, or CRAB
    """
    badge_config = {
        "BULL": {"icon": "🐂", "color": "success", "text": "BULL Market"},
        "BEAR": {"icon": "🐻", "color": "danger", "text": "BEAR Market"},
        "CRAB": {"icon": "🦀", "color": "warning", "text": "CRAB Market (Sideways)"}
    }
    
    config = badge_config.get(regime, badge_config["CRAB"])
    
    return dbc.Badge(
        [html.Span(config["icon"], style={'marginRight': '5px'}), config["text"]],
        color=config["color"],
        className="me-1",
        style={'fontSize': '14px', 'padding': '8px 12px'}
    )


def create_smart_hint_card(hint_data: dict = None) -> html.Div:
    """
    Create Smart Hint Card combining Phase 3 Strategy with Phase 2 ML.
    
    Args:
        hint_data: Dictionary with strategy recommendation
    """
    if hint_data is None:
        hint_data = {
            "recommended_strategy": "Loading...",
            "description": "Click 'Refresh Forecast' to generate recommendation",
            "icon": "💡",
            "color": "#6b7280",
            "confidence": 0,
            "price_direction": "NEUTRAL",
            "vol_regime": "NORMAL"
        }
    
    return html.Div([
        html.Div([
            html.Span(hint_data.get("icon", "💡"), style={'fontSize': '24px', 'marginRight': '10px'}),
            html.Span("Smart Strategy Hint", style={'color': '#00d4ff', 'fontWeight': 'bold', 'fontSize': '16px'})
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.H5(
                hint_data.get("recommended_strategy", "Loading..."),
                style={'color': hint_data.get("color", "#fff"), 'marginBottom': '5px'}
            ),
            html.P(
                hint_data.get("description", ""),
                style={'color': '#9ca3af', 'fontSize': '13px', 'marginBottom': '10px'}
            ),
            html.Div([
                html.Span(f"Direction: {hint_data.get('price_direction', 'N/A')}", 
                         style={'color': '#aaa', 'fontSize': '12px', 'marginRight': '15px'}),
                html.Span(f"IV: {hint_data.get('vol_regime', 'N/A')}", 
                         style={'color': '#aaa', 'fontSize': '12px', 'marginRight': '15px'}),
                html.Span(f"Confidence: {hint_data.get('confidence', 0):.0f}%", 
                         style={'color': '#ff9800', 'fontSize': '12px'})
            ])
        ], style={
            'backgroundColor': '#262a3d',
            'padding': '15px',
            'borderRadius': '8px',
            'borderLeft': f"4px solid {hint_data.get('color', '#666')}"
        })
    ], id='smart-hint-card')


def create_forecast_tab() -> html.Div:
    """
    Create the ML Forecast Tab layout for Port 8053.
    
    Contains:
    - Signal Strength Gauge
    - Predicted Price Path Chart
    - Regime Classification Badge
    - Smart Hint Card
    - Refresh Forecast Button
    - Last Updated Timestamp
    """
    return html.Div([
        # Header
        html.Div([
            html.H4([
                html.Span("🔮 ML Price & Volatility Forecast", style={'marginRight': '10px'}),
                dbc.Badge("Phase 2", color="info", className="me-2"),
                dbc.Badge("LIVE", color="success")
            ], style={'color': '#ffffff', 'marginBottom': '10px'}),
            html.P(
                "AI-powered price direction and volatility predictions with strategy recommendations",
                style={'color': '#888', 'fontSize': '13px', 'marginBottom': '15px'}
            )
        ]),
        
        # Ticker selector and Refresh button row
        html.Div([
            html.Div([
                html.Label("Ticker:", style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '10px'}),
                dcc.Input(
                    id='forecast-ticker-input',
                    type='text',
                    value='SPY',
                    placeholder='Enter ticker...',
                    style={
                        'width': '100px',
                        'backgroundColor': '#2a2d3a',
                        'color': '#fff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px',
                        'marginRight': '15px'
                    }
                ),
                html.Label("Price:", style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '10px'}),
                dcc.Input(
                    id='forecast-price-input',
                    type='number',
                    value=450,
                    placeholder='Current price...',
                    style={
                        'width': '100px',
                        'backgroundColor': '#2a2d3a',
                        'color': '#fff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px',
                        'marginRight': '15px'
                    }
                ),
                dbc.Button(
                    [html.Span("🔄 ", style={'marginRight': '5px'}), "Refresh Forecast"],
                    id='refresh-forecast-btn',
                    color='primary',
                    className='me-2'
                ),
                html.Span(
                    id='forecast-last-updated',
                    children="Last Updated: --",
                    style={'color': '#6b7280', 'fontSize': '12px', 'marginLeft': '15px'}
                )
            ], style={'display': 'flex', 'alignItems': 'center'})
        ], style={'marginBottom': '20px', 'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px'}),
        
        # Main content - Two columns
        html.Div([
            # Left column - Gauge and Regime
            html.Div([
                # Signal Gauge
                html.Div([
                    dcc.Graph(
                        id='gauge-signal',
                        figure=create_signal_gauge(0, "NEUTRAL"),
                        config={'displayModeBar': False}
                    )
                ], style={
                    'backgroundColor': '#1e2130',
                    'padding': '15px',
                    'borderRadius': '8px',
                    'marginBottom': '15px'
                }),
                
                # Regime Badge
                html.Div([
                    html.Div([
                        html.Span("Market Regime: ", style={'color': '#9ca3af', 'marginRight': '10px'}),
                        html.Span(id='badge-regime', children=[create_regime_badge("CRAB")])
                    ])
                ], style={
                    'backgroundColor': '#1e2130',
                    'padding': '15px',
                    'borderRadius': '8px',
                    'marginBottom': '15px',
                    'textAlign': 'center'
                }),
                
                # Prediction Metrics
                html.Div([
                    html.H6("📊 Prediction Metrics", style={'color': '#00d4ff', 'marginBottom': '10px'}),
                    html.Div([
                        html.Div([
                            html.Div("Direction", style={'color': '#6b7280', 'fontSize': '11px'}),
                            html.Div(id='metric-direction', children="NEUTRAL", 
                                    style={'color': '#ff9800', 'fontSize': '18px', 'fontWeight': 'bold'})
                        ], style={'flex': '1', 'textAlign': 'center'}),
                        html.Div([
                            html.Div("Confidence", style={'color': '#6b7280', 'fontSize': '11px'}),
                            html.Div(id='metric-confidence', children="0%", 
                                    style={'color': '#2196F3', 'fontSize': '18px', 'fontWeight': 'bold'})
                        ], style={'flex': '1', 'textAlign': 'center'}),
                        html.Div([
                            html.Div("Change", style={'color': '#6b7280', 'fontSize': '11px'}),
                            html.Div(id='metric-change', children="0%", 
                                    style={'color': '#4caf50', 'fontSize': '18px', 'fontWeight': 'bold'})
                        ], style={'flex': '1', 'textAlign': 'center'})
                    ], style={'display': 'flex'})
                ], style={
                    'backgroundColor': '#1e2130',
                    'padding': '15px',
                    'borderRadius': '8px'
                })
            ], style={'flex': '0.4', 'marginRight': '15px'}),
            
            # Right column - Chart and Smart Hint
            html.Div([
                # Price Path Chart
                html.Div([
                    dcc.Graph(
                        id='chart-prediction',
                        figure=create_price_path_chart(),
                        config={'displayModeBar': False}
                    )
                ], style={
                    'backgroundColor': '#1e2130',
                    'padding': '15px',
                    'borderRadius': '8px',
                    'marginBottom': '15px'
                }),
                
                # Smart Hint Card
                html.Div([
                    html.Div(id='smart-hint-container', children=[create_smart_hint_card()])
                ], style={
                    'backgroundColor': '#1e2130',
                    'padding': '15px',
                    'borderRadius': '8px'
                })
            ], style={'flex': '0.6'})
        ], style={'display': 'flex'}),
        
        # Volatility Section
        html.Div([
            html.H5([
                html.Span("📈 Volatility Forecast", style={'marginRight': '10px'}),
                dbc.Badge("IV Analysis", color="secondary")
            ], style={'color': '#ffffff', 'marginBottom': '15px', 'marginTop': '20px'}),
            
            html.Div([
                html.Div([
                    html.Div("Current IV", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='vol-current-iv', children="--", 
                            style={'color': '#e0e0e0', 'fontSize': '24px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center', 'padding': '15px'}),
                html.Div([
                    html.Div("Forecast IV", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='vol-forecast-iv', children="--", 
                            style={'color': '#9c27b0', 'fontSize': '24px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center', 'padding': '15px'}),
                html.Div([
                    html.Div("IV Rank", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='vol-iv-rank', children="--", 
                            style={'color': '#00bcd4', 'fontSize': '24px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center', 'padding': '15px'}),
                html.Div([
                    html.Div("Vol Regime", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='vol-regime', children="--", 
                            style={'color': '#ff9800', 'fontSize': '24px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center', 'padding': '15px'})
            ], style={
                'display': 'flex',
                'backgroundColor': '#1e2130',
                'borderRadius': '8px'
            })
        ]),
        
        # Store for forecast data
        dcc.Store(id='forecast-data-store', data={})
        
    ], style={'padding': '20px'})
