"""
News fetcher for Market Trends tab.
Provides simple interface to fetch recent headlines for tickers.
Mission A3: Live News Integration + ENV HOTFIX
"""
import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple sliding-window rate limiter for news requests."""
    def __init__(self, max_requests: int, window_seconds: int):
        from collections import deque
        from threading import Lock
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = Lock()

    def acquire(self):
        import time
        with self.lock:
            now = time.time()
            while self.requests and self.requests[0] <= now - self.window_seconds:
                self.requests.popleft()
            if len(self.requests) >= self.max_requests:
                sleep_time = self.window_seconds - (now - self.requests[0]) + 0.05
                time.sleep(sleep_time)
            self.requests.append(time.time())


class NewsClient:
    """Unified news client with Finnhub primary, NewsAPI fallback."""
    
    def __init__(self, auto_validate: bool = True):
        """
        Initialize NewsClient with API keys.
        
        Args:
            auto_validate: If True, ensure keys are present via load_env
        """
        # Load environment - but don't fail if keys are missing (graceful degradation)
        try:
            from .load_env import load_environment
            env_status = load_environment(raise_on_missing=False)
        except Exception as e:
            logger.warning(f"[NewsClient] Environment load failed: {e}")
            
        self.finnhub_key = os.getenv('FINNHUB_API_KEY')
        self.newsapi_key = os.getenv('NEWSAPI_KEY') or os.getenv('NEWS_API_KEY')
        
        available = []
        if self.finnhub_key:
            available.append('Finnhub')
        if self.newsapi_key:
            available.append('NewsAPI')
            
        if available:
            logger.info(f"[NewsClient] Providers available: {', '.join(available)}")
        else:
            logger.warning("[NewsClient] No news providers available - news will be empty")
            
        # Rate limiter: avoid blasting Finnhub with >30 requests/min by default
        self._rate_limiter = RateLimiter(max_requests=30, window_seconds=60)
        # Concurrency throttle for batch fetches
        self._max_workers = 3
        
    def fetch_ticker_news(self, ticker: str, days: int = 7, max_items: int = 3) -> List[Dict]:
        """
        Fetch recent news for a single ticker.
        
        Args:
            ticker: Stock symbol
            days: Days of history to fetch
            max_items: Maximum number of news items to return
            
        Returns:
            List of news dicts with keys: ticker, headline, source, timestamp, url
        """
        news_items = []
        
        # Try Finnhub first with rate limiting and retry/backoff on 429
        if self.finnhub_key:
            try:
                self._rate_limiter.acquire()
                news_items = self._fetch_finnhub_with_retries(ticker, days)
                if news_items:
                    logger.info(f"[NewsClient] Fetched {len(news_items)} items from Finnhub for {ticker}")
                    return news_items[:max_items]
            except Exception as e:
                logger.warning(f"[NewsClient] Finnhub failed for {ticker}: {e}")
        
        # Fallback to NewsAPI
        if self.newsapi_key:
            try:
                news_items = self._fetch_newsapi(ticker, days)
                if news_items:
                    logger.info(f"[NewsClient] Fetched {len(news_items)} items from NewsAPI for {ticker}")
                    return news_items[:max_items]
            except Exception as e:
                logger.warning(f"[NewsClient] NewsAPI failed for {ticker}: {e}")
        
        logger.info(f"[NewsClient] No news available for {ticker}")
        return []
    
    def _fetch_finnhub(self, ticker: str, days: int) -> List[Dict]:
        """Fetch from Finnhub company news endpoint."""
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        url = f'https://finnhub.io/api/v1/company-news'
        params = {
            'symbol': ticker,
            'from': from_date,
            'to': to_date,
            'token': self.finnhub_key
        }
        
        # Reduced timeout from 10s to 3s to prevent UI blocking
        response = requests.get(url, params=params, timeout=3)
        response.raise_for_status()
        
        items = response.json()
        if not isinstance(items, list):
            return []
        
        news = []
        for item in items:
            try:
                # Finnhub returns epoch timestamp
                timestamp = datetime.utcfromtimestamp(item.get('datetime', 0))
                news.append({
                    'ticker': ticker,
                    'headline': item.get('headline', 'No headline'),
                    'source': item.get('source', 'Finnhub'),
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'url': item.get('url', '')
                })
            except Exception as e:
                logger.debug(f"[NewsClient] Error parsing Finnhub item: {e}")
                continue
        
        return news

    def _fetch_finnhub_with_retries(self, ticker: str, days: int, retries: int = 3, backoff: float = 1.0) -> List[Dict]:
        """Call Finnhub with simple retry/backoff on 429 or transient errors."""
        attempt = 0
        while attempt < retries:
            try:
                return self._fetch_finnhub(ticker, days)
            except requests.HTTPError as he:
                status = getattr(he.response, 'status_code', None)
                if status == 429:
                    wait = backoff * (2 ** attempt)
                    logger.warning(f"[NewsClient] Finnhub 429 for {ticker}, backing off {wait:.1f}s (attempt {attempt+1}/{retries})")
                    import time
                    time.sleep(wait)
                    attempt += 1
                    continue
                else:
                    raise
            except Exception:
                # For other exceptions, do a small backoff and retry once
                wait = backoff * (2 ** attempt)
                logger.warning(f"[NewsClient] Finnhub transient error for {ticker}, retrying in {wait:.1f}s (attempt {attempt+1}/{retries})")
                import time
                time.sleep(wait)
                attempt += 1
                continue

        # All retries failed
        logger.error(f"[NewsClient] Finnhub retries exhausted for {ticker}")
        return []
    
    def _fetch_newsapi(self, ticker: str, days: int) -> List[Dict]:
        """Fetch from NewsAPI everything endpoint."""
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': ticker,
            'from': from_date,
            'sortBy': 'publishedAt',
            'pageSize': 10,
            'apiKey': self.newsapi_key
        }
        
        # Reduced timeout from 10s to 3s to prevent UI blocking
        response = requests.get(url, params=params, timeout=3)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get('articles', [])
        
        news = []
        for article in articles:
            try:
                timestamp_str = article.get('publishedAt', '')
                timestamp = pd.to_datetime(timestamp_str).strftime('%Y-%m-%d %H:%M:%S')
                
                news.append({
                    'ticker': ticker,
                    'headline': article.get('title', 'No headline'),
                    'source': article.get('source', {}).get('name', 'NewsAPI'),
                    'timestamp': timestamp,
                    'url': article.get('url', '')
                })
            except Exception as e:
                logger.debug(f"[NewsClient] Error parsing NewsAPI article: {e}")
                continue
        
        return news


def fetch_news_for_tickers(tickers: List[str], max_per_ticker: int = 2) -> Dict[str, List[Dict]]:
    """
    Fetch news for multiple tickers.
    
    Args:
        tickers: List of stock symbols
        max_per_ticker: Maximum news items per ticker
        
    Returns:
        Dict mapping ticker -> list of news items
    """
    client = NewsClient()
    results = {}
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Submit tasks with limited concurrency to avoid hitting provider rate limits
    with ThreadPoolExecutor(max_workers=client._max_workers) as ex:
        futures = {ex.submit(client.fetch_ticker_news, t, 7, max_per_ticker): t for t in tickers}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                results[t] = fut.result()
            except Exception as e:
                logger.error(f"[fetch_news_for_tickers] Failed to fetch news for {t}: {e}")
                results[t] = []

    return results


    
    
    
