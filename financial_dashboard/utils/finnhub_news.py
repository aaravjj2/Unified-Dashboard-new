"""
Finnhub News Integration with Sentiment Analysis
Fetches company news from Finnhub API with rate limiting
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import deque
import threading
import json
from pathlib import Path
from typing import Optional

# Load environment variables for API keys
from dotenv import load_dotenv
_base = Path(__file__).parent.parent
load_dotenv(_base / "keys.env", override=True)
load_dotenv(_base.parent / "doppler.env", override=True)
load_dotenv(_base.parent / "keys.env", override=True)

logger = logging.getLogger(__name__)

# Rate limiter class (60 requests per minute per key)
class RateLimiter:
    def __init__(self, max_calls=60, time_window=60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()
            # Remove calls older than time_window
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            if len(self.calls) >= self.max_calls:
                # Wait until oldest call expires
                sleep_time = self.time_window - (now - self.calls[0]) + 0.1
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    # Clean up again after sleep
                    now = time.time()
                    while self.calls and self.calls[0] < now - self.time_window:
                        self.calls.popleft()
            
            self.calls.append(now)


# Initialize rate limiters for both keys
FINNHUB_KEY_1 = os.getenv('FINNHUB_API_KEY', '')
FINNHUB_KEY_2 = os.getenv('FINNHUB2_API_KEY', '')
rate_limiter_1 = RateLimiter(max_calls=60, time_window=60)
rate_limiter_2 = RateLimiter(max_calls=60, time_window=60)

# Simple on-disk cache for news to avoid repeated network calls
CACHE_DIR = Path(__file__).parent.parent / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / 'finnhub_news_cache.json'
CACHE_LOCK = threading.Lock()


def _load_cache() -> dict:
    try:
        if not CACHE_FILE.exists():
            return {}
        with CACHE_FILE.open('r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict):
    try:
        with CACHE_LOCK:
            with CACHE_FILE.open('w') as f:
                json.dump(cache, f)
    except Exception as e:
        logger.debug(f"Failed to write news cache: {e}")


def get_cached_news(ticker: str, ttl_seconds: int = 3600) -> Optional[list]:
    """Return cached news for ticker if present and not older than ttl_seconds."""
    try:
        cache = _load_cache()
        entry = cache.get(ticker)
        if not entry:
            return None
        ts = entry.get('ts', 0)
        if time.time() - ts > ttl_seconds:
            return None
        return entry.get('data', [])
    except Exception:
        return None


def set_cached_news(ticker: str, data: list):
    try:
        cache = _load_cache()
        cache[ticker] = {'ts': time.time(), 'data': data}
        _save_cache(cache)
    except Exception as e:
        logger.debug(f"Failed to set cache for {ticker}: {e}")


def prefetch_news_for_tickers(tickers, days_back=7, ttl_seconds=3600):
    """Fetch news for a list of tickers in parallel and populate the on-disk cache.

    This is intended to run in a background thread/worker so UI rendering is not blocked.
    """
    if not tickers:
        return

    def _fetch_and_cache(t):
        try:
            # If cache is fresh, skip
            cached = get_cached_news(t, ttl_seconds=ttl_seconds)
            if cached is not None:
                return
            news = get_ticker_news_parallel(t, days_back=days_back, max_news=10)
            if news is None:
                news = []
            set_cached_news(t, news)
        except Exception as e:
            logger.debug(f"Prefetch error for {t}: {e}")

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(tickers)))) as ex:
        futures = [ex.submit(_fetch_and_cache, t) for t in tickers]
        # don't block waiting for all to finish here; this function can be invoked in background
        for fut in as_completed(futures, timeout=30):
            try:
                fut.result()
            except Exception:
                continue


def prefetch_news_in_background(tickers, days_back=7, ttl_seconds=3600):
    t = threading.Thread(target=prefetch_news_for_tickers, args=(tickers, days_back, ttl_seconds), daemon=True)
    t.start()


# Background job registry for prefetch jobs
PREFETCH_JOBS_LOCK = threading.Lock()
PREFETCH_JOBS = {}


def start_prefetch_job(tickers, days_back=7, ttl_seconds=3600):
    """Start a background prefetch job and return a job_id.

    Job status is stored in PREFETCH_JOBS[job_id] with keys: started, finished, error, tickers, started_at, finished_at
    """
    job_id = f"prefetch-{int(time.time()*1000)}"

    def _job():
        with PREFETCH_JOBS_LOCK:
            PREFETCH_JOBS[job_id]['started'] = True
            PREFETCH_JOBS[job_id]['started_at'] = time.time()
        try:
            prefetch_news_for_tickers(tickers, days_back=days_back, ttl_seconds=ttl_seconds)
            with PREFETCH_JOBS_LOCK:
                PREFETCH_JOBS[job_id]['finished'] = True
                PREFETCH_JOBS[job_id]['finished_at'] = time.time()
        except Exception as e:
            with PREFETCH_JOBS_LOCK:
                PREFETCH_JOBS[job_id]['error'] = str(e)
                PREFETCH_JOBS[job_id]['finished'] = True
                PREFETCH_JOBS[job_id]['finished_at'] = time.time()

    with PREFETCH_JOBS_LOCK:
        PREFETCH_JOBS[job_id] = {
            'tickers': list(tickers),
            'started': False,
            'finished': False,
            'error': None,
            'started_at': None,
            'finished_at': None
        }

    th = threading.Thread(target=_job, daemon=True)
    th.start()
    return job_id


def get_prefetch_job_status(job_id):
    with PREFETCH_JOBS_LOCK:
        return PREFETCH_JOBS.get(job_id)


def get_latest_prefetch_timestamp():
    """Return the latest prefetched timestamp recorded in the cache file (approx)."""
    try:
        cache = _load_cache()
        latest = 0
        for v in cache.values():
            ts = v.get('ts', 0)
            if ts and ts > latest:
                latest = ts
        return latest
    except Exception:
        return 0


def get_simple_sentiment(headline, summary):
    """
    Simple rule-based sentiment analysis.
    Returns: 'positive', 'negative', or 'neutral'
    """
    text = (headline + ' ' + summary).lower()
    
    # Positive keywords
    positive_words = [
        'beat', 'surge', 'gain', 'rise', 'jump', 'upgrade', 'growth',
        'profit', 'revenue', 'exceed', 'outperform', 'strong', 'success',
        'breakthrough', 'approval', 'launched', 'partnership', 'acquired',
        'expansion', 'record', 'soar', 'rally', 'bullish', 'optimistic'
    ]
    
    # Negative keywords
    negative_words = [
        'fall', 'drop', 'decline', 'loss', 'miss', 'downgrade', 'weak',
        'concern', 'issue', 'problem', 'lawsuit', 'investigation', 'delay',
        'cut', 'reduce', 'slash', 'warning', 'risk', 'bearish', 'pessimistic',
        'plunge', 'crash', 'fail', 'bankruptcy', 'layoff', 'recession'
    ]
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'


def fetch_company_news(ticker, api_key, rate_limiter, days_back=30):
    """
    Fetch company news from Finnhub for a single ticker.
    
    Args:
        ticker: Stock symbol
        api_key: Finnhub API key
        rate_limiter: RateLimiter instance
        days_back: Number of days to look back
    
    Returns:
        List of news dicts or None on error
    """
    try:
        # Wait for rate limit
        rate_limiter.wait_if_needed()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Finnhub API endpoint
        url = "https://finnhub.io/api/v1/company-news"
        params = {
            'symbol': ticker,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'token': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        news_items = response.json()
        
        if not news_items:
            logger.debug(f"No news found for {ticker}")
            return []
        
        # Process and enrich news items
        processed_news = []
        for item in news_items[:10]:  # Limit to 10 most recent
            try:
                headline = item.get('headline', 'No headline')
                summary = item.get('summary', '')
                
                # Get sentiment
                sentiment = get_simple_sentiment(headline, summary)
                
                # Convert timestamp to readable date
                timestamp = item.get('datetime', 0)
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M') if timestamp else 'Unknown'
                
                processed_news.append({
                    'date': date_str,
                    'headline': headline,
                    'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                    'sentiment': sentiment,
                    'source': item.get('source', 'Unknown'),
                    'url': item.get('url', '')
                })
            except Exception as e:
                logger.warning(f"Error processing news item: {e}")
                continue
        
        return processed_news
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching news for {ticker}: {e}")
        return None


def get_ticker_news_parallel(ticker, days_back=30, max_news=5):
    """
    Fetch news for a ticker using both API keys in parallel.
    
    Args:
        ticker: Stock symbol
        days_back: Days to look back
        max_news: Maximum number of news items to return
    
    Returns:
        List of news dicts sorted by date (most recent first)
    """
    if not FINNHUB_KEY_1 and not FINNHUB_KEY_2:
        logger.warning("No Finnhub API keys configured")
        return []
    
    all_news = []
    
    # Use ThreadPoolExecutor for parallel fetching
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        
        if FINNHUB_KEY_1:
            futures.append(executor.submit(fetch_company_news, ticker, FINNHUB_KEY_1, rate_limiter_1, days_back))
        
        if FINNHUB_KEY_2:
            futures.append(executor.submit(fetch_company_news, ticker, FINNHUB_KEY_2, rate_limiter_2, days_back))
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    all_news.extend(result)
            except Exception as e:
                logger.error(f"Error in parallel news fetch: {e}")
    
    if not all_news:
        return []
    
    # Remove duplicates based on headline
    seen_headlines = set()
    unique_news = []
    for news in all_news:
        if news['headline'] not in seen_headlines:
            seen_headlines.add(news['headline'])
            unique_news.append(news)
    
    # Sort by date (most recent first) - handle datetime objects and strings
    try:
        unique_news.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M') if isinstance(x['date'], str) else x['date'], reverse=True)
    except:
        pass  # Keep original order if sorting fails
    
    # Return top N news items
    return unique_news[:max_news]


def get_high_severity_news(ticker, days_back=7):
    """
    Get recent high-impact news for a ticker.
    High severity determined by sentiment and recency.
    
    Returns:
        List of high-severity news items
    """
    # Check on-disk cache first (1 hour TTL). If present and fresh, use it to avoid network call.
    cached = get_cached_news(ticker, ttl_seconds=3600)
    if cached is not None:
        all_news = cached
    else:
        all_news = get_ticker_news_parallel(ticker, days_back=days_back, max_news=10)
        # Persist fetched news to cache for future quick reads
        if all_news is not None:
            try:
                set_cached_news(ticker, all_news)
            except Exception:
                pass
    
    if not all_news:
        return []
    
    # Consider news from last 7 days as potentially high severity
    # Prioritize negative news (requires immediate attention)
    high_severity = []
    for news in all_news:
        if news['sentiment'] == 'negative':
            high_severity.append({
                **news,
                'severity': 'HIGH'
            })
        elif news['sentiment'] == 'positive' and len(high_severity) < 3:
            high_severity.append({
                **news,
                'severity': 'MEDIUM'
            })
    
    return high_severity[:5]  # Top 5 high-severity items


if __name__ == '__main__':
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    test_ticker = 'AAPL'
    print(f"Fetching news for {test_ticker}...")
    
    news = get_ticker_news_parallel(test_ticker, days_back=7, max_news=5)
    
    print(f"\nFound {len(news)} news items:\n")
    for item in news:
        print(f"[{item['sentiment'].upper()}] {item['date']}")
        print(f"  {item['headline']}")
        print(f"  Source: {item['source']}")
        print()
