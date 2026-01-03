"""
Consolidated Workspace Layouts
Phase 15+ - Enhanced Agent-UX with Professional Alpaca Theme

Defines 4 main workspace layouts:
1. Scanner: Market Viz (GEX/Vol) + Flow Tape + Pattern Feed
2. Strategy: Chain + Builder + AI Forecasts  
3. Command: Positions + Trade Ops (Risk/Execution)
4. Admin: Status + Research

These replace the 12 individual tabs with 4 consolidated workspaces.
Enhanced with professional trading terminal aesthetics.
"""

import logging
import sys
import os
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from typing import Optional, Dict, Any, List
import numpy as np
from datetime import datetime

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Week 2 enhancements
try:
    from src.ui.components.loading_states import (
        inject_loading_css,
        create_skeleton_card,
        create_skeleton_gauge,
        create_loading_spinner,
    )
    from src.ui.components.tooltips import (
        create_tooltip,
        create_rich_tooltip,
        create_greeks_tooltip,
    )
    from src.ui.components.buttons import (
        create_button,
        inject_button_css,
        create_icon_button,
    )
    ENHANCEMENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Week 2 enhancements not available: {e}")
    ENHANCEMENTS_AVAILABLE = False
    # Fallback implementations
    def inject_loading_css():
        return html.Style("")
    def inject_button_css():
        return html.Style("")
    def create_button(button_id, text, **kwargs):
        return dbc.Button(text, id=button_id)
    def create_skeleton_card(**kwargs):
        return html.Div("Loading...", style={"padding": "20px"})
    def create_skeleton_gauge():
        return html.Div("Loading gauge...", style={"padding": "20px"})
    def create_loading_spinner(**kwargs):
        return dbc.Spinner()
    def create_tooltip(target_id, content, **kwargs):
        return dbc.Tooltip(content, target=target_id)
    def create_rich_tooltip(target_id, title, description, **kwargs):
        return dbc.Tooltip(f"{title}: {description}", target=target_id)
    def create_greeks_tooltip(target_id, greek_name, value, interpretation):
        return dbc.Tooltip(f"{greek_name}: {interpretation}", target=target_id)
    def create_icon_button(button_id, icon, **kwargs):
        return dbc.Button(icon, id=button_id, size="sm")

logger = logging.getLogger(__name__)

# =============================================================================
# PROFESSIONAL ALPACA THEME - Design Tokens
# =============================================================================

ALPACA_DARK = {
    # Brand Colors
    "gold": "#F5C211",
    "gold_light": "#FFD54F",
    "gold_dark": "#C9A000",
    
    # Background Hierarchy (GitHub Dark-inspired)
    "bg": "#0D1117",           # Deepest background
    "paper": "#161B22",        # Card backgrounds  
    "bg_tertiary": "#21262D",  # Input/hover backgrounds
    "bg_elevated": "#30363D",  # Elevated elements
    
    # Legacy aliases
    "accent": "#F5C211",
    "positive": "#3FB950",
    "negative": "#F85149",
    "text": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#6E7681",
    "grid": "#30363D",
    
    # Semantic Colors
    "success": "#3FB950",
    "danger": "#F85149",
    "warning": "#D29922",
    "info": "#58A6FF",
    
    # Borders
    "border": "#30363D",
    "border_muted": "#21262D",
}

# =============================================================================
# ENHANCED COMPONENT STYLES
# =============================================================================

CARD_STYLE = {
    "backgroundColor": ALPACA_DARK["paper"],
    "border": f"1px solid {ALPACA_DARK['border']}",
    "borderRadius": "12px",
    "padding": "20px",
    "marginBottom": "16px",
}

CARD_ACCENT_STYLE = {
    "backgroundColor": ALPACA_DARK["paper"],
    "border": f"2px solid {ALPACA_DARK['gold']}",
    "borderRadius": "12px",
    "padding": "20px",
    "marginBottom": "16px",
    "boxShadow": "0 0 20px rgba(245, 194, 17, 0.1)",
}

HEADER_STYLE = {
    "color": ALPACA_DARK["text"],
    "fontSize": "16px",
    "fontWeight": "600",
    "marginBottom": "16px",
    "paddingBottom": "8px",
    "borderBottom": f"2px solid {ALPACA_DARK['gold']}",
    "display": "flex",
    "alignItems": "center",
    "gap": "8px",
}

METRIC_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(4, 1fr)",
    "gap": "12px",
    "marginBottom": "20px",
}

METRIC_CARD_STYLE = {
    "backgroundColor": ALPACA_DARK["bg_tertiary"],
    "borderRadius": "8px",
    "padding": "16px",
    "textAlign": "center",
    "border": f"1px solid {ALPACA_DARK['border_muted']}",
    "transition": "all 0.2s ease",
}

TAB_STYLE = {
    "backgroundColor": ALPACA_DARK["bg"],
    "color": ALPACA_DARK["text_secondary"],
    "border": "none",
    "padding": "10px 24px",
    "fontWeight": "500",
}

TAB_SELECTED_STYLE = {
    "backgroundColor": ALPACA_DARK["bg_tertiary"],
    "color": ALPACA_DARK["gold"],
    "border": "none",
    "borderBottom": f"3px solid {ALPACA_DARK['gold']}",
    "padding": "10px 24px",
    "fontWeight": "600",
}


# =============================================================================
# REUSABLE UI COMPONENTS
# =============================================================================

