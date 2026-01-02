"""
Enhanced Quant Dashboard - Port 8052
Integrated real data + ML/AI powered trading platform
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, jsonify, request
from dash import Dash, html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Import our real data and ML modules
from services.quant_platform.real_data_connectors import (
    data_service, APIKeys, TiingoConnector, FinnhubConnector,
    PolygonConnector, AlpacaConnector, NewsAPIConnector, 
    RedditConnector, FREDConnector, OllamaConnector, UsageTracker
)
from services.quant_platform.ml_ai_engine import (
    ml_engine, SentimentAnalyzer, PricePredictionEngine,
    MarketRegimeDetector, AIMarketAnalyst
)

# Ported Tabs
try:
    from financial_dashboard.tabs.market_forecast_tab import layout as mf_layout, register_callbacks as mf_callbacks
    MF_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import Market Forecast: {e}")
    MF_AVAILABLE = False

try:
    from financial_dashboard.tabs.options_bots import create_layout as bots_layout, register_callbacks as bots_callbacks
    BOTS_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import Options Bots: {e}")
    BOTS_AVAILABLE = False

try:
    from financial_dashboard.tabs.portfolio_tracker.layout import get_layout as portfolio_layout, register_callbacks as portfolio_callbacks
    PORTFOLIO_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import Portfolio Tracker: {e}")
    PORTFOLIO_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== FLASK SERVER =====
server = Flask(__name__)
server.secret_key = os.urandom(24)

# ===== DASH APP =====
app = Dash(
    __name__,
    server=server,
    url_base_pathname='/',
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True
)

# ===== CUSTOM STYLES =====
COLORS = {
    "bg_dark": "#0a0a0a",
    "bg_card": "#1a1a2e",
    "bg_card_hover": "#16213e",
    "accent_blue": "#00d4ff",
    "accent_green": "#00ff88",
    "accent_red": "#ff4757",
    "accent_yellow": "#ffc107",
    "accent_purple": "#a855f7",
    "text_primary": "#ffffff",
    "text_secondary": "#94a3b8",
    "border": "#334155"
}

CARD_STYLE = {
    "backgroundColor": COLORS["bg_card"],
    "borderRadius": "12px",
    "border": f"1px solid {COLORS['border']}",
    "padding": "20px",
    "marginBottom": "20px",
    "boxShadow": "0 4px 20px rgba(0,0,0,0.3)"
}

HEADER_STYLE = {
    "color": COLORS["accent_blue"],
    "marginBottom": "15px",
    "fontWeight": "600"
}

# ===== HELPER FUNCTIONS =====
def create_price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create candlestick chart with indicators"""
    if df is None or len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=20, color="white"))
        fig.update_layout(template="plotly_dark", paper_bgcolor=COLORS["bg_dark"])
        return fig
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05,
                        row_heights=[0.7, 0.3])
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol,
        increasing_line_color=COLORS["accent_green"],
        decreasing_line_color=COLORS["accent_red"]
    ), row=1, col=1)
    
    # Moving averages
    if len(df) >= 20:
        sma20 = df['close'].rolling(20).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma20, name="SMA 20",
                                line=dict(color=COLORS["accent_blue"], width=1)), row=1, col=1)
    if len(df) >= 50:
        sma50 = df['close'].rolling(50).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma50, name="SMA 50",
                                line=dict(color=COLORS["accent_yellow"], width=1)), row=1, col=1)
    
    # Volume
    if 'volume' in df.columns:
        colors = [COLORS["accent_green"] if df['close'].iloc[i] >= df['open'].iloc[i] 
                  else COLORS["accent_red"] for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['volume'], name="Volume",
                            marker_color=colors, opacity=0.7), row=2, col=1)
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        plot_bgcolor=COLORS["bg_dark"],
        title=dict(text=f"{symbol} Price Chart", font=dict(color=COLORS["accent_blue"])),
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=50, r=50, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    return fig


def create_indicator_card(title: str, value: str, change: str = None, 
                         icon: str = "chart-line", color: str = None) -> dbc.Card:
    """Create a metric indicator card"""
    if color is None:
        color = COLORS["accent_blue"]
    
    change_color = COLORS["accent_green"] if change and change.startswith("+") else COLORS["accent_red"]
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas fa-{icon}", style={"color": color, "fontSize": "24px"}),
                html.Span(title, style={"marginLeft": "10px", "color": COLORS["text_secondary"]})
            ]),
            html.H3(value, style={"color": COLORS["text_primary"], "marginTop": "10px"}),
            html.Span(change, style={"color": change_color}) if change else None
        ])
    ], style=CARD_STYLE)


