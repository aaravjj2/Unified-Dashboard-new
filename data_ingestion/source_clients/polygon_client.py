"""
Polygon.io API Client

Provides access to Polygon.io market data API with WebSocket support for real-time data.

API Documentation: https://polygon.io/docs/stocks
"""

import os
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PolygonClient:
    """
    Client for Polygon.io Stock API
    
    Features:
    - Real-time and historical stock data
    - WebSocket streaming support
    - Aggregates (bars) data
    - Ticker details and news
    """
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Polygon client
        
        Args:
            api_key: Polygon API key (or use POLYGON_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            logger.warning("Polygon API key not provided. Client will have limited functionality.")
        
        self.session = requests.Session()
    
    def get_last_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get the most recent quote for a ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
        
        Returns:
            Dict with last quote data
        """
        url = f"{self.BASE_URL}/v2/last/nbbo/{ticker}"
        params = {'apiKey': self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Add metadata
            data['ticker'] = ticker
            data['source'] = 'polygon'
            data['fetched_at'] = datetime.utcnow().isoformat()
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Polygon API error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker, 'source': 'polygon'}
    
    def get_aggregates(self, ticker: str, multiplier: int = 1, 
                      timespan: str = 'day', days_back: int = 30) -> Dict[str, Any]:
        """
        Get aggregate bars (OHLCV) data
        
        Args:
            ticker: Stock ticker symbol
            multiplier: Size of timespan multiplier
            timespan: Size of time window (minute, hour, day, week, month, quarter, year)
            days_back: Number of days of historical data
        
        Returns:
            Dict with aggregates data
        """
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        url = f"{self.BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        params = {
            'apiKey': self.api_key,
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 50000
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Add metadata
            data['ticker'] = ticker
            data['source'] = 'polygon'
            data['timespan'] = timespan
            data['fetched_at'] = datetime.utcnow().isoformat()
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Polygon aggregates error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker, 'source': 'polygon'}
    
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
            # Get last quote
            quote = self.get_last_quote(ticker)
            
            # Get aggregates (historical bars)
            aggs = self.get_aggregates(ticker, multiplier=1, timespan='day', days_back=days_back)
            
            # Extract latest bar if available
            latest_bar = {}
            if aggs.get('results') and len(aggs['results']) > 0:
                latest = aggs['results'][-1]
                latest_bar = {
                    'open': latest.get('o'),
                    'high': latest.get('h'),
                    'low': latest.get('l'),
                    'close': latest.get('c'),
                    'volume': latest.get('v'),
                    'timestamp': latest.get('t')
                }
            
            # Calculate change percentage
            change_pct = None
            if len(aggs.get('results', [])) >= 2:
                prev_close = aggs['results'][-2].get('c')
                curr_close = aggs['results'][-1].get('c')
                if prev_close and curr_close:
                    change_pct = ((curr_close - prev_close) / prev_close) * 100
            
            # Combine data
            combined = {
                'ticker': ticker,
                'source': 'polygon',
                'current_price': latest_bar.get('close'),
                'previous_close': aggs['results'][-2].get('c') if len(aggs.get('results', [])) >= 2 else None,
                'change_pct': change_pct,
                'high': latest_bar.get('high'),
                'low': latest_bar.get('low'),
                'volume': latest_bar.get('volume'),
                'historical': aggs,
                'fetched_at': datetime.utcnow().isoformat()
            }
            
            results.append(combined)
            logger.info(f"Fetched Polygon data for {ticker}: ${combined.get('current_price')}")
        
        return results
    
    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """
        Get ticker details and company information
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dict with ticker details
        """
        url = f"{self.BASE_URL}/v3/reference/tickers/{ticker}"
        params = {'apiKey': self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            data['source'] = 'polygon'
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Polygon ticker details error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker}
