"""
News Manager for Market Trends Tab

Handles news fetching with TTL-based caching and auto-refresh logic.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
Agent-1B: Enhanced with fixture support, AZURE_DISABLED enforcement, and extended logging
"""

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dash import html
from financial_dashboard.utils.news_client import fetch_news_for_tickers

logger = logging.getLogger(__name__)

# Enhanced logging to diagnostics directory
_log_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'reports/market_trends_fix/diagnostics/news_ops.log'
)
os.makedirs(os.path.dirname(_log_file), exist_ok=True)
_file_handler = logging.FileHandler(_log_file)
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(_file_handler)
logger.setLevel(logging.INFO)

# Azure blocking log
_azure_blocked_log = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'reports/market_trends_fix/diagnostics/azure_blocked.log'
)


class NewsManager:
    """
    Manages news fetching and caching for Market Trends.
    
    Implements 5-minute TTL cache to minimize API calls while
    keeping news reasonably fresh.
    """
    
    def __init__(self, ttl_seconds: int = 300, providers: List[str] = None):
        """
        Initialize News Manager.
        
        Args:
            ttl_seconds: Time-to-live for cache in seconds (default 5 minutes)
            providers: List of provider names (for compatibility, currently uses news_client)
        """
        self.ttl_seconds = ttl_seconds
        self.providers = providers or ['finnhub', 'alpaca']
        self.deterministic_mode = os.getenv('MARKET_TRENDS_DETERMINISTIC', '0') == '1'
        
        self._cache = {
            'data': None,
            'tickers': None,
            'timestamp': None
        }
        
        logger.info(f"NewsManager initialized: ttl={ttl_seconds}s, providers={self.providers}, deterministic={self.deterministic_mode}")
    
    def fetch_news(self, tickers: List[str], force_refresh: bool = False, 
                   max_per_ticker: int = 2) -> Dict[str, List[Dict]]:
        """
        Fetch news for tickers with TTL caching.
        
        Args:
            tickers: List of ticker symbols
            force_refresh: If True, bypass cache and fetch fresh data
            max_per_ticker: Maximum news items per ticker
            
        Returns:
            Dict mapping ticker to list of news items
            
        Raises:
            Exception: If all news providers fail and no cache available
        """
        # AZURE_DISABLED: Block any Azure provider attempts
        if 'azure' in [p.lower() for p in self.providers]:
            logger.warning("Azure provider requested but AZURE_DISABLED is active")
            with open(_azure_blocked_log, 'a') as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} - Azure provider blocked in fetch_news\n")
            self.providers = [p for p in self.providers if p.lower() != 'azure']
        
        # Check if we can use cache
        if not force_refresh and self._can_use_cache(tickers):
            cache_age = self._get_cache_age()
            logger.info(f"Using cached news (age: {cache_age:.1f}s)")
            return self._cache['data']
        
        # Deterministic mode: use fixtures
        if self.deterministic_mode:
            logger.info("Deterministic mode enabled, using fixture data")
            news_data = self._fetch_from_fixture(tickers, max_per_ticker)
            
            # Update cache
            self._cache['data'] = news_data
            self._cache['tickers'] = list(tickers)
            self._cache['timestamp'] = time.time()
            
            return news_data
        
        # Fetch fresh news from providers
        logger.info(f"Fetching fresh news for {len(tickers)} tickers")
        
        try:
            news_data = fetch_news_for_tickers(tickers, max_per_ticker=max_per_ticker)
            
            # Update cache
            self._cache['data'] = news_data
            self._cache['tickers'] = list(tickers)
            self._cache['timestamp'] = time.time()
            
            total_items = sum(len(items) for items in news_data.values())
            logger.info(f"Fetched {total_items} news items, cache updated")
            
            return news_data
            
        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            
            # If we have stale cache, return it with warning
            if self._cache['data'] is not None:
                logger.warning("Returning stale cached news due to fetch failure")
                return self._cache['data']
            
            # Fallback to fixture if no cache
            logger.warning("No cache available, falling back to fixture")
            return self._fetch_from_fixture(tickers, max_per_ticker)
    
    def is_news_stale(self) -> bool:
        """
        Check if cached news is stale (older than TTL).
        
        Returns:
            True if cache is stale or empty, False if fresh
        """
        if self._cache['timestamp'] is None:
            return True
        
        age = time.time() - self._cache['timestamp']
        return age >= self.ttl_seconds
    
    def should_refresh(self) -> bool:
        """
        Check if cache should be refreshed (auto-refresh helper).
        
        Returns:
            True if cache is stale or empty
        """
        return self.is_news_stale() or self._cache['data'] is None
    
    def get_cache_age(self) -> Optional[float]:
        """
        Get cache age in seconds (public API for compatibility).
        
        Returns:
            Age in seconds, or None if no cache
        """
        if self._cache['timestamp'] is None:
            return None
        return self._get_cache_age()
    
    def get_cached_news(self) -> Optional[Dict[str, List[Dict]]]:
        """
        Get cached news without fetching.
        
        Returns:
            Cached news data, or None if no cache
        """
        return self._cache['data']
    
    def render_news_panel(self, news_data: Optional[Dict[str, List[Dict]]] = None,
                         show_loading: bool = False) -> html.Div:
        """
        Render news panel HTML component.
        
        Args:
            news_data: News data to render (uses cache if None)
            show_loading: If True, show loading indicator
            
        Returns:
            html.Div containing news items or appropriate message
        """
        if show_loading:
            return html.Div(
                'Loading news...',
                **{
                    'data-testid': 'news-panel',
                    'style': {
                        'padding': '16px',
                        'color': '#94a3b8',
                        'textAlign': 'center',
                        'fontStyle': 'italic'
                    }
                }
            )
        
        # Use provided data or cached data
        if news_data is None:
            news_data = self.get_cached_news()
        
        if news_data is None:
            return html.Div(
                'No news data available. Run analysis to fetch news.',
                **{
                    'data-testid': 'news-panel',
                    'style': {
                        'padding': '16px',
                        'color': '#94a3b8',
                        'textAlign': 'center'
                    }
                }
            )
        
        # Check if we have any news items
        has_news = any(len(items) > 0 for items in news_data.values())
        
        if not has_news:
            return html.Div(
                'No recent news available from providers.',
                **{
                    'data-testid': 'news-panel',
                    'style': {
                        'padding': '16px',
                        'color': '#94a3b8',
                        'textAlign': 'center'
                    }
                }
            )
        
        # Render news items
        news_elements = []
        
        for ticker, headlines in news_data.items():
            for headline_data in headlines:
                news_elements.append(html.Div([
                    html.Strong(
                        f"{ticker}: ",
                        style={'color': '#3b82f6', 'fontWeight': 'bold'}
                    ),
                    html.A(
                        headline_data.get('headline', 'No headline'),
                        href=headline_data.get('url', '#'),
                        target='_blank',
                        style={
                            'color': '#e0e0e0',
                            'textDecoration': 'none',
                            'hover': {'textDecoration': 'underline'}
                        }
                    ),
                    html.Span(
                        f" - {headline_data.get('source', 'Unknown')}",
                        style={
                            'fontSize': '12px',
                            'color': '#94a3b8',
                            'marginLeft': '8px',
                            'fontStyle': 'italic'
                        }
                    )
                ], style={
                    'marginBottom': '12px',
                    'padding': '8px',
                    'borderBottom': '1px solid #333',
                    'lineHeight': '1.5'
                }))
        
        # Add cache age indicator if cache is stale
        if self.is_news_stale() and self._cache['timestamp'] is not None:
            age_minutes = int(self._get_cache_age() / 60)
            news_elements.insert(0, html.Div(
                f"⚠️ News is {age_minutes} minutes old (refreshing...)",
                style={
                    'padding': '8px',
                    'backgroundColor': '#fef3c7',
                    'color': '#92400e',
                    'borderRadius': '4px',
                    'marginBottom': '12px',
                    'fontSize': '12px',
                    'textAlign': 'center'
                }
            ))
        
        return html.Div(
            news_elements,
            **{
                'data-testid': 'news-panel',
                'style': {'padding': '8px'}
            }
        )
    
    def clear_cache(self):
        """Clear news cache."""
        self._cache = {
            'data': None,
            'tickers': None,
            'timestamp': None
        }
        logger.info("News cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache metadata for debugging.
        
        Returns:
            Dict with cache information
        """
        return {
            'has_data': self._cache['data'] is not None,
            'tickers': self._cache['tickers'],
            'timestamp': self._cache['timestamp'],
            'age_seconds': self._get_cache_age(),
            'is_stale': self.is_news_stale(),
            'ttl_seconds': self.ttl_seconds,
            'item_count': sum(len(items) for items in self._cache['data'].values()) 
                         if self._cache['data'] else 0
        }
    
    # Private helper methods
    
    def _can_use_cache(self, tickers: List[str]) -> bool:
        """Check if cache can be used for given tickers."""
        if self._cache['data'] is None:
            return False
        
        if self._cache['tickers'] != tickers:
            logger.debug("Cache miss: ticker list changed")
            return False
        
        if self.is_news_stale():
            logger.debug("Cache miss: data is stale")
            return False
        
        return True
    
    def _get_cache_age(self) -> float:
        """Get cache age in seconds."""
        if self._cache['timestamp'] is None:
            return float('inf')
        
        return time.time() - self._cache['timestamp']
    
    def _fetch_from_fixture(self, tickers: List[str], max_per_ticker: int = 2) -> Dict[str, List[Dict]]:
        """
        Fetch news from fixture file (deterministic/fallback).
        
        Args:
            tickers: List of ticker symbols
            max_per_ticker: Max items per ticker
            
        Returns:
            Dict mapping ticker to news items
        """
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'tests/fixtures/market_trends/news_fixtures.json'
        )
        
        try:
            if os.path.exists(fixture_path):
                with open(fixture_path, 'r', encoding='utf-8') as f:
                    fixture_data = json.load(f)
                
                # Extract news items from fixture
                all_news = fixture_data.get('news_items', [])
                
                # Organize by ticker
                news_by_ticker = {}
                for ticker in tickers:
                    ticker_upper = ticker.upper()
                    ticker_news = [
                        item for item in all_news
                        if ticker_upper in (item.get('headline', '') + item.get('summary', '')).upper()
                    ]
                    news_by_ticker[ticker] = ticker_news[:max_per_ticker]
                    
                    # If no ticker-specific news, use generic items
                    if not ticker_news:
                        news_by_ticker[ticker] = all_news[:max_per_ticker]
                
                logger.info(f"Loaded news from fixture: {sum(len(v) for v in news_by_ticker.values())} items")
                return news_by_ticker
            else:
                logger.warning(f"Fixture file not found: {fixture_path}, using stub data")
                return self._generate_stub_news(tickers, max_per_ticker)
        
        except Exception as e:
            logger.error(f"Error loading fixture: {e}")
            return self._generate_stub_news(tickers, max_per_ticker)
    
    def _generate_stub_news(self, tickers: List[str], max_per_ticker: int = 2) -> Dict[str, List[Dict]]:
        """
        Generate stub news items for testing (last resort fallback).
        
        Args:
            tickers: List of ticker symbols
            max_per_ticker: Max items per ticker
            
        Returns:
            Dict mapping ticker to stub news items
        """
        news_by_ticker = {}
        for ticker in tickers:
            news_by_ticker[ticker] = [
                {
                    'headline': f'Market Update: {ticker} - Stub Data',
                    'summary': f'Latest developments for {ticker} - data unavailable.',
                    'source': 'Stub Provider',
                    'url': '#',
                    'datetime': datetime.now(timezone.utc).isoformat()
                }
                for _ in range(max_per_ticker)
            ]
        
        logger.info(f"Generated stub news for {len(tickers)} tickers")
        return news_by_ticker