# ===== LAYOUT COMPONENTS =====
def create_header():
    """Create dashboard header"""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-chart-pie", style={"color": COLORS["accent_blue"], "fontSize": "28px"}),
                        html.Span(" Quant Trading Platform", style={"color": COLORS["text_primary"], 
                                                                     "fontSize": "24px", "fontWeight": "bold",
                                                                     "marginLeft": "10px"})
                    ])
                ], width="auto"),
                dbc.Col([
                    dbc.Badge("LIVE", color="success", className="me-2"),
                    html.Span(id="current-time", style={"color": COLORS["text_secondary"]})
                ], width="auto", className="ms-auto")
            ], align="center", className="g-0 w-100")
        ], fluid=True),
        color=COLORS["bg_card"],
        dark=True,
        style={"borderBottom": f"1px solid {COLORS['border']}"}
    )


def create_sidebar():
    """Create navigation sidebar"""
    nav_items = [
        {"icon": "home", "label": "Dashboard", "tab": "dashboard"},
        {"icon": "chart-line", "label": "Market Forecast", "tab": "forecast"},
        {"icon": "robot", "label": "Trading Bots", "tab": "bots"},
        {"icon": "brain", "label": "AI Analysis", "tab": "ai"},
        {"icon": "wallet", "label": "Portfolio", "tab": "portfolio"},
        {"icon": "newspaper", "label": "News & Sentiment", "tab": "news"},
        {"icon": "chart-bar", "label": "Technical Analysis", "tab": "technical"},
        {"icon": "cog", "label": "Settings", "tab": "settings"},
    ]
    
    return html.Div([
        html.Div([
            dbc.Button([
                html.I(className=f"fas fa-{item['icon']}", style={"marginRight": "10px"}),
                item['label']
            ], id=f"nav-{item['tab']}", color="link", className="w-100 text-start mb-2",
               style={"color": COLORS["text_secondary"]})
            for item in nav_items
        ], style={"padding": "20px"})
    ], style={
        "backgroundColor": COLORS["bg_card"],
        "height": "100vh",
        "position": "fixed",
        "width": "240px",
        "borderRight": f"1px solid {COLORS['border']}"
    })


def create_dashboard_content():
    """Create main dashboard content"""
    return html.Div([
        # API Status Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("API Status", style=HEADER_STYLE),
                    html.Div(id="api-status-display")
                ], style=CARD_STYLE)
            ], width=12)
        ], className="mb-3"),
        
        # Market Overview Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Market Overview", style=HEADER_STYLE),
                    dbc.Row([
                        dbc.Col(id="spy-card", width=3),
                        dbc.Col(id="qqq-card", width=3),
                        dbc.Col(id="iwm-card", width=3),
                        dbc.Col(id="vix-card", width=3),
                    ])
                ], style=CARD_STYLE)
            ], width=12)
        ], className="mb-3"),
        
        # Charts Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Price Chart", style=HEADER_STYLE),
                    dbc.InputGroup([
                        dbc.Input(id="symbol-input", value="AAPL", placeholder="Enter symbol..."),
                        dbc.Button("Load", id="load-symbol-btn", color="primary")
                    ], className="mb-3"),
                    dcc.Graph(id="price-chart")
                ], style=CARD_STYLE)
            ], width=8),
            dbc.Col([
                html.Div([
                    html.H5("AI Market Analysis", style=HEADER_STYLE),
                    html.Div(id="ai-analysis-display", style={
                        "backgroundColor": "#0f0f23",
                        "padding": "15px",
                        "borderRadius": "8px",
                        "minHeight": "400px",
                        "color": COLORS["text_secondary"]
                    })
                ], style=CARD_STYLE)
            ], width=4)
        ], className="mb-3"),
        
        # Trading Signals Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Trading Signals", style=HEADER_STYLE),
                    html.Div(id="trading-signals-display")
                ], style=CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H5("Market Regime", style=HEADER_STYLE),
                    html.Div(id="market-regime-display")
                ], style=CARD_STYLE)
            ], width=6)
        ], className="mb-3"),
        
        # Account & Positions Row
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Alpaca Account", style=HEADER_STYLE),
                    html.Div(id="account-display")
                ], style=CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H5("Open Positions", style=HEADER_STYLE),
                    html.Div(id="positions-display")
                ], style=CARD_STYLE)
            ], width=6)
        ])
    ])


