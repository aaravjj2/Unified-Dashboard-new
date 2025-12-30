"""
Market Trends Tab - Complete Rebuild
=====================================

Market Trends Tab - Analyze market sentiment and trends across sectors."""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import numpy as np
import pandas as pd

from dash import html, callback, Input, Output, State, no_update, ALL, ctx
from dash.exceptions import PreventUpdate
from dash import dcc
import dash_bootstrap_components as dbc
import numpy as np
# Shared UI components for improvements
try:
    from financial_dashboard.components.shared_ui import (
        create_tab_toolbar, create_metric_card, create_summary_stats_row,
        create_loading_skeleton, create_date_range_filter, create_sector_filter,
        create_ticker_filter, create_last_updated_timestamp, create_notification_toast,
        create_refresh_button, create_export_button, create_historical_toggle,
        create_chart_container, create_empty_state
    )
    SHARED_UI_AVAILABLE = True
except ImportError:
    SHARED_UI_AVAILABLE = False


# Import shared utilities
from financial_dashboard import _shared as SH
from financial_dashboard.utils import market_trend as MT
from financial_dashboard.utils.cache_manager import CacheManager
from financial_dashboard.utils.news_manager import NewsManager

# Phase 5: Regime Detection Engine
try:
    from financial_dashboard.tabs.market_trends.regime_engine import RegimeDetector, REGIME_LABELS, REGIME_COLORS
    REGIME_ENGINE_AVAILABLE = True
except ImportError as e:
    REGIME_ENGINE_AVAILABLE = False
try:
    from financial_dashboard.serving.serving_client import ServingClient
    _SC = ServingClient()
except Exception:
    _SC = None
from financial_dashboard.utils.news_client import fetch_news_for_tickers
from financial_dashboard.utils.price_fetcher import PriceFetcher
from financial_dashboard.utils.price_client import PriceClient
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# Log regime engine status after logger is defined
if REGIME_ENGINE_AVAILABLE:
    logger.info("✅ Regime Detection Engine loaded (Phase 5)")

# Finnhub client for sector and market cap data
try:
    import finnhub
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
    if FINNHUB_API_KEY:
        finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
        logger.info("✅ Finnhub client initialized for company data")
    else:
        finnhub_client = None
        logger.warning("⚠️ No FINNHUB_API_KEY found, using placeholder data")
except Exception as e:
    finnhub_client = None
    logger.warning(f"⚠️ Finnhub not available: {e}")


# Sector ETFs for Heatmap
SECTOR_ETFS = {
    'Technology': 'XLK',
    'Financials': 'XLF',
    'Healthcare': 'XLV',
    'Cons. Discretionary': 'XLY',
    'Cons. Staples': 'XLP',
    'Energy': 'XLE',
    'Utilities': 'XLU',
    'Industrials': 'XLI',
    'Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Comm. Services': 'XLC'
}

# ========================================================================
# MODULE-LEVEL INITIALIZATION
# ========================================================================

# Initialize Cache Manager
CACHE_FILE = os.path.join(SH.OUT_ROOT, 'market_brief.json')
cache_manager = CacheManager(CACHE_FILE, SH.RESULTS_CACHE, ttl_seconds=300)

# Initialize News Manager
news_manager = NewsManager(ttl_seconds=300)

logger.info("Market Trends module initialized with CacheManager and NewsManager")

# ========================================================================
# HELPER FUNCTIONS
# ========================================================================

