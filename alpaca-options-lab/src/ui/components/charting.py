"""
TradingView Lightweight Charts Component - Phase 3: The Cockpit
================================================================
Fast, professional candlestick charts using dash-tvlwc.

Performance: 60fps, handles 10k+ candles smoothly.
Replaces slow Plotly charts for real-time price action.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

# Dash imports
from dash import html, dcc
import dash_bootstrap_components as dbc

# TradingView Lightweight Charts
try:
    from dash_tvlwc import Tvlwc
    TVLWC_AVAILABLE = True
except ImportError:
    TVLWC_AVAILABLE = False
    logging.warning("dash_tvlwc not installed. Run: pip install dash-tvlwc")

logger = logging.getLogger(__name__)


# =============================================================================
# ALPACA DARK THEME
# =============================================================================

ALPACA_DARK = {
    "bg": "#0D1117",
    "paper": "#161B22",
    "bg_tertiary": "#21262D",
    "gold": "#F5C211",
    "text": "#E6EDF3",
    "text_secondary": "#8B949E",
    "grid": "#30363D",
    "success": "#3FB950",  # Bullish candles
    "danger": "#F85149",   # Bearish candles
}


# =============================================================================
# TRADINGVIEW CHART CONFIGURATION
# =============================================================================

def get_tv_chart_config() -> Dict[str, Any]:
    """
    Get TradingView Lightweight Charts configuration.
    
    Optimized for Alpaca Dark theme with professional aesthetics.
    """
    return {
        "layout": {
            "background": {"type": "solid", "color": ALPACA_DARK["paper"]},
            "textColor": ALPACA_DARK["text_secondary"],
            "fontSize": 12,
            "fontFamily": "'SF Mono', 'JetBrains Mono', monospace"
        },
        "grid": {
            "vertLines": {"color": ALPACA_DARK["grid"], "style": 1, "visible": True},
            "horzLines": {"color": ALPACA_DARK["grid"], "style": 1, "visible": True}
        },
        "crosshair": {
            "mode": 1,  # Normal crosshair
            "vertLine": {
                "color": ALPACA_DARK["gold"],
                "width": 1,
                "style": 3,  # Dashed
                "labelBackgroundColor": ALPACA_DARK["gold"]
            },
            "horzLine": {
                "color": ALPACA_DARK["gold"],
                "width": 1,
                "style": 3,
                "labelBackgroundColor": ALPACA_DARK["gold"]
            }
        },
        "rightPriceScale": {
            "borderColor": ALPACA_DARK["grid"],
            "textColor": ALPACA_DARK["text_secondary"],
            "scaleMargins": {"top": 0.1, "bottom": 0.1}
        },
        "timeScale": {
            "borderColor": ALPACA_DARK["grid"],
            "textColor": ALPACA_DARK["text_secondary"],
            "timeVisible": True,
            "secondsVisible": False
        },
        "watermark": {
            "visible": False
        }
    }


def get_candlestick_series_config() -> Dict[str, Any]:
    """Get candlestick series styling configuration."""
    return {
        "upColor": ALPACA_DARK["success"],      # Bullish candles
        "downColor": ALPACA_DARK["danger"],     # Bearish candles
        "borderUpColor": ALPACA_DARK["success"],
        "borderDownColor": ALPACA_DARK["danger"],
        "wickUpColor": ALPACA_DARK["success"],
        "wickDownColor": ALPACA_DARK["danger"],
        "priceFormat": {
            "type": "price",
            "precision": 2,
            "minMove": 0.01
        }
    }


# =============================================================================
# DATA CONVERSION
# =============================================================================

def dataframe_to_tv_format(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert pandas DataFrame to TradingView format.
    
    Args:
        df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            or DateTimeIndex with OHLCV columns
            
    Returns:
        List of dicts: [{'time': '2024-01-01', 'open': 100, 'high': 102, ...}]
    """
    if df is None or len(df) == 0:
        return []
    
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Handle different DataFrame formats
    if 'timestamp' not in df.columns and isinstance(df.index, pd.DatetimeIndex):
        df['timestamp'] = df.index
    
    # Ensure we have required columns
    required_cols = ['open', 'high', 'low', 'close']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        # Try case-insensitive match
        col_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['open', 'high', 'low', 'close', 'volume']:
                col_map[col] = col_lower
        if col_map:
            df = df.rename(columns=col_map)
    
    # Convert timestamp to string format
    if 'timestamp' in df.columns:
        if isinstance(df['timestamp'].iloc[0], (pd.Timestamp, datetime)):
            df['time'] = df['timestamp'].dt.strftime('%Y-%m-%d')
        else:
            df['time'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')
    else:
        # Use index
        df['time'] = pd.to_datetime(df.index).strftime('%Y-%m-%d')
    
    # Build data list with validation
    data = []
    for _, row in df.iterrows():
        # Validate and convert OHLC values
        try:
            open_val = float(row['open']) if not pd.isna(row['open']) else None
            high_val = float(row['high']) if not pd.isna(row['high']) else None
            low_val = float(row['low']) if not pd.isna(row['low']) else None
            close_val = float(row['close']) if not pd.isna(row['close']) else None
            
            # Skip if any required value is None/NaN
            if any(v is None for v in [open_val, high_val, low_val, close_val]):
                logger.warning(f"Skipping candle with NaN values: {row.get('time', 'unknown')}")
                continue
            
            candle = {
                'time': str(row['time']),
                'open': open_val,
                'high': high_val,
                'low': low_val,
                'close': close_val
            }
            
            # Add volume if available and valid
            if 'volume' in row and not pd.isna(row['volume']):
                try:
                    volume_val = float(row['volume'])
                    if volume_val >= 0:  # Volume should be non-negative
                        candle['volume'] = volume_val
                except (ValueError, TypeError):
                    pass  # Skip invalid volume
            
            data.append(candle)
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Error processing candle row: {e}")
            continue
    
    return data


def generate_mock_ohlcv(symbol: str = "SPY", days: int = 60) -> pd.DataFrame:
    """Generate mock OHLCV data for testing."""
    np.random.seed(hash(symbol) % 2**32)
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Starting price
    if symbol == "NVDA":
        base = 140.0
    elif symbol == "TSLA":
        base = 250.0
    elif symbol == "SPY":
        base = 450.0
    else:
        base = 100.0
    
    # Generate price walk
    returns = np.random.randn(days) * 0.02  # 2% daily volatility
    closes = base * np.cumprod(1 + returns)
    
    # Generate OHLC from close
    highs = closes * (1 + np.abs(np.random.randn(days) * 0.01))
    lows = closes * (1 - np.abs(np.random.randn(days) * 0.01))
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    
    volumes = np.random.randint(10000000, 50000000, days)
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })


# =============================================================================
# CHART COMPONENTS
# =============================================================================

def render_tv_chart(df: Optional[pd.DataFrame] = None, 
                   symbol: str = "SPY",
                   height: int = 400,
                   chart_id: str = "tv-chart-main") -> html.Div:
    """
    Render TradingView Lightweight Chart component.
    
    Phase 3: The Cockpit - Fast, professional candlestick charts.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol for title/mock data
        height: Chart height in pixels
        chart_id: Unique ID for the chart
        
    Returns:
        Dash component (Tvlwc if available, else Plotly fallback)
    """
    if not TVLWC_AVAILABLE:
        logger.warning("TradingView charts not available, using Plotly fallback")
        return _render_plotly_fallback(df, symbol, height)
    
    # Generate or convert data
    if df is None or len(df) == 0:
        df = generate_mock_ohlcv(symbol)
    
    tv_data = dataframe_to_tv_format(df)
    
    if not tv_data or len(tv_data) == 0:
        logger.warning(f"No valid chart data for {symbol}, generating mock data")
        df = generate_mock_ohlcv(symbol)
        tv_data = dataframe_to_tv_format(df)
    
    if not tv_data or len(tv_data) == 0:
        return html.Div("No chart data available", style={
            'color': ALPACA_DARK['text_secondary'],
            'padding': '20px',
            'textAlign': 'center'
        })
    
    # Chart options
    chart_options = get_tv_chart_config()
    chart_options['height'] = height
    chart_options['width'] = "100%"
    
    # Series options
    series_options = {
        "candlestick": get_candlestick_series_config()
    }
    
    # Validate tv_data structure before proceeding
    if not tv_data or not isinstance(tv_data, list) or len(tv_data) == 0:
        logger.error(f"No valid chart data for {symbol}")
        return html.Div([
            html.Span("⚠️ Chart data unavailable", style={
                'color': ALPACA_DARK['text'],
                'fontSize': '14px'
            })
        ], style={
            'color': ALPACA_DARK['text_secondary'],
            'padding': '40px 20px',
            'textAlign': 'center',
            'backgroundColor': ALPACA_DARK['paper'],
            'borderRadius': '12px',
            'border': f"1px solid {ALPACA_DARK['grid']}",
            'minHeight': f"{height}px",
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center'
        })
    
    # Double-check each candle has required fields
    valid_candles = []
    for candle in tv_data:
        if isinstance(candle, dict) and all(k in candle for k in ['time', 'open', 'high', 'low', 'close']):
            # Ensure no undefined/None values
            if all(candle[k] is not None for k in ['open', 'high', 'low', 'close']):
                valid_candles.append(candle)
    
    if len(valid_candles) < 2:  # Need at least 2 candles for a meaningful chart
        logger.error(f"Insufficient valid candles for {symbol}: {len(valid_candles)}")
        return html.Div([
            html.Span("⚠️ Insufficient chart data", style={
                'color': ALPACA_DARK['text'],
                'fontSize': '14px'
            })
        ], style={
            'color': ALPACA_DARK['text_secondary'],
            'padding': '40px 20px',
            'textAlign': 'center',
            'backgroundColor': ALPACA_DARK['paper'],
            'borderRadius': '12px',
            'border': f"1px solid {ALPACA_DARK['grid']}",
            'minHeight': f"{height}px",
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center'
        })
    
    # Use validated candles
    tv_data = valid_candles
    series_data = [tv_data]  # Wrap in array for seriesData format
    
    # Calculate price change for header
    current_price = tv_data[-1]['close']
    price_change_pct = ""
    price_change_color = ALPACA_DARK['text_secondary']
    if len(tv_data) > 1:
        prev_price = tv_data[-2]['close']
        change = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
        price_change_pct = f"  {change:+.2f}%"
        price_change_color = ALPACA_DARK['success'] if change > 0 else ALPACA_DARK['danger']
    
    return html.Div([
        # Header
        html.Div([
            html.Span(f"📊 {symbol}", style={
                'fontSize': '14px',
                'fontWeight': '600',
                'color': ALPACA_DARK['text']
            }),
            html.Span(f"  ${current_price:.2f}", style={
                'fontSize': '16px',
                'fontWeight': 'bold',
                'color': ALPACA_DARK['gold'],
                'marginLeft': '8px'
            }),
            html.Span(price_change_pct, style={
                'fontSize': '12px',
                'color': price_change_color,
                'marginLeft': '8px'
            })
        ], style={
            'marginBottom': '8px',
            'paddingBottom': '8px',
            'borderBottom': f"2px solid {ALPACA_DARK['gold']}"
        }),
        
        # TradingView Chart
        html.Div([
            Tvlwc(
                id=chart_id,
                seriesData=series_data,
                seriesTypes=["candlestick"],
                chartOptions=chart_options,
                seriesOptions=[series_options["candlestick"]]
            )
        ], style={'borderRadius': '8px', 'overflow': 'hidden'})
    ], style={
        'backgroundColor': ALPACA_DARK['paper'],
        'padding': '16px',
        'borderRadius': '12px',
        'border': f"1px solid {ALPACA_DARK['grid']}"
    })