def create_forecast_content():
    """Create market forecast tab content"""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("📈 AI-Powered Market Forecast", style=HEADER_STYLE),
                    html.P("Machine learning predictions using multiple data sources", 
                           style={"color": COLORS["text_secondary"]})
                ], style=CARD_STYLE)
            ])
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Prediction Parameters", style=HEADER_STYLE),
                    dbc.Label("Symbol"),
                    dbc.Input(id="forecast-symbol", value="SPY", className="mb-2"),
                    dbc.Label("Forecast Days"),
                    dcc.Slider(id="forecast-days", min=1, max=30, value=5, 
                              marks={1: '1', 5: '5', 10: '10', 20: '20', 30: '30'}),
                    dbc.Button("Generate Forecast", id="generate-forecast-btn", 
                              color="primary", className="mt-3 w-100")
                ], style=CARD_STYLE)
            ], width=3),
            dbc.Col([
                html.Div([
                    html.H5("Price Forecast", style=HEADER_STYLE),
                    dcc.Graph(id="forecast-chart")
                ], style=CARD_STYLE)
            ], width=9)
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Model Performance", style=HEADER_STYLE),
                    html.Div(id="model-performance")
                ], style=CARD_STYLE)
            ], width=4),
            dbc.Col([
                html.Div([
                    html.H5("Feature Importance", style=HEADER_STYLE),
                    dcc.Graph(id="feature-importance-chart")
                ], style=CARD_STYLE)
            ], width=8)
        ])
    ])


def create_bots_content():
    """Create trading bots tab content"""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("🤖 Automated Trading Bots", style=HEADER_STYLE),
                    html.P("AI-powered trading automation with real-time execution", 
                           style={"color": COLORS["text_secondary"]})
                ], style=CARD_STYLE)
            ])
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Bot Status", style=HEADER_STYLE),
                    html.Div([
                        create_bot_card("Momentum Bot", "active", "+2.3%"),
                        create_bot_card("Mean Reversion Bot", "paused", "-0.5%"),
                        create_bot_card("Sentiment Bot", "active", "+1.8%"),
                        create_bot_card("Arbitrage Bot", "inactive", "0.0%"),
                    ])
                ], style=CARD_STYLE)
            ], width=4),
            dbc.Col([
                html.Div([
                    html.H5("Bot Performance", style=HEADER_STYLE),
                    dcc.Graph(id="bot-performance-chart")
                ], style=CARD_STYLE)
            ], width=8)
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Recent Bot Trades", style=HEADER_STYLE),
                    html.Div(id="bot-trades-table")
                ], style=CARD_STYLE)
            ])
        ])
    ])


def create_bot_card(name: str, status: str, pnl: str):
    """Create a bot status card"""
    status_colors = {"active": COLORS["accent_green"], "paused": COLORS["accent_yellow"], 
                     "inactive": COLORS["text_secondary"]}
    pnl_color = COLORS["accent_green"] if pnl.startswith("+") else COLORS["accent_red"]
    
    return html.Div([
        html.Div([
            html.Span("●", style={"color": status_colors.get(status, "white"), "marginRight": "10px"}),
            html.Strong(name, style={"color": COLORS["text_primary"]}),
        ]),
        html.Div([
            html.Span(status.upper(), style={"color": status_colors.get(status), "fontSize": "12px"}),
            html.Span(f" | P&L: ", style={"color": COLORS["text_secondary"], "fontSize": "12px"}),
            html.Span(pnl, style={"color": pnl_color, "fontSize": "12px"})
        ])
    ], style={"padding": "10px", "borderBottom": f"1px solid {COLORS['border']}"})