def _sanitize_for_json(obj):
    """Sanitize data for JSON serialization."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    if pd.isna(obj):
        return None
    return str(obj)


# Module-level FinBERT analyzer (lazy loaded)
_finbert_analyzer = None


def _get_finbert_analyzer():
    """Lazy load FinBERT analyzer for better sentiment analysis."""
    global _finbert_analyzer
    if _finbert_analyzer is None:
        try:
            from financial_dashboard.models.finbert_sentiment import FinBERTSentimentAnalyzer
            _finbert_analyzer = FinBERTSentimentAnalyzer()
            if _finbert_analyzer.initialize():
                logger.info("✅ FinBERT analyzer loaded for news sentiment")
            else:
                _finbert_analyzer = False  # Mark as unavailable
        except Exception as e:
            logger.warning(f"FinBERT unavailable, using keyword-based sentiment: {e}")
            _finbert_analyzer = False
    return _finbert_analyzer if _finbert_analyzer else None


def _headline_sentiment(text: str, ticker: str = '') -> Dict[str, Any]:
    """
    Enhanced headline sentiment classifier.

    Returns a dict with keys:
      - 'sentiment': one of 'Bullish'|'Bearish'|'Neutral'
      - 'score': float where positive = bullish, negative = bearish
      - 'confidence': 'high'|'medium'|'low'
      - 'method': 'finbert'|'keyword'

    Uses FinBERT when available, falls back to expanded keyword-based classifier.
    """
    if not text:
        return {'sentiment': 'Neutral', 'score': 0.0, 'confidence': 'low', 'method': 'none'}

    # Try FinBERT first for more accurate sentiment
    analyzer = _get_finbert_analyzer()
    sc = _SC
    if analyzer:
        try:
            result = analyzer.analyze_text(text)
            compound = result.get('compound', 0.0)
            
            # Map compound score to sentiment
            if compound >= 0.2:
                sentiment = 'Bullish'
                confidence = 'high' if compound >= 0.5 else 'medium'
            elif compound <= -0.2:
                sentiment = 'Bearish'
                confidence = 'high' if compound <= -0.5 else 'medium'
            else:
                sentiment = 'Neutral'
                confidence = 'high' if abs(compound) < 0.1 else 'medium'
            
            return {
                'sentiment': sentiment,
                'score': round(compound, 3),
                'confidence': confidence,
                'method': 'finbert'
            }
        except Exception as e:
            logger.debug(f"FinBERT analysis failed, using keyword fallback: {e}")
    # If we have a remote serving client, prefer that for inference
    if sc and sc.mode != 'local':
        try:
            sc_res = sc.analyze_sentiment([text])
            if sc_res.get('status') == 'success' and 'data' in sc_res:
                data = sc_res['data']
                # Support BentoML response format with "sentiments"
                preds = data.get('sentiments') if isinstance(data, dict) and 'sentiments' in data else data
                if isinstance(preds, list) and preds:
                    first = preds[0]
                    label = first.get('sentiment') if 'sentiment' in first else first.get('label', 'neutral')
                    score = first.get('score', 0.0)
                    if label == 'positive' or label == 'bullish':
                        return {'sentiment': 'Bullish', 'score': round(score, 3), 'confidence': 'medium', 'method': 'bento/triton'}
                    if label == 'negative' or label == 'bearish':
                        return {'sentiment': 'Bearish', 'score': round(-score, 3), 'confidence': 'medium', 'method': 'bento/triton'}
        except Exception:
            pass

    # Enhanced keyword-based fallback
    txt = text.lower()

    # Expanded weighted keyword lists (keyword -> weight)
    bullish_keywords = {
        # Strong bullish signals
        'beat': 1.2, 'beats': 1.2, 'beats expectations': 1.8, 'exceeds': 1.3,
        'outperform': 1.3, 'outperforms': 1.3, 'upgrade': 1.4, 'upgraded': 1.4,
        'surge': 1.2, 'surges': 1.2, 'soar': 1.3, 'soars': 1.3, 'jump': 1.0, 'jumps': 1.0,
        'rally': 1.1, 'rallies': 1.1, 'breakout': 1.2, 'breakthrough': 1.1,
        # Moderate bullish
        'rise': 0.8, 'rises': 0.8, 'rising': 0.7, 'gain': 0.8, 'gains': 0.8,
        'strong': 0.7, 'strength': 0.6, 'record': 0.9, 'record high': 1.4,
        'growth': 0.8, 'growing': 0.7, 'expand': 0.6, 'expansion': 0.7,
        'profit': 0.8, 'profitable': 0.7, 'revenue growth': 1.0,
        'positive': 0.6, 'optimistic': 0.8, 'bullish': 1.0,
        'buy': 0.6, 'buying': 0.5, 'acquisition': 0.7, 'deal': 0.5,
        'raise guidance': 1.3, 'beat guidance': 1.5, 'above estimates': 1.2,
        # Tech/AI specific
        'ai breakthrough': 1.3, 'new product': 0.8, 'partnership': 0.6,
        'innovation': 0.7, 'market share': 0.6, 'demand surge': 1.1,
        'orders': 0.5, 'backlog': 0.6, 'momentum': 0.7
    }

    bearish_keywords = {
        # Strong bearish signals
        'miss': -1.2, 'misses': -1.2, 'missed': -1.2, 'missed expectations': -1.5,
        'downgrade': -1.4, 'downgraded': -1.4, 'underperform': -1.3,
        'plunge': -1.4, 'plunges': -1.4, 'crash': -1.5, 'crashes': -1.5,
        'collapse': -1.4, 'tumble': -1.2, 'tumbles': -1.2, 'plummet': -1.4,
        # Moderate bearish
        'drop': -0.9, 'drops': -0.9, 'decline': -0.8, 'declines': -0.8, 'declining': -0.7,
        'fall': -0.8, 'falls': -0.8, 'falling': -0.7, 'slip': -0.6, 'slips': -0.6,
        'weak': -0.8, 'weakness': -0.7, 'weaker': -0.8, 'disappointing': -1.0,
        'loss': -1.0, 'losses': -1.0, 'losing': -0.8, 'lose': -0.7,
        'negative': -0.6, 'pessimistic': -0.8, 'bearish': -1.0,
        'sell': -0.6, 'selling': -0.5, 'selloff': -1.1, 'sell-off': -1.1,
        'warning': -1.1, 'warns': -1.0, 'caution': -0.7, 'concern': -0.6, 'concerns': -0.6,
        'cut guidance': -1.4, 'lower guidance': -1.3, 'below estimates': -1.2,
        'recall': -1.0, 'lawsuit': -0.9, 'investigation': -0.8,
        # Market specific
        'recession': -1.2, 'inflation': -0.5, 'layoff': -0.9, 'layoffs': -1.0,
        'cuts': -0.6, 'cost cutting': -0.4, 'slowdown': -0.8, 'slowing': -0.7,
        'headwinds': -0.7, 'challenges': -0.5, 'uncertainty': -0.6
    }

    score = 0.0
    matched_keywords = []

    # Count occurrences and weight
    for kw, w in bullish_keywords.items():
        if kw in txt:
            score += w
            matched_keywords.append((kw, w))

    for kw, w in bearish_keywords.items():
        if kw in txt:
            score += w
            matched_keywords.append((kw, w))

    # Slight boost if ticker is explicitly mentioned along with sentiment
    if ticker and ticker.lower() in txt:
        if any(kw in txt for kw in ['beat', 'beats', 'upgrade', 'surge', 'rally', 'gain', 'soar']):
            score += 0.3
        if any(kw in txt for kw in ['miss', 'missed', 'downgrade', 'drop', 'decline', 'loss', 'warning']):
            score -= 0.3

    # Lower thresholds for better sensitivity (was 1.5/-1.5)
    if score >= 0.5:
        sentiment = 'Bullish'
    elif score <= -0.5:
        sentiment = 'Bearish'
    else:
        sentiment = 'Neutral'
    
    # Determine confidence based on score magnitude and keyword matches
    abs_score = abs(score)
    if abs_score >= 1.5 and len(matched_keywords) >= 2:
        confidence = 'high'
    elif abs_score >= 0.7:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {'sentiment': sentiment, 'score': round(score, 2), 'confidence': confidence, 'method': 'keyword'}


def _render_table(records: List[Dict]) -> html.Div:
    """
    Render HTML table with test-friendly data attributes.
    
    Args:
        records: List of dicts with ticker data
        
    Returns:
        html.Div containing the table
    """
    if not records:
        return html.Div(
            "No data available. Click 'Run Analysis' to generate results.",
            style={'padding': '20px', 'textAlign': 'center', 'color': '#9ca3af'}
        )
    
    df = pd.DataFrame(records)
    
    # Ensure ticker is first column
    if 'ticker' in df.columns:
        cols = ['ticker'] + [c for c in df.columns if c != 'ticker']
        df = df[cols]
    
    # Build table headers (white text)
    headers = [html.Th(col.replace('_', ' ').title(), style={'color': 'white'}) for col in df.columns]
    
    # Build table rows (white text)
    rows = []
    for _, row in df.iterrows():
        ticker = row.get('ticker', 'UNKNOWN')
        cells = [html.Td(str(row[col]) if not pd.isna(row[col]) else '', style={'color': 'white'}) for col in df.columns]
        rows.append(html.Tr(cells, **{'data-ticker': ticker}))
    
    table = html.Table(
        [html.Thead(html.Tr(headers)), html.Tbody(rows)],
        className='market-trends-table table table-sm',
        **{'data-testid': 'market-trends-data-table'},
        style={
            'width': '100%',
            'borderCollapse': 'collapse',
            'marginTop': '16px',
            'color': 'white',
            'tableLayout': 'auto'
        }
    )
    
    # Wrap the table in a named wrapper for easier targeted styling and
    # to keep horizontal scrolling behavior intact.
    return html.Div(
        table,
        className='market-trends-table-wrapper',
        style={'overflowX': 'auto'}
    )


def _render_news(news_data: Dict[str, List[Dict]]) -> html.Div:
    """
    Render news panel.
    
    Args:
        news_data: Dict mapping ticker to list of news items
        
    Returns:
        html.Div containing news items
    """
    if not news_data or not any(news_data.values()):
        return html.Div(
            "No recent news available",
            **{'data-testid': 'news-panel'},
            style={'padding': '16px', 'color': '#9ca3af', 'textAlign': 'center'}
        )
    
    news_items = []
    for ticker, items in news_data.items():
        for item in items:
            headline = item.get('headline', 'No headline')
            url = item.get('url', '#')
            source = item.get('source', 'Unknown')

            # Compute sentiment with enhanced analyzer
            sentiment_result = _headline_sentiment(headline, ticker)
            sentiment = item.get('sentiment') or sentiment_result.get('sentiment')
            score = item.get('sentiment_score') or sentiment_result.get('score')
            confidence = sentiment_result.get('confidence', 'medium')
            method = sentiment_result.get('method', 'keyword')

            # Enhanced badge styling with confidence indication
            if sentiment == 'Bullish':
                base_color = '#10b981' if confidence != 'low' else '#6ee7b7'
                badge_style = {'backgroundColor': base_color, 'color': 'white', 'padding': '2px 8px', 'borderRadius': '12px', 'fontSize': '12px', 'marginLeft': '8px'}
                emoji = '📈' if confidence == 'high' else '↗️'
            elif sentiment == 'Bearish':
                base_color = '#ef4444' if confidence != 'low' else '#fca5a5'
                badge_style = {'backgroundColor': base_color, 'color': 'white', 'padding': '2px 8px', 'borderRadius': '12px', 'fontSize': '12px', 'marginLeft': '8px'}
                emoji = '📉' if confidence == 'high' else '↘️'
            else:
                badge_style = {'backgroundColor': '#6b7280', 'color': 'white', 'padding': '2px 8px', 'borderRadius': '12px', 'fontSize': '12px', 'marginLeft': '8px'}
                emoji = '➡️'

            # Show score indicator for non-neutral sentiments
            score_indicator = f" ({score:+.2f})" if score != 0 else ""

            news_items.append(
                html.Div([
                    html.A(
                        headline,
                        href=url,
                        target='_blank',
                        style={'color': '#3b82f6', 'textDecoration': 'none'}
                    ),
                    html.Span(
                        f"{emoji} {sentiment}{score_indicator}",
                        className='news-sentiment-badge',
                        **{'data-sentiment': sentiment, 'data-sentiment-score': str(score), 'data-confidence': confidence, 'data-method': method},
                        style=badge_style
                    ),
                    html.Span(
                        f" - {ticker} ({source})",
                        style={'color': '#6b7280', 'fontSize': '12px', 'marginLeft': '8px'}
                    )
                ], style={'marginBottom': '10px', 'padding': '4px 0'})
            )
    
    return html.Div(
        news_items,
        **{'data-testid': 'news-panel'},
        style={'padding': '12px'}
    )


def _compute_market_trend(data: List[Dict]) -> Optional[Dict]:
    """
    Compute market trend from analysis data.
    
    Args:
        data: List of ticker analysis results
        
    Returns:
        Dict with trend info or None
    """
    try:
        # Calculate trend based on IMMEDIATE DAY performance, not moving average
        if not data:
            return None
        
        df = pd.DataFrame(data)
        
        # Try to get today's change from 'change_pct' or 'day_change_pct' field
        # If not available, fall back to 'return_pct' but with adjusted thresholds
        if 'change_pct' in df.columns:
            avg_change = df['change_pct'].mean()
        elif 'day_change_pct' in df.columns:
            avg_change = df['day_change_pct'].mean()
        elif 'return_pct' in df.columns:
            # Fallback: use return_pct but this is period-based, not ideal
            avg_change = df['return_pct'].mean()
            logger.warning("Using period return_pct for market trend - consider adding day_change_pct field")
        else:
            logger.warning("No price change data available for market trend calculation")
            return None
        
        # Thresholds for DAILY changes (much smaller than period-based)
        # Typical daily market moves: -2% to +2% is normal range
        if avg_change > 1.5:
            label = 'Strong Bull'
        elif avg_change > 0.5:
            label = 'Bull'
        elif avg_change > -0.5:
            label = 'Neutral'
        elif avg_change > -1.5:
            label = 'Bear'
        else:
            label = 'Strong Bear'
        
        return {
            'label': label,
            'composite': avg_change,
            'generated_at': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error computing market trend: {e}")
        return None


def _render_screener_results(results: List[Dict]) -> html.Div:
    """Render stock screener results as a table."""
    if not results:
        return html.Div([
            html.P("No stocks match your criteria. Try adjusting the filters.", 
                   style={'textAlign': 'center', 'color': '#64748b', 'padding': '40px'})
        ])
    
    rows = []
    for r in results[:50]:  # Top 50
        trend_color = '#10b981' if r['trend'] == 'bullish' else '#ef4444' if r['trend'] == 'bearish' else '#94a3b8'
        trend_icon = '📈' if r['trend'] == 'bullish' else '📉' if r['trend'] == 'bearish' else '➡️'
        rsi_color = '#ef4444' if r['rsi'] > 70 else '#10b981' if r['rsi'] < 30 else '#94a3b8'
        
        rows.append(html.Tr([
            html.Td(r['ticker'], style={'fontWeight': 'bold', 'color': 'white'}),
            html.Td(f"${r['price']:.2f}", style={'color': 'white'}),
            html.Td(f"{r['volume']:,.0f}", style={'color': '#94a3b8', 'fontSize': '13px'}),
            html.Td(html.Span(f"{trend_icon} {r['trend'].title()}", style={'color': trend_color})),
            html.Td(f"{r['rsi']:.1f}", style={'color': rsi_color}),
            html.Td(
                html.Span(f"{r['score']:.0f}", style={
                    'backgroundColor': '#10b981' if r['score'] >= 70 else '#f59e0b' if r['score'] >= 50 else '#94a3b8',
                    'color': 'white',
                    'padding': '4px 12px',
                    'borderRadius': '12px',
                    'fontSize': '12px',
                    'fontWeight': 'bold'
                })
            )
        ]))
    
    return html.Div([
        html.H5([
            html.I(className="bi bi-check-circle-fill me-2", style={'color': '#10b981'}),
            f"Found {len(results)} Matching Stocks"
        ], className="mb-3", style={'color': 'white'}),
        dbc.Table([
            html.Thead(html.Tr([
                html.Th("Ticker", style={'color': '#94a3b8'}),
                html.Th("Price", style={'color': '#94a3b8'}),
                html.Th("Volume", style={'color': '#94a3b8'}),
                html.Th("Trend", style={'color': '#94a3b8'}),
                html.Th("RSI", style={'color': '#94a3b8'}),
                html.Th("Score", style={'color': '#94a3b8'})
            ])),
            html.Tbody(rows)
        ], striped=True, hover=True, responsive=True, style={'fontSize': '14px', 'backgroundColor': 'rgba(0,0,0,0.3)'})
    ])


def _compute_multi_timeframe_trends(price_results: Dict) -> Dict[str, Any]:
    """
    Compute market trends across multiple timeframes (1D, 1W, 1M).
    
    Args:
        price_results: Dict of ticker -> price data from PriceClient
        
    Returns:
        Dict with multi-timeframe trend data
    """
    try:
        timeframes = {}
        
        for period_name, lookback_days in [('1D', 1), ('1W', 7), ('1M', 30)]:
            period_changes = []
            
            for ticker, data in price_results.items():
                if 'prices' not in data or len(data['prices']) < lookback_days + 1:
                    continue
                
                prices = data['prices']
                current_price = prices[-1]
                past_price = prices[-(lookback_days + 1)]
                
                if past_price and current_price and past_price > 0:
                    change_pct = ((current_price - past_price) / past_price) * 100
                    period_changes.append(change_pct)
            
            if not period_changes:
                timeframes[period_name] = {
                    'trend': 'Unknown',
                    'avg_change': 0.0,
                    'signal': 'HOLD'
                }
                continue
            
            avg_change = sum(period_changes) / len(period_changes)
            
            # Determine trend based on average change
            # Adjust thresholds based on timeframe
            if period_name == '1D':
                thresholds = (1.5, 0.5, -0.5, -1.5)
            elif period_name == '1W':
                thresholds = (3.0, 1.0, -1.0, -3.0)
            else:  # 1M
                thresholds = (5.0, 2.0, -2.0, -5.0)
            
            if avg_change > thresholds[0]:
                trend = 'Strong Bull'
                signal = 'BUY'
            elif avg_change > thresholds[1]:
                trend = 'Bull'
                signal = 'BUY'
            elif avg_change > thresholds[2]:
                trend = 'Neutral'
                signal = 'HOLD'
            elif avg_change > thresholds[3]:
                trend = 'Bear'
                signal = 'SELL'
            else:
                trend = 'Strong Bear'
                signal = 'SELL'
            
            timeframes[period_name] = {
                'trend': trend,
                'avg_change': round(avg_change, 2),
                'signal': signal,
                'sample_size': len(period_changes)
            }
        
        # Determine overall trend alignment
        signals = [tf['signal'] for tf in timeframes.values()]
        if all(s == 'BUY' for s in signals):
            alignment = 'STRONG BUY - All timeframes bullish'
            alignment_strength = 'PERFECT'
        elif all(s == 'SELL' for s in signals):
            alignment = 'STRONG SELL - All timeframes bearish'
            alignment_strength = 'PERFECT'
        elif signals.count('BUY') >= 2:
            alignment = 'BUY - Majority bullish'
            alignment_strength = 'GOOD'
        elif signals.count('SELL') >= 2:
            alignment = 'SELL - Majority bearish'
            alignment_strength = 'GOOD'
        else:
            alignment = 'MIXED - Conflicting signals'
            alignment_strength = 'WEAK'
        
        return {
            'timeframes': timeframes,
            'alignment': alignment,
            'alignment_strength': alignment_strength,
            'generated_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error computing multi-timeframe trends: {e}")
        return {
            'timeframes': {},
            'alignment': 'Error',
            'alignment_strength': 'UNKNOWN',
            'error': str(e)
        }


def _compute_risk_metrics(price_results: Dict, risk_free_rate: float = 0.04) -> Dict[str, Any]:
    """
    Compute risk metrics for market analysis.
    
    Args:
        price_results: Dict of ticker -> price data from PriceClient
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino calculations
        
    Returns:
        Dict with risk metrics
    """
    try:
        logger.info(f"🔍 Computing risk metrics for {len(price_results)} tickers")
        all_returns = []
        for ticker, data in price_results.items():
            if 'prices' not in data or len(data['prices']) < 2:
                continue
            prices = data['prices']
            # Calculate daily returns
            for i in range(1, len(prices)):
                if prices[i] and prices[i-1] and prices[i-1] > 0:
                    daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                    all_returns.append(daily_return)
        
        if not all_returns or len(all_returns) < 2:
            return {'error': 'Insufficient data for risk metrics'}
        
        import numpy as np
        returns_array = np.array(all_returns)
        
        # Calculate metrics
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        # Sharpe Ratio (annualized)
        daily_rf = risk_free_rate / 252
        sharpe = ((mean_return - daily_rf) / std_return) * np.sqrt(252) if std_return > 0 else 0.0
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns_array[returns_array < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else std_return
        sortino = ((mean_return - daily_rf) / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0
        
        # Maximum Drawdown
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdown) * 100  # Convert to percentage
        
        # Calmar Ratio (return / max drawdown)
        annual_return = (np.prod(1 + returns_array) ** (252 / len(returns_array)) - 1) * 100
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # Volatility (annualized)
        annual_vol = std_return * np.sqrt(252) * 100
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns_array, 5) * 100
        
        return {
            'sharpe_ratio': round(sharpe, 3),
            'sortino_ratio': round(sortino, 3),
            'max_drawdown_pct': round(max_drawdown, 2),
            'calmar_ratio': round(calmar, 3),
            'annual_volatility_pct': round(annual_vol, 2),
            'annual_return_pct': round(annual_return, 2),
            'value_at_risk_95_pct': round(var_95, 2),
            'sample_size': len(all_returns),
            'generated_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error computing risk metrics: {e}")
        return {'error': str(e)}


def _compute_momentum_indicators(price_results: Dict) -> Dict[str, Any]:
    """
    Compute advanced momentum indicators for market analysis.
    
    Args:
        price_results: Dict of ticker -> price data from PriceClient
        
    Returns:
        Dict with momentum indicators
    """
    try:
        import numpy as np
        
        all_rsi = []
        all_macd_signal = []
        all_stoch = []
        all_williams = []
        
        for ticker, data in price_results.items():
            if 'prices' not in data or len(data['prices']) < 30:
                continue
            
            prices = np.array(data['prices'])
            
            # RSI (Relative Strength Index) - 14 period
            if len(prices) >= 14:
                deltas = np.diff(prices)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                
                avg_gain = np.mean(gains[-14:])
                avg_loss = np.mean(losses[-14:])
                
                if avg_loss > 0:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    all_rsi.append(rsi)
            
            # MACD (Moving Average Convergence Divergence)
            if len(prices) >= 26:
                # 12-period EMA
                ema12 = prices[-12:].mean()
                # 26-period EMA
                ema26 = prices[-26:].mean()
                # MACD line
                macd = ema12 - ema26
                # Signal line (9-period EMA of MACD)
                macd_signal = macd  # Simplified
                all_macd_signal.append(1 if macd > 0 else -1)
            
            # Stochastic Oscillator - 14 period
            if len(prices) >= 14:
                period_high = np.max(prices[-14:])
                period_low = np.min(prices[-14:])
                current = prices[-1]
                
                if period_high > period_low:
                    stoch_k = ((current - period_low) / (period_high - period_low)) * 100
                    all_stoch.append(stoch_k)
            
            # Williams %R - 14 period
            if len(prices) >= 14:
                period_high = np.max(prices[-14:])
                period_low = np.min(prices[-14:])
                current = prices[-1]
                
                if period_high > period_low:
                    williams = ((period_high - current) / (period_high - period_low)) * -100
                    all_williams.append(williams)
        
        # Aggregate indicators
        result = {
            'generated_at': datetime.now().isoformat()
        }
        
        if all_rsi:
            avg_rsi = np.mean(all_rsi)
            result['rsi'] = {
                'value': round(avg_rsi, 2),
                'signal': 'Overbought' if avg_rsi > 70 else 'Oversold' if avg_rsi < 30 else 'Neutral',
                'interpretation': 'Strong sell signal' if avg_rsi > 80 else 'Sell signal' if avg_rsi > 70 else 'Buy signal' if avg_rsi < 30 else 'Strong buy signal' if avg_rsi < 20 else 'Neutral'
            }
        
        if all_macd_signal:
            macd_bullish = sum(1 for x in all_macd_signal if x > 0) / len(all_macd_signal)
            result['macd'] = {
                'bullish_pct': round(macd_bullish * 100, 2),
                'signal': 'Bullish' if macd_bullish > 0.6 else 'Bearish' if macd_bullish < 0.4 else 'Neutral'
            }
        
        if all_stoch:
            avg_stoch = np.mean(all_stoch)
            result['stochastic'] = {
                'value': round(avg_stoch, 2),
                'signal': 'Overbought' if avg_stoch > 80 else 'Oversold' if avg_stoch < 20 else 'Neutral'
            }
        
        if all_williams:
            avg_williams = np.mean(all_williams)
            result['williams_r'] = {
                'value': round(avg_williams, 2),
                'signal': 'Overbought' if avg_williams > -20 else 'Oversold' if avg_williams < -80 else 'Neutral'
            }
        
        # Overall momentum signal
        signals = []
        if 'rsi' in result:
            if result['rsi']['signal'] == 'Oversold':
                signals.append('BUY')
            elif result['rsi']['signal'] == 'Overbought':
                signals.append('SELL')
        
        if 'macd' in result:
            if result['macd']['signal'] == 'Bullish':
                signals.append('BUY')
            elif result['macd']['signal'] == 'Bearish':
                signals.append('SELL')
        
        if signals:
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')
            if buy_count > sell_count:
                result['overall_signal'] = 'BUY'
            elif sell_count > buy_count:
                result['overall_signal'] = 'SELL'
            else:
                result['overall_signal'] = 'NEUTRAL'
        else:
            result['overall_signal'] = 'NEUTRAL'
        
        result['sample_size'] = len(price_results)
        
        return result
    
    except Exception as e:
        logger.error(f"Error computing momentum indicators: {e}")
        return {'error': str(e)}


# ========================================================================
# BACKGROUND JOB FUNCTION
# ========================================================================

def run_full_analysis(tickers_str: str, period: str = '1y', 
                     include_news: bool = True, 
                      include_options: bool = False) -> Dict[str, Any]:
    """
    Run full market trends analysis (background job entrypoint).
    
    Args:
        tickers_str: Comma-separated ticker symbols
        period: Time period (e.g., '1y', '6mo')
        include_news: Whether to fetch news
        include_options: Whether to include options analysis
        
    Returns:
        Dict with analysis results
    """
    try:
        logger.info(f"Starting market trends analysis: tickers={tickers_str}, period={period}")
        
        # Parse tickers
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        
        if not tickers:
            return {'error': 'No valid tickers provided'}
        
        # Initialize unified price client (prefers Alpaca -> Finnhub -> yfinance)
        price_client = PriceClient()

        # Fetch real price data for all tickers (1y lookback for month_start)
        logger.info(f"Fetching price data for {len(tickers)} tickers via PriceClient...")
        # investment_per_ticker used to compute profit/loss (keeps previous behaviour)
        price_results = price_client.get_prices(tickers, lookback_days=365, investment_per_ticker=1000.0)

        # Log provider usage summary so tests and ops can see which upstreams were used
        try:
            provider_counts = {}
            for tk, pdata in price_results.items():
                src = pdata.get('source', 'Local')
                provider_counts[src] = provider_counts.get(src, 0) + 1

            logger.info(f"Price provider usage summary: {provider_counts}")
            # Also attach a short human-readable summary to the response for debugging
            price_provider_summary = ', '.join([f"{k}:{v}" for k, v in provider_counts.items()])
        except Exception:
            price_provider_summary = 'unknown'
            logger.exception("Failed to compute price provider summary")
        
        # Build results with real data
        results = []
        total_return = 0.0
        valid_count = 0
        
        for ticker in tickers:
            try:
                price_data = price_results.get(ticker)
                
                if not price_data:
                    logger.warning(f"No price data for {ticker}")
                    results.append({
                        'ticker': ticker,
                        'error': 'Price data unavailable'
                    })
                    continue
                
                # Calculate return percentage
                current = price_data['current_price']
                month_start = price_data['month_start_price']
                return_pct = ((current - month_start) / month_start * 100) if month_start > 0 else 0.0
                
                # Calculate volatility (approximation based on daily change percent)
                # PriceClient returns daily_change as percent in most providers
                raw_daily = price_data.get('daily_change', 0.0) or 0.0
                # Ensure absolute percent value
                daily_change_pct = abs(raw_daily)
                volatility = daily_change_pct * 15.8  # Annualize approximation
                
                result = {
                    'ticker': ticker,
                    'current_price': current,
                    'daily_change': price_data['daily_change'],
                    'day_change_pct': raw_daily,  # Add immediate day change percentage for trend calculation
                    'week_start_price': price_data['week_start_price'],
                    'month_start_price': month_start,
                    'return_pct': round(return_pct, 2),
                    'volatility': round(volatility, 2),
                    'profit_loss': price_data['profit_loss'],
                    'data_source': price_data['source'],
                    'analyzed_at': datetime.now().isoformat()
                }
                results.append(result)
                
                # Track for market trend calculation
                total_return += return_pct
                valid_count += 1
                
                logger.info(f"✅ {ticker}: ${current:.2f} ({return_pct:+.2f}%)")
                
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                results.append({
                    'ticker': ticker,
                    'error': str(e)
                })
        
        # Compute market trend from aggregated data
        market_trend = None
        if valid_count > 0:
            avg_return = total_return / valid_count
            
            # Simple classification
            if avg_return > 5:
                label = 'Strong Bull'
                color = '#10b981'
            elif avg_return > 2:
                label = 'Bull'
                color = '#84cc16'
            elif avg_return > -2:
                label = 'Neutral'
                color = '#94a3b8'
            elif avg_return > -5:
                label = 'Bear'
                color = '#f59e0b'
            else:
                label = 'Strong Bear'
                color = '#ef4444'
            
            market_trend = {
                'label': label,
                'composite': round(avg_return / 10, 2),  # Normalize to -1 to 1 scale
                'avg_return': round(avg_return, 2),
                'color': color,
                'generated_at': datetime.now().isoformat(),
                'source': 'calculated',
                'ticker_count': valid_count
            }
            
            logger.info(f"📊 Market Trend: {label} (avg return: {avg_return:+.2f}%)")
        
        # Compute multi-timeframe trends
        multi_timeframe = _compute_multi_timeframe_trends(price_results)
        logger.info(f"🔄 Multi-Timeframe: {multi_timeframe.get('alignment', 'N/A')}")
        
        # Compute risk-adjusted metrics
        risk_metrics = _compute_risk_metrics(price_results)
        if 'error' not in risk_metrics:
            logger.info(f"📊 Risk Metrics: Sharpe={risk_metrics.get('sharpe_ratio')}, MaxDD={risk_metrics.get('max_drawdown_pct')}%")
        
        # Compute momentum indicators
        momentum_indicators = _compute_momentum_indicators(price_results)
        if 'error' not in momentum_indicators:
            logger.info(f"📈 Momentum: RSI={momentum_indicators.get('rsi', {}).get('value')}, Signal={momentum_indicators.get('overall_signal')}")
        
        # Fetch news if requested
        news_data = {}
        if include_news and valid_count > 0:
            try:
                # Get news for top 5 tickers by return
                sorted_results = sorted(
                    [r for r in results if 'return_pct' in r],
                    key=lambda x: x['return_pct'],
                    reverse=True
                )
                top_tickers = [r['ticker'] for r in sorted_results[:5]]
                
                logger.info(f"Fetching news for top tickers: {top_tickers}")
                news_data = news_manager.fetch_news(top_tickers, max_per_ticker=2)
                # Annotate each news item with a sentiment prediction so the
                # cached response persists it for UI and tests.
                for tk, items in list(news_data.items()):
                    annotated = []
                    for it in items:
                        try:
                            headline = it.get('headline', '')
                            s = _headline_sentiment(headline, tk)
                            it['sentiment'] = s.get('sentiment')
                            it['sentiment_score'] = s.get('score')
                        except Exception:
                            it['sentiment'] = 'Neutral'
                            it['sentiment_score'] = 0.0
                        annotated.append(it)
                    news_data[tk] = annotated

                logger.info(f"✅ Fetched and annotated news for {len(news_data)} tickers")
            except Exception as e:
                logger.error(f"Error fetching news: {e}")
        
        # Build response
        response = {
            'detailed': results,
            'market_trend': market_trend,
            'multi_timeframe': multi_timeframe,
            'risk_metrics': risk_metrics,
            'momentum_indicators': momentum_indicators,
            'news': news_data,
            'generated_at': datetime.now().isoformat(),
            'price_provider_summary': price_provider_summary if 'price_provider_summary' in locals() else 'unknown',
            'tickers': tickers,
            'period': period,
            'success_count': valid_count,
            'total_count': len(tickers)
        }
        
        # Save to cache (also updates memory automatically)
        cache_manager.save_to_disk(response)
        
        logger.info(f"✅ Analysis complete: {valid_count}/{len(tickers)} tickers analyzed successfully")
        logger.info(f"📊 Response keys: {list(response.keys())}")
        logger.info(f"📊 Multi-timeframe keys: {list(response.get('multi_timeframe', {}).keys())}")
        logger.info(f"📊 Risk metrics keys: {list(response.get('risk_metrics', {}).keys())}")
        logger.info(f"📊 Momentum keys: {list(response.get('momentum_indicators', {}).keys())}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        return {'error': str(e)}


# ============================================================================
# Stock Screener
# ============================================================================

# Module-level cache for screener results
_SCREENER_CACHE = {}
_SCREENER_CACHE_TIMESTAMP = {}
SCREENER_CACHE_TTL = 300  # 5 minutes

# Company data cache (sector, market cap) - 24 hour TTL
_COMPANY_DATA_CACHE = {}
_COMPANY_DATA_TIMESTAMP = {}
COMPANY_DATA_TTL = 86400  # 24 hours

def _get_company_data(ticker: str) -> Dict[str, Any]:
    """
    Get company profile data (sector, market cap) from Finnhub with caching.
    Falls back to placeholders if API unavailable.
    """
    from datetime import datetime
    
    # Check cache first
    if ticker in _COMPANY_DATA_CACHE:
        cache_time = _COMPANY_DATA_TIMESTAMP.get(ticker, 0)
        if datetime.now().timestamp() - cache_time < COMPANY_DATA_TTL:
            return _COMPANY_DATA_CACHE[ticker]
    
    # Try Finnhub API
    if finnhub_client:
        try:
            profile = finnhub_client.company_profile2(symbol=ticker)
            if profile:
                data = {
                    'sector': profile.get('finnhubIndustry', 'Unknown'),
                    'market_cap': profile.get('marketCapitalization', 0) * 1_000_000  # Convert from millions
                }
                # Cache the result
                _COMPANY_DATA_CACHE[ticker] = data
                _COMPANY_DATA_TIMESTAMP[ticker] = datetime.now().timestamp()
                return data
        except Exception as e:
            logger.debug(f"Finnhub API error for {ticker}: {str(e)[:50]}")
    
    # Fallback to placeholder
    return {
        'sector': 'Unknown',
        'market_cap': 0
    }

def _screen_stocks(
    universe: List[str],
    min_price: float = 0,
    max_price: float = float('inf'),
    min_volume: int = 0,
    min_market_cap: float = 0,
    sectors: List[str] = None,
    min_rsi: float = 0,
    max_rsi: float = 100,
    trend: str = None
) -> List[Dict]:
    """
    Screen stocks based on multiple criteria using free APIs.
    Now with caching and parallel processing for better performance.
    
    Args:
        universe: List of ticker symbols to screen
        min_price: Minimum stock price
        max_price: Maximum stock price
        min_volume: Minimum daily volume
        min_market_cap: Minimum market capitalization
        sectors: List of sectors to include (None = all)
        min_rsi: Minimum RSI value (0-100)
        max_rsi: Maximum RSI value (0-100)
        trend: 'bullish', 'bearish', 'neutral', or None for any
    
    Returns:
        List of dicts with stock data and scores
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime
    
    # Create cache key from filter parameters
    cache_key = f"{min_price}_{max_price}_{min_volume}_{min_rsi}_{max_rsi}_{trend}"
    
    # Check cache
    if cache_key in _SCREENER_CACHE:
        cache_time = _SCREENER_CACHE_TIMESTAMP.get(cache_key, 0)
        if datetime.now().timestamp() - cache_time < SCREENER_CACHE_TTL:
            logger.info(f"📦 Returning cached screener results ({len(_SCREENER_CACHE[cache_key])} stocks)")
            return _SCREENER_CACHE[cache_key]
    
    logger.info(f"🔍 Screening {len(universe)} stocks with filters: price=${min_price}-${max_price}, vol={min_volume}, RSI={min_rsi}-{max_rsi}, trend={trend}")
    
    price_client = PriceClient()
    
    def screen_single_stock(ticker: str) -> Optional[Dict]:
        """Screen a single stock - used for parallel processing"""
        try:
            # Get price history
            logger.debug(f"📊 Fetching price data for {ticker}...")
            price_data = price_client.get_price_history(
                ticker,
                period='2mo',  # 60 days for RSI
                interval='1d'
            )
            
            if not price_data or price_data.empty or len(price_data) < 14:
                logger.warning(f"❌ {ticker}: Insufficient data (got {len(price_data) if price_data is not None and not price_data.empty else 0} bars, need 14+)")
                return None
            
            logger.debug(f"✅ {ticker}: Got {len(price_data)} bars of data")
            
            # Get current price and volume
            current_price = float(price_data['Close'].iloc[-1])
            current_volume = int(price_data['Volume'].iloc[-1])
            
            # Apply price filter
            if current_price < min_price or current_price > max_price:
                return None
            
            # Apply volume filter
            if current_volume < min_volume:
                return None
            
            # Calculate RSI
            closes = price_data['Close'].values
            if len(closes) >= 14:
                deltas = np.diff(closes)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                avg_gain = np.mean(gains[-14:])
                avg_loss = np.mean(losses[-14:])
                if avg_loss > 0:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                else:
                    rsi = 100
            else:
                rsi = 50
            
            # Apply RSI filter
            if rsi < min_rsi or rsi > max_rsi:
                return None
            
            # Calculate trend using SMA
            if len(closes) >= 20:
                sma_20 = np.mean(closes[-20:])
            else:
                sma_20 = current_price
                
            if current_price > sma_20 * 1.02:
                stock_trend = 'bullish'
            elif current_price < sma_20 * 0.98:
                stock_trend = 'bearish'
            else:
                stock_trend = 'neutral'
            
            # Apply trend filter
            if trend and trend != 'any' and stock_trend != trend:
                return None
            
            # Calculate score (0-100)
            score = 50
            
            # Price momentum
            if len(closes) >= 5:
                week_change = ((closes[-1] - closes[-5]) / closes[-5]) * 100
                if week_change > 5:
                    score += 15
                elif week_change > 2:
                    score += 10
                elif week_change < -5:
                    score -= 15
            
            # Trend bonus
            if stock_trend == 'bullish':
                score += 15
            elif stock_trend == 'bearish':
                score -= 10
            
            # RSI bonuses
            if rsi < 30:  # Oversold - potential buy
                score += 20
            elif rsi > 70:  # Overbought - caution
                score -= 15
            elif 40 <= rsi <= 60:  # Healthy range
                score += 5
            
            # Volume bonus
            if current_volume > 5_000_000:
                score += 10
            elif current_volume > 1_000_000:
                score += 5
            
            # Get real company data (sector, market cap)
            company_data = _get_company_data(ticker)
            
            return {
                'ticker': ticker,
                'price': current_price,
                'volume': current_volume,
                'market_cap': company_data['market_cap'],
                'sector': company_data['sector'],
                'rsi': rsi,
                'trend': stock_trend,
                'score': max(0, min(100, score))
            }
            
        except Exception as e:
            logger.warning(f"Failed to screen {ticker}: {str(e)[:100]}")
            return None
    
    # Process stocks in parallel using ThreadPoolExecutor
    results = []
    try:
        # Use up to 10 workers for parallel processing
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_ticker = {executor.submit(screen_single_stock, ticker): ticker 
                              for ticker in universe}
            
            # Collect results as they complete
            for future in as_completed(future_to_ticker):
                result = future.result()
                if result:
                    results.append(result)
                    logger.debug(f"✅ {result['ticker']}: ${result['price']:.2f}, Vol={result['volume']:,}, RSI={result['rsi']:.1f}, Score={result['score']}")
        
        logger.info(f"✅ Screening complete: {len(results)}/{len(universe)} stocks passed filters")
        
        # Cache the results
        _SCREENER_CACHE[cache_key] = results
        _SCREENER_CACHE_TIMESTAMP[cache_key] = datetime.now().timestamp()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Screening failed: {e}", exc_info=True)
        return []





