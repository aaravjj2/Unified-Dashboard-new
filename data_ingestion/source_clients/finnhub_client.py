"""
Finnhub API Client

Provides access to Finnhub market data API for stock prices, fundamentals, and news.

API Documentation: https://finnhub.io/docs/api
"""

import os
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FinnhubClient:
    """
    Client for Finnhub Stock API
    
    Features:
    - Stock quotes (real-time and historical)
    - Company fundamentals
    - News and sentiment
    - Technical indicators
    """
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Finnhub client
        
        Args:
            api_key: Finnhub API key (or use FINNHUB_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            logger.warning("Finnhub API key not provided. Client will have limited functionality.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-Finnhub-Token': self.api_key if self.api_key else ''
        })
    
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get real-time quote for a ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
        
        Returns:
            Dict with keys: c (current price), h (high), l (low), o (open), pc (previous close), t (timestamp)
        """
        url = f"{self.BASE_URL}/quote"
        params = {'symbol': ticker}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Add metadata
            data['ticker'] = ticker
            data['source'] = 'finnhub'
            data['fetched_at'] = datetime.utcnow().isoformat()
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Finnhub API error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker, 'source': 'finnhub'}
    
    def get_candles(self, ticker: str, resolution: str = 'D', 
                    days_back: int = 30) -> Dict[str, Any]:
        """
        Get historical candlestick data
        
        Args:
            ticker: Stock ticker symbol
            resolution: Time resolution (1, 5, 15, 30, 60, D, W, M)
            days_back: Number of days of historical data
        
        Returns:
            Dict with keys: c, h, l, o, t, v (close, high, low, open, timestamp, volume arrays)
        """
        url = f"{self.BASE_URL}/stock/candle"
        
        end_time = int(datetime.utcnow().timestamp())
        start_time = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
        
        params = {
            'symbol': ticker,
            'resolution': resolution,
            'from': start_time,
            'to': end_time
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Add metadata
            data['ticker'] = ticker
            data['source'] = 'finnhub'
            data['resolution'] = resolution
            data['fetched_at'] = datetime.utcnow().isoformat()
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Finnhub candles error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker, 'source': 'finnhub'}
    
    def get_market_data(self, tickers: List[str], period: str = '1mo') -> List[Dict[str, Any]]:
        """
        Get market data for multiple tickers (unified interface)
        
        Args:
            tickers: List of ticker symbols
            period: Time period ('1d', '1w', '1mo', '3mo', '1y')
        
        Returns:
            List of dicts with market data for each ticker
        """
        # Map period to days
        period_map = {
            '1d': 1,
            '1w': 7,
            '1mo': 30,
            '3mo': 90,
            '1y': 365
        }
        days_back = period_map.get(period, 30)
        
        results = []
        for ticker in tickers:
            # Get current quote
            quote = self.get_quote(ticker)
            
            # Get historical data
            candles = self.get_candles(ticker, resolution='D', days_back=days_back)
            
            # Combine data
            combined = {
                'ticker': ticker,
                'source': 'finnhub',
                'current_price': quote.get('c'),
                'previous_close': quote.get('pc'),
                'change_pct': ((quote.get('c', 0) - quote.get('pc', 0)) / quote.get('pc', 1)) * 100 if quote.get('pc') else None,
                'high': quote.get('h'),
                'low': quote.get('l'),
                'volume': candles.get('v', [])[-1] if candles.get('v') else None,
                'historical': candles,
                'fetched_at': datetime.utcnow().isoformat()
            }
            
            results.append(combined)
            logger.info(f"Fetched Finnhub data for {ticker}: ${combined.get('current_price')}")
        
        return results
    
    def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """
        Get company profile and fundamentals
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dict with company information
        """
        url = f"{self.BASE_URL}/stock/profile2"
        params = {'symbol': ticker}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            data['ticker'] = ticker
            data['source'] = 'finnhub'
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Finnhub profile error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker}