def create_ai_content():
    """Create AI analysis tab content"""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("🧠 AI Analysis Center", style=HEADER_STYLE),
                    html.P("Deep learning insights and natural language analysis", 
                           style={"color": COLORS["text_secondary"]})
                ], style=CARD_STYLE)
            ])
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("AI Chat Assistant", style=HEADER_STYLE),
                    html.Div(id="chat-messages", style={
                        "height": "300px",
                        "overflowY": "auto",
                        "backgroundColor": "#0f0f23",
                        "padding": "15px",
                        "borderRadius": "8px"
                    }),
                    dbc.InputGroup([
                        dbc.Input(id="chat-input", placeholder="Ask about markets..."),
                        dbc.Button("Send", id="chat-send-btn", color="primary")
                    ], className="mt-2")
                ], style=CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H5("Sentiment Analysis", style=HEADER_STYLE),
                    dbc.Textarea(id="sentiment-input", placeholder="Enter text to analyze...",
                                style={"height": "150px", "backgroundColor": "#0f0f23", "color": "white"}),
                    dbc.Button("Analyze Sentiment", id="analyze-sentiment-btn", 
                              color="primary", className="mt-2"),
                    html.Div(id="sentiment-result", className="mt-3")
                ], style=CARD_STYLE)
            ], width=6)
        ])
    ])


def create_news_content():
    """Create news and sentiment tab content"""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("📰 News & Sentiment Feed", style=HEADER_STYLE),
                    html.P("Real-time news aggregation with AI sentiment scoring", 
                           style={"color": COLORS["text_secondary"]})
                ], style=CARD_STYLE)
            ])
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Market News", style=HEADER_STYLE),
                    dbc.Button("Refresh News", id="refresh-news-btn", color="primary", className="mb-3"),
                    html.Div(id="news-feed")
                ], style=CARD_STYLE)
            ], width=8),
            dbc.Col([
                html.Div([
                    html.H5("Reddit Sentiment", style=HEADER_STYLE),
                    html.Div(id="reddit-feed")
                ], style=CARD_STYLE)
            ], width=4)
        ])
    ])


def create_settings_content():
    """Create settings content with API usage"""
    counts = UsageTracker.get_counts()
    
    rows = []
    for api, count in counts.items():
        rows.append(html.Tr([
            html.Td(api.upper()),
            html.Td(str(count))
        ]))
        
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("⚙️ Settings & Usage", style=HEADER_STYLE),
                    html.P("System configuration and API usage tracking", 
                           style={"color": COLORS["text_secondary"]})
                ], style=CARD_STYLE)
            ])
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("API Usage Stats", style=HEADER_STYLE),
                    dbc.Table([
                        html.Thead(html.Tr([html.Th("API"), html.Th("Calls")])),
                        html.Tbody(rows)
                    ], bordered=True, dark=True, hover=True, striped=True)
                ], style=CARD_STYLE)
            ], width=6)
        ])
    ])


# ===== MAIN LAYOUT =====
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='current-tab', data='dashboard'),
    dcc.Interval(id='update-interval', interval=30000, n_intervals=0),
    
    # Header
    create_header(),
    
    # Main content area
    html.Div([
        # Sidebar
        create_sidebar(),
        
        # Content
        html.Div([
            html.Div(id="page-content", style={"padding": "20px"})
        ], style={"marginLeft": "240px"})
    ], style={"backgroundColor": COLORS["bg_dark"], "minHeight": "100vh"})
], style={"backgroundColor": COLORS["bg_dark"]})


# ===== CALLBACKS =====
@app.callback(
    Output('page-content', 'children'),
    Output('current-tab', 'data'),
    [Input(f'nav-{tab}', 'n_clicks') for tab in ['dashboard', 'forecast', 'bots', 'ai', 'portfolio', 'news', 'technical', 'settings']],
    State('current-tab', 'data')
)
def update_page(*args):
    """Update page content based on navigation"""
    from dash import ctx
    triggered = ctx.triggered_id
    
    # Map nav id -> (tab_name, callable returning layout)
    tab_map = {
        'nav-dashboard': ('dashboard', lambda: create_dashboard_content()),
        'nav-forecast': ('forecast', lambda: (mf_layout() if MF_AVAILABLE else create_forecast_content())),
        'nav-bots': ('bots', lambda: (bots_layout() if BOTS_AVAILABLE else create_bots_content())),
        'nav-ai': ('ai', lambda: create_ai_content()),
        'nav-portfolio': ('portfolio', lambda: (portfolio_layout() if PORTFOLIO_AVAILABLE else html.Div("Portfolio content coming soon..."))),
        'nav-news': ('news', lambda: create_news_content()),
        'nav-technical': ('technical', lambda: html.Div("Technical Analysis content coming soon...")),
        'nav-settings': ('settings', lambda: create_settings_content()),
    }

    if triggered and triggered in tab_map:
        tab_name, layout_fn = tab_map[triggered]
        try:
            content = layout_fn()
        except Exception as e:
            logger.exception(f"Error building layout for {tab_name}: {e}")
            content = html.Div([
                html.H4("Error loading tab"),
                html.P(f"{e}"),
                html.Pre(str(e))
            ], style=CARD_STYLE)
        return content, tab_name

    return create_dashboard_content(), 'dashboard'


