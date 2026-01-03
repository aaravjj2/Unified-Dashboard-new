"""
Scanner Workspace UI - Phase 1: Hybrid Sentiment Engine
========================================================
A new tab/workspace featuring:
- Hype Gauges for watchlist symbols (NVDA, TSLA, SPY, GLD)
- Candlestick chart with pattern alerts overlay
- Live news feed from FinViz

Implements Ideas #14, #80, #212 from ALPACA_500_NEW_IDEAS.md
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Dash imports
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Add parent paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Week 2 enhancements
try:
    from src.ui.components.buttons import create_button
except ImportError:
    def create_button(button_id, text, **kwargs):
        return dbc.Button(text, id=button_id, **kwargs)

# Local imports with fallbacks
try:
    from financial_dashboard.engines.news import HybridNewsClient, get_news_client
except ImportError:
    HybridNewsClient = None
    def get_news_client():
        return None

try:
    from financial_dashboard.engines.analysis import PatternDetector
except ImportError:
    PatternDetector = None

try:
    from financial_dashboard.config.sentiment import get_scanner_config
except ImportError:
    try:
        from financial_dashboard.config import get_scanner_config
    except ImportError:
        def get_scanner_config():
            class MockConfig:
                DEFAULT_SYMBOLS = ['NVDA', 'TSLA', 'SPY', 'GLD']
                HYPE_GAUGE_REFRESH_MS = 30000
                NEWS_FEED_REFRESH_MS = 60000
                MAX_NEWS_ITEMS = 20
            return MockConfig()

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Default watchlist
DEFAULT_SYMBOLS = ['NVDA', 'TSLA', 'SPY', 'GLD']

# Color scheme (matches DARKLY theme)
COLORS = {
    'background': '#222222',
    'card_bg': '#303030',
    'text': '#FFFFFF',
    'text_muted': '#AAAAAA',
    'bullish': '#00D084',
    'bearish': '#FF6B6B',
    'neutral': '#FFD93D',
    'accent': '#6C5CE7',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_price_data(symbol: str, period: str = '5d', interval: str = '15m') -> Optional[pd.DataFrame]:
    """
    Fetch price data using yfinance with retry logic.
    
    NO MOCK FALLBACK - returns empty DataFrame if all sources fail.
    """
    if not YF_AVAILABLE:
        logger.error(f"yfinance not available - install with: pip install yfinance")
        return pd.DataFrame()  # Return empty instead of mock
    
    # Retry up to 3 times with backoff
    for attempt in range(3):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                logger.info(f"✅ Fetched {len(df)} bars for {symbol} from yfinance")
                return df
            # If empty, try with longer period
            if attempt == 0 and df.empty:
                df = ticker.history(period='1mo', interval='1h')
                if not df.empty:
                    return df
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/3 failed for {symbol}: {e}")
            if attempt < 2:
                import time
                time.sleep(0.5 * (attempt + 1))
    
    logger.error(f"❌ All attempts failed for {symbol} - returning empty data")
    return pd.DataFrame()  # Return empty DataFrame, NOT mock data


# NOTE: Mock data function removed - we now return empty DataFrames instead
# to force proper API integration and avoid silently using fake data


def create_hype_gauge(symbol: str, score: float, label: str, is_mock: bool = False) -> dbc.Card:
    """
    Create a single hype gauge card for a symbol.
    
    Args:
        symbol: Ticker symbol
        score: Hype score 0-1
        label: Sentiment label (Bullish/Bearish/Neutral)
        is_mock: Whether data is mock
    """
    # Determine color based on score
    if score >= 0.6:
        color = COLORS['bullish']
        icon = "🚀"
    elif score <= 0.4:
        color = COLORS['bearish']
        icon = "📉"
    else:
        color = COLORS['neutral']
        icon = "➡️"
    
    # Create gauge figure
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score * 100,
        number={'suffix': '%', 'font': {'size': 24, 'color': COLORS['text']}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': COLORS['text_muted']},
            'bar': {'color': color},
            'bgcolor': COLORS['card_bg'],
            'borderwidth': 0,
            'steps': [
                {'range': [0, 40], 'color': 'rgba(255,107,107,0.2)'},
                {'range': [40, 60], 'color': 'rgba(255,217,61,0.2)'},
                {'range': [60, 100], 'color': 'rgba(0,208,132,0.2)'}
            ],
            'threshold': {
                'line': {'color': COLORS['text'], 'width': 2},
                'thickness': 0.75,
                'value': score * 100
            }
        }
    ))
    
    fig.update_layout(
        height=150,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': COLORS['text']}
    )
    
    mock_badge = dbc.Badge("MOCK", color="warning", className="ms-2") if is_mock else None
    
    return dbc.Card([
        dbc.CardHeader([
            html.Span(f"{icon} {symbol}", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
            mock_badge
        ], style={'backgroundColor': COLORS['card_bg'], 'borderBottom': f'2px solid {color}'}),
        dbc.CardBody([
            dcc.Graph(figure=fig, config={'displayModeBar': False}, style={'height': '150px'}),
            html.Div([
                html.Span(label, style={'color': color, 'fontWeight': 'bold'}),
            ], className="text-center mt-1")
        ], style={'padding': '0.5rem'})
    ], style={'backgroundColor': COLORS['card_bg'], 'border': 'none', 'borderRadius': '8px'}, **{'data-test-id': f'hype-gauge-{symbol}'})


def create_candlestick_chart(df: pd.DataFrame, symbol: str, 
                            patterns: Optional[List[Dict]] = None) -> go.Figure:
    """
    Create candlestick chart with optional pattern overlays.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Ticker symbol for title
        patterns: List of detected patterns to overlay
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} Price', 'Volume')
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price',
        increasing_line_color=COLORS['bullish'],
        decreasing_line_color=COLORS['bearish']
    ), row=1, col=1)
    
    # Volume bars
    colors = [COLORS['bullish'] if df['Close'].iloc[i] >= df['Open'].iloc[i] 
              else COLORS['bearish'] for i in range(len(df))]
    
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name='Volume',
        marker_color=colors,
        opacity=0.5
    ), row=2, col=1)
    
    # Add pattern annotations if provided
    if patterns:
        for pattern in patterns:
            if pattern.get('confidence', 0) >= 0.6:
                # Add annotation at the pattern location
                pattern_name = pattern.get('pattern', 'Pattern')
                signal = pattern.get('signal', 'Neutral')
                color = COLORS['bullish'] if signal == 'Bullish' else (
                    COLORS['bearish'] if signal == 'Bearish' else COLORS['neutral']
                )
                
                # Add a shape or annotation
                fig.add_annotation(
                    x=df.index[-1],
                    y=df['High'].iloc[-1],
                    text=f"📍 {pattern_name}",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=color,
                    font=dict(color=color, size=12),
                    bgcolor=COLORS['card_bg'],
                    bordercolor=color,
                    row=1, col=1
                )
                
                # Add target price line if available
                if pattern.get('target_price'):
                    fig.add_hline(
                        y=pattern['target_price'],
                        line_dash="dash",
                        line_color=COLORS['bullish'],
                        annotation_text=f"Target: ${pattern['target_price']:.2f}",
                        row=1, col=1
                    )
                
                # Add stop loss line if available
                if pattern.get('stop_loss'):
                    fig.add_hline(
                        y=pattern['stop_loss'],
                        line_dash="dash",
                        line_color=COLORS['bearish'],
                        annotation_text=f"Stop: ${pattern['stop_loss']:.2f}",
                        row=1, col=1
                    )
    
    # Layout
    fig.update_layout(
        height=500,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        margin=dict(l=50, r=50, t=50, b=30),
        xaxis_rangeslider_visible=False,
        showlegend=False
    )
    
    fig.update_xaxes(gridcolor='#444444', showgrid=True)
    fig.update_yaxes(gridcolor='#444444', showgrid=True)
    
    return fig


