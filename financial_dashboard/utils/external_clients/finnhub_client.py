"""
Finnhub API Client for real-time and historical market data.

This client provides a robust, rate-limited interface to the Finnhub Stock API,
handling quote fetching, historical candle data, and error scenarios gracefully.

Rate Limit: 60 requests/minute per API key (enforced via RateLimiter)
Documentation: https://finnhub.io/docs/api
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from collections import deque
from threading import Lock
import requests


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.
    
    Tracks request timestamps and enforces maximum requests per time window.
    Imported from Agent 1's refactored implementation.
    """
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds (e.g., 60 for per-minute limit)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()  # Stores timestamps of requests
        self.lock = Lock()
    
    def acquire(self) -> None:
        """
        Acquire permission to make a request. Blocks if rate limit would be exceeded.
        
        This method automatically sleeps if necessary to respect the rate limit.
        """
        with self.lock:
            now = time.time()
            
            # Remove requests outside the current window
            while self.requests and self.requests[0] <= now - self.window_seconds:
                self.requests.popleft()
            
            # If at limit, calculate required sleep time
            if len(self.requests) >= self.max_requests:
                # Sleep until the oldest request falls outside the window
                sleep_time = self.window_seconds - (now - self.requests[0]) + 0.1  # Add 100ms buffer
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached ({self.max_requests}/{self.window_seconds}s). Sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    
                    # Clean up again after sleep
                    now = time.time()
                    while self.requests and self.requests[0] <= now - self.window_seconds:
                        self.requests.popleft()
            
            # Record this request
            self.requests.append(now)