@app.callback(
    Output('api-status-display', 'children'),
    Input('update-interval', 'n_intervals')
)
def update_api_status(n):
    """Update API status display"""
    status = data_service.get_status()
    ml_status = ml_engine.status()
    
    badges = []
    for api, available in status.items():
        color = "success" if available else "danger"
        badges.append(dbc.Badge(api.upper(), color=color, className="me-2 mb-1"))
    
    if ml_status.get("ollama_available"):
        badges.append(dbc.Badge(f"OLLAMA ({ml_status.get('ollama_model', 'N/A')})", 
                               color="info", className="me-2 mb-1"))
    
    return html.Div(badges)


@app.callback(
    [Output('spy-card', 'children'),
     Output('qqq-card', 'children'),
     Output('iwm-card', 'children'),
     Output('vix-card', 'children')],
    Input('update-interval', 'n_intervals')
)
def update_market_overview(n):
    """Update market overview cards"""
    cards = []
    symbols = ['SPY', 'QQQ', 'IWM', 'VIX']
    
    try:
        for symbol in symbols:
            try:
                quote = data_service.finnhub.get_quote(symbol)
                if quote and 'c' in quote:
                    price = quote.get('c', 0)
                    change = quote.get('dp', 0)
                    change_str = f"{'+' if change >= 0 else ''}{change:.2f}%"
                    cards.append(create_indicator_card(
                        symbol, f"${price:.2f}", change_str,
                        icon="chart-line" if symbol != "VIX" else "bolt",
                        color=COLORS["accent_green"] if change >= 0 else COLORS["accent_red"]
                    ))
                else:
                    cards.append(create_indicator_card(symbol, "N/A", None))
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                cards.append(create_indicator_card(symbol, "Err", None, color=COLORS["accent_red"]))
                
    except Exception as e:
        logger.error(f"Global error in market overview: {e}")
        # Ensure we return 4 cards even on error
        while len(cards) < 4:
            cards.append(create_indicator_card("Error", "N/A", None))
            
    return cards


@app.callback(
    Output('price-chart', 'figure'),
    [Input('load-symbol-btn', 'n_clicks')],
    [State('symbol-input', 'value')]
)
def update_price_chart(n_clicks, symbol):
    """Update price chart"""
    if not symbol:
        symbol = "AAPL"
    
    df = data_service.tiingo.get_history(symbol.upper(), days=180)
    if df is None:
        df = data_service.polygon.get_aggregates(symbol.upper(), days=180)
    if df is None:
        df = data_service.alpaca.get_bars(symbol.upper())
    
    return create_price_chart(df, symbol.upper())