def create_tv_candlestick_chart(symbol: str = "SPY", 
                                df: Optional[pd.DataFrame] = None,
                                height: int = 400) -> dbc.Card:
    """
    Create a self-contained TradingView chart card.
    
    Wrapper for render_tv_chart with card styling.
    """
    return dbc.Card([
        dbc.CardBody([
            render_tv_chart(df, symbol, height, f"tv-chart-{symbol.lower()}")
        ])
    ], style={
        'backgroundColor': ALPACA_DARK['paper'],
        'border': f"1px solid {ALPACA_DARK['grid']}",
        'borderRadius': '12px'
    })


def _render_plotly_fallback(df: Optional[pd.DataFrame], 
                            symbol: str,
                            height: int) -> html.Div:
    """Fallback to Plotly if TradingView not available."""
    import plotly.graph_objects as go
    
    if df is None:
        df = generate_mock_ohlcv(symbol)
    
    fig = go.Figure(data=[
        go.Candlestick(
            x=df['timestamp'] if 'timestamp' in df.columns else df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color=ALPACA_DARK['success'],
            decreasing_line_color=ALPACA_DARK['danger']
        )
    ])
    
    fig.update_layout(
        height=height,
        template='plotly_dark',
        plot_bgcolor=ALPACA_DARK['paper'],
        paper_bgcolor=ALPACA_DARK['paper'],
        font={'color': ALPACA_DARK['text']},
        xaxis={'rangeslider': {'visible': False}},
        margin={'l': 20, 'r': 20, 't': 30, 'b': 20}
    )
    
    return html.Div([
        html.Div(f"⚠️ TradingView charts not available (Plotly fallback)", style={
            'color': ALPACA_DARK['text_secondary'],
            'fontSize': '11px',
            'marginBottom': '8px'
        }),
        dcc.Graph(figure=fig, config={'displayModeBar': False})
    ])


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("TradingView Charts Component Test")
    print("=" * 60)
    
    # Test data conversion
    df = generate_mock_ohlcv("NVDA", days=30)
    tv_data = dataframe_to_tv_format(df)
    
    print(f"\n✅ Generated {len(tv_data)} candles")
    print(f"   First: {tv_data[0]}")
    print(f"   Last:  {tv_data[-1]}")
    
    if TVLWC_AVAILABLE:
        print("\n✅ dash_tvlwc is installed and ready")
    else:
        print("\n❌ dash_tvlwc not installed")
        print("   Run: pip install dash-tvlwc")
    
    print("\n" + "=" * 60)