# ========================================================================
# UI HELPER FOR NEW IMPROVEMENTS
# ========================================================================

def _create_improvement_cards(result: Dict) -> html.Div:
    """Create UI cards for multi-timeframe, risk metrics, and momentum indicators."""
    logger.info(f"🎨 Creating improvement cards from result with keys: {list(result.keys())[:15]}")
    cards = []
    
    # Multi-Timeframe Analysis Card - HORIZONTAL LAYOUT
    mtf = result.get('multi_timeframe', {})
    if mtf and 'timeframes' in mtf:
        timeframes = mtf['timeframes']
        alignment = mtf.get('alignment', 'Unknown')
        strength = mtf.get('alignment_strength', 'UNKNOWN')
        
        # Color based on alignment strength
        strength_color = '#10b981' if strength == 'PERFECT' else '#f59e0b' if strength == 'GOOD' else '#94a3b8'
        
        # Create horizontal period badges
        period_badges = []
        for period, data in timeframes.items():
            signal_color = '#10b981' if data['signal'] == 'BUY' else '#ef4444' if data['signal'] == 'SELL' else '#94a3b8'
            
            period_badges.append(
                html.Div([
                    html.Div(period, style={
                        'fontSize': '11px',
                        'fontWeight': 'bold',
                        'color': '#94a3b8',
                        'marginBottom': '4px'
                    }),
                    html.Div(data['trend'], style={
                        'fontSize': '13px',
                        'fontWeight': '600',
                        'color': 'white',
                        'marginBottom': '2px'
                    }),
                    html.Div(f"{data['avg_change']:+.2f}%", style={
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'color': signal_color,
                        'marginBottom': '4px'
                    }),
                    html.Span(data['signal'], style={
                        'backgroundColor': signal_color,
                        'color': 'white',
                        'padding': '3px 10px',
                        'borderRadius': '12px',
                        'fontSize': '10px',
                        'fontWeight': 'bold'
                    })
                ], style={
                    'textAlign': 'center',
                    'flex': '1',
                    'padding': '12px 8px',
                    'backgroundColor': 'rgba(255,255,255,0.03)',
                    'borderRadius': '8px',
                    'border': f'1px solid {signal_color}33'
                })
            )
        
        cards.append(dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-clock-history me-2"),
                    "Multi-Timeframe Analysis"
                ]),
                dbc.CardBody([
                    html.Div([
                        html.Span("Market Alignment: ", style={'fontSize': '12px', 'color': '#94a3b8'}),
                        html.Span(alignment, style={
                            'fontSize': '14px',
                            'fontWeight': 'bold',
                            'color': strength_color,
                            'marginLeft': '6px'
                        })
                    ], className="mb-3"),
                    html.Div(period_badges, style={
                        'display': 'flex',
                        'gap': '12px',
                        'justifyContent': 'space-between'
                    })
                ])
            ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})
        ], width=4))
    
    # Risk Metrics Card
    risk = result.get('risk_metrics', {})
    if risk and 'sharpe_ratio' in risk:
        risk_items = [
            ("Sharpe Ratio", risk.get('sharpe_ratio'), ">1 is good"),
            ("Sortino Ratio", risk.get('sortino_ratio'), ">1 is good"),
            ("Max Drawdown", f"{risk.get('max_drawdown_pct', 0):.2f}%", "Lower is better"),
            ("Calmar Ratio", risk.get('calmar_ratio'), ">1 is good"),
            ("Annual Vol", f"{risk.get('annual_volatility_pct', 0):.1f}%", ""),
            ("VaR 95%", f"{risk.get('value_at_risk_95_pct', 0):.2f}%", "5% worst case")
        ]
        
        risk_rows = []
        for label, value, note in risk_items:
            risk_rows.append(html.Tr([
                html.Td(label, style={'fontWeight': 'bold'}),
                html.Td(str(value)),
                html.Td(html.Small(note, className="text-muted"))
            ]))
        
        cards.append(dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-shield-check me-2"),
                    "Risk-Adjusted Metrics"
                ]),
                dbc.CardBody([
                    dbc.Table([
                        html.Tbody(risk_rows)
                    ], size="sm", striped=True, style={'backgroundColor': 'rgba(0,0,0,0.3)'})
                ])
            ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})
        ], width=4))
    
    # Momentum Indicators Card
    momentum = result.get('momentum_indicators', {})
    if momentum and 'overall_signal' in momentum:
        overall_signal = momentum.get('overall_signal', 'NEUTRAL')
        signal_color = '#10b981' if overall_signal == 'BUY' else '#ef4444' if overall_signal == 'SELL' else '#94a3b8'
        
        momentum_items = []
        if 'rsi' in momentum:
            rsi = momentum['rsi']
            momentum_items.append(("RSI", f"{rsi['value']:.1f}", rsi['signal']))
        if 'macd' in momentum:
            macd = momentum['macd']
            momentum_items.append(("MACD", f"{macd['bullish_pct']:.0f}% Bullish", macd['signal']))
        if 'stochastic' in momentum:
            stoch = momentum['stochastic']
            momentum_items.append(("Stochastic", f"{stoch['value']:.1f}", stoch['signal']))
        if 'williams_r' in momentum:
            will = momentum['williams_r']
            momentum_items.append(("Williams %R", f"{will['value']:.1f}", will['signal']))
        
        momentum_rows = []
        for indicator, value, signal in momentum_items:
            sig_color = '#10b981' if 'Oversold' in signal or 'Bullish' in signal else '#ef4444' if 'Overbought' in signal or 'Bearish' in signal else '#94a3b8'
            momentum_rows.append(html.Tr([
                html.Td(indicator, style={'fontWeight': 'bold'}),
                html.Td(value),
                html.Td(html.Span(signal, style={'color': sig_color}))
            ]))
        
        cards.append(dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-graph-up me-2"),
                    "Momentum Indicators"
                ]),
                dbc.CardBody([
                    html.Div([
                        html.Span("Overall Signal: ", style={'fontWeight': 'bold'}),
                        html.Span(overall_signal, style={
                            'backgroundColor': signal_color,
                            'color': 'white',
                            'padding': '4px 12px',
                            'borderRadius': '4px',
                            'fontWeight': 'bold'
                        })
                    ], className="mb-3 text-center"),
                    dbc.Table([
                        html.Tbody(momentum_rows)
                    ], size="sm", striped=True, style={'backgroundColor': 'rgba(0,0,0,0.3)'}
                ])
            ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})
        ], width=4))
    
    if cards:
        logger.info(f"✅ Created {len(cards)} improvement cards")
        return html.Div([
            html.Hr(style={'borderColor': 'rgba(255,255,255,0.1)', 'margin': '20px 0'}),
            html.H5("Advanced Analytics", className="mb-3", style={'color': 'white'}),
            dbc.Row(cards, className="g-3 mb-4")
        ])
    else:
        logger.warning("⚠️ No improvement cards created - data may be missing")
    return html.Div()


