"""
Alpaca Markets API Client

Provides access to Alpaca's market data API for stocks and crypto.

API Documentation: https://alpaca.markets/docs/api-references/market-data-api/
"""

import os
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AlpacaClient:
    """
    Client for Alpaca Markets Data API
    
    Features:
    - Real-time and historical stock data
    - Bars, quotes, and trades
    - Crypto market data
    - News and corporate actions
    """
    
    BASE_URL = "https://data.alpaca.markets"
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        """
        Initialize Alpaca client
        
        Args:
            api_key: Alpaca API key (or use ALPACA_API_KEY env var)
            secret_key: Alpaca secret key (or use ALPACA_SECRET_KEY env var)
        """
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.secret_key = secret_key or os.getenv('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            logger.warning("Alpaca credentials not provided. Client will have limited functionality.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'APCA-API-KEY-ID': self.api_key if self.api_key else '',
            'APCA-API-SECRET-KEY': self.secret_key if self.secret_key else ''
        })
    
    def get_latest_trade(self, ticker: str) -> Dict[str, Any]:
        """
        Get the latest trade for a ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
        
        Returns:
            Dict with latest trade data
        """
        url = f"{self.BASE_URL}/v2/stocks/{ticker}/trades/latest"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Add metadata
            data['ticker'] = ticker
            data['source'] = 'alpaca'
            data['fetched_at'] = datetime.utcnow().isoformat()
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpaca API error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker, 'source': 'alpaca'}
    
    def get_bars(self, ticker: str, timeframe: str = '1Day', 
                 days_back: int = 30, limit: int = 10000) -> Dict[str, Any]:
        """
        Get historical bars (OHLCV) data
        
        Args:
            ticker: Stock ticker symbol
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day, etc.)
            days_back: Number of days of historical data
            limit: Maximum number of bars to return
        
        Returns:
            Dict with bars data
        """
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        url = f"{self.BASE_URL}/v2/stocks/{ticker}/bars"
        params = {
            'timeframe': timeframe,
            'start': start_date,
            'end': end_date,
            'limit': limit,
            'adjustment': 'all',
            'feed': 'sip'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Add metadata
            data['ticker'] = ticker
            data['source'] = 'alpaca'
            data['timeframe'] = timeframe
            data['fetched_at'] = datetime.utcnow().isoformat()
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpaca bars error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker, 'source': 'alpaca'}
    
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
            # Get latest trade
            trade = self.get_latest_trade(ticker)
            
            # Get historical bars
            bars = self.get_bars(ticker, timeframe='1Day', days_back=days_back)
            
            # Extract latest bar if available
            latest_bar = {}
            if bars.get('bars') and len(bars['bars']) > 0:
                latest = bars['bars'][-1]
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
            if len(bars.get('bars', [])) >= 2:
                prev_close = bars['bars'][-2].get('c')
                curr_close = bars['bars'][-1].get('c')
                if prev_close and curr_close:
                    change_pct = ((curr_close - prev_close) / prev_close) * 100
            
            # Get current price from trade or latest bar
            current_price = trade.get('trade', {}).get('p') or latest_bar.get('close')
            
            # Combine data
            combined = {
                'ticker': ticker,
                'source': 'alpaca',
                'current_price': current_price,
                'previous_close': bars['bars'][-2].get('c') if len(bars.get('bars', [])) >= 2 else None,
                'change_pct': change_pct,
                'high': latest_bar.get('high'),
                'low': latest_bar.get('low'),
                'volume': latest_bar.get('volume'),
                'historical': bars,
                'fetched_at': datetime.utcnow().isoformat()
            }
            
            results.append(combined)
            logger.info(f"Fetched Alpaca data for {ticker}: ${combined.get('current_price')}")
        
        return results
    
    def get_snapshot(self, ticker: str) -> Dict[str, Any]:
        """
        Get snapshot (latest quote, trade, bar, and daily bar) for a ticker
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dict with snapshot data
        """
        url = f"{self.BASE_URL}/v2/stocks/{ticker}/snapshot"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            data['ticker'] = ticker
            data['source'] = 'alpaca'
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpaca snapshot error for {ticker}: {e}")
            return {'error': str(e), 'ticker': ticker}