@app.callback(
    Output('ai-analysis-display', 'children'),
    [Input('load-symbol-btn', 'n_clicks')],
    [State('symbol-input', 'value')]
)
def update_ai_analysis(n_clicks, symbol):
    """Update AI analysis"""
    if not symbol:
        return html.P("Enter a symbol and click Load", style={"color": COLORS["text_secondary"]})
    
    # Get price data
    df = data_service.tiingo.get_history(symbol.upper(), days=100)
    if df is None:
        return html.P("Unable to fetch data", style={"color": COLORS["accent_red"]})
    
    # Get analysis
    analyst = AIMarketAnalyst()
    news = data_service.finnhub.get_company_news(symbol.upper(), days=3)
    news_texts = [n.get('headline', '') for n in news[:5]] if news else None
    
    analysis = analyst.analyze_stock(symbol.upper(), df, news_texts)
    
    return html.Div([
        html.H6(f"Analysis for {symbol.upper()}", style={"color": COLORS["accent_blue"]}),
        html.Hr(style={"borderColor": COLORS["border"]}),
        
        html.P([
            html.Strong("Market Regime: "),
            html.Span(analysis['regime']['regime'], style={"color": COLORS["accent_yellow"]})
        ]),
        html.P([
            html.Strong("Confidence: "),
            f"{analysis['regime']['confidence']:.0%}"
        ]),
        
        html.Hr(style={"borderColor": COLORS["border"]}),
        
        html.P([
            html.Strong("5-Day Return: "),
            html.Span(f"{analysis['regime']['metrics']['return_5d']:.2%}",
                     style={"color": COLORS["accent_green"] if analysis['regime']['metrics']['return_5d'] > 0 else COLORS["accent_red"]})
        ]),
        html.P([
            html.Strong("20-Day Return: "),
            html.Span(f"{analysis['regime']['metrics']['return_20d']:.2%}",
                     style={"color": COLORS["accent_green"] if analysis['regime']['metrics']['return_20d'] > 0 else COLORS["accent_red"]})
        ]),
        
        html.Hr(style={"borderColor": COLORS["border"]}),
        
        html.Div([
            html.Strong("AI Insight: "),
            html.P(analysis.get('ai_analysis', 'AI analysis unavailable - Ollama may not be running'),
                  style={"color": COLORS["text_secondary"], "fontSize": "13px", "marginTop": "5px"})
        ]) if analysis.get('ai_analysis') else html.P("Start Ollama for AI insights", style={"color": COLORS["accent_yellow"]})
    ])


@app.callback(
    Output('trading-signals-display', 'children'),
    [Input('load-symbol-btn', 'n_clicks')],
    [State('symbol-input', 'value')]
)
def update_trading_signals(n_clicks, symbol):
    """Update trading signals"""
    if not symbol:
        return html.P("Enter a symbol to see signals")
    
    df = data_service.tiingo.get_history(symbol.upper(), days=100)
    if df is None:
        return html.P("Unable to fetch data")
    
    analyst = AIMarketAnalyst()
    signals = analyst.generate_trade_signals(symbol.upper(), df)
    
    signal_color = {
        "BUY": COLORS["accent_green"],
        "SELL": COLORS["accent_red"],
        "HOLD": COLORS["accent_yellow"]
    }
    
    return html.Div([
        html.Div([
            html.H4(signals['overall_signal'], style={"color": signal_color.get(signals['overall_signal'])}),
            html.P(f"Confidence: {signals['confidence']:.0%}", style={"color": COLORS["text_secondary"]})
        ], style={"textAlign": "center", "marginBottom": "20px"}),
        
        html.Hr(style={"borderColor": COLORS["border"]}),
        
        html.Div([
            html.Div([
                html.Span("●", style={"color": signal_color.get(s['signal']), "marginRight": "10px"}),
                html.Strong(s['indicator'], style={"marginRight": "10px"}),
                html.Span(s['reason'], style={"color": COLORS["text_secondary"], "fontSize": "12px"})
            ], style={"marginBottom": "10px"})
            for s in signals['signals']
        ]),
        
        html.Hr(style={"borderColor": COLORS["border"]}),
        
        html.Div([
            html.P(f"RSI: {signals['indicators']['rsi']:.1f}"),
            html.P(f"MACD: {signals['indicators']['macd']:.4f}"),
            html.P(f"SMA20: ${signals['indicators']['sma20']:.2f}"),
            html.P(f"SMA50: ${signals['indicators']['sma50']:.2f}"),
        ], style={"fontSize": "12px", "color": COLORS["text_secondary"]})
    ])