# ========================================================================
# LAYOUT
# ========================================================================

def layout():
    """
    Market Trends tab layout.
    """
    logger.info("🎨 layout() called - starting")
    
    # Load cached data for initial render (with error handling)
    cached = {}
    try:
        cached = cache_manager.load_from_disk()
        logger.info(f"Loaded {len(cached.get('detailed', []))} records from cache for layout")
    except Exception as e:
        logger.warning(f"Could not load cache for layout: {e}")
    
    logger.info("Rendering initial table...")
    # Pre-render table if cache exists
    initial_table = _render_table(cached.get('detailed', []))
    logger.info("Rendering improvement cards from cache...")
    initial_improvement_cards = _create_improvement_cards(cached)
    logger.info("Combining table and improvement cards...")
    initial_results = html.Div([
        initial_table,
        initial_improvement_cards
    ])
    logger.info("Rendering initial news...")
    initial_news = _render_news(cached.get('news', {}))
    
    # Market trend badge
    trend_badge = html.Span(
        'Market Trend: Unknown',
        **{'data-testid': 'market-trend-badge'},
        style={
            'backgroundColor': '#94a3b8',
            'color': 'white',
            'padding': '4px 12px',
            'borderRadius': '4px',
            'fontSize': '14px',
            'fontWeight': 'bold',
            'marginLeft': '12px'
        }
    )
    
    if cached and 'market_trend' in cached:
        trend = cached['market_trend']
        trend_badge = html.Span(
            f"Market Trend: {trend.get('label', 'Unknown')}",
            **{'data-testid': 'market-trend-badge'},
            style={
                'backgroundColor': '#10b981',
                'color': 'white',
                'padding': '4px 12px',
                'borderRadius': '4px',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'marginLeft': '12px'
            }
        )

    # Provider summary (visible for diagnostics and tests)
    provider_summary_text = cached.get('price_provider_summary') if cached else None
    provider_summary = html.Span(
        f"Providers used: {provider_summary_text if provider_summary_text else 'unknown'}",
        id='mt-provider-summary',
        **{'data-testid': 'mt-provider-summary'},
        style={
            'marginLeft': '12px',
            'color': 'white',
            'backgroundColor': 'rgba(0,0,0,0.15)',
            'padding': '4px 10px',
            'borderRadius': '4px',
            'fontSize': '12px'
        }
    )
    
    # Try to get live market data for enhanced display
    fear_greed_widget = html.Div()
    indices_row = html.Div()
    try:
        from financial_dashboard.services.live_market_data import get_live_market_service
        live_service = get_live_market_service()
        
        # Fear & Greed Index Widget
        fg = live_service.get_fear_greed_index()
        fg_color = '#10b981' if fg.value >= 60 else '#ef4444' if fg.value <= 40 else '#f59e0b'
        fear_greed_widget = dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-speedometer2 me-2"),
                "Fear & Greed Index"
            ]),
            dbc.CardBody([
                html.Div([
                    html.H1(str(fg.value), style={'color': fg_color, 'fontSize': '48px', 'marginBottom': '0'}),
                    html.P(fg.classification, style={'color': fg_color, 'fontWeight': 'bold', 'fontSize': '18px'}),
                    dbc.Progress(value=fg.value, color="success" if fg.value >= 60 else "danger" if fg.value <= 40 else "warning", 
                                className="mb-2", style={'height': '10px'}),
                    html.Small(f"Yesterday: {fg.previous_close}", className="text-muted")
                ], style={'textAlign': 'center'})
            ])
        ], className="h-100", style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})
        
        # Market Indices Row - HORIZONTAL (all 4 in one row with smaller width)
        indices = live_service.get_market_indices()
        index_cards = []
        for symbol, idx in list(indices.items())[:4]:
            color = 'success' if idx.change_pct >= 0 else 'danger'
            index_cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6(idx.name, className="text-muted mb-1", style={'fontSize': '11px'}),
                            html.H5(f"${idx.price:,.2f}", className="mb-0", style={'fontSize': '16px'}),
                            html.Span(
                                f"{idx.change:+.2f} ({idx.change_pct:+.2f}%)",
                                className=f"text-{color}",
                                style={'fontSize': '12px'}
                            )
                        ], style={'padding': '10px'})
                    ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})
                ], width=3)  # Changed from width=3 in loop to single row of 4
            )
        indices_row = dbc.Row(index_cards, className="mb-4")
        
    except Exception as e:
        logger.warning(f"Could not load live market data for layout: {e}")
    
    return html.Div([
        # === IMPROVEMENTS: Toolbar with filters ===
        html.Div([
            create_tab_toolbar(
                tab_name="market_trends",
                filters=[create_sector_filter('market-trends-sector'), create_date_range_filter('market-trends-date')] if SHARED_UI_AVAILABLE else [],
                show_refresh=True,
                show_export=True,
                show_help=True,
                help_text="Track market trends across sectors and indices with real-time data."
            ) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === LIVE MARKET INDICES ROW ===
        indices_row,
        
        # === IMPROVEMENTS: Notification Toast ===
        html.Div([
            create_notification_toast("market_trends-toast", "Market Trends Update") if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # Header
        html.Div([
            html.H3([
                html.I(className="bi bi-graph-up-arrow me-2"),
                'Market Trends'
            ]),
            trend_badge,
            provider_summary
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
        
        # === MAIN CONTENT WITH TABS ===
        dcc.Tabs(id='market-trends-subtabs', value='overview-tab', children=[
            # Tab 1: Overview (existing content)
            dcc.Tab(label='📊 Overview', value='overview-tab', children=[
                # Compact 3-column grid layout
                dbc.Row([
                    # Column 1 - Controls
                    dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-sliders me-2"),
                        "Controls"
                    ]),
                    dbc.CardBody([
                        html.Label('Tickers', className="mb-1 small"),
                        dcc.Textarea(
                            id='tickers-input',
                            value='NVDA,AAPL,MSFT,GOOGL,META,AMZN,TSLA',
                            style={'width': '100%', 'fontSize': '12px', 'backgroundColor': 'rgba(0,0,0,0.2)', 
                                   'color': 'white', 'border': '1px solid rgba(255,255,255,0.2)'},
                            rows=2
                        ),
                        dbc.ButtonGroup([
                            dbc.Button(
                                [html.I(className="bi bi-play-fill me-1"), 'Run'],
                                id='mt-run-analysis-btn',
                                n_clicks=0,
                                color="primary",
                                size="sm",
                                className="mt-2"
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-arrow-clockwise me-1")],
                                id='mt-refresh-display-btn',
                                n_clicks=0,
                                color="success",
                                size="sm",
                                outline=True,
                                className="mt-2"
                            ),
                        ], className="w-100"),
                        html.Div(
                            id='status',
                            children='Ready',
                            className="small mt-2",
                            style={
                                'padding': '6px 8px',
                                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                                'borderRadius': '4px'
                            }
                        ),
                    ], style={'padding': '12px'})
                ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)', 'height': '100%'}),
            ], width=3),
            
            # Column 2 - Fear & Greed + News (Compact)
            dbc.Col([
                # Fear & Greed Widget (Compact)
                fear_greed_widget if fear_greed_widget else html.Div(),
                
                # News Section (Compact)
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-newspaper me-2"),
                        "Headlines"
                    ], style={'padding': '8px 12px'}),
                    dbc.CardBody([
                        html.Div(initial_news, id='news-container', style={'maxHeight': '300px', 'overflowY': 'auto'})
                    ], style={'padding': '8px'})
                ], className="mt-3" if fear_greed_widget else "", style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'})
            ], width=4),
            
            # Column 3 - Sector Heatmap
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-grid-3x3-gap me-2"),
                        "Sector Performance"
                    ], style={'padding': '8px 12px'}),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(id='sector-heatmap', config={'displayModeBar': False}, style={'height': '280px'}),
                            type='circle'
                        )
                    ], style={'padding': '8px'})
                ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)', 'height': '100%'}),
            ], width=5),
        ], className="mb-3"),
        
        # Collapsible Results Table
        dbc.Card([
            dbc.CardHeader([
                dbc.Button(
                    [
                        html.I(className="bi bi-table me-2"),
                        "Ticker Analysis Results",
                        html.I(id="mt-results-toggle-icon", className="bi bi-chevron-down ms-2")
                    ],
                    id="mt-results-toggle",
                    color="link",
                    className="text-white text-decoration-none w-100 text-start p-0",
                    style={'fontSize': '16px'}
                )
            ], style={'padding': '12px'}),
            dbc.Collapse(
                dbc.CardBody([
                    dcc.Loading(
                        id='loading',
                        children=[
                            html.Div(
                                initial_results,  # Changed from initial_table to include improvement cards
                                id='results-area',
                                style={'marginTop': '0', 'maxHeight': '400px', 'overflowY': 'auto'}
                            )
                        ],
                        type='circle'
                    )
                ], style={'padding': '12px'}),
                id="mt-results-collapse",
                is_open=False  # Start collapsed to save space
            )
        ], style={'backgroundColor': 'rgba(0,0,0,0.3)', 'border': '1px solid rgba(255,255,255,0.1)'}),
            ]),  # Close Overview Tab children list
            
            # Tab 2: Stock Screener (ENHANCED)
            dcc.Tab(label='🔍 Screener', value='screener-tab', children=[
                dbc.Row([
                    # Left Column - Filters
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className="bi bi-funnel-fill me-2"),
                                "Screening Filters"
                            ]),
                            dbc.CardBody([
                                # Price Range
                                html.Label("Price Range ($)", className="fw-bold", style={'fontSize': '13px', 'color': '#e2e8f0'}),
                                dcc.RangeSlider(
                                    id='screener-price-range',
                                    min=0, max=1000, step=5, value=[0, 1000],
                                    marks={
                                        0: {'label': '$0', 'style': {'color': '#94a3b8'}},
                                        250: {'label': '$250', 'style': {'color': '#94a3b8'}},
                                        500: {'label': '$500', 'style': {'color': '#94a3b8'}},
                                        750: {'label': '$750', 'style': {'color': '#94a3b8'}},
                                        1000: {'label': '$1K+', 'style': {'color': '#94a3b8'}}
                                    },
                                    tooltip={"placement": "bottom", "always_visible": False}
                                ),
                                
                                # Volume Filter
                                html.Label("Minimum Volume", className="fw-bold mt-3", style={'fontSize': '13px', 'color': '#e2e8f0'}),
                                dcc.Dropdown(
                                    id='screener-volume',
                                    options=[
                                        {'label': '🔹 Any Volume', 'value': 0},
                                        {'label': '🔸 100K+ (Active)', 'value': 100000},
                                        {'label': '🟡 1M+ (Very Active)', 'value': 1000000},
                                        {'label': '🟢 5M+ (High Liquidity)', 'value': 5000000},
                                        {'label': '🔵 10M+ (Ultra Liquid)', 'value': 10000000}
                                    ],
                                    value=0,
                                    className="mt-2",
                                    style={'backgroundColor': '#1e293b', 'color': 'white', 'border': '1px solid #334155'}
                                ),
                                
                                # RSI Range
                                html.Label("RSI Range (14-period)", className="fw-bold mt-3", style={'fontSize': '13px', 'color': '#e2e8f0'}),
                                html.Small("30 = Oversold, 70 = Overbought", className="text-muted"),
                                dcc.RangeSlider(
                                    id='screener-rsi',
                                    min=0, max=100, step=5, value=[0, 100],
                                    marks={
                                        0: {'label': '0', 'style': {'color': '#94a3b8'}},
                                        30: {'label': '30 (OS)', 'style': {'color': '#10b981'}},
                                        50: {'label': '50', 'style': {'color': '#94a3b8'}},
                                        70: {'label': '70 (OB)', 'style': {'color': '#ef4444'}},
                                        100: {'label': '100', 'style': {'color': '#94a3b8'}}
                                    },
                                    tooltip={"placement": "bottom", "always_visible": False}
                                ),
                                
                                # Trend Filter
                                html.Label("Trend Direction", className="fw-bold mt-3", style={'fontSize': '13px', 'color': '#e2e8f0'}),
                                dcc.Dropdown(
                                    id='screener-trend',
                                    options=[
                                        {'label': '🔹 Any Trend', 'value': 'any'},
                                        {'label': '📈 Bullish Only (Price > SMA20)', 'value': 'bullish'},
                                        {'label': '📉 Bearish Only (Price < SMA20)', 'value': 'bearish'},
                                        {'label': '➡️ Neutral Only', 'value': 'neutral'}
                                    ],
                                    value='any',
                                    className="mt-2",
                                    style={'backgroundColor': '#1e293b', 'color': 'white', 'border': '1px solid #334155'}
                                ),
                                
                                # Screen Button
                                dbc.Button(
                                    [html.I(className="bi bi-search me-2"), "🔍 Screen 120 Stocks"],
                                    id='run-screener-btn',
                                    color='success',
                                    size='lg',
                                    className='mt-4 w-100',
                                    style={'fontWeight': 'bold'}
                                ),
                                
                                # Results Count
                                html.Div(
                                    id='screener-count',
                                    className='mt-3 text-center',
                                    style={'color': '#94a3b8', 'fontSize': '13px', 'fontStyle': 'italic'}
                                )
                            ])
                        ], style={'backgroundColor': 'rgba(0,0,0,0.4)', 'border': '1px solid rgba(255,255,255,0.15)'}),
                        
                        # Fear & Greed Widget
                        fear_greed_widget if fear_greed_widget else html.Div(),
                        
                    ], width=3),
                    
                    # Right Column - Results
                    dbc.Col([
                        html.Div(id='screener-results-area', children=[
                            html.Div([
                                html.I(className="bi bi-funnel text-muted", style={'fontSize': '64px'}),
                                html.H4("Ready to Screen Stocks", className="mt-4 text-muted"),
                                html.P("Set your filters on the left and click the green button to find stocks matching your criteria.", 
                                       className="text-muted", style={'fontSize': '14px'}),
                                html.Hr(style={'borderColor': 'rgba(255,255,255,0.1)', 'width': '50%', 'margin': '30px auto'}),
                                html.Div([
                                    html.H6("What you can filter by:", style={'color': '#94a3b8'}),
                                    html.Ul([
                                        html.Li("💵 Price range ($0 to $1000+)"),
                                        html.Li("📊 Trading volume (liquidity)"),
                                        html.Li("📈 RSI momentum (oversold/overbought)"),
                                        html.Li("🎯 Trend direction (bullish/bearish/neutral)")
                                    ], style={'color': '#64748b', 'textAlign': 'left', 'display': 'inline-block'})
                                ])
                            ], style={'textAlign': 'center', 'padding': '80px 40px', 'color': '#64748b'})
                        ])
                    ], width=9)
                ], className="mt-3")
            ]),  # Close Screener Tab children list
            
            # Tab 3: Regime Monitor (Phase 5 - Market Intelligence)
            dcc.Tab(label='🎯 Regime Monitor', value='regime-tab', children=[
                dbc.Row([
                    # Left Column - Controls
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className="bi bi-cpu me-2"),
                                "Regime Detection Settings"
                            ]),
                            dbc.CardBody([
                                html.Label("Select Ticker", className="fw-bold", style={'fontSize': '13px', 'color': '#e2e8f0'}),
                                dcc.Dropdown(
                                    id='regime-ticker-select',
                                    options=[
                                        {'label': 'NVDA', 'value': 'NVDA'},
                                        {'label': 'AAPL', 'value': 'AAPL'},
                                        {'label': 'MSFT', 'value': 'MSFT'},
                                        {'label': 'GOOGL', 'value': 'GOOGL'},
                                        {'label': 'META', 'value': 'META'},
                                        {'label': 'AMZN', 'value': 'AMZN'},
                                        {'label': 'TSLA', 'value': 'TSLA'},
                                        {'label': 'SPY', 'value': 'SPY'},
                                    ],
                                    value='NVDA',
                                    clearable=False,
                                    style={'backgroundColor': 'rgba(0,0,0,0.3)'}
                                ),
                                
                                html.Label("Detection Method", className="fw-bold mt-3", style={'fontSize': '13px', 'color': '#e2e8f0'}),
                                dcc.RadioItems(
                                    id='regime-method-select',
                                    options=[
                                        {'label': ' HMM (Hidden Markov Model)', 'value': 'hmm'},
                                        {'label': ' K-Means Clustering', 'value': 'kmeans'},
                                    ],
                                    value='hmm',
                                    inline=False,
                                    style={'color': '#e2e8f0'},
                                    labelStyle={'display': 'block', 'marginBottom': '8px'}
                                ),
                                
                                html.Label("Lookback Days", className="fw-bold mt-3", style={'fontSize': '13px', 'color': '#e2e8f0'}),
                                dcc.Slider(
                                    id='regime-lookback-slider',
                                    min=30, max=365, step=30, value=252,
                                    marks={
                                        30: '30d',
                                        90: '90d',
                                        180: '6M',
                                        252: '1Y',
                                        365: '365d'
                                    },
                                    tooltip={"placement": "bottom", "always_visible": False}
                                ),
                                
                                dbc.Button(
                                    [html.I(className="bi bi-cpu me-2"), "Detect Regimes"],
                                    id='regime-detect-btn',
                                    color="primary",
                                    className='mt-4 w-100',
                                    style={'fontWeight': 'bold'}
                                ),
                            ])
                        ], style={'backgroundColor': 'rgba(0,0,0,0.4)', 'border': '1px solid rgba(255,255,255,0.15)'}),
                        
                        # Current Regime Card
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className="bi bi-activity me-2"),
                                "Current Regime"
                            ]),
                            dbc.CardBody([
                                html.Div(id='regime-current-display', children=[
                                    html.P("Run detection to see current market regime", 
                                           className="text-muted mb-0", style={'fontSize': '14px'})
                                ])
                            ])
                        ], className="mt-3", style={'backgroundColor': 'rgba(0,0,0,0.4)', 'border': '1px solid rgba(255,255,255,0.15)'}),
                        
                    ], width=3),
                    
                    # Right Column - Results
                    dbc.Col([
                        # Regime Chart
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className="bi bi-graph-up me-2"),
                                "Regime Detection Results"
                            ]),
                            dbc.CardBody([
                                dcc.Loading(
                                    html.Div(id='regime-chart-container', children=[
                                        html.Div([
                                            html.I(className="bi bi-cpu text-muted", style={'fontSize': '64px'}),
                                            html.H4("Regime Detection Ready", className="mt-4 text-muted"),
                                            html.P("Select a ticker and method, then click 'Detect Regimes' to analyze market conditions.", 
                                                   className="text-muted", style={'fontSize': '14px'})
                                        ], style={'textAlign': 'center', 'padding': '80px 40px'})
                                    ]),
                                    type='circle'
                                )
                            ])
                        ], style={'backgroundColor': 'rgba(0,0,0,0.4)', 'border': '1px solid rgba(255,255,255,0.15)'}),
                        
                        # Regime Statistics
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className="bi bi-bar-chart me-2"),
                                "Regime Statistics"
                            ]),
                            dbc.CardBody([
                                html.Div(id='regime-stats-container', children=[
                                    html.P("Statistics will appear after detection", 
                                           className="text-muted mb-0", style={'fontSize': '14px', 'textAlign': 'center'})
                                ])
                            ])
                        ], className="mt-3", style={'backgroundColor': 'rgba(0,0,0,0.4)', 'border': '1px solid rgba(255,255,255,0.15)'}),
                    ], width=9)
                ], className="mt-3")
            ])  # Close Regime Monitor Tab
        ]),  # Close dcc.Tabs children list
        
        # Hidden stores: trends-results-store is centralized in `layout_placeholders.py`.
        
    ], style={'padding': '20px', 'maxWidth': '1400px', 'margin': '0 auto'})