def create_workspace_header(
    title: str,
    icon: str,
    badges: List[Dict[str, str]] = None,
    subtitle: str = None
) -> html.Div:
    """Create a consistent workspace header with icon, title, and badges."""
    badge_elements = []
    if badges:
        for b in badges:
            badge_elements.append(
                dbc.Badge(
                    b.get("text", ""),
                    color=b.get("color", "secondary"),
                    className="me-1",
                    style={"fontSize": "11px", "fontWeight": "600"}
                )
            )
    
    return html.Div([
        html.Div([
            html.Span(icon, style={"fontSize": "32px", "marginRight": "16px"}),
            html.Div([
                html.H3(
                    title,
                    style={
                        "color": ALPACA_DARK["text"],
                        "margin": "0",
                        "fontWeight": "700",
                        "fontSize": "26px",
                        "letterSpacing": "-0.5px",
                    }
                ),
                html.Span(
                    subtitle,
                    style={"color": ALPACA_DARK["text_muted"], "fontSize": "13px"}
                ) if subtitle else None,
            ]),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div(badge_elements, style={"display": "flex", "alignItems": "center", "gap": "4px"}),
    ], style={
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "marginBottom": "24px",
        "paddingBottom": "16px",
        "borderBottom": f"1px solid {ALPACA_DARK['border']}",
    })


def create_metric_card(
    label: str,
    value: str,
    sublabel: str = None,
    color: str = None,
    icon: str = None
) -> html.Div:
    """Create an enhanced metric display card."""
    value_color = {
        "success": ALPACA_DARK["success"],
        "danger": ALPACA_DARK["danger"],
        "warning": ALPACA_DARK["warning"],
        "info": ALPACA_DARK["info"],
        "gold": ALPACA_DARK["gold"],
        "positive": ALPACA_DARK["positive"],
        "negative": ALPACA_DARK["negative"],
    }.get(color, ALPACA_DARK["text"])
    
    return html.Div([
        html.Div([
            html.Span(icon, style={"marginRight": "4px"}) if icon else None,
            html.Span(label),
        ], style={
            "fontSize": "11px",
            "color": ALPACA_DARK["text_muted"],
            "textTransform": "uppercase",
            "letterSpacing": "0.5px",
            "marginBottom": "6px",
        }),
        html.Div(
            value,
            style={
                "fontSize": "26px",
                "fontWeight": "700",
                "fontFamily": "'JetBrains Mono', 'SF Mono', monospace",
                "color": value_color,
                "lineHeight": "1.2",
            }
        ),
        html.Div(
            sublabel,
            style={
                "fontSize": "11px",
                "color": ALPACA_DARK["text_muted"],
                "marginTop": "4px",
            }
        ) if sublabel else None,
    ], style=METRIC_CARD_STYLE)


def create_section_card(
    title: str,
    icon: str,
    children: List,
    accent: bool = False,
    badge: str = None
) -> html.Div:
    """Create a section card with header and optional accent border."""
    header_content = [
        html.Span(icon, style={"color": ALPACA_DARK["gold"], "fontSize": "20px"}),
        html.Span(title, style={"fontWeight": "600", "fontSize": "15px"}),
    ]
    if badge:
        header_content.append(
            dbc.Badge(badge, color="success", className="ms-2", style={"fontSize": "10px"})
        )
    
    return html.Div([
        html.Div(header_content, style=HEADER_STYLE),
        html.Div(children),
    ], style=CARD_ACCENT_STYLE if accent else CARD_STYLE)


# ===========================================================================
# PATTERN FEED COMPONENT
# ===========================================================================

def create_pattern_feed(patterns: Optional[List[Dict]] = None) -> html.Div:
    """
    Create enhanced Pattern Feed component showing detected chart patterns.
    
    Args:
        patterns: List of detected pattern dictionaries
        
    Returns:
        Pattern feed div component
    """
    if patterns is None:
        patterns = []
    
    pattern_items = []
    
    if not patterns:
        pattern_items.append(
            html.Div([
                html.Div("🔍", style={"fontSize": "36px", "marginBottom": "12px"}),
                html.Div("Scanning for chart patterns...", style={
                    "color": ALPACA_DARK["text"],
                    "fontSize": "14px",
                    "fontWeight": "500",
                }),
                html.Div("Patterns will appear here when detected", style={
                    "color": ALPACA_DARK["text_muted"],
                    "fontSize": "12px",
                    "marginTop": "4px",
                }),
            ], style={
                "textAlign": "center",
                "padding": "48px 20px",
            })
        )
    else:
        for p in patterns[:5]:  # Show top 5 patterns
            signal = p.get("signal", "neutral")
            pattern_type = p.get("pattern_type", "unknown")
            confidence = p.get("confidence", 0)
            description = p.get("description", "")
            target = p.get("target_price")
            
            # Configuration based on signal
            signal_config = {
                "bullish": {
                    "color": ALPACA_DARK["positive"],
                    "icon": "📈",
                    "border": ALPACA_DARK["positive"]
                },
                "bearish": {
                    "color": ALPACA_DARK["negative"],
                    "icon": "📉",
                    "border": ALPACA_DARK["negative"]
                },
            }.get(signal, {
                "color": ALPACA_DARK["text"],
                "icon": "➡️",
                "border": ALPACA_DARK["border"]
            })
            
            pattern_items.append(
                html.Div(
                    children=[
                        html.Div(
                            children=[
                                html.Span(signal_config["icon"], style={
                                    "marginRight": "8px", 
                                    "fontSize": "18px"
                                }),
                                html.Span(
                                    signal.upper(),
                                    style={
                                        "color": signal_config["color"],
                                        "fontWeight": "700",
                                        "fontSize": "12px",
                                        "marginRight": "12px",
                                    }
                                ),
                                html.Span(
                                    pattern_type.replace("_", " ").title(),
                                    style={
                                        "color": ALPACA_DARK["gold"],
                                        "fontWeight": "500"
                                    }
                                ),
                            ],
                            style={"marginBottom": "6px"}
                        ),
                        html.Div(
                            children=[
                                html.Span(description, style={
                                    "color": ALPACA_DARK["text_muted"],
                                    "fontSize": "12px"
                                }),
                            ]
                        ),
                        html.Div(
                            children=[
                                dbc.Badge(f"{confidence:.0%} conf", color="info", className="me-2"),
                                dbc.Badge(
                                    f"Target: ${target:.2f}", 
                                    color="success"
                                ) if target else None,
                            ],
                            style={"marginTop": "8px"}
                        ),
                    ],
                    style={
                        "padding": "14px 16px",
                        "borderLeft": f"4px solid {signal_config['border']}",
                        "marginBottom": "8px",
                        "backgroundColor": ALPACA_DARK["bg_tertiary"],
                        "borderRadius": "0 8px 8px 0",
                        "transition": "all 0.2s ease",
                    }
                )
            )
    
    return create_section_card(
        title="Pattern Feed",
        icon="🎯",
        badge="LIVE",
        accent=True,
        children=[
            html.Div(
                id="pattern-feed-items",
                children=pattern_items,
                style={"maxHeight": "400px", "overflowY": "auto"}
            ),
            dcc.Store(id="pattern-feed-store", data=patterns),
            dcc.Interval(id="pattern-feed-interval", interval=30000, n_intervals=0),
        ]
    )


# ===========================================================================
# SCANNER LAYOUT
# ===========================================================================

def scanner_layout() -> html.Div:
    """
    Scanner Workspace: The Cockpit - Phase 3.
    
    Layout:
    - Top Row: 4 Hype Gauges (Phase 1 Sentiment)
    - Middle Row (70/30 Split):
        * Left: TradingView Lightweight Chart (Phase 3)
        * Right: Live News Feed + Pattern Alerts
    - Bottom Row: Whale Stream (Phase 3) - Options flow filtered for Premium > $50K
    
    Phase 1: Hybrid Sentiment Engine (Hype Gauges + News Feed)
    Phase 3: TradingView Charts + Whale Stream
    """
    # Phase 3: Import TradingView chart component
    try:
        from financial_dashboard.dash.components.charting import render_tv_chart, generate_mock_ohlcv
        from financial_dashboard.dash.components.flow_feed import create_whale_stream
        
        # Generate mock price data
        price_df = generate_mock_ohlcv("SPY", days=60)
        tv_chart = render_tv_chart(price_df, "SPY", height=450, chart_id="scanner-tv-chart")
        
        # Whale stream
        whale_stream = create_whale_stream(flow_data=None, min_premium=50000, component_id="scanner-whale-stream")
        
        tvlwc_available = True
    except ImportError as e:
        logger.warning(f"Phase 3 components not available: {e}")
        # Fallback to old components
        try:
            from financial_dashboard.components.charts.gex import create_gex_chart, generate_mock_gex_data
            spot_price = 450.0
            ticker = "SPY"
            gex_data = generate_mock_gex_data(spot_price=spot_price)
            tv_chart = create_gex_chart(gex_data, spot_price=spot_price, ticker=ticker)
        except:
            tv_chart = html.Div("Chart loading...", style={"height": "450px", "backgroundColor": ALPACA_DARK["paper"]})
        
        whale_stream = html.Div("Whale Stream loading...", style={"height": "400px", "backgroundColor": ALPACA_DARK["paper"]})
        tvlwc_available = False
    
    # Phase 1: Import Hype Gauge components
    hype_gauges = create_hype_gauges_row()
    news_feed = create_news_feed_card()
    
    return html.Div(
        id="scanner-workspace",
        className="fade-in",
        children=[
            # Hidden stores for sentiment data
            dcc.Store(id='scanner-selected-symbol', data='SPY'),
            dcc.Store(id='scanner-sentiment-data', data={}),
            dcc.Interval(id='scanner-hype-interval', interval=30000, n_intervals=0),
            dcc.Interval(id='scanner-news-interval', interval=60000, n_intervals=0),
            
            # Header - Phase 3: The Cockpit
            create_workspace_header(
                title="Scanner Workspace - The Cockpit",
                icon="🔭",
                subtitle="Real-time price action, sentiment & whale flow",
                badges=[
                    {"text": "TVLWC" if tvlwc_available else "PLOTLY", "color": "success" if tvlwc_available else "warning"},
                    {"text": "HYPE", "color": "danger"},
                    {"text": "NEWS", "color": "primary"},
                    {"text": "WHALE STREAM", "color": "info"},
                    {"text": "Phase 3", "color": "gold"},
                ]
            ),
            
            # Top Row: Phase 1 Hype Gauges (Sentiment Engine)
            html.Div([
                html.H6([
                    html.Span("📡", style={"marginRight": "8px"}),
                    "Retail Sentiment Gauges",
                    dbc.Badge("LIVE", color="success", className="ms-2", style={"fontSize": "10px"}),
                ], style={"color": ALPACA_DARK["text"], "marginBottom": "12px"}),
                hype_gauges,
            ], style={"marginBottom": "20px"}),
            
            # Middle Row (70/30 Split): TradingView Chart + News Feed + Pattern Alerts
            dbc.Row(
                children=[
                    # Left 70%: TradingView Lightweight Chart
                    dbc.Col(
                        children=[
                            create_section_card(
                                title="Price Action - TradingView Lightweight Chart",
                                icon="📊",
                                badge="60fps" if tvlwc_available else "Standard",
                                accent=True,
                                children=[tv_chart]
                            )
                        ],
                        md=8
                    ),
                    # Right 30%: News Feed + Pattern Alerts
                    dbc.Col(
                        children=[
                            news_feed,
                            html.Div(style={"height": "10px"}),  # Spacer
                            create_pattern_feed(),
                        ],
                        md=4
                    ),
                ],
                className="mb-3"
            ),
            
            # Bottom Row: Whale Stream (Premium > $50K)
            dbc.Row(
                children=[
                    dbc.Col(
                        children=[
                            create_section_card(
                                title="🐋 Whale Stream",
                                icon="💰",
                                badge="$50K+ PREMIUM",
                                accent=True,
                                children=[whale_stream]
                            )
                        ],
                        md=12
                    ),
                ],
            ),
        ],
        style={
            "padding": "24px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


def create_hype_gauges_row() -> html.Div:
    """
    Create row of Hype Gauges for watchlist symbols.
    Phase 1: Hybrid Sentiment Engine
    """
    import plotly.graph_objects as go
    
    symbols = ['NVDA', 'TSLA', 'SPY', 'GLD']
    
    def make_gauge(symbol: str, score: float = 0.5, label: str = "Loading...") -> dbc.Col:
        """Create a single hype gauge."""
        if score >= 0.6:
            color = ALPACA_DARK["success"]
            icon = "🚀"
        elif score <= 0.4:
            color = ALPACA_DARK["danger"]
            icon = "📉"
        else:
            color = ALPACA_DARK["warning"]
            icon = "➡️"
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score * 100,
            number={'suffix': '%', 'font': {'size': 18, 'color': ALPACA_DARK['text']}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': ALPACA_DARK['text_muted']},
                'bar': {'color': color},
                'bgcolor': ALPACA_DARK['bg_tertiary'],
                'borderwidth': 0,
                'steps': [
                    {'range': [0, 40], 'color': 'rgba(248,81,73,0.15)'},
                    {'range': [40, 60], 'color': 'rgba(210,153,34,0.15)'},
                    {'range': [60, 100], 'color': 'rgba(63,185,80,0.15)'}
                ],
            }
        ))
        
        fig.update_layout(
            height=120,
            margin=dict(l=15, r=15, t=25, b=5),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': ALPACA_DARK['text']}
        )
        
        return dbc.Col([
            html.Div([
                html.Div([
                    html.Span(f"{icon} {symbol}", style={
                        'fontWeight': 'bold', 
                        'fontSize': '14px',
                        'color': ALPACA_DARK['text']
                    }),
                    dbc.Badge("MOCK", color="warning", style={"fontSize": "9px", "marginLeft": "6px"})
                ], style={'borderBottom': f'2px solid {color}', 'paddingBottom': '6px', 'marginBottom': '8px'}),
                dcc.Graph(figure=fig, config={'displayModeBar': False}, style={'height': '120px'}),
                html.Div(label, style={'textAlign': 'center', 'color': color, 'fontWeight': 'bold', 'fontSize': '12px'})
            ], style={
                'backgroundColor': ALPACA_DARK['paper'],
                'borderRadius': '8px',
                'padding': '10px',
                'border': f'1px solid {ALPACA_DARK["border"]}'
            })
        ], md=3)
    
    # Generate initial gauges with mock data
    gauges = []
    mock_scores = {'NVDA': 0.72, 'TSLA': 0.58, 'SPY': 0.55, 'GLD': 0.42}
    mock_labels = {'NVDA': 'Bullish', 'TSLA': 'Neutral', 'SPY': 'Neutral', 'GLD': 'Bearish'}
    
    for symbol in symbols:
        score = mock_scores.get(symbol, 0.5)
        label = mock_labels.get(symbol, 'Neutral')
        gauges.append(make_gauge(symbol, score, label))
    
    return dbc.Row(gauges, id='scanner-hype-gauges')


def create_news_feed_card() -> html.Div:
    """
    Create news feed card for scanner.
    Phase 2: Color-coded sentiment (Green/Red/Yellow)
    """
    # Mock headlines with sentiment for initial render
    mock_headlines = [
        {"time": "10:45AM", "headline": "NVDA surges on AI chip demand expectations", "source": "Reuters", "sentiment": "Positive"},
        {"time": "10:30AM", "headline": "SPY hits intraday high amid tech rally", "source": "Bloomberg", "sentiment": "Positive"},
        {"time": "10:15AM", "headline": "Tesla options activity spikes before earnings", "source": "MarketWatch", "sentiment": "Neutral"},
        {"time": "09:45AM", "headline": "Gold futures retreat as dollar strengthens", "source": "CNBC", "sentiment": "Negative"},
        {"time": "09:30AM", "headline": "Fed officials signal rate path uncertainty", "source": "WSJ", "sentiment": "Neutral"},
    ]
    
    # Sentiment colors
    SENTIMENT_COLORS = {
        'Positive': ALPACA_DARK['success'],  # Green
        'Negative': ALPACA_DARK['danger'],   # Red
        'Neutral': ALPACA_DARK['warning']    # Yellow
    }
    
    SENTIMENT_ICONS = {
        'Positive': '🟢',
        'Negative': '🔴',
        'Neutral': '🟡'
    }
    
    rows = []
    for h in mock_headlines:
        sentiment = h.get("sentiment", "Neutral")
        color = SENTIMENT_COLORS.get(sentiment, ALPACA_DARK['text'])
        icon = SENTIMENT_ICONS.get(sentiment, '⚪')
        
        rows.append(html.Tr([
            html.Td(h["time"], style={
                'width': '70px', 
                'color': ALPACA_DARK['text_muted'], 
                'fontSize': '12px',
                'padding': '8px'
            }),
            html.Td([
                html.Span(icon, style={'marginRight': '6px'}),
                html.Span(h["headline"], style={'color': color, 'fontSize': '13px'}),
                html.Small(f" ({h['source']})", style={'color': ALPACA_DARK['text_muted']})
            ], style={'padding': '8px'})
        ]))
    
    return html.Div([
        html.Div([
            html.Span("📰", style={"marginRight": "8px"}),
            "Live News Feed",
            dbc.Badge(id="scanner-news-count", children="5", color="info", className="ms-2", style={"fontSize": "10px"}),
            # Phase 2: Sentiment filter dropdown
            dcc.Dropdown(
                id='scanner-news-filter',
                options=[
                    {'label': '🔵 All', 'value': 'all'},
                    {'label': '🟢 Positive', 'value': 'Positive'},
                    {'label': '🔴 Negative', 'value': 'Negative'},
                    {'label': '🟡 Neutral', 'value': 'Neutral'},
                ],
                value='all',
                clearable=False,
                style={'width': '120px', 'marginLeft': 'auto', 'fontSize': '12px'}
            )
        ], style={
            "color": ALPACA_DARK["text"],
            "fontSize": "14px",
            "fontWeight": "600",
            "marginBottom": "12px",
            "paddingBottom": "8px",
            "borderBottom": f"2px solid {ALPACA_DARK['gold']}",
            "display": "flex",
            "alignItems": "center",
            "gap": "8px"
        }),
        html.Div([
            dbc.Table([
                html.Tbody(rows, id='scanner-news-feed')
            ], bordered=False, hover=True, responsive=True, 
               style={'backgroundColor': 'transparent', 'marginBottom': '0'})
        ], style={'maxHeight': '250px', 'overflowY': 'auto'})
    ], style={
        'backgroundColor': ALPACA_DARK['paper'],
        'borderRadius': '12px',
        'padding': '16px',
        'border': f'1px solid {ALPACA_DARK["border"]}',
        'height': '100%'
    })


def create_ai_recs_panel() -> html.Div:
    """
    Create AI Recommendations panel for Strategy Workspace.
    Phase 2: Shows strategy recommendations from AIRecommender.
    """
    # Mock recommendations for initial render
    mock_recs = [
        {
            "strategy": "Debit Call Spread",
            "symbol": "NVDA",
            "confidence": 85,
            "signal": "Strong",
            "reason": "High hype (78) + Bullish forecast",
            "risk": "Moderate"
        },
        {
            "strategy": "Iron Condor",
            "symbol": "SPY",
            "confidence": 72,
            "signal": "Moderate",
            "reason": "Low hype + High vol regime",
            "risk": "Moderate"
        },
        {
            "strategy": "Bull Put Spread",
            "symbol": "GLD",
            "confidence": 68,
            "signal": "Moderate",
            "reason": "Safe haven bullish sentiment",
            "risk": "Conservative"
        }
    ]
    
    rec_cards = []
    for rec in mock_recs:
        signal_color = {
            'Strong': ALPACA_DARK['success'],
            'Moderate': ALPACA_DARK['warning'],
            'Weak': ALPACA_DARK['text_muted']
        }.get(rec['signal'], ALPACA_DARK['text'])
        
        risk_color = {
            'Conservative': ALPACA_DARK['success'],
            'Moderate': ALPACA_DARK['warning'],
            'Aggressive': ALPACA_DARK['danger']
        }.get(rec['risk'], ALPACA_DARK['text'])
        
        rec_cards.append(html.Div([
            # Header: Strategy + Symbol
            html.Div([
                html.Span(f"🎯 {rec['strategy']}", style={
                    'fontWeight': 'bold',
                    'color': ALPACA_DARK['gold'],
                    'fontSize': '14px'
                }),
                dbc.Badge(rec['symbol'], color="primary", className="ms-2")
            ], style={'marginBottom': '8px'}),
            
            # Confidence bar
            html.Div([
                html.Span(f"Confidence: {rec['confidence']}%", style={
                    'fontSize': '11px',
                    'color': ALPACA_DARK['text_muted']
                }),
                dbc.Progress(
                    value=rec['confidence'],
                    color="success" if rec['confidence'] >= 75 else "warning" if rec['confidence'] >= 60 else "danger",
                    style={'height': '6px', 'marginTop': '4px'}
                )
            ], style={'marginBottom': '8px'}),
            
            # Reason
            html.Div(rec['reason'], style={
                'fontSize': '12px',
                'color': ALPACA_DARK['text_secondary'],
                'marginBottom': '8px'
            }),
            
            # Footer: Signal + Risk + Build Button
            html.Div([
                dbc.Badge(f"Signal: {rec['signal']}", style={
                    'backgroundColor': signal_color,
                    'marginRight': '4px'
                }),
                dbc.Badge(f"Risk: {rec['risk']}", style={
                    'backgroundColor': risk_color,
                    'marginRight': 'auto'
                }),
                create_button(
                    button_id={'type': 'ai-rec-build', 'index': rec['symbol']},
                    text="Build →",
                    variant="primary",
                    size="sm",
                    style={'fontSize': '11px'}
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '4px'})
            
        ], style={
            'backgroundColor': ALPACA_DARK['bg_tertiary'],
            'borderRadius': '8px',
            'padding': '12px',
            'marginBottom': '10px',
            'border': f'1px solid {ALPACA_DARK["border"]}'
        }))
    
    return html.Div([
        # Header
        html.Div([
            html.Span("🤖", style={"marginRight": "8px"}),
            "AI Recommendations",
            dbc.Badge("Phase 2", color="warning", className="ms-2", style={"fontSize": "10px"}),
        ], style={
            "color": ALPACA_DARK["text"],
            "fontSize": "14px",
            "fontWeight": "600",
            "marginBottom": "12px",
            "paddingBottom": "8px",
            "borderBottom": f"2px solid {ALPACA_DARK['gold']}",
        }),
        
        # Refresh button
        create_button(
            button_id="refresh-ai-recs",
            text=[html.I(className="bi bi-arrow-clockwise me-1"), "Refresh AI Recs"],
            variant="primary",
            size="sm",
            full_width=True,
            className="mb-3"
        ),
        
        # Recommendations list
        html.Div(rec_cards, id='ai-recs-container', style={'maxHeight': '400px', 'overflowY': 'auto'}),
        
        # Legend
        html.Div([
            html.Small("Click 'Build →' to auto-fill Strategy Builder", style={
                'color': ALPACA_DARK['text_muted'],
                'fontSize': '11px'
            })
        ], style={'marginTop': '10px', 'textAlign': 'center'})
        
    ], style={
        'backgroundColor': ALPACA_DARK['paper'],
        'borderRadius': '12px',
        'padding': '16px',
        'border': f'2px solid {ALPACA_DARK["gold"]}',
        'boxShadow': '0 0 20px rgba(245, 194, 17, 0.1)',
        'height': '100%'
    })


# ===========================================================================
# STRATEGY LAYOUT
# ===========================================================================

def strategy_layout() -> html.Div:
    """
    Strategy Workspace: Chain + Builder + AI Forecasts.
    
    Enhanced with professional trading terminal aesthetics.
    """
    # Import strategy components
    try:
        from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import (
            create_chain_viewer_panel,
            create_greeks_panel,
            create_iv_surface_panel,
            create_strategy_builder,
            create_ml_recommendations_panel,
        )
        from financial_dashboard.tabs.options_lab.strategy_engine_ui import create_strategy_analysis_tab
        from forecast_ui.tabs.forecasts import create_forecast_tab
        
        chain_viewer = create_chain_viewer_panel()
        greeks_panel = create_greeks_panel()
        iv_panel = create_iv_surface_panel()
        strategy_builder = create_strategy_builder()
        ml_panel = create_ml_recommendations_panel()
        strategy_engine = create_strategy_analysis_tab()
        forecast_tab = create_forecast_tab()
        
    except ImportError as e:
        logger.error(f"Error importing strategy components: {e}")
        chain_viewer = html.Div("Chain Viewer loading...", id="chain-viewer-placeholder",
                               className="skeleton", style={"height": "400px", "borderRadius": "8px"})
        greeks_panel = html.Div("Greeks loading...", id="greeks-panel-placeholder",
                               className="skeleton", style={"height": "200px", "borderRadius": "8px"})
        iv_panel = html.Div("IV loading...", id="iv-panel-placeholder",
                           className="skeleton", style={"height": "300px", "borderRadius": "8px"})
        strategy_builder = html.Div("Builder loading...", id="builder-placeholder",
                                   className="skeleton", style={"height": "300px", "borderRadius": "8px"})
        ml_panel = html.Div("ML loading...", id="ml-placeholder",
                           className="skeleton", style={"height": "200px", "borderRadius": "8px"})
        strategy_engine = html.Div("Engine loading...", id="engine-placeholder",
                                  className="skeleton", style={"height": "400px", "borderRadius": "8px"})
        forecast_tab = html.Div("Forecast loading...", id="forecast-placeholder",
                               className="skeleton", style={"height": "400px", "borderRadius": "8px"})
    
    return html.Div(
        id="strategy-workspace",
        className="fade-in",
        **{'data-test-id': 'strategy-workspace'},
        children=[
            # Header
            create_workspace_header(
                title="Strategy Workspace",
                icon="⚔️",
                subtitle="Options chain analysis & strategy construction",
                badges=[
                    {"text": "CHAIN", "color": "primary"},
                    {"text": "BUILD", "color": "warning"},
                    {"text": "AI", "color": "danger"},
                ]
            ),
            
            # Quick Stats Row
            html.Div([
                create_metric_card("IV Rank", "45%", "Percentile", "info", "📊"),
                create_metric_card("Expected Move", "±$12.50", "2.8%", "warning", "📈"),
                create_metric_card("Max Pain", "$448", "Friday Exp", "gold", "🎯"),
                create_metric_card("P/C Ratio", "0.85", "Bullish Bias", "success", "⚖️"),
            ], style=METRIC_GRID_STYLE),
            
            # Sub-tabs for strategy sections
            dcc.Tabs(
                id="strategy-sub-tabs",
                value="chain-tab",
                children=[
                    dcc.Tab(
                        label="📈 Chain & Greeks",
                        value="chain-tab",
                        children=[
                            html.Div(
                                children=[chain_viewer, greeks_panel, iv_panel],
                                style={"padding": "20px"},
                                **{'data-test-id': 'strategy-chain-panel'}
                            )
                        ],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                    dcc.Tab(
                        label="🎯 Builder",
                        value="builder-tab",
                        children=[
                            html.Div([
                                # Phase 2: Side-by-side layout - Builder + AI Recs
                                dbc.Row([
                                    dbc.Col([strategy_builder], md=8, **{'data-test-id': 'strategy-builder-panel'}),
                                    dbc.Col([html.Div([create_ai_recs_panel()], **{'data-test-id': 'strategy-ai-recs-panel'})], md=4),
                                ])
                            ], style={"padding": "20px"})
                        ],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                    dcc.Tab(
                        label="🦅 Engine",
                        value="engine-tab",
                        children=[html.Div(strategy_engine, **{'data-test-id': 'strategy-engine-panel'})],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                    dcc.Tab(
                        label="🤖 AI Forecast",
                        value="ai-tab",
                        children=[
                            html.Div(
                                children=[ml_panel, forecast_tab],
                                style={"padding": "20px"},
                                **{'data-test-id': 'strategy-ml-panel'}
                            )
                        ],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                ],
                style={"marginBottom": "16px"}
            ),
        ],
        style={
            "padding": "24px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


# ===========================================================================
# COMMAND LAYOUT
# ===========================================================================

def command_layout() -> html.Div:
    """
    Command Workspace: Positions + Trade Ops (Risk/Execution).
    
    Central hub for position management and trade execution.
    """
    try:
        from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import (
            create_positions_panel,
            create_risk_analytics_panel,
            create_flow_analysis_panel,
        )
        from tradeops_ui.tabs.trade_ops import create_trade_ops_tab
        
        positions_panel = create_positions_panel()
        risk_panel = create_risk_analytics_panel()
        flow_panel = create_flow_analysis_panel()
        trade_ops = create_trade_ops_tab()
        
    except ImportError as e:
        logger.error(f"Error importing command components: {e}")
        positions_panel = html.Div("Positions loading...", id="positions-placeholder",
                                  className="skeleton", style={"height": "300px", "borderRadius": "8px"})
        risk_panel = html.Div("Risk loading...", id="risk-placeholder",
                             className="skeleton", style={"height": "250px", "borderRadius": "8px"})
        flow_panel = html.Div("Flow loading...", id="flow-placeholder",
                             className="skeleton", style={"height": "300px", "borderRadius": "8px"})
        trade_ops = html.Div("Trade Ops loading...", id="tradeops-placeholder",
                            className="skeleton", style={"height": "400px", "borderRadius": "8px"})
    
    return html.Div(
        id="command-workspace",
        className="fade-in",
        **{'data-test-id': 'command-workspace'},
        children=[
            # Header
            create_workspace_header(
                title="Command Center",
                icon="🎮",
                subtitle="Position management & trade execution",
                badges=[
                    {"text": "POSITIONS", "color": "primary"},
                    {"text": "RISK", "color": "danger"},
                    {"text": "EXECUTE", "color": "success"},
                ]
            ),
            
            # Portfolio Summary Metrics
            html.Div([
                create_metric_card("Net P/L", "+$2,450", "Today", "success", "💰"),
                create_metric_card("Delta", "-125", "Shares Eq.", "warning", "Δ"),
                create_metric_card("Theta", "+$85", "Per Day", "success", "Θ"),
                create_metric_card("Risk Score", "LOW", "3 Positions", "success", "⚠️"),
            ], style=METRIC_GRID_STYLE, **{'data-test-id': 'command-portfolio-metrics'}),
            
            # Sub-tabs
            dcc.Tabs(
                id="command-sub-tabs",
                value="positions-tab",
                **{'data-test-id': 'command-sub-tabs'},
                children=[
                    dcc.Tab(
                        label="💼 Positions",
                        value="positions-tab",
                        **{'data-test-id': 'command-positions-tab'},
                        children=[
                            html.Div(
                                children=[positions_panel],
                                style={"padding": "20px"},
                                **{'data-test-id': 'positions-panel'}
                            )
                        ],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                    dcc.Tab(
                        label="⚠️ Risk & P/L",
                        value="risk-tab",
                        **{'data-test-id': 'command-risk-tab'},
                        children=[
                            html.Div(
                                children=[risk_panel, flow_panel],
                                style={"padding": "20px"},
                                **{'data-test-id': 'risk-panel'}
                            )
                        ],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                    dcc.Tab(
                        label="⚙️ Trade Ops",
                        value="tradeops-tab",
                        **{'data-test-id': 'command-tradeops-tab'},
                        children=[trade_ops],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                ],
                style={"marginBottom": "16px"}
            ),
        ],
        style={
            "padding": "24px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


# ===========================================================================
# PHASE 4: HEALTH CHECK PANEL
# ===========================================================================

def create_health_check_card() -> html.Div:
    """
    Create Health Check card for Admin workspace.
    
    Phase 4: Shows API status, Math Integrity, and Error Log.
    """
    # Get API status from news client
    try:
        from financial_dashboard.engines.news.hybrid_client import get_news_client
        news_client = get_news_client()
        api_statuses = news_client.get_api_status_simple()
    except Exception as e:
        logger.warning(f"Could not get API status: {e}")
        api_statuses = {
            'Finnhub': None,
            'FinViz': None,
            'StockTwits': None,
            'NewsAPI': None,
            'Tiingo': None,
        }
    
    # Add Alpaca status (always check separately)
    try:
        import os
        alpaca_key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
        api_statuses['Alpaca'] = bool(alpaca_key)
    except:
        api_statuses['Alpaca'] = None
    
    # Get Math Integrity status
    try:
        from financial_dashboard.tests.quality.golden_vectors import get_math_integrity_status
        math_status = get_math_integrity_status()
        math_integrity = math_status.get('math_integrity', False)
        math_tests_passed = math_status.get('tests_passed', 0)
        math_tests_total = math_status.get('tests_total', 0)
    except Exception as e:
        logger.warning(f"Could not get math integrity status: {e}")
        math_integrity = None
        math_tests_passed = 0
        math_tests_total = 0
    
    # Get last 10 lines of system.log
    log_lines = []
    try:
        from pathlib import Path
        log_file = Path(__file__).parent.parent.parent.parent / "reports" / "logs" / "system.log"
        if log_file.exists():
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                log_lines = all_lines[-10:] if len(all_lines) > 10 else all_lines
    except Exception as e:
        log_lines = [f"Could not read log file: {e}"]
    
    # Build API status indicators
    def status_indicator(name: str, status: bool) -> html.Div:
        if status is True:
            icon = "🟢"
            color = ALPACA_DARK["success"]
            label = "Online"
        elif status is False:
            icon = "🔴"
            color = ALPACA_DARK["danger"]
            label = "Offline"
        else:
            icon = "🟡"
            color = ALPACA_DARK["warning"]
            label = "Unknown"
        
        return html.Div([
            html.Span(icon, style={"marginRight": "8px"}),
            html.Span(name, style={"color": ALPACA_DARK["text"], "fontWeight": "500", "minWidth": "100px", "display": "inline-block"}),
            html.Span(label, style={"color": color, "fontSize": "12px"}),
        ], style={"padding": "8px 0", "borderBottom": f"1px solid {ALPACA_DARK['border_muted']}"})
    
    api_indicators = [status_indicator(name, status) for name, status in api_statuses.items()]
    
    # Math integrity indicator
    if math_integrity is True:
        math_icon = "✅"
        math_color = ALPACA_DARK["success"]
        math_label = f"PASS ({math_tests_passed}/{math_tests_total} tests)"
    elif math_integrity is False:
        math_icon = "❌"
        math_color = ALPACA_DARK["danger"]
        math_label = f"FAIL ({math_tests_passed}/{math_tests_total} tests)"
    else:
        math_icon = "⚠️"
        math_color = ALPACA_DARK["warning"]
        math_label = "Not Tested"
    
    return html.Div([
        # Header
        html.Div([
            html.Span("🏥", style={"marginRight": "8px", "fontSize": "20px", "color": ALPACA_DARK["gold"]}),
            html.Span("System Health Check", style={"fontWeight": "600", "fontSize": "15px"}),
            dbc.Badge("Phase 4", color="warning", className="ms-2", style={"fontSize": "10px"}),
        ], style={
            "color": ALPACA_DARK["text"],
            "marginBottom": "16px",
            "paddingBottom": "8px",
            "borderBottom": f"2px solid {ALPACA_DARK['gold']}",
        }),
        
        dbc.Row([
            # Left Column: API Status
            dbc.Col([
                html.Div([
                    html.H6("API Status", style={"color": ALPACA_DARK["text"], "marginBottom": "12px"}),
                    html.Div(api_indicators),
                ], style={
                    "backgroundColor": ALPACA_DARK["bg_tertiary"],
                    "borderRadius": "8px",
                    "padding": "16px",
                    "height": "100%",
                }),
            ], md=4),
            
            # Middle Column: Math Integrity
            dbc.Col([
                html.Div([
                    html.H6("Math Integrity", style={"color": ALPACA_DARK["text"], "marginBottom": "12px"}),
                    html.Div([
                        html.Span(math_icon, style={"fontSize": "48px", "marginBottom": "12px", "display": "block"}),
                        html.Div(math_label, style={
                            "color": math_color,
                            "fontWeight": "bold",
                            "fontSize": "18px",
                        }),
                        html.Div("Black-Scholes Verification", style={
                            "color": ALPACA_DARK["text_muted"],
                            "fontSize": "12px",
                            "marginTop": "4px",
                        }),
                    ], style={"textAlign": "center", "padding": "20px"}),
                ], style={
                    "backgroundColor": ALPACA_DARK["bg_tertiary"],
                    "borderRadius": "8px",
                    "padding": "16px",
                    "height": "100%",
                }),
            ], md=3),
            
            # Right Column: Error Log
            dbc.Col([
                html.Div([
                    html.H6([
                        "Error Log",
                        dbc.Badge("Last 10", color="info", className="ms-2", style={"fontSize": "10px"}),
                    ], style={"color": ALPACA_DARK["text"], "marginBottom": "12px"}),
                    html.Div(
                        children=[
                            html.Pre(
                                "".join(log_lines) if log_lines else "No log entries",
                                style={
                                    "color": ALPACA_DARK["text_secondary"],
                                    "fontSize": "10px",
                                    "fontFamily": "'JetBrains Mono', 'SF Mono', monospace",
                                    "margin": "0",
                                    "whiteSpace": "pre-wrap",
                                    "wordBreak": "break-all",
                                }
                            )
                        ],
                        id="admin-error-log",
                        style={
                            "maxHeight": "200px",
                            "overflowY": "auto",
                            "backgroundColor": ALPACA_DARK["bg"],
                            "borderRadius": "4px",
                            "padding": "8px",
                        }
                    ),
                ], style={
                    "backgroundColor": ALPACA_DARK["bg_tertiary"],
                    "borderRadius": "8px",
                    "padding": "16px",
                    "height": "100%",
                }),
            ], md=5),
        ]),
        
        # Refresh interval
        dcc.Interval(id="admin-health-interval", interval=30000, n_intervals=0),
        dcc.Store(id="admin-health-store", data={}),
    ], style={
        "backgroundColor": ALPACA_DARK["paper"],
        "borderRadius": "12px",
        "padding": "20px",
        "border": f"2px solid {ALPACA_DARK['gold']}",
        "marginBottom": "20px",
        "boxShadow": "0 0 20px rgba(245, 194, 17, 0.1)",
    })


# ===========================================================================
# ADMIN LAYOUT
# ===========================================================================

def admin_layout() -> html.Div:
    """
    Admin Workspace: Status + Research + Health Check.
    
    Phase 4: Enhanced with Health Check panel.
    """
    try:
        from financial_dashboard.tabs.options_lab.system_status_ui import create_system_status_panel
        from research_ui.tabs.research import create_research_tab
        
        status_panel = create_system_status_panel()
        research_tab = create_research_tab()
        
    except ImportError as e:
        logger.error(f"Error importing admin components: {e}")
        status_panel = html.Div("Status loading...", id="status-placeholder",
                               className="skeleton", style={"height": "400px", "borderRadius": "8px"})
        research_tab = html.Div("Research loading...", id="research-placeholder",
                               className="skeleton", style={"height": "400px", "borderRadius": "8px"})
    
    # Phase 4: Health Check Card
    health_check = create_health_check_card()
    
    return html.Div(
        id="admin-workspace",
        className="fade-in",
        **{'data-test-id': 'admin-workspace'},
        children=[
            # Header
            create_workspace_header(
                title="Admin Workspace",
                icon="🔧",
                subtitle="System monitoring & research tools",
                badges=[
                    {"text": "STATUS", "color": "info"},
                    {"text": "HEALTH", "color": "success"},
                    {"text": "RESEARCH", "color": "warning"},
                    {"text": "Phase 4", "color": "gold"},
                ]
            ),
            
            # Phase 4: Health Check Panel (NEW)
            health_check,
            
            # System Health Metrics
            html.Div([
                create_metric_card("API Status", "Online", "Alpaca", "success", "🟢"),
                create_metric_card("Data Feed", "Live", "< 100ms", "success", "📡"),
                create_metric_card("Models", "3/3", "Loaded", "success", "🤖"),
                create_metric_card("Cache", "85%", "Hit Rate", "info", "💾"),
            ], style=METRIC_GRID_STYLE, **{'data-test-id': 'admin-health-metrics'}),
            
            # Sub-tabs
            dcc.Tabs(
                id="admin-sub-tabs",
                value="status-tab",
                **{'data-test-id': 'admin-sub-tabs'},
                children=[
                    dcc.Tab(
                        label="🔧 System Status",
                        value="status-tab",
                        **{'data-test-id': 'admin-status-tab'},
                        children=[status_panel],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                    dcc.Tab(
                        label="📊 Research Lab",
                        value="research-tab",
                        **{'data-test-id': 'admin-research-tab'},
                        children=[research_tab],
                        style=TAB_STYLE,
                        selected_style=TAB_SELECTED_STYLE
                    ),
                ],
                style={"marginBottom": "16px"}
            ),
        ],
        style={
            "padding": "24px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


# =============================================================================
# WORKSPACE REGISTRY
# =============================================================================

WORKSPACE_REGISTRY = {
    "scanner": {
        "label": "🔭 Scanner",
        "layout": scanner_layout,
        "description": "Market Viz, Flow Tape, Pattern Feed",
        "color": "warning",
    },
    "strategy": {
        "label": "⚔️ Strategy",
        "layout": strategy_layout,
        "description": "Chain, Builder, AI Forecasts",
        "color": "info",
    },
    "command": {
        "label": "🎮 Command",
        "layout": command_layout,
        "description": "Positions, Risk, Execution",
        "color": "danger",
    },
    "admin": {
        "label": "🔧 Admin",
        "layout": admin_layout,
        "description": "Status, Research",
        "color": "success",
    },
}


def get_workspace_tabs() -> List[dcc.Tab]:
    """
    Get the 4 consolidated workspace tabs with enhanced styling.
    
    Returns:
        List of dcc.Tab components
    """
    tabs = []
    
    for key, config in WORKSPACE_REGISTRY.items():
        tabs.append(
            dcc.Tab(
                label=config["label"],
                value=f"{key}-workspace-tab",
                children=[config["layout"]()],
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE
            )
        )
    
    return tabs