def create_news_table(headlines: List[Dict]) -> dbc.Table:
    """
    Create a Bootstrap table for news headlines.
    
    Args:
        headlines: List of headline dicts with time, headline, link, source
    """
    if not headlines:
        return html.Div("No news available", className="text-muted text-center p-4")
    
    rows = []
    for h in headlines[:15]:  # Limit to 15 items
        time_str = h.get('time', '')
        headline = h.get('headline', '')
        link = h.get('link', '#')
        source = h.get('source', '')
        
        # Truncate long headlines
        if len(headline) > 80:
            headline = headline[:77] + "..."
        
        rows.append(html.Tr([
            html.Td(time_str, style={'width': '80px', 'color': COLORS['text_muted'], 'fontSize': '0.85rem'}),
            html.Td([
                html.A(headline, href=link, target="_blank", 
                      style={'color': COLORS['text'], 'textDecoration': 'none'}),
                html.Small(f" ({source})" if source else "", 
                          style={'color': COLORS['text_muted']})
            ]),
        ]))
    
    return dbc.Table([
        html.Tbody(rows)
    ], bordered=False, hover=True, responsive=True, 
       style={'backgroundColor': COLORS['card_bg']})


# =============================================================================
# MAIN LAYOUT FUNCTION
# =============================================================================

