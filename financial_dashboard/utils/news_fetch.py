"""
News Fetching Utility

Fetches headlines from news sources like Finnhub with key rotation and rate limiting.
Caches results to minimize API calls.

Usage:
    from utils import news_fetch
    headlines = news_fetch.fetch_headlines(['AAPL', 'MSFT'], since_ts='2025-10-01')
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

# API Configuration
FINNHUB_API_KEYS = [
    os.environ.get('FINNHUB_API_KEY_1'),
    os.environ.get('FINNHUB_API_KEY_2'),
    os.environ.get('FINNHUB_API_KEY_3')
]
FINNHUB_API_KEYS = [key for key in FINNHUB_API_KEYS if key]  # Filter out None

CACHE_DIR = Path('cache/news')
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting
REQUESTS_PER_MINUTE = 60
REQUEST_DELAY = 60.0 / REQUESTS_PER_MINUTE
last_request_time = 0
current_key_index = 0


def fetch_headlines(tickers: List[str], since_ts: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch news headlines for given tickers.
    
    Args:
        tickers: List of stock tickers
        since_ts: Fetch news since this timestamp (YYYY-MM-DD format)
                 Defaults to 7 days ago
    
    Returns:
        DataFrame with columns: ticker, headline, summary, source, timestamp, url
    """
    if not FINNHUB_API_KEYS:
        logger.error("No Finnhub API keys configured. Set FINNHUB_API_KEY_1, _2, _3 in environment.")
        return pd.DataFrame()
    
    if since_ts is None:
        since_dt = datetime.now() - timedelta(days=7)
        since_ts = since_dt.strftime('%Y-%m-%d')
    
    # Check cache first
    cache_file = CACHE_DIR / f"headlines_{since_ts}_{'_'.join(sorted(tickers[:5]))}.parquet"
    if cache_file.exists():
        cache_age = time.time() - cache_file.stat().st_mtime
        if cache_age < 3600:  # Cache valid for 1 hour
            logger.info(f"Loading headlines from cache: {cache_file}")
            return pd.read_parquet(cache_file)
    
    all_headlines = []
    
    for ticker in tickers:
        try:
            headlines = _fetch_ticker_news(ticker, since_ts)
            for headline in headlines:
                all_headlines.append({
                    'ticker': ticker,
                    'headline': headline.get('headline', ''),
                    'summary': headline.get('summary', ''),
                    'source': headline.get('source', ''),
                    'timestamp': datetime.fromtimestamp(headline.get('datetime', 0)),
                    'url': headline.get('url', '')
                })
        except Exception as e:
            logger.warning(f"Error fetching news for {ticker}: {e}")
            continue
    
    if not all_headlines:
        return pd.DataFrame(columns=['ticker', 'headline', 'summary', 'source', 'timestamp', 'url'])
    
    df = pd.DataFrame(all_headlines)
    
    # Cache results
    try:
        df.to_parquet(cache_file, index=False)
        logger.info(f"Cached {len(df)} headlines to {cache_file}")
    except Exception as e:
        logger.warning(f"Error caching headlines: {e}")
    
    return df


def _fetch_ticker_news(ticker: str, since_ts: str) -> List[Dict]:
    """Fetch news for a single ticker from Finnhub API."""
    global last_request_time, current_key_index
    
    # Rate limiting
    elapsed = time.time() - last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    
    # Get current API key
    api_key = FINNHUB_API_KEYS[current_key_index]
    
    # Convert date to Unix timestamp
    since_dt = datetime.strptime(since_ts, '%Y-%m-%d')
    from_ts = int(since_dt.timestamp())
    to_ts = int(datetime.now().timestamp())
    
    url = 'https://finnhub.io/api/v1/company-news'
    params = {
        'symbol': ticker,
        'from': since_ts,
        'to': datetime.now().strftime('%Y-%m-%d'),
        'token': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        last_request_time = time.time()
        
        if response.status_code == 429:  # Rate limit hit
            logger.warning(f"Rate limit hit for key {current_key_index}. Rotating keys.")
            current_key_index = (current_key_index + 1) % len(FINNHUB_API_KEYS)
            time.sleep(1)
            return _fetch_ticker_news(ticker, since_ts)  # Retry with new key
        
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"Fetched {len(data)} headlines for {ticker}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {ticker}: {e}")
        return []


def fetch_market_news(category: str = 'general', limit: int = 50) -> pd.DataFrame:
    """
    Fetch general market news (not ticker-specific).
    
    Args:
        category: News category (general, forex, crypto, merger)
        limit: Maximum number of headlines to fetch
    
    Returns:
        DataFrame with news headlines
    """
    global last_request_time, current_key_index
    
    if not FINNHUB_API_KEYS:
        logger.error("No Finnhub API keys configured")
        return pd.DataFrame()
    
    # Rate limiting
    elapsed = time.time() - last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    
    api_key = FINNHUB_API_KEYS[current_key_index]
    
    url = 'https://finnhub.io/api/v1/news'
    params = {
        'category': category,
        'token': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        last_request_time = time.time()
        
        if response.status_code == 429:
            current_key_index = (current_key_index + 1) % len(FINNHUB_API_KEYS)
            time.sleep(1)
            return fetch_market_news(category, limit)
        
        response.raise_for_status()
        data = response.json()
        
        headlines = []
        for item in data[:limit]:
            headlines.append({
                'headline': item.get('headline', ''),
                'summary': item.get('summary', ''),
                'source': item.get('source', ''),
                'timestamp': datetime.fromtimestamp(item.get('datetime', 0)),
                'url': item.get('url', ''),
                'category': category
            })
        
        df = pd.DataFrame(headlines)
        logger.info(f"Fetched {len(df)} market news headlines (category: {category})")
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for market news: {e}")
        return pd.DataFrame()


if __name__ == '__main__':
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print("Testing news fetch utility...")
    print("\n1. Fetching ticker-specific news...")
    ticker_news = fetch_headlines(['AAPL', 'MSFT'], since_ts='2025-10-01')
    print(f"Found {len(ticker_news)} headlines")
    if not ticker_news.empty:
        print(ticker_news.head())
    
    print("\n2. Fetching general market news...")
    market_news = fetch_market_news('general', limit=10)
    print(f"Found {len(market_news)} headlines")
    if not market_news.empty:
        print(market_news.head())
