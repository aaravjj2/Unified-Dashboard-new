"""
Market Trends Tab - Complete Rebuild
=====================================

Clean implementation with:
- Working callbacks (no hangs)
- CacheManager integration
- NewsManager integration
- Background jobs for price/news refresh
- Admin endpoints
- Comprehensive error handling
- Full test coverage support
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

import pandas as pd
from dash import dcc, html, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
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
from financial_dashboard.utils.news_client import fetch_news_for_tickers
from financial_dashboard.utils.price_fetcher import PriceFetcher
from financial_dashboard.utils.price_client import PriceClient
import plotly.express as px

logger = logging.getLogger(__name__)

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


def _headline_sentiment(text: str, ticker: str = '') -> Dict[str, Any]:
    """
    Lightweight headline sentiment classifier.

    Returns a dict with keys:
      - 'sentiment': one of 'Bullish'|'Bearish'|'Neutral'
      - 'score': float where positive = bullish, negative = bearish

    This is a deterministic, explainable, keyword-weighted classifier
    designed to run offline and be easily extended.
    """
    if not text:
        return {'sentiment': 'Neutral', 'score': 0.0}

    txt = text.lower()

    # Weighted keyword lists (keyword -> weight)
    bullish_keywords = {
        'beat': 1.5, 'beats': 1.5, 'beats expectations': 2.0, 'outperform': 1.5,
        'upgrade': 1.5, 'surge': 1.3, 'soar': 1.4, 'rise': 1.1, 'rally': 1.2,
        'gain': 1.0, 'gains': 1.0, 'strong': 1.0, 'record': 1.2, 'growth': 1.1,
        'positive': 0.9, 'buy': 0.8, 'bull': 0.7, 'acquisition': 0.8, 'beat guidance': 2.0
    }

    bearish_keywords = {
        'miss': -1.5, 'missed': -1.5, 'downgrade': -1.6, 'underperform': -1.5,
        'drop': -1.1, 'decline': -1.0, 'fall': -1.0, 'weak': -1.0, 'loss': -1.3,
        'losses': -1.3, 'plummet': -1.6, 'negative': -0.9, 'sell': -0.8,
        'warning': -1.4, 'cut guidance': -1.8, 'lower guidance': -1.6, 'recall': -1.2
    }

    score = 0.0

    # Count occurrences and weight
    for kw, w in bullish_keywords.items():
        if kw in txt:
            score += w

    for kw, w in bearish_keywords.items():
        if kw in txt:
            score += w

    # Slight boost if ticker is explicitly mentioned along with a directional verb
    if ticker and ticker.lower() in txt:
        if any(kw in txt for kw in ['beat', 'beats', 'upgrade', 'surge', 'rally', 'gain']):
            score += 0.25
        if any(kw in txt for kw in ['miss', 'missed', 'downgrade', 'drop', 'decline', 'loss']):
            score -= 0.25

    # Interpret score into buckets
    if score >= 1.5:
        sentiment = 'Bullish'
    elif score <= -1.5:
        sentiment = 'Bearish'
    else:
        sentiment = 'Neutral'

    return {'sentiment': sentiment, 'score': round(score, 2)}


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

            # Prefer persisted sentiment if present, otherwise compute on the fly
            sentiment = item.get('sentiment') or _headline_sentiment(headline, ticker).get('sentiment')
            score = item.get('sentiment_score') or _headline_sentiment(headline, ticker).get('score')

            if sentiment == 'Bullish':
                badge_style = {'backgroundColor': '#10b981', 'color': 'white', 'padding': '2px 8px', 'borderRadius': '12px', 'fontSize': '12px', 'marginLeft': '8px'}
            elif sentiment == 'Bearish':
                badge_style = {'backgroundColor': '#ef4444', 'color': 'white', 'padding': '2px 8px', 'borderRadius': '12px', 'fontSize': '12px', 'marginLeft': '8px'}
            else:
                badge_style = {'backgroundColor': '#9ca3af', 'color': 'white', 'padding': '2px 8px', 'borderRadius': '12px', 'fontSize': '12px', 'marginLeft': '8px'}

            news_items.append(
                html.Div([
                    html.A(
                        headline,
                        href=url,
                        target='_blank',
                        style={'color': '#3b82f6', 'textDecoration': 'none'}
                    ),
                    html.Span(
                        f"{sentiment}",
                        className='news-sentiment-badge',
                        **{'data-sentiment': sentiment, 'data-sentiment-score': str(score)},
                        style=badge_style
                    ),
                    html.Span(
                        f" - {ticker} ({source})",
                        style={'color': '#6b7280', 'fontSize': '12px', 'marginLeft': '8px'}
                    )
                ], style={'marginBottom': '8px'})
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
        # Simple trend calculation based on average performance
        if not data:
            return None
        
        df = pd.DataFrame(data)
        if 'return_pct' not in df.columns:
            return None
        
        avg_return = df['return_pct'].mean()
        
        # Simple thresholds
        if avg_return > 5:
            label = 'Strong Bull'
        elif avg_return > 2:
            label = 'Bull'
        elif avg_return > -2:
            label = 'Neutral'
        elif avg_return > -5:
            label = 'Bear'
        else:
            label = 'Strong Bear'
        
        return {
            'label': label,
            'composite': avg_return,
            'generated_at': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error computing market trend: {e}")
        return None


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
        return response
        
    except Exception as e:
        logger.exception("Fatal error in run_full_analysis")
        return {'error': str(e)}


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
        
        # === IMPROVEMENTS: Summary Statistics ===
        html.Div([
            create_summary_stats_row([
                {'title': 'SPY', 'value': '$--', 'icon': 'fa-chart-line', 'color': 'primary'},
            {'title': 'Trending Up', 'value': '--', 'icon': 'fa-arrow-up', 'color': 'success'},
            {'title': 'Trending Down', 'value': '--', 'icon': 'fa-arrow-down', 'color': 'danger'},
            {'title': 'Volatility', 'value': '--%', 'icon': 'fa-bolt', 'color': 'warning'}
            ]) if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # === IMPROVEMENTS: Notification Toast ===
        html.Div([
            create_notification_toast("market_trends-toast", "Market Trends Update") if SHARED_UI_AVAILABLE else html.Div()
        ]),
        
        # Header
        html.Div([
            html.H3('Market Trends'),
                trend_badge,
                provider_summary
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
        
        # Controls
        html.Div([
            html.Label('Tickers (comma separated)'),
            dcc.Textarea(
                id='tickers-input',
                value='NVDA,AAPL,MSFT,GOOGL,META,AMZN,TSLA',
                style={'width': '100%', 'maxWidth': '600px', 'resize': 'vertical'},
                rows=2
            ),
        ], style={'marginBottom': '12px'}),
        
        html.Div([
            html.Button(
                'Run Analysis',
                id='mt-run-analysis-btn',
                n_clicks=0,
                style={
                    'backgroundColor': '#3b82f6',
                    'color': 'white',
                    'padding': '8px 16px',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer'
                }
            ),
            html.Button(
                'Refresh Display',
                id='mt-refresh-display-btn',
                n_clicks=0,
                style={
                    'backgroundColor': '#10b981',
                    'color': 'white',
                    'padding': '8px 16px',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'marginLeft': '8px'
                }
            ),
        ], style={'marginBottom': '16px'}),
        
        # Status
        html.Div(
            id='status',
            children='Ready',
            style={
                'padding': '8px 12px',
                'backgroundColor': '#f3f4f6',
                'borderRadius': '4px',
                'marginBottom': '16px',
                'display': 'block'
            }
        ),
        
        # News Section
        html.Div([
            html.H4('Recent Headlines', style={'marginBottom': '12px'}),
            html.Div(initial_news, id='news-container')
        ], style={'marginBottom': '16px'}),
        
        # Sector Heatmap Section
        html.Div([
            html.H4('Sector Performance', style={'marginBottom': '12px'}),
            dcc.Loading(
                dcc.Graph(id='sector-heatmap', config={'displayModeBar': False}, style={'height': '400px'}),
                type='circle'
            )
        ], style={'marginBottom': '24px'}),
        
        # Results Table
        dcc.Loading(
            id='loading',
            children=[
                html.Div(
                    initial_table,
                    id='results-area',
                    style={'marginTop': '16px'}
                )
            ],
            type='circle'
        ),
        
        # Hidden stores: trends-results-store is centralized in `layout_placeholders.py`.
        
    ], style={'padding': '20px', 'maxWidth': '1200px', 'margin': '0 auto'})


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
                table,
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
        """Fetch sector data and render heatmap."""
        try:
            import yfinance as yf
            
            data = []
            tickers = list(SECTOR_ETFS.values())
            
            # Fetch last 5 days to calculate change
            # Use progress=False to avoid printing to stdout
            df = yf.download(tickers, period="5d", progress=False)['Close']
            
            if df.empty:
                return go.Figure()
                
            # Calculate % change from previous close
            current_prices = df.iloc[-1]
            prev_prices = df.iloc[-2]
            
            changes = ((current_prices - prev_prices) / prev_prices) * 100
            
            for sector, ticker in SECTOR_ETFS.items():
                if ticker in changes:
                    change = changes[ticker]
                    data.append({
                        'Sector': sector,
                        'Ticker': ticker,
                        'Change': change,
                        'AbsChange': abs(change),
                        'Color': change
                    })
            
            if not data:
                return go.Figure()
                
            # Create Treemap
            fig = px.treemap(
                data,
                path=['Sector'],
                values='AbsChange', # Size by magnitude of move
                color='Change',
                color_continuous_scale=['#ef4444', '#f3f4f6', '#10b981'], # Red to Green
                color_continuous_midpoint=0,
                custom_data=['Change', 'Ticker']
            )
            
            fig.update_traces(
                textposition='middle center',
                texttemplate='<b>%{label}</b><br>%{customdata[1]}<br>%{customdata[0]:.2f}%',
                hovertemplate='<b>%{label}</b> (%{customdata[1]})<br>Change: %{customdata[0]:.2f}%<extra></extra>'
            )
            
            fig.update_layout(
                margin=dict(t=0, l=0, r=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error updating sector heatmap: {e}")
            return go.Figure()

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
    
    logger.info("✅ Market Trends callbacks registered successfully!")