# ========================================================================
# CALLBACKS
# ========================================================================

def register_callbacks(app):
    """
    Register all callbacks for Market Trends tab.
    """
    logger.info("🔵 Registering Market Trends callbacks...")
    
    # Prevent double registration
    if getattr(app, '_market_trends_callbacks_registered', False):
        logger.info("Callbacks already registered, skipping")
        return
    
    setattr(app, '_market_trends_callbacks_registered', True)
    
    # ====================================================================
    # CALLBACK 1: Run Analysis
    # ====================================================================
    @app.callback(
        Output('status', 'children'),
        Output('status', 'style'),
        Output('current-job', 'data'),
        Output('poll-interval', 'disabled'),
        Input('mt-run-analysis-btn', 'n_clicks'),
        State('tickers-input', 'value'),
        State('current-job', 'data'),
        prevent_initial_call=True
    )
    def run_analysis(n_clicks, tickers_str, current_job):
        """Start analysis job when Run Analysis button clicked."""
        if not n_clicks or n_clicks == 0:
            raise PreventUpdate
        
        # Check if job already running
        if current_job:
            logger.info(f"Job already running: {current_job}")
            return (
                f"⏳ Job {current_job} already running...",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#fef3c7',
                    'color': '#92400e',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                current_job,
                False  # Keep polling enabled
            )
        
        # Validate input
        if not tickers_str or not tickers_str.strip():
            return (
                "❌ Please enter at least one ticker symbol",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#fee2e2',
                    'color': '#991b1b',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                None,
                True
            )
        
        # Start background job
        try:
            job_id = SH.start_background_job(
                target=run_full_analysis,
                kwargs={
                    'tickers_str': tickers_str,
                    'period': '1y',
                    'include_news': True,
                    'include_options': False
                }
            )
            
            logger.info(f"Started analysis job: {job_id}")
            
            return (
                f"🚀 Starting analysis... (Job: {job_id})",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#dbeafe',
                    'color': '#1e40af',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                job_id,
                False  # Enable polling
            )
            
        except Exception as e:
            logger.error(f"Failed to start job: {e}")
            return (
                f"❌ Error: {str(e)}",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#fee2e2',
                    'color': '#991b1b',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                None,
                True
            )
    
    # ====================================================================
    # CALLBACK 2: Poll Job Status
    # ====================================================================
    @app.callback(
        Output('results-area', 'children'),
        Output('news-container', 'children'),
        Output('status', 'children', allow_duplicate=True),
        Output('status', 'style', allow_duplicate=True),
        Output('current-job', 'data', allow_duplicate=True),
        Output('poll-interval', 'disabled', allow_duplicate=True),
        Output('trends-results-store', 'data'),
        Input('poll-interval', 'n_intervals'),
        State('current-job', 'data'),
        prevent_initial_call=True
    )
    def poll_job_status(n_intervals, job_id):
        """Poll job status and update results when complete."""
        if not job_id:
            raise PreventUpdate
        
        # Check job status
        status_info = SH.get_job_status(job_id)
        
        if not status_info:
            # Job not found
            logger.error(f"Job {job_id} not found")
            return (
                html.Div(
                    "Job not found",
                    style={'padding': '20px', 'color': '#ef4444'}
                ),
                no_update,
                "❌ Job not found",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#fee2e2',
                    'color': '#991b1b',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                None,
                True,
                no_update
            )
        
        # Check if job is still running
        elif status_info['status'] == 'running':
            # Job still running
            return (
                no_update,
                no_update,
                f"⏳ Analysis running... ({status_info.get('progress', 0)}%)",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#dbeafe',
                    'color': '#1e40af',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                job_id,
                False,  # Keep polling
                no_update
            )
            
        elif status_info['status'] == 'completed':
            # Job complete
            result = status_info.get('result', {})
            
            # Render table
            table = _render_table(result.get('detailed', []))
            
            # Render improvement cards (multi-timeframe, risk metrics, momentum)
            improvement_cards = _create_improvement_cards(result)
            
            # Combine table and improvement cards
            full_results = html.Div([
                table,
                improvement_cards
            ])
            
            # Render news
            news = _render_news(result.get('news', {}))
            
            # Update trend badge
            trend = result.get('market_trend')
            trend_badge = "Market Trend: Unknown"
            trend_style = {
                'backgroundColor': '#94a3b8',
                'color': 'white',
                'padding': '4px 12px',
                'borderRadius': '4px',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'marginLeft': '12px'
            }
            
            if trend:
                trend_badge = f"Market Trend: {trend.get('label', 'Unknown')}"
                trend_style['backgroundColor'] = trend.get('color', '#94a3b8')
            
            trend_component = html.Span(
                trend_badge,
                **{'data-testid': 'market-trend-badge'},
                style=trend_style
            )
            
            logger.info(f"Job {job_id} completed successfully")
            
            return (
                full_results,  # Changed from 'table' to include improvement cards
                news,
                f"✅ Analysis complete! ({len(result.get('detailed', []))} tickers analyzed)",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#d1fae5',
                    'color': '#065f46',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                None,  # Clear job ID
                True,  # Disable polling
                result # Update store
            )
            
        else:
            # Job failed or unknown status
            error_msg = status_info.get('error', 'Unknown error')
            logger.error(f"Job {job_id} failed: {error_msg}")
            return (
                html.Div(
                    f"Analysis failed: {error_msg}",
                    style={'padding': '20px', 'color': '#ef4444'}
                ),
                no_update,
                f"❌ Analysis failed: {error_msg}",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#fee2e2',
                    'color': '#991b1b',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                },
                None,
                True,  # Stop polling
                no_update
            )
        

    
    # ====================================================================
    # CALLBACK 3: Update Sector Heatmap
    # ====================================================================
    @app.callback(
        Output('sector-heatmap', 'figure'),
        Input('interval-component', 'n_intervals')
    )
    def update_sector_heatmap(n):
        """Fetch sector data via PriceClient and render heatmap."""
        import time as _time
        _fetch_start = _time.time()
        data_source = 'unknown'
        
        try:
            tickers = list(SECTOR_ETFS.values())
            
            # Use PriceClient for consistent provider fallback, caching, and telemetry
            pc = PriceClient()
            price_results = pc.get_prices(tickers, lookback_days=7, cache_ttl=60)
            
            # Determine primary data source from results
            sources_used = set()
            for ticker_data in price_results.values():
                src = ticker_data.get('source', 'Local')
                if src and src != 'Local':
                    sources_used.add(src)
            data_source = ', '.join(sorted(sources_used)) if sources_used else 'Local'
            
            data = []
            for sector, ticker in SECTOR_ETFS.items():
                ticker_data = price_results.get(ticker)
                if not ticker_data:
                    continue
                
                current = ticker_data.get('current_price')
                # Use week_start_price for more accurate daily change; fall back to start_price
                prev = ticker_data.get('week_start_price') or ticker_data.get('start_price')
                
                if current is None or prev is None or prev == 0:
                    continue
                
                change = ((current - prev) / prev) * 100
                data.append({
                    'Sector': sector,
                    'Ticker': ticker,
                    'Change': change,
                    'AbsChange': abs(change),
                    'Color': change
                })
            
            if not data:
                # Return empty figure with helpful annotation
                fig = go.Figure()
                fig.add_annotation(
                    text="No sector data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color="#888")
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                return fig
                
            # Create Treemap
            fig = px.treemap(
                data,
                path=['Sector'],
                values='AbsChange',  # Size by magnitude of move
                color='Change',
                color_continuous_scale=['#ef4444', '#f3f4f6', '#10b981'],  # Red to Green
                color_continuous_midpoint=0,
                custom_data=['Change', 'Ticker']
            )
            
            fig.update_traces(
                textposition='middle center',
                texttemplate='<b>%{label}</b><br>%{customdata[1]}<br>%{customdata[0]:.2f}%',
                hovertemplate='<b>%{label}</b> (%{customdata[1]})<br>Change: %{customdata[0]:.2f}%<extra></extra>'
            )
            
            # Add data source annotation
            fetch_duration = _time.time() - _fetch_start
            fig.update_layout(
                margin=dict(t=25, l=0, r=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                annotations=[
                    dict(
                        text=f"Source: {data_source} | {fetch_duration:.1f}s",
                        xref="paper", yref="paper",
                        x=1, y=1.02, xanchor="right", yanchor="bottom",
                        showarrow=False,
                        font=dict(size=9, color="#666")
                    )
                ]
            )
            
            logger.info(f"Sector heatmap updated: {len(data)} sectors, source={data_source}, duration={fetch_duration:.2f}s")
            return fig
            
        except Exception as e:
            logger.error(f"Error updating sector heatmap: {e}", exc_info=True)
            # Return graceful error figure instead of empty
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading sector data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="#ef4444")
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            return fig

    # ====================================================================
    # CALLBACK 4: Refresh Display
    # ====================================================================
    @app.callback(
        Output('results-area', 'children', allow_duplicate=True),
        Output('news-container', 'children', allow_duplicate=True),
        Output('status', 'children', allow_duplicate=True),
        Output('status', 'style', allow_duplicate=True),
        Input('mt-refresh-display-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def refresh_display(n_clicks):
        """Refresh display from cache."""
        if not n_clicks or n_clicks == 0:
            raise PreventUpdate
        
        # Load from disk cache (analysis results)
        cached = cache_manager.load_from_disk()

        # Also refresh the centralized price cache so we can merge latest prices
        try:
            # This updates SH.RESULTS_CACHE['results']['prices'] when possible
            SH.refresh_prices_cache(force_fetch_missing=True)
        except Exception:
            # Non-fatal: continue with whatever prices we already have
            logger.debug("Could not refresh shared price cache before display refresh")

        # Merge latest prices (if available) into each detailed record so UI shows freshest prices
        prices_map = {}
        try:
            prices_map = (SH.RESULTS_CACHE.get('results') or {}).get('prices', {})
        except Exception:
            prices_map = {}

        if not cached or not cached.get('detailed'):
            # No analysis results to render
            return (
                html.Div(
                    "No cached data available. Click 'Run Analysis' first.",
                    style={'padding': '20px', 'color': '#9ca3af', 'textAlign': 'center'}
                ),
                html.Div(
                    "No news available",
                    style={'padding': '16px', 'color': '#9ca3af', 'textAlign': 'center'}
                ),
                "⚠️ No cached data found",
                {
                    'padding': '8px 12px',
                    'backgroundColor': '#fef3c7',
                    'color': '#92400e',
                    'borderRadius': '4px',
                    'marginBottom': '16px'
                }
            )

        detailed = cached.get('detailed', [])

        # Normalize ticker keys and merge price fields
        for rec in detailed:
            try:
                t = rec.get('ticker') or rec.get('symbol')
                if not t:
                    continue
                t_up = t.upper()
                p = prices_map.get(t_up) or prices_map.get(t)
                if not p:
                    continue

                # Merge common price fields if present in the price map
                # Use existing analysis fields as fallback
                if 'current_price' in p:
                    rec['current_price'] = p.get('current_price')
                if 'daily_change' in p:
                    rec['daily_change'] = p.get('daily_change')
                # Support both explicit month/week keys and legacy 'start_price'
                if 'month_start_price' in p:
                    rec['month_start_price'] = p.get('month_start_price')
                elif 'start_price' in p:
                    rec['month_start_price'] = p.get('start_price')
                if 'week_start_price' in p:
                    rec['week_start_price'] = p.get('week_start_price')
                elif 'start_price' in p:
                    rec['week_start_price'] = p.get('start_price')
                if 'profit_loss' in p:
                    rec['profit_loss'] = p.get('profit_loss')
                # Preserve or update data source
                if 'source' in p:
                    rec['data_source'] = p.get('source')
            except Exception:
                continue

        # Render merged data
        table = _render_table(detailed)
        news = _render_news(cached.get('news', {}))

        generated_at = cached.get('generated_at', 'unknown time')

        return (
            table,
            news,
            f"🔄 Refreshed from cache (generated: {generated_at})",
            {
                'padding': '8px 12px',
                'backgroundColor': '#dbeafe',
                'color': '#1e40af',
                'borderRadius': '4px',
                'marginBottom': '16px'
            }
        )

    # ====================================================================
    # CALLBACK: Toggle results table collapse
    # ====================================================================
    @app.callback(
        [Output('mt-results-collapse', 'is_open'),
         Output('mt-results-toggle-icon', 'className')],
        [Input('mt-results-toggle', 'n_clicks')],
        [State('mt-results-collapse', 'is_open')]
    )
    def toggle_results_collapse(n_clicks, is_open):
        """Toggle the results table collapse and update icon."""
        if n_clicks:
            new_state = not is_open
            icon_class = "bi bi-chevron-up ms-2" if new_state else "bi bi-chevron-down ms-2"
            return new_state, icon_class
        return is_open, "bi bi-chevron-down ms-2"

    # ====================================================================
    # CALLBACK: Update provider summary display from store
    # ====================================================================
    @app.callback(
        Output('mt-provider-summary', 'children'),
        Input('trends-results-store', 'data')
    )
    def update_provider_summary(store_data):
        """Update the small provider summary element when store changes."""
        try:
            if not store_data:
                return 'Providers used: unknown'

            ps = store_data.get('price_provider_summary') or store_data.get('price_provider_summary', 'unknown')
            return f"Providers used: {ps}"
        except Exception:
            return 'Providers used: unknown'

    
    # ====================================================================
    # CALLBACK: Stock Screener
    # ====================================================================
    @app.callback(
        Output('screener-results-area', 'children'),
        Output('screener-count', 'children'),
        Input('run-screener-btn', 'n_clicks'),
        State('screener-price-range', 'value'),
        State('screener-volume', 'value'),
        State('screener-rsi', 'value'),
        State('screener-trend', 'value'),
        prevent_initial_call=True
    )
    def run_screener(n_clicks, price_range, volume, rsi_range, trend):
        """Run stock screener with user-defined filters"""
        logger.info(f"🎯 SCREENER CALLBACK TRIGGERED: n_clicks={n_clicks}")
        
        if not n_clicks:
            logger.warning(f"⚠️ Screener prevented: n_clicks={n_clicks}")
            raise PreventUpdate
        
        try:
            from picker.screening_universe import SCREENING_UNIVERSE
            
            logger.info(f"🔍 Running screener: price={price_range}, vol={volume}, rsi={rsi_range}, trend={trend}")
            
            # Run screening
            results = _screen_stocks(
                universe=SCREENING_UNIVERSE,
                min_price=price_range[0] if price_range else 0,
                max_price=price_range[1] if price_range else float('inf'),
                min_volume=volume if volume else 0,
                min_rsi=rsi_range[0] if rsi_range else 0,
                max_rsi=rsi_range[1] if rsi_range else 100,
                trend=None if not trend or trend == 'any' else trend
            )
            
            # Sort by score (highest first)
            results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
            
            # Render results
            results_ui = _render_screener_results(results_sorted)
            
            # Check if results came from cache
            cache_key = f"{price_range[0] if price_range else 0}_{price_range[1] if price_range else float('inf')}_{volume if volume else 0}_{rsi_range[0] if rsi_range else 0}_{rsi_range[1] if rsi_range else 100}_{None if not trend or trend == 'any' else trend}"
            from_cache = cache_key in _SCREENER_CACHE
            cache_indicator = " (📦 cached)" if from_cache else ""
            
            # Count message
            count_msg = f"✅ Screened {len(SCREENING_UNIVERSE)} stocks, found {len(results)} matches{cache_indicator}"
            
            return results_ui, count_msg
            
        except Exception as e:
            logger.error(f"Screener error: {e}", exc_info=True)
            return html.Div(
                f"❌ Error: {str(e)[:200]}",
                style={'color': '#ef4444', 'padding': '20px'}
            ), "❌ Screening failed"
    
    # ====================================================================
    # CALLBACK: Regime Detection (Phase 5 - Market Intelligence)
    # ====================================================================
    @app.callback(
        Output('regime-chart-container', 'children'),
        Output('regime-current-display', 'children'),
        Output('regime-stats-container', 'children'),
        Input('regime-detect-btn', 'n_clicks'),
        State('regime-ticker-select', 'value'),
        State('regime-method-select', 'value'),
        State('regime-lookback-slider', 'value'),
        prevent_initial_call=True
    )
    def detect_market_regimes(n_clicks, ticker, method, lookback_days):
        """Detect market regimes using HMM or K-Means clustering."""
        logger.info(f"🎯 REGIME DETECTION CALLBACK: ticker={ticker}, method={method}, lookback={lookback_days}")
        
        if not n_clicks or not ticker:
            raise PreventUpdate
        
        # Check if regime engine is available
        if not REGIME_ENGINE_AVAILABLE:
            error_msg = html.Div([
                html.I(className="bi bi-exclamation-triangle text-warning", style={'fontSize': '48px'}),
                html.H5("Regime Engine Not Available", className="mt-3 text-warning"),
                html.P("Install hmmlearn: pip install hmmlearn", className="text-muted")
            ], style={'textAlign': 'center', 'padding': '40px'})
            return error_msg, "❌ Engine not available", "N/A"
        
        try:
            # Initialize detector
            detector = RegimeDetector(n_regimes=3, method=method)
            
            # Detect regimes
            result = detector.detect_regimes(ticker, lookback_days=lookback_days)
            
            if result is None:
                error_ui = html.Div([
                    html.I(className="bi bi-x-circle text-danger", style={'fontSize': '48px'}),
                    html.H5(f"No data for {ticker}", className="mt-3 text-danger"),
                    html.P("Unable to fetch price data. Try another ticker.", className="text-muted")
                ], style={'textAlign': 'center', 'padding': '40px'})
                return error_ui, "❌ No data", "N/A"
            
            # Create regime chart
            df = result['data']
            current_regime = result['current_regime']
            regime_probs = result.get('regime_probabilities', {})
            
            # Build chart
            fig = go.Figure()
            
            # Add price line
            fig.add_trace(go.Scatter(
                x=df['Date'] if 'Date' in df.columns else df.index,
                y=df['Close'],
                mode='lines',
                name='Price',
                line=dict(color='#60a5fa', width=2)
            ))
            
            # Color regions by regime
            regimes = df['regime'].values
            dates = df['Date'].values if 'Date' in df.columns else df.index.values
            
            # Add colored background for each regime period
            for i in range(len(regimes)):
                regime = int(regimes[i])
                color = REGIME_COLORS.get(regime, 'gray')
                if i > 0:
                    fig.add_vrect(
                        x0=dates[i-1], x1=dates[i],
                        fillcolor=color, opacity=0.15,
                        layer="below", line_width=0
                    )
            
            # Update layout
            fig.update_layout(
                title=dict(text=f"{ticker} Regime Detection ({method.upper()})", font=dict(color='white', size=16)),
                xaxis=dict(title='Date', gridcolor='rgba(255,255,255,0.1)', color='white'),
                yaxis=dict(title='Price ($)', gridcolor='rgba(255,255,255,0.1)', color='white'),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0.2)',
                legend=dict(font=dict(color='white')),
                height=400,
                margin=dict(l=50, r=20, t=50, b=50)
            )
            
            chart_ui = dcc.Graph(figure=fig, config={'displayModeBar': False})
            
            # Current regime display
            regime_label = REGIME_LABELS.get(current_regime, 'Unknown')
            regime_color = REGIME_COLORS.get(current_regime, 'gray')
            
            current_ui = html.Div([
                html.Div([
                    html.Span("●", style={'color': regime_color, 'fontSize': '24px', 'marginRight': '10px'}),
                    html.Span(regime_label, style={'fontSize': '18px', 'fontWeight': 'bold', 'color': regime_color})
                ]),
                html.Hr(style={'borderColor': 'rgba(255,255,255,0.1)', 'margin': '12px 0'}),
                html.Div([
                    html.Small("Confidence: ", style={'color': '#94a3b8'}),
                    html.Small(f"{regime_probs.get(current_regime, 0.0)*100:.1f}%", 
                              style={'color': regime_color, 'fontWeight': 'bold'})
                ]) if regime_probs else html.Div()
            ])
            
            # Regime statistics
            regime_counts = df['regime'].value_counts().sort_index()
            stats_children = []
            for regime_id in range(3):
                count = regime_counts.get(regime_id, 0)
                pct = (count / len(df)) * 100 if len(df) > 0 else 0
                label = REGIME_LABELS.get(regime_id, f'Regime {regime_id}')
                color = REGIME_COLORS.get(regime_id, 'gray')
                
                stats_children.append(
                    dbc.Row([
                        dbc.Col(html.Span("●", style={'color': color, 'fontSize': '16px'}), width=1),
                        dbc.Col(html.Span(label, style={'color': '#e2e8f0', 'fontSize': '13px'}), width=6),
                        dbc.Col(html.Span(f"{pct:.1f}%", style={'color': color, 'fontWeight': 'bold', 'fontSize': '13px'}), width=3),
                        dbc.Col(html.Span(f"({count}d)", style={'color': '#94a3b8', 'fontSize': '12px'}), width=2),
                    ], className="mb-2")
                )
            
            stats_ui = html.Div(stats_children)
            
            logger.info(f"✅ Regime detection complete: {ticker} is in {regime_label}")
            return chart_ui, current_ui, stats_ui
            
        except Exception as e:
            logger.error(f"Regime detection error: {e}", exc_info=True)
            error_ui = html.Div([
                html.I(className="bi bi-exclamation-triangle text-danger", style={'fontSize': '48px'}),
                html.H5("Detection Error", className="mt-3 text-danger"),
                html.P(str(e)[:200], className="text-muted", style={'fontSize': '12px'})
            ], style={'textAlign': 'center', 'padding': '40px'})
            return error_ui, "❌ Error", "N/A"
    
    logger.info("✅ Market Trends callbacks registered successfully!")