class FinnhubClient:
    """
    Client for interacting with the Finnhub Stock API.
    
    Provides rate-limited access to real-time quotes and historical candle data.
    Automatically manages API rate limits (60 requests/minute) and handles common
    error scenarios including network failures, authentication errors, and rate limit violations.
    
    Environment Variables:
        FINNHUB_API_KEY: Your Finnhub API key (required)
        
    Example:
        >>> client = FinnhubClient()
        >>> quote = client.get_quote("AAPL")
        >>> if quote:
        ...     print(f"Current price: ${quote['c']}")
        >>> 
        >>> candles = client.get_candles("AAPL", "D", 30)
        >>> if candles:
        ...     print(f"Fetched {len(candles['t'])} daily candles")
    """
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Finnhub client.
        
        Args:
            api_key: Optional API key. If not provided, reads from FINNHUB_API_KEY environment variable.
            
        Raises:
            ValueError: If no API key is provided and FINNHUB_API_KEY is not set.
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Finnhub API key not provided. "
                "Set FINNHUB_API_KEY environment variable or pass api_key parameter."
            )
        
        # Initialize rate limiter: 60 requests per minute
        self.rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
        
        # Create session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "X-Finnhub-Token": self.api_key,
            "Content-Type": "application/json"
        })
        
        logger.info("✅ FinnhubClient initialized with rate limiting (60 req/min)")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make a rate-limited request to the Finnhub API.
        
        Args:
            endpoint: API endpoint path (e.g., "/quote")
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary, or None if request failed
        """
        # Acquire rate limit permission (will block if necessary)
        self.rate_limiter.acquire()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            # Handle common HTTP errors
            if response.status_code == 403:
                logger.error(f"❌ Finnhub API authentication failed (403 Forbidden). Check your API key.")
                return None
            
            elif response.status_code == 429:
                logger.warning(f"⚠️  Finnhub API rate limit exceeded (429 Too Many Requests). Consider upgrading API tier.")
                return None
            
            elif response.status_code != 200:
                logger.error(f"❌ Finnhub API request failed with status {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Finnhub API request timed out for {endpoint}")
            return None
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Network error connecting to Finnhub API: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Unexpected error making Finnhub API request: {e}")
            return None
            
        except ValueError as e:
            logger.error(f"❌ Invalid JSON response from Finnhub API: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Fetch real-time quote data for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")
            
        Returns:
            Dictionary containing quote data with keys:
                - 'c': Current price
                - 'h': High price of the day
                - 'l': Low price of the day
                - 'o': Open price of the day
                - 'pc': Previous close price
                - 't': Timestamp (Unix seconds)
                
            Returns None if the request fails or data is unavailable.
            
        Example:
            >>> quote = client.get_quote("AAPL")
            >>> if quote:
            ...     print(f"AAPL current price: ${quote['c']:.2f}")
            ...     print(f"Change: {((quote['c'] / quote['pc']) - 1) * 100:.2f}%")
        """
        if not symbol:
            logger.warning("⚠️  Empty symbol provided to get_quote()")
            return None
        
        logger.debug(f"Fetching quote for {symbol}")
        
        data = self._make_request("/quote", params={"symbol": symbol.upper()})
        
        if data is None:
            return None
        
        # Validate response contains expected fields
        required_fields = ['c', 'h', 'l', 'o', 'pc', 't']
        if not all(field in data for field in required_fields):
            logger.warning(f"⚠️  Incomplete quote data for {symbol}: {data}")
            return None
        
        # Check if data is valid (Finnhub returns 0 for invalid symbols)
        if data.get('c', 0) == 0 and data.get('t', 0) == 0:
            logger.warning(f"⚠️  No quote data available for {symbol} (possibly invalid symbol)")
            return None
        
        logger.debug(f"✅ Quote fetched for {symbol}: ${data['c']:.2f}")
        return data
    
    def get_candles(
        self, 
        symbol: str, 
        resolution: str, 
        count: int,
        from_timestamp: Optional[int] = None
    ) -> Optional[Dict[str, List]]:
        """
        Fetch historical price candles (OHLCV data) for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")
            resolution: Candle resolution - one of: "1", "5", "15", "30", "60", "D", "W", "M"
                       (1/5/15/30/60 = minutes, D = day, W = week, M = month)
            count: Number of candles to fetch (used to calculate 'from' timestamp if not provided)
            from_timestamp: Optional Unix timestamp to start from. If not provided,
                          calculates based on count and resolution.
            
        Returns:
            Dictionary containing candle data with keys:
                - 't': List of timestamps (Unix seconds)
                - 'o': List of open prices
                - 'h': List of high prices
                - 'l': List of low prices
                - 'c': List of close prices
                - 'v': List of volumes
                - 's': Status ('ok' if successful, 'no_data' if no data)
                
            Returns None if the request fails.
            
        Example:
            >>> # Get 30 days of daily candles
            >>> candles = client.get_candles("AAPL", "D", 30)
            >>> if candles and candles['s'] == 'ok':
            ...     closes = candles['c']
            ...     print(f"Latest close: ${closes[-1]:.2f}")
            ...     print(f"30-day high: ${max(candles['h']):.2f}")
        """
        if not symbol:
            logger.warning("⚠️  Empty symbol provided to get_candles()")
            return None
        
        # Calculate 'from' timestamp if not provided
        if from_timestamp is None:
            # Estimate seconds per candle based on resolution
            resolution_seconds = {
                "1": 60,
                "5": 300,
                "15": 900,
                "30": 1800,
                "60": 3600,
                "D": 86400,
                "W": 604800,
                "M": 2592000,  # Approximate (30 days)
            }
            
            seconds_per_candle = resolution_seconds.get(resolution, 86400)
            lookback_seconds = count * seconds_per_candle
            from_timestamp = int(time.time() - lookback_seconds)
        
        to_timestamp = int(time.time())
        
        logger.debug(f"Fetching {count} {resolution} candles for {symbol}")
        
        params = {
            "symbol": symbol.upper(),
            "resolution": resolution,
            "from": from_timestamp,
            "to": to_timestamp
        }
        
        data = self._make_request("/stock/candle", params=params)
        
        if data is None:
            return None
        
        # Check status
        status = data.get('s', 'error')
        if status == 'no_data':
            logger.warning(f"⚠️  No candle data available for {symbol} (resolution: {resolution})")
            return data
        
        if status != 'ok':
            logger.error(f"❌ Candle request failed with status: {status}")
            return None
        
        # Validate response contains expected fields
        required_fields = ['t', 'o', 'h', 'l', 'c', 'v']
        if not all(field in data for field in required_fields):
            logger.warning(f"⚠️  Incomplete candle data for {symbol}: {data}")
            return None
        
        candle_count = len(data['t'])
        logger.debug(f"✅ Fetched {candle_count} candles for {symbol}")
        return data
    
    def close(self):
        """
        Close the HTTP session and clean up resources.
        
        Should be called when the client is no longer needed.
        """
        if hasattr(self, 'session'):
            self.session.close()
            logger.debug("FinnhubClient session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session is closed."""
        self.close()


if __name__ == "__main__":
    """
    Quick test of the FinnhubClient functionality.
    
    Usage:
        export FINNHUB_API_KEY=your_key_here
        python finnhub_client.py
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Testing FinnhubClient...\n")
    
    with FinnhubClient() as client:
        # Test 1: Get quote
        print("Test 1: Fetching AAPL quote...")
        quote = client.get_quote("AAPL")
        if quote:
            print(f"✅ Current price: ${quote['c']:.2f}")
            print(f"   Day range: ${quote['l']:.2f} - ${quote['h']:.2f}")
        else:
            print("❌ Quote fetch failed")
        
        print()
        
        # Test 2: Get historical candles
        print("Test 2: Fetching 30 days of daily candles for AAPL...")
        candles = client.get_candles("AAPL", "D", 30)
        if candles and candles.get('s') == 'ok':
            print(f"✅ Fetched {len(candles['t'])} candles")
            print(f"   Latest close: ${candles['c'][-1]:.2f}")
            print(f"   30-day high: ${max(candles['h']):.2f}")
            print(f"   30-day low: ${min(candles['l']):.2f}")
        else:
            print("❌ Candle fetch failed")
    
    print("\n✅ FinnhubClient test complete")
