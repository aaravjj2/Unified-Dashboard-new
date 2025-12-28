"""
AlphaSimClient - Client wrapper for calling AlphaSim API.

This client provides a simple interface for other services to call AlphaSim,
with automatic fallback and error handling.
"""
import os
import requests
from typing import Any, Dict, Optional
from urllib.parse import urljoin


class AlphaSimClient:
    """
    Client for calling AlphaSim API.
    
    Usage:
        client = AlphaSimClient(base_url="http://localhost:8065", apikey="demo")
        data = client.time_series_daily("AAPL")
        sma = client.sma("AAPL", time_period=20)
        sentiment = client.news_sentiment("AAPL")
        options = client.options_chain("AAPL")
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        apikey: Optional[str] = None,
        timeout: int = 30,
        admin_key: Optional[str] = None
    ):
        """
        Initialize AlphaSimClient.
        
        Args:
            base_url: AlphaSim API base URL (default: from ALPHA_SIM_URL env)
            apikey: API key for rate limiting (default: from ALPHA_SIM_APIKEY env)
            timeout: Request timeout in seconds
            admin_key: Admin API key for admin endpoints
        """
        self.base_url = (base_url or os.getenv("ALPHA_SIM_URL", "http://localhost:8065")).rstrip('/') + '/'
        self.apikey = apikey or os.getenv("ALPHA_SIM_APIKEY", "demo")
        self.timeout = timeout
        self.admin_key = admin_key or os.getenv("ALPHA_SIM_ADMIN_KEY")
    
    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a GET request to the AlphaSim API.
        
        Args:
            path: API endpoint path
            params: Query parameters
        
        Returns:
            JSON response dict
        
        Raises:
            requests.RequestException: On network errors
            ValueError: On invalid responses
        """
        params = params or {}
        if self.apikey:
            params['apikey'] = self.apikey
        
        url = urljoin(self.base_url, path)
        
        headers = {}
        if self.admin_key:
            headers['X-Admin-Key'] = self.admin_key
        
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=self.timeout
        )
        
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 3600)
            raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds.")
        
        response.raise_for_status()
        return response.json()
    
    def _post(self, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a POST request to the AlphaSim API.
        """
        params = params or {}
        if self.apikey:
            params['apikey'] = self.apikey
        
        url = urljoin(self.base_url, path)
        
        headers = {}
        if self.admin_key:
            headers['X-Admin-Key'] = self.admin_key
        
        response = requests.post(
            url,
            json=data,
            params=params,
            headers=headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    # ---------- Query Endpoints ----------
    
    def time_series_daily(self, symbol: str, outputsize: str = 'compact') -> Dict[str, Any]:
        """
        Get daily time series data.
        
        Args:
            symbol: Ticker symbol
            outputsize: 'compact' (100 points) or 'full'
        
        Returns:
            TIME_SERIES_DAILY response
        """
        return self._get('query', {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize
        })
    
    def time_series_intraday(
        self,
        symbol: str,
        interval: str = '5min',
        outputsize: str = 'compact'
    ) -> Dict[str, Any]:
        """
        Get intraday time series data.
        
        Args:
            symbol: Ticker symbol
            interval: Time interval (1min, 5min, 15min, 30min, 60min)
            outputsize: 'compact' or 'full'
        
        Returns:
            TIME_SERIES_INTRADAY response
        """
        return self._get('query', {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': interval,
            'outputsize': outputsize
        })
    
    def sma(
        self,
        symbol: str,
        time_period: int = 10,
        series_type: str = 'close',
        interval: str = 'daily'
    ) -> Dict[str, Any]:
        """
        Get Simple Moving Average indicator.
        
        Args:
            symbol: Ticker symbol
            time_period: Number of periods
            series_type: Price type (open, high, low, close)
            interval: Time interval
        
        Returns:
            SMA response
        """
        return self._get('query', {
            'function': 'SMA',
            'symbol': symbol,
            'time_period': time_period,
            'series_type': series_type,
            'interval': interval
        })
    
    def ema(
        self,
        symbol: str,
        time_period: int = 10,
        series_type: str = 'close'
    ) -> Dict[str, Any]:
        """
        Get Exponential Moving Average indicator.
        """
        return self._get('query', {
            'function': 'EMA',
            'symbol': symbol,
            'time_period': time_period,
            'series_type': series_type
        })
    
    def rsi(
        self,
        symbol: str,
        time_period: int = 14,
        series_type: str = 'close'
    ) -> Dict[str, Any]:
        """
        Get Relative Strength Index indicator.
        """
        return self._get('query', {
            'function': 'RSI',
            'symbol': symbol,
            'time_period': time_period,
            'series_type': series_type
        })
    
    def news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get news sentiment analysis for a symbol.
        
        Args:
            symbol: Ticker symbol
        
        Returns:
            NEWS_SENTIMENT response with aggregate scores and article feed
        """
        return self._get('query', {
            'function': 'NEWS_SENTIMENT',
            'symbol': symbol
        })
    
    def options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None,
        option_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get options chain data.
        
        Args:
            symbol: Ticker symbol
            expiration: Specific expiration date (YYYY-MM-DD) or None for all
            option_type: 'call', 'put', or None for both
        
        Returns:
            HISTORICAL_OPTIONS response with options chain
        """
        params = {
            'function': 'HISTORICAL_OPTIONS',
            'symbol': symbol
        }
        if expiration:
            params['expiration'] = expiration
        if option_type:
            params['option_type'] = option_type
        
        return self._get('query', params)
    
    # ---------- Health/Metrics ----------
    
    def health(self) -> Dict[str, Any]:
        """Check API health."""
        return self._get('health')
    
    def metrics(self) -> Dict[str, Any]:
        """Get API metrics."""
        return self._get('metrics')
    
    # ---------- Admin Endpoints ----------
    
    def admin_get_quota(self, key: str) -> Dict[str, Any]:
        """
        Get quota info for an API key (admin only).
        
        Args:
            key: API key to check
        
        Returns:
            Quota information
        """
        return self._get(f'admin/quota/{key}')
    
    def admin_reset_quota(self, key: str, tokens: Optional[float] = None) -> Dict[str, Any]:
        """
        Reset quota for an API key (admin only).
        
        Args:
            key: API key to reset
            tokens: Number of tokens to set (defaults to max)
        
        Returns:
            Reset confirmation
        """
        params = {}
        if tokens is not None:
            params['tokens'] = tokens
        return self._post(f'admin/reset/{key}', params=params)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


# Feature flag helper
def use_alpha_sim() -> bool:
    """
    Check if AlphaSim should be used instead of external providers.
    
    Returns:
        True if USE_ALPHA_SIM env var is set to 'true'
    """
    return os.getenv('USE_ALPHA_SIM', 'false').lower() == 'true'


def get_alpha_sim_client() -> Optional[AlphaSimClient]:
    """
    Get AlphaSimClient if USE_ALPHA_SIM is enabled.
    
    Returns:
        AlphaSimClient instance if enabled, None otherwise
    """
    if use_alpha_sim():
        return AlphaSimClient()
    return None


# PriceClient integration helper
class AlphaSimPriceAdapter:
    """
    Adapter to use AlphaSim with PriceClient interface.
    
    This provides compatibility with existing code that uses PriceClient.
    """
    
    def __init__(self, client: Optional[AlphaSimClient] = None):
        self.client = client or AlphaSimClient()
    
    def get_daily(self, symbol: str, outputsize: str = 'compact') -> Optional[Dict]:
        """Get daily OHLCV data in PriceClient format."""
        try:
            result = self.client.time_series_daily(symbol, outputsize)
            
            # Convert to simple dict format
            if 'Time Series (Daily)' in result:
                return result['Time Series (Daily)']
            return None
        except Exception:
            return None
    
    def get_intraday(self, symbol: str, interval: str = '5min') -> Optional[Dict]:
        """Get intraday OHLCV data."""
        try:
            result = self.client.time_series_intraday(symbol, interval)
            
            key = f'Time Series ({interval})'
            if key in result:
                return result[key]
            return None
        except Exception:
            return None