def create_scanner_layout() -> html.Div:
    """
    Create the Scanner Workspace layout.
    
    Returns:
        Dash HTML Div containing the complete scanner UI
    """
    config = get_scanner_config()
    symbols = config.DEFAULT_SYMBOLS if hasattr(config, 'DEFAULT_SYMBOLS') else DEFAULT_SYMBOLS
    
    return html.Div([
        # Hidden stores for data
        dcc.Store(id='scanner-selected-symbol', data=symbols[0]),
        dcc.Store(id='scanner-sentiment-data', data={}),
        dcc.Store(id='scanner-news-data', data=[]),
        dcc.Store(id='scanner-pattern-data', data={}),
        
        # Auto-refresh intervals
        dcc.Interval(
            id='scanner-hype-interval',
            interval=30000,  # 30 seconds
            n_intervals=0
        ),
        dcc.Interval(
            id='scanner-news-interval',
            interval=60000,  # 1 minute
            n_intervals=0
        ),
        
        # Header
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="bi bi-broadcast me-2"),
                    "Scanner Workspace",
                    dbc.Badge("LIVE", color="success", className="ms-2")
                ], className="mb-0"),
                html.P("Real-time sentiment and news for your watchlist", 
                      className="text-muted mb-0")
            ], width=8),
            dbc.Col([
                dbc.ButtonGroup([
                    create_button(
                        button_id="scanner-refresh-btn",
                        text=[html.I(className="bi bi-arrow-clockwise me-1"), "Refresh"],
                        variant="primary",
                        size="sm"
                    ),
                    create_button(
                        button_id="scanner-settings-btn",
                        text=[html.I(className="bi bi-gear")],
                        variant="secondary",
                        size="sm"
                    ),
                ], className="float-end")
            ], width=4)
        ], className="mb-4"),
        
        # Row 1: Hype Gauges
        html.Div([
            html.H5([
                html.I(className="bi bi-speedometer2 me-2"),
                "Hype Gauges"
            ], className="mb-3"),
            dbc.Row(id='scanner-hype-gauges', children=[
                dbc.Col(create_hype_gauge(sym, 0.5, "Loading...", True), md=3)
                for sym in symbols
            ])
        ], className="mb-4"),
        
        # Row 2: Chart and Pattern Alerts
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Span([
                            html.I(className="bi bi-graph-up me-2"),
                            "Price Chart"
                        ]),
                        dbc.ButtonGroup([
                            create_button(
                                button_id=f"scanner-sym-btn-{sym}",
                                text=sym,
                                variant="ghost" if i > 0 else "primary",
                                size="sm",
                                className="me-1"
                            )
                            for i, sym in enumerate(symbols)
                        ], className="float-end")
                    ], style={'backgroundColor': COLORS['card_bg']}),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(id='scanner-price-chart', 
                                     config={'displayModeBar': True, 'displaylogo': False}),
                            type="circle"
                        )
                    ])
                ], style={'backgroundColor': COLORS['card_bg'], 'border': 'none'})
            ], md=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-lightning me-2"),
                        "Pattern Alerts"
                    ], style={'backgroundColor': COLORS['card_bg']}),
                    dbc.CardBody(id='scanner-pattern-alerts', children=[
                        html.Div("Analyzing patterns...", className="text-muted text-center p-4")
                    ])
                ], style={'backgroundColor': COLORS['card_bg'], 'border': 'none', 'height': '100%'})
            ], md=4)
        ], className="mb-4"),
        
        # Row 3: News Feed
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-newspaper me-2"),
                        "Live News Feed",
                        dbc.Badge(id="scanner-news-count", children="0", color="info", className="ms-2")
                    ], style={'backgroundColor': COLORS['card_bg']}),
                    dbc.CardBody(id='scanner-news-feed', children=[
                        html.Div("Loading news...", className="text-muted text-center p-4")
                    ], style={'maxHeight': '400px', 'overflowY': 'auto'})
                ], style={'backgroundColor': COLORS['card_bg'], 'border': 'none'})
            ])
        ])
        
    ], style={'padding': '1rem', 'backgroundColor': COLORS['background'], 'minHeight': '100vh'})


