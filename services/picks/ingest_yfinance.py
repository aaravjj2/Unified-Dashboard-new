"""
YFinance Connector for Picks Pipeline

Provides price data and fallback news retrieval using yfinance.
"""

import os
import json
import time
import yfinance as yf
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

DIAGNOSTICS_DIR = Path(__file__).parent.parent.parent / 'reports' / 'picks' / 'diagnostics'
DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_prices(tickers: List[str]) -> Dict[str, Dict]:
    """
    Fetch current prices and market data for tickers using yfinance.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Dict mapping ticker -> price/volume/marketcap data
    """
    prices_data = {}
    failed_tickers = []
    
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            
            # Get latest price from history
            hist = ticker.history(period='5d', interval='1d')
            
            if hist.empty:
                print(f"⚠️  No price data for {ticker_symbol}")
                failed_tickers.append(ticker_symbol)
                continue
            
            latest = hist.iloc[-1]
            
            # Get info for additional fields
            info = ticker.info
            
            prices_data[ticker_symbol] = {
                'last_price': float(latest['Close']),
                'last_price_timestamp': latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name),
                'volume': float(latest.get('Volume', 0)),
                'open': float(latest.get('Open', 0)),
                'high': float(latest.get('High', 0)),
                'low': float(latest.get('Low', 0)),
                'avg_daily_volume': info.get('averageDailyVolume10Day', info.get('averageVolume', 0)),
                'marketcap': info.get('marketCap', 0),
                'price_provenance': 'yfinance',
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error fetching {ticker_symbol}: {e}")
            failed_tickers.append(ticker_symbol)
    
    # Save diagnostics
    timestamp = int(time.time())
    output_file = DIAGNOSTICS_DIR / f'yfinance_prices_{timestamp}.json'
    
    diagnostic_data = {
        'timestamp': datetime.now().isoformat(),
        'tickers_requested': len(tickers),
        'tickers_succeeded': len(prices_data),
        'failed_tickers': failed_tickers,
        'prices_data': prices_data
    }
    
    with open(output_file, 'w') as f:
        json.dump(diagnostic_data, f, indent=2)
    
    print(f"✅ YFinance prices fetched: {len(prices_data)}/{len(tickers)} tickers")
    print(f"   Diagnostics: {output_file}")
    
    return prices_data


def fetch_news_fallback(ticker: str) -> List[Dict]:
    """
    Fallback news retrieval using yfinance Ticker.news.
    
    Args:
        ticker: Single ticker symbol
        
    Returns:
        List of news articles
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        news = ticker_obj.news
        
        if not news:
            return []
        
        # Convert to standard format
        standardized_news = []
        for article in news[:10]:  # Limit to 10
            standardized_news.append({
                'headline': article.get('title', ''),
                'source': article.get('publisher', 'Yahoo Finance'),
                'url': article.get('link', ''),
                'datetime': article.get('providerPublishTime', int(time.time())),
                'summary': article.get('title', '')  # Yahoo doesn't provide summary
            })
        
        return standardized_news
        
    except Exception as e:
        print(f"YFinance news fallback failed for {ticker}: {e}")
        return []


def fetch_news_for_universe_fallback(tickers: List[str]) -> Dict[str, List[Dict]]:
    """
    Fetch news for all tickers using yfinance as fallback.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Dict mapping ticker -> list of news articles
    """
    news_by_ticker = {}
    
    for ticker in tickers:
        news_by_ticker[ticker] = fetch_news_fallback(ticker)
        time.sleep(0.5)  # Rate limiting
    
    # Save diagnostics
    timestamp = int(time.time())
    output_file = DIAGNOSTICS_DIR / f'yfinance_news_fallback_{timestamp}.json'
    
    diagnostic_data = {
        'timestamp': datetime.now().isoformat(),
        'tickers': len(tickers),
        'news_by_ticker': news_by_ticker
    }
    
    with open(output_file, 'w') as f:
        json.dump(diagnostic_data, f, indent=2)
    
    print(f"✅ YFinance news fallback: {len(news_by_ticker)} tickers")
    print(f"   Diagnostics: {output_file}")
    
    return news_by_ticker


def enrich_with_technicals(tickers: List[str], period: str = '1mo') -> Dict[str, Dict]:
    """
    Calculate technical indicators for tickers.
    
    Args:
        tickers: List of ticker symbols
        period: Historical period for calculations
        
    Returns:
        Dict mapping ticker -> technical indicators
    """
    technicals = {}
    
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period)
            
            if len(hist) < 5:
                continue
            
            # Calculate simple indicators
            returns = hist['Close'].pct_change()
            
            technicals[ticker_symbol] = {
                'volatility_30d': float(returns.std() * (252 ** 0.5) * 100),  # Annualized
                'return_1m': float((hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100),
                'avg_volume_30d': float(hist['Volume'].mean())
            }
            
        except Exception as e:
            print(f"Technicals failed for {ticker_symbol}: {e}")
    
    return technicals
