"""
Finnhub News Connector for Picks Pipeline

Fetches company news from Finnhub API with rate limiting and fallback.
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', '')
FINNHUB_BASE_URL = 'https://finnhub.io/api/v1'
RATE_LIMIT_DELAY = 1.0  # seconds between requests
MAX_RETRIES = 3

DIAGNOSTICS_DIR = Path(__file__).parent.parent.parent / 'reports' / 'picks' / 'diagnostics'
DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_news_for_universe(tickers: List[str], days_back: int = 7) -> Dict[str, List[Dict]]:
    """
    Fetch news for a list of tickers from Finnhub.
    
    Args:
        tickers: List of ticker symbols
        days_back: Number of days to look back for news
        
    Returns:
        Dict mapping ticker -> list of news articles
        
    Raises:
        ValueError: If FINNHUB_API_KEY is missing (non-fatal, caller should fallback)
    """
    if not FINNHUB_API_KEY:
        raise ValueError("FINNHUB_API_KEY not set - fallback to yfinance required")
    
    news_by_ticker = {}
    failed_tickers = []
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    from_date = start_date.strftime('%Y-%m-%d')
    to_date = end_date.strftime('%Y-%m-%d')
    
    for ticker in tickers:
        success = False
        
        for attempt in range(MAX_RETRIES):
            try:
                url = f'{FINNHUB_BASE_URL}/company-news'
                params = {
                    'symbol': ticker,
                    'from': from_date,
                    'to': to_date,
                    'token': FINNHUB_API_KEY
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 429:
                    # Rate limited
                    wait_time = (2 ** attempt) * RATE_LIMIT_DELAY
                    print(f"Rate limited for {ticker}, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                news_articles = response.json()
                
                news_by_ticker[ticker] = news_articles if isinstance(news_articles, list) else []
                success = True
                break
                
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {ticker}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RATE_LIMIT_DELAY * (attempt + 1))
        
        if not success:
            failed_tickers.append(ticker)
            news_by_ticker[ticker] = []
        
        # Rate limiting between tickers
        time.sleep(RATE_LIMIT_DELAY)
    
    # Save raw response to diagnostics
    timestamp = int(time.time())
    output_file = DIAGNOSTICS_DIR / f'finnhub_raw_{timestamp}.json'
    
    diagnostic_data = {
        'timestamp': datetime.now().isoformat(),
        'tickers_requested': len(tickers),
        'tickers_succeeded': len(tickers) - len(failed_tickers),
        'failed_tickers': failed_tickers,
        'date_range': {'from': from_date, 'to': to_date},
        'news_by_ticker': news_by_ticker
    }
    
    with open(output_file, 'w') as f:
        json.dump(diagnostic_data, f, indent=2)
    
    print(f"✅ Finnhub news fetched: {len(news_by_ticker)} tickers")
    print(f"   Diagnostics: {output_file}")
    
    if failed_tickers:
        print(f"⚠️  Failed tickers: {failed_tickers}")
    
    return news_by_ticker


def get_news_count_24h(ticker: str, news_list: List[Dict]) -> int:
    """Count news articles in last 24 hours."""
    if not news_list:
        return 0
    
    cutoff = datetime.now() - timedelta(hours=24)
    cutoff_ts = int(cutoff.timestamp())
    
    count = 0
    for article in news_list:
        if 'datetime' in article and article['datetime'] >= cutoff_ts:
            count += 1
    
    return count


def get_latest_news_summary(news_list: List[Dict], max_items: int = 3) -> List[Dict]:
    """Extract summary of latest news articles."""
    if not news_list:
        return []
    
    # Sort by datetime descending
    sorted_news = sorted(news_list, key=lambda x: x.get('datetime', 0), reverse=True)
    
    summaries = []
    for article in sorted_news[:max_items]:
        summaries.append({
            'headline': article.get('headline', ''),
            'source': article.get('source', ''),
            'url': article.get('url', ''),
            'datetime': article.get('datetime', 0),
            'summary': article.get('summary', '')[:200]  # Truncate
        })
    
    return summaries