@app.callback(
    Output('market-regime-display', 'children'),
    [Input('load-symbol-btn', 'n_clicks')],
    [State('symbol-input', 'value')]
)
def update_market_regime(n_clicks, symbol):
    """Update market regime display"""
    if not symbol:
        return html.P("Enter a symbol")
    
    df = data_service.tiingo.get_history(symbol.upper(), days=200)
    if df is None:
        return html.P("Unable to fetch data")
    
    detector = MarketRegimeDetector()
    regime = detector.detect(df)
    
    regime_colors = {
        "BULL_TRENDING": COLORS["accent_green"],
        "BEAR_TRENDING": COLORS["accent_red"],
        "BULL_VOLATILE": "#90EE90",
        "BEAR_VOLATILE": "#FFB6C1",
        "RANGING": COLORS["accent_yellow"],
        "BREAKOUT": COLORS["accent_blue"],
        "BREAKDOWN": COLORS["accent_purple"]
    }
    
    return html.Div([
        html.H4(regime['regime'], style={"color": regime_colors.get(regime['regime'], "white")}),
        html.P(regime['description'], style={"color": COLORS["text_secondary"]}),
        html.P(f"Confidence: {regime['confidence']:.0%}"),
        
        html.Hr(style={"borderColor": COLORS["border"]}),
        
        html.Div([
            html.P(f"Volatility: {regime['metrics']['volatility']:.4f}"),
            html.P(f"Price vs SMA20: {regime['metrics']['price_vs_sma20']:.2%}"),
            html.P(f"SMA20 vs SMA50: {regime['metrics']['sma20_vs_sma50']:.2%}"),
        ], style={"fontSize": "12px", "color": COLORS["text_secondary"]})
    ])


@app.callback(
    Output('account-display', 'children'),
    Input('update-interval', 'n_intervals')
)
def update_account(n):
    """Update Alpaca account display"""
    account = data_service.alpaca.get_account()
    
    if not account:
        return html.P("Alpaca not configured or unavailable", style={"color": COLORS["accent_red"]})
    
    return html.Div([
        html.P([html.Strong("Status: "), account.get('status', 'N/A')]),
        html.P([html.Strong("Equity: "), f"${float(account.get('equity', 0)):,.2f}"]),
        html.P([html.Strong("Buying Power: "), f"${float(account.get('buying_power', 0)):,.2f}"]),
        html.P([html.Strong("Cash: "), f"${float(account.get('cash', 0)):,.2f}"]),
        html.P([html.Strong("Day Trades: "), str(account.get('daytrade_count', 0))]),
    ], style={"color": COLORS["text_secondary"]})


@app.callback(
    Output('positions-display', 'children'),
    Input('update-interval', 'n_intervals')
)
def update_positions(n):
    """Update positions display"""
    positions = data_service.alpaca.get_positions()
    
    if not positions:
        return html.P("No open positions", style={"color": COLORS["text_secondary"]})
    
    return html.Div([
        html.Div([
            html.Div([
                html.Strong(p.get('symbol', 'N/A')),
                html.Span(f" | Qty: {p.get('qty', 0)}", style={"marginLeft": "10px"}),
                html.Span(f" | P&L: ${float(p.get('unrealized_pl', 0)):.2f}", 
                         style={"color": COLORS["accent_green"] if float(p.get('unrealized_pl', 0)) >= 0 else COLORS["accent_red"]})
            ], style={"padding": "8px", "borderBottom": f"1px solid {COLORS['border']}"})
            for p in positions[:10]
        ])
    ])


@app.callback(
    Output('sentiment-result', 'children'),
    [Input('analyze-sentiment-btn', 'n_clicks')],
    [State('sentiment-input', 'value')]
)
def analyze_sentiment_callback(n_clicks, text):
    """Analyze sentiment of input text"""
    if not text:
        return html.P("Enter text to analyze", style={"color": COLORS["text_secondary"]})
    
    result = ml_engine.sentiment.analyze(text)
    
    sentiment_color = {
        "bullish": COLORS["accent_green"],
        "bearish": COLORS["accent_red"],
        "neutral": COLORS["accent_yellow"]
    }
    
    return html.Div([
        html.H5(result.get('sentiment', 'Unknown').upper(), 
               style={"color": sentiment_color.get(result.get('sentiment'), "white")}),
        html.P(f"Score: {result.get('score', 0):.2f}"),
        html.P(f"Confidence: {result.get('confidence', 0):.0%}"),
        html.P(f"Impact: {result.get('market_impact', 'N/A')}")
    ])


