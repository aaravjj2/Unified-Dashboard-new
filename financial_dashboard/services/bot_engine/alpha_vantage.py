"""
Alpha Vantage Client with Rate Limiting
========================================

Implements strict 5 calls/minute rate limiting for Alpha Vantage API.
Uses a TokenBucket algorithm with time.sleep for enforcement.

Author: Bot Engine Team
Date: December 2025
"""

import os
import time
import logging
import threading
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Track rate limit state."""
    tokens: float = 5.0
    max_tokens: float = 5.0
    refill_rate: float = 5.0 / 60.0  # 5 tokens per 60 seconds
    last_refill: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def __post_init__(self):
        # Ensure lock is created even when using default_factory
        if not hasattr(self, 'lock') or self.lock is None:
            self.lock = threading.Lock()


class RateLimiter:
    """
    Token Bucket Rate Limiter for API calls.
    
    Enforces max 5 calls/minute for Alpha Vantage free tier.
    Uses blocking wait if tokens exhausted.
    
    Usage:
        limiter = RateLimiter(max_calls=5, period_seconds=60)
        
        @limiter.limit
        def make_api_call():
            ...
    """
    
    def __init__(self, max_calls: int = 5, period_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in the period
            period_seconds: Time window in seconds
        """
        self.max_tokens = float(max_calls)
        self.refill_rate = max_calls / period_seconds
        self.tokens = self.max_tokens
        self.last_refill = time.time()
        self._lock = threading.Lock()
        
        logger.info(f"RateLimiter initialized: {max_calls} calls / {period_seconds}s")
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token, blocking if necessary.
        
        Args:
            timeout: Max seconds to wait (None = wait forever)
            
        Returns:
            True if token acquired, False if timeout
        """
        deadline = None if timeout is None else time.time() + timeout
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(f"Token acquired. Remaining: {self.tokens:.2f}")
                    return True
                
                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.refill_rate
            
            # Check timeout
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    logger.warning("Rate limiter timeout - token not acquired")
                    return False
                wait_time = min(wait_time, remaining)
            
            logger.info(f"Rate limit reached. Waiting {wait_time:.1f}s for next token...")
            time.sleep(wait_time)
    
    def limit(self, func: Callable) -> Callable:
        """
        Decorator to rate-limit a function.
        
        Usage:
            @limiter.limit
            def api_call():
                ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self.acquire()
            return func(*args, **kwargs)
        return wrapper
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return self.tokens
    
    def time_until_token(self) -> float:
        """Get seconds until next token is available."""
        with self._lock:
            self._refill()
            if self.tokens >= 1.0:
                return 0.0
            return (1.0 - self.tokens) / self.refill_rate