# =============================================================================
# CALLBACKS
# =============================================================================

def register_scanner_callbacks(app):
    """
    Register all callbacks for the scanner workspace.
    
    Args:
        app: Dash app instance
    """
    
    @app.callback(
        Output('scanner-hype-gauges', 'children'),
        [Input('scanner-hype-interval', 'n_intervals')],
        prevent_initial_call=False
    )
    def update_hype_gauges(n_intervals):
        """Update all hype gauges with LIVE sentiment data - NO MOCK FALLBACK."""
        config = get_scanner_config()
        symbols = config.DEFAULT_SYMBOLS if hasattr(config, 'DEFAULT_SYMBOLS') else DEFAULT_SYMBOLS
        
        gauges = []
        client = get_news_client()
        
        for symbol in symbols:
            is_mock = False
            try:
                if client:
                    hype_data = client.get_hype_score(symbol)
                    score = hype_data.get('hype_score', 0.5)
                    label = hype_data.get('sentiment_label', 'Neutral')
                    is_mock = hype_data.get('is_mock', False)  # Default to False
                    source = hype_data.get('sentiment_source', 'unknown')
                    
                    # Only mark as mock if the source explicitly says so
                    if source == 'mock':
                        is_mock = True
                        
                    logger.debug(f"Hype for {symbol}: {score:.2f} ({label}) via {source}")
                else:
                    score = 0.5
                    label = "Connecting..."
                    is_mock = False  # Not mock, just waiting for connection
            except Exception as e:
                logger.error(f"Error getting hype for {symbol}: {e}")
                score = 0.5
                label = "API Error"
                is_mock = False  # Not mock, just error
            
            gauges.append(
                dbc.Col(create_hype_gauge(symbol, score, label, is_mock), md=3)
            )
        
        return gauges
    
    @app.callback(
        [Output('scanner-price-chart', 'figure'),
         Output('scanner-pattern-alerts', 'children'),
         Output('scanner-selected-symbol', 'data')],
        [Input(f'scanner-sym-btn-{sym}', 'n_clicks') for sym in DEFAULT_SYMBOLS],
        [State('scanner-selected-symbol', 'data')],
        prevent_initial_call=False
    )
    def update_chart_and_patterns(*args):
        """Update chart and pattern detection when symbol changes."""
        from dash import ctx
        
        # Determine which symbol was clicked
        config = get_scanner_config()
        symbols = config.DEFAULT_SYMBOLS if hasattr(config, 'DEFAULT_SYMBOLS') else DEFAULT_SYMBOLS
        
        current_symbol = args[-1] or symbols[0]
        
        # Check which button triggered
        if ctx.triggered_id:
            for sym in symbols:
                if ctx.triggered_id == f'scanner-sym-btn-{sym}':
                    current_symbol = sym
                    break
        
        # Fetch price data
        df = get_price_data(current_symbol)
        
        # Detect patterns
        patterns = []
        pattern_alerts = []
        
        if PatternDetector and df is not None and len(df) > 20:
            try:
                detector = PatternDetector()
                detected = detector.detect_patterns(df['Close'])
                
                for p in detected:
                    if hasattr(p, 'to_dict'):
                        patterns.append(p.to_dict())
                    
                    # Create alert card
                    if p.confidence >= 0.6:
                        signal_color = (
                            COLORS['bullish'] if p.signal.value == 'Bullish' 
                            else COLORS['bearish'] if p.signal.value == 'Bearish'
                            else COLORS['neutral']
                        )
                        
                        pattern_alerts.append(dbc.Card([
                            dbc.CardBody([
                                html.H6([
                                    html.Span("🎯 " if p.signal.value == 'Bullish' else "⚠️ "),
                                    p.pattern
                                ], style={'color': signal_color}),
                                html.P([
                                    f"Confidence: {p.confidence:.0%}",
                                    html.Br(),
                                    html.Small(p.description, className="text-muted")
                                ], className="mb-1"),
                                html.Div([
                                    dbc.Badge(p.signal.value, color="success" if p.signal.value == 'Bullish' else "danger" if p.signal.value == 'Bearish' else "secondary")
                                ])
                            ], style={'padding': '0.75rem'})
                        ], className="mb-2", style={'backgroundColor': '#3a3a3a', 'border': 'none'}))
            except Exception as e:
                logger.error(f"Pattern detection error: {e}")
        
        if not pattern_alerts:
            pattern_alerts = [html.Div("No significant patterns detected", 
                                      className="text-muted text-center p-4")]
        
        # Create chart
        if df is not None and len(df) > 0:
            fig = create_candlestick_chart(df, current_symbol, patterns)
        else:
            fig = go.Figure()
            fig.update_layout(
                annotations=[{'text': 'No data available', 'showarrow': False}],
                paper_bgcolor=COLORS['background'],
                plot_bgcolor=COLORS['background']
            )
        
        return fig, pattern_alerts, current_symbol
    
    @app.callback(
        [Output('scanner-news-feed', 'children'),
         Output('scanner-news-count', 'children')],
        [Input('scanner-news-interval', 'n_intervals'),
         Input('scanner-selected-symbol', 'data')],
        prevent_initial_call=False
    )
    def update_news_feed(n_intervals, symbol):
        """Update news feed for selected symbol - LIVE DATA ONLY."""
        if not symbol:
            symbol = DEFAULT_SYMBOLS[0]
        
        client = get_news_client()
        headlines_data = []
        
        try:
            if client:
                headlines = client.get_finviz_headlines(symbol, max_items=20)
                headlines_data = [h.to_dict() if hasattr(h, 'to_dict') else h for h in headlines]
                logger.info(f"✅ Fetched {len(headlines_data)} headlines for {symbol}")
            else:
                # No client available - show error message, NOT mock data
                logger.warning(f"⚠️ News client not available for {symbol}")
                headlines_data = []
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            headlines_data = []
        
        # If no data, show helpful message
        if not headlines_data:
            headlines_data = [{
                'time': datetime.now().strftime('%I:%M%p'),
                'headline': f'📰 Live news feed connecting... Check API keys if this persists.',
                'link': '',
                'source': 'System'
            }]
        
        news_table = create_news_table(headlines_data)
        count = str(len(headlines_data))
        
        return news_table, count
    
    # Button styling callback (highlight active symbol)
    for sym in DEFAULT_SYMBOLS:
        @app.callback(
            Output(f'scanner-sym-btn-{sym}', 'color'),
            [Input('scanner-selected-symbol', 'data')],
            prevent_initial_call=False
        )
        def update_button_style(selected, btn_sym=sym):
            return "primary" if selected == btn_sym else "outline-primary"
    
    logger.info("✅ Scanner workspace callbacks registered")


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    from dash import Dash
    
    logging.basicConfig(level=logging.INFO)
    
    app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
    app.layout = create_scanner_layout()
    register_scanner_callbacks(app)
    
    print("=" * 60)
    print("Scanner Workspace Test Server")
    print("=" * 60)
    print("Open http://localhost:8054 in your browser")
    
    app.run(debug=True, port=8054)