@app.callback(
    Output('news-feed', 'children'),
    Input('refresh-news-btn', 'n_clicks')
)
def update_news_feed(n_clicks):
    """Update news feed"""
    news = data_service.news.get_headlines(category="business", limit=15)
    
    if not news:
        return html.P("Unable to fetch news", style={"color": COLORS["accent_red"]})
    
    return html.Div([
        html.Div([
            html.A(article.get('title', 'No title'), 
                  href=article.get('url', '#'), target="_blank",
                  style={"color": COLORS["accent_blue"], "textDecoration": "none"}),
            html.P(article.get('source', {}).get('name', 'Unknown'), 
                  style={"fontSize": "11px", "color": COLORS["text_secondary"], "marginBottom": "10px"})
        ], style={"padding": "8px", "borderBottom": f"1px solid {COLORS['border']}"})
        for article in news
    ])


@app.callback(
    Output('reddit-feed', 'children'),
    Input('update-interval', 'n_intervals')
)
def update_reddit_feed(n):
    """Update Reddit sentiment feed"""
    posts = data_service.reddit.get_subreddit_posts("wallstreetbets", limit=10)
    
    if not posts:
        return html.P("Reddit unavailable", style={"color": COLORS["text_secondary"]})
    
    return html.Div([
        html.Div([
            html.P(post.get('title', '')[:80] + "...", 
                  style={"marginBottom": "2px", "color": COLORS["text_primary"]}),
            html.Span(f"⬆️ {post.get('score', 0)} | 💬 {post.get('num_comments', 0)}",
                     style={"fontSize": "11px", "color": COLORS["text_secondary"]})
        ], style={"padding": "8px", "borderBottom": f"1px solid {COLORS['border']}"})
        for post in posts
    ])


@app.callback(
    Output('current-time', 'children'),
    Input('update-interval', 'n_intervals')
)
def update_time(n):
    """Update current time display"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ===== API ENDPOINTS =====
@server.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "apis": data_service.get_status(),
        "ml": ml_engine.status()
    })


@server.route('/api/quote/<symbol>')
def api_quote(symbol):
    """Get quote for symbol"""
    quote = data_service.finnhub.get_quote(symbol.upper())
    return jsonify(quote if quote else {"error": "Unable to fetch quote"})


@server.route('/api/analysis/<symbol>')
def api_analysis(symbol):
    """Get AI analysis for symbol"""
    df = data_service.tiingo.get_history(symbol.upper(), days=100)
    if df is None:
        return jsonify({"error": "Unable to fetch data"})
    
    analyst = AIMarketAnalyst()
    analysis = analyst.analyze_stock(symbol.upper(), df)
    
    # Convert any non-serializable objects
    if 'regime' in analysis and 'metrics' in analysis['regime']:
        for k, v in analysis['regime']['metrics'].items():
            analysis['regime']['metrics'][k] = float(v) if not isinstance(v, (int, float, str)) else v
    
    return jsonify(analysis)


# ===== REGISTER CALLBACKS =====
if MF_AVAILABLE:
    try:
        mf_callbacks(app)
        logger.info("Registered Market Forecast callbacks")
    except Exception as e:
        logger.error(f"Error registering Market Forecast callbacks: {e}")

if BOTS_AVAILABLE:
    try:
        bots_callbacks(app)
        logger.info("Registered Options Bots callbacks")
    except Exception as e:
        logger.error(f"Error registering Options Bots callbacks: {e}")

if PORTFOLIO_AVAILABLE:
    try:
        portfolio_callbacks(app)
        logger.info("Registered Portfolio Tracker callbacks")
    except Exception as e:
        logger.error(f"Error registering Portfolio Tracker callbacks: {e}")


# ===== MAIN =====
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 QUANT TRADING PLATFORM - PORT 8052")
    print("=" * 60)
    print(f"Dashboard URL: http://localhost:8052")
    print("=" * 60)
    
    # Check API status
    status = data_service.get_status()
    ml_status = ml_engine.status()
    
    print("\n📊 API Status:")
    for api, available in status.items():
        icon = "✅" if available else "❌"
        print(f"  {icon} {api}")
    
    print("\n🤖 ML Status:")
    print(f"  Ollama: {'✅' if ml_status['ollama_available'] else '❌'} ({ml_status.get('ollama_model', 'N/A')})")
    print(f"  Groq: {'✅' if ml_status['groq_available'] else '❌'}")
    print(f"  sklearn: {'✅' if ml_status['sklearn_available'] else '❌'}")
    
    print("\n" + "=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=8052)