class AlphaVantageClient:
    """
    Alpha Vantage API Client with Rate Limiting.
    
    Features:
    - Strict 5 calls/minute rate limiting
    - RSI and MACD technical indicators
    - Error handling with retries
    - Deterministic mode for testing
    
    Usage:
        client = AlphaVantageClient()
        rsi = client.get_rsi("AAPL")
        macd = client.get_macd("SPY")
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str = None, deterministic: bool = None):
        """
        Initialize Alpha Vantage client.
        
        Args:
            api_key: API key (defaults to ALPHA_VANTAGE_API_KEY env var)
            deterministic: If True, return mock data (for testing)
        """
        self.api_key = api_key or os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')
        
        # Check deterministic mode
        if deterministic is None:
            deterministic = os.environ.get('BOT_DETERMINISTIC', '0') == '1'
        self.deterministic = deterministic
        
        # Initialize rate limiter (5 calls per minute)
        self._rate_limiter = RateLimiter(max_calls=5, period_seconds=60)
        
        # Session for connection pooling
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'UnifiedDashboard/1.0 BotEngine'
        })
        
        # Cache for recent calls
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info(f"AlphaVantageClient initialized (deterministic={deterministic})")
    
    def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Make rate-limited API request.
        
        Args:
            params: Query parameters
            
        Returns:
            JSON response dict
        """
        # Add API key
        params['apikey'] = self.api_key
        
        # Acquire rate limit token (blocks if needed)
        self._rate_limiter.acquire()
        
        try:
            response = self._session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            if 'Note' in data and 'call frequency' in data['Note'].lower():
                logger.warning(f"Rate limit warning from AV: {data['Note']}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            raise
    
    def _get_mock_rsi(self, ticker: str) -> Dict[str, Any]:
        """Return deterministic mock RSI data."""
        import hashlib
        # Generate deterministic value based on ticker
        hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        base_rsi = 30 + (hash_val % 40)  # RSI between 30-70
        
        return {
            'ticker': ticker,
            'indicator': 'RSI',
            'period': 14,
            'latest_value': base_rsi + (hash_val % 10 - 5),
            'previous_value': base_rsi,
            'timestamp': datetime.now().isoformat(),
            'data_points': [
                {'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                 'value': base_rsi + (i % 10 - 5)}
                for i in range(10)
            ],
            'source': 'mock'
        }
    
    def _get_mock_macd(self, ticker: str) -> Dict[str, Any]:
        """Return deterministic mock MACD data."""
        import hashlib
        hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        
        macd_val = (hash_val % 200 - 100) / 100  # -1 to 1
        signal_val = macd_val * 0.8
        
        return {
            'ticker': ticker,
            'indicator': 'MACD',
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'latest': {
                'macd': macd_val,
                'signal': signal_val,
                'histogram': macd_val - signal_val
            },
            'timestamp': datetime.now().isoformat(),
            'data_points': [
                {
                    'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                    'macd': macd_val + (i % 5 - 2) * 0.1,
                    'signal': signal_val + (i % 3 - 1) * 0.05,
                    'histogram': (macd_val - signal_val) + (i % 4 - 2) * 0.05
                }
                for i in range(10)
            ],
            'source': 'mock'
        }
    
    def get_rsi(self, ticker: str, period: int = 14, interval: str = 'daily') -> Dict[str, Any]:
        """
        Get RSI (Relative Strength Index) for a ticker.
        
        Args:
            ticker: Stock symbol
            period: RSI period (default 14)
            interval: Time interval ('daily', '60min', etc.)
            
        Returns:
            Dict with RSI data including latest value and history
        """
        ticker = ticker.upper().strip()
        
        # Check cache
        cache_key = f"rsi_{ticker}_{period}_{interval}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                logger.debug(f"RSI cache hit for {ticker}")
                return cached['data']
        
        # Return mock data in deterministic mode
        if self.deterministic:
            logger.info(f"[MOCK] Getting RSI for {ticker}")
            return self._get_mock_rsi(ticker)
        
        # Make API request
        logger.info(f"Fetching RSI for {ticker} (period={period}, interval={interval})")
        
        params = {
            'function': 'RSI',
            'symbol': ticker,
            'interval': interval,
            'time_period': str(period),
            'series_type': 'close'
        }
        
        data = self._make_request(params)
        
        # Parse response
        tech_key = f"Technical Analysis: RSI"
        if tech_key not in data:
            raise ValueError(f"No RSI data in response for {ticker}")
        
        rsi_data = data[tech_key]
        dates = sorted(rsi_data.keys(), reverse=True)
        
        result = {
            'ticker': ticker,
            'indicator': 'RSI',
            'period': period,
            'latest_value': float(rsi_data[dates[0]]['RSI']),
            'previous_value': float(rsi_data[dates[1]]['RSI']) if len(dates) > 1 else None,
            'timestamp': datetime.now().isoformat(),
            'data_points': [
                {'date': d, 'value': float(rsi_data[d]['RSI'])}
                for d in dates[:30]
            ],
            'source': 'alphavantage'
        }
        
        # Cache result
        self._cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        return result
    
    def get_macd(self, ticker: str, fast_period: int = 12, slow_period: int = 26,
                 signal_period: int = 9, interval: str = 'daily') -> Dict[str, Any]:
        """
        Get MACD (Moving Average Convergence Divergence) for a ticker.
        
        Args:
            ticker: Stock symbol
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)
            interval: Time interval ('daily', '60min', etc.)
            
        Returns:
            Dict with MACD data including MACD line, signal, and histogram
        """
        ticker = ticker.upper().strip()
        
        # Check cache
        cache_key = f"macd_{ticker}_{fast_period}_{slow_period}_{signal_period}_{interval}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                logger.debug(f"MACD cache hit for {ticker}")
                return cached['data']
        
        # Return mock data in deterministic mode
        if self.deterministic:
            logger.info(f"[MOCK] Getting MACD for {ticker}")
            return self._get_mock_macd(ticker)
        
        # Make API request
        logger.info(f"Fetching MACD for {ticker}")
        
        params = {
            'function': 'MACD',
            'symbol': ticker,
            'interval': interval,
            'series_type': 'close',
            'fastperiod': str(fast_period),
            'slowperiod': str(slow_period),
            'signalperiod': str(signal_period)
        }
        
        data = self._make_request(params)
        
        # Parse response
        tech_key = "Technical Analysis: MACD"
        if tech_key not in data:
            raise ValueError(f"No MACD data in response for {ticker}")
        
        macd_data = data[tech_key]
        dates = sorted(macd_data.keys(), reverse=True)
        
        latest = macd_data[dates[0]]
        
        result = {
            'ticker': ticker,
            'indicator': 'MACD',
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'latest': {
                'macd': float(latest['MACD']),
                'signal': float(latest['MACD_Signal']),
                'histogram': float(latest['MACD_Hist'])
            },
            'timestamp': datetime.now().isoformat(),
            'data_points': [
                {
                    'date': d,
                    'macd': float(macd_data[d]['MACD']),
                    'signal': float(macd_data[d]['MACD_Signal']),
                    'histogram': float(macd_data[d]['MACD_Hist'])
                }
                for d in dates[:30]
            ],
            'source': 'alphavantage'
        }
        
        # Cache result
        self._cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        return result
    
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get real-time quote for a ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dict with current price, change, volume
        """
        ticker = ticker.upper().strip()
        
        if self.deterministic:
            import hashlib
            hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
            price = 100 + (hash_val % 400)
            return {
                'ticker': ticker,
                'price': price,
                'change': (hash_val % 20 - 10) / 10,
                'change_percent': (hash_val % 100 - 50) / 100,
                'volume': hash_val % 10000000,
                'timestamp': datetime.now().isoformat(),
                'source': 'mock'
            }
        
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': ticker
        }
        
        data = self._make_request(params)
        
        if 'Global Quote' not in data:
            raise ValueError(f"No quote data for {ticker}")
        
        quote = data['Global Quote']
        
        return {
            'ticker': ticker,
            'price': float(quote.get('05. price', 0)),
            'change': float(quote.get('09. change', 0)),
            'change_percent': float(quote.get('10. change percent', '0%').replace('%', '')),
            'volume': int(quote.get('06. volume', 0)),
            'timestamp': datetime.now().isoformat(),
            'source': 'alphavantage'
        }
    
    @property
    def rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return {
            'available_tokens': self._rate_limiter.available_tokens,
            'max_tokens': self._rate_limiter.max_tokens,
            'time_until_next': self._rate_limiter.time_until_token()
        }
    
    def clear_cache(self):
        """Clear the response cache."""
        self._cache.clear()
        logger.info("AlphaVantage cache cleared")


# Module-level singleton
_client: Optional[AlphaVantageClient] = None


def get_av_client(deterministic: bool = None) -> AlphaVantageClient:
    """Get or create the Alpha Vantage client singleton."""
    global _client
    if _client is None:
        _client = AlphaVantageClient(deterministic=deterministic)
    return _client
