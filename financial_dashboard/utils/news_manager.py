"""
News Manager for Market Trends Tab

Handles news fetching with TTL-based caching and auto-refresh logic.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dash import html
from financial_dashboard.utils.news_client import fetch_news_for_tickers

logger = logging.getLogger(__name__)


class NewsManager:
    """
    Manages news fetching and caching for Market Trends.
    
    Implements 5-minute TTL cache to minimize API calls while
    keeping news reasonably fresh.
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize News Manager.
        
        Args:
            ttl_seconds: Time-to-live for cache in seconds (default 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache = {
            'data': None,
            'tickers': None,
            'timestamp': None
        }
    
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
            Exception: If all news providers fail
        """
        # Check if we can use cache
        if not force_refresh and self._can_use_cache(tickers):
            logger.info(f"Using cached news (age: {self._get_cache_age():.1f}s)")
            return self._cache['data']
        
        # Fetch fresh news
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
            
            # No cache available, re-raise exception
            raise
    
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
