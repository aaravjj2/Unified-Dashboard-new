"""
Technical Indicators Client (No External API Dependencies)
==========================================================

Calculates RSI, MACD, and other indicators locally using yfinance data.
NO Alpha Vantage or external paid API required.

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

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed - using mock data only")


class RateLimiter:
    """
    Token Bucket Rate Limiter for API calls.
    Still useful for rate-limiting yfinance calls to avoid IP blocks.
    """
    
    def __init__(self, max_calls: int = 10, period_seconds: int = 60):
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
        """Acquire a token, blocking if necessary."""
        deadline = None if timeout is None else time.time() + timeout
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                
                wait_time = (1.0 - self.tokens) / self.refill_rate
            
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return False
                wait_time = min(wait_time, remaining)
            
            time.sleep(min(wait_time, 1.0))
    
    def limit(self, func: Callable) -> Callable:
        """Decorator to rate-limit a function."""
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


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index) from price series.
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    delta = prices.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    # Use exponential moving average for smoother RSI
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1e-10)  # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    MACD Line = 12-day EMA - 26-day EMA
    Signal Line = 9-day EMA of MACD Line
    Histogram = MACD Line - Signal Line
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


class AlphaVantageClient:
    """
    Technical Indicators Client - NO EXTERNAL API DEPENDENCY.
    
    Uses yfinance for price data and calculates indicators locally.
    Falls back to deterministic mock data for testing.
    
    Features:
    - RSI calculation (local)
    - MACD calculation (local)
    - No paid API required
    - Rate limiting for yfinance
    
    Usage:
        client = AlphaVantageClient()
        rsi = client.get_rsi("AAPL")
        macd = client.get_macd("SPY")
    """
    
    def __init__(self, api_key: str = None, deterministic: bool = None):
        """
        Initialize client.
        
        Args:
            api_key: Ignored - no external API used
            deterministic: If True, return mock data (for testing)
        """
        # Check deterministic mode
        if deterministic is None:
            deterministic = os.environ.get('BOT_DETERMINISTIC', '0') == '1'
        self.deterministic = deterministic
        
        # Rate limiter for yfinance (more generous than paid APIs)
        self._rate_limiter = RateLimiter(max_calls=10, period_seconds=60)
        
        # Cache for recent data
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 minutes
        
        mode = "deterministic" if deterministic else "yfinance"
        logger.info(f"TechnicalIndicatorsClient initialized (mode={mode}, NO external API)")
    
    def _fetch_prices(self, ticker: str, period: str = "3mo") -> Optional[pd.DataFrame]:
        """Fetch price data from yfinance."""
        if not YFINANCE_AVAILABLE or self.deterministic:
            return None
        
        try:
            self._rate_limiter.acquire()
            
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            
            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                return None
            
            return df
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            return None
    
    def _get_mock_rsi(self, ticker: str) -> Dict[str, Any]:
        """Return deterministic mock RSI data."""
        import hashlib
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
        
        macd_val = (hash_val % 200 - 100) / 100
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
        
        Calculated locally from yfinance data - NO external API.
        
        Args:
            ticker: Stock symbol
            period: RSI period (default 14)
            interval: Time interval (ignored, always daily)
            
        Returns:
            Dict with RSI data including latest value and history
        """
        ticker = ticker.upper().strip()
        
        # Check cache
        cache_key = f"rsi_{ticker}_{period}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                logger.debug(f"RSI cache hit for {ticker}")
                return cached['data']
        
        # Return mock data in deterministic mode
        if self.deterministic:
            logger.info(f"[MOCK] Getting RSI for {ticker}")
            return self._get_mock_rsi(ticker)
        
        # Fetch real data from yfinance
        logger.info(f"Calculating RSI for {ticker} (period={period}) using yfinance")
        
        df = self._fetch_prices(ticker)
        if df is None or len(df) < period + 5:
            logger.warning(f"Insufficient data for {ticker}, using mock")
            return self._get_mock_rsi(ticker)
        
        # Calculate RSI
        rsi_series = calculate_rsi(df['Close'], period)
        
        # Get recent values
        recent_rsi = rsi_series.dropna().tail(30)
        
        result = {
            'ticker': ticker,
            'indicator': 'RSI',
            'period': period,
            'latest_value': float(recent_rsi.iloc[-1]),
            'previous_value': float(recent_rsi.iloc[-2]) if len(recent_rsi) > 1 else None,
            'timestamp': datetime.now().isoformat(),
            'data_points': [
                {'date': idx.strftime('%Y-%m-%d'), 'value': float(val)}
                for idx, val in recent_rsi.items()
            ],
            'source': 'yfinance_local'
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
        
        Calculated locally from yfinance data - NO external API.
        """
        ticker = ticker.upper().strip()
        
        # Check cache
        cache_key = f"macd_{ticker}_{fast_period}_{slow_period}_{signal_period}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                logger.debug(f"MACD cache hit for {ticker}")
                return cached['data']
        
        # Return mock data in deterministic mode
        if self.deterministic:
            logger.info(f"[MOCK] Getting MACD for {ticker}")
            return self._get_mock_macd(ticker)
        
        # Fetch real data from yfinance
        logger.info(f"Calculating MACD for {ticker} using yfinance")
        
        df = self._fetch_prices(ticker)
        if df is None or len(df) < slow_period + signal_period + 5:
            logger.warning(f"Insufficient data for {ticker}, using mock")
            return self._get_mock_macd(ticker)
        
        # Calculate MACD
        macd_data = calculate_macd(df['Close'], fast_period, slow_period, signal_period)
        
        # Get recent values
        recent_macd = macd_data['macd'].dropna().tail(30)
        recent_signal = macd_data['signal'].dropna().tail(30)
        recent_hist = macd_data['histogram'].dropna().tail(30)
        
        result = {
            'ticker': ticker,
            'indicator': 'MACD',
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'latest': {
                'macd': float(recent_macd.iloc[-1]),
                'signal': float(recent_signal.iloc[-1]),
                'histogram': float(recent_hist.iloc[-1])
            },
            'timestamp': datetime.now().isoformat(),
            'data_points': [
                {
                    'date': idx.strftime('%Y-%m-%d'),
                    'macd': float(recent_macd.loc[idx]) if idx in recent_macd.index else 0,
                    'signal': float(recent_signal.loc[idx]) if idx in recent_signal.index else 0,
                    'histogram': float(recent_hist.loc[idx]) if idx in recent_hist.index else 0
                }
                for idx in recent_macd.index
            ],
            'source': 'yfinance_local'
        }
        
        # Cache result
        self._cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        return result
    
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote for a ticker using yfinance."""
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
        
        try:
            self._rate_limiter.acquire()
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'ticker': ticker,
                'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'change': info.get('regularMarketChange', 0),
                'change_percent': info.get('regularMarketChangePercent', 0),
                'volume': info.get('regularMarketVolume', 0),
                'timestamp': datetime.now().isoformat(),
                'source': 'yfinance'
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {ticker}: {e}")
            # Return mock on error
            import hashlib
            hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
            return {
                'ticker': ticker,
                'price': 100 + (hash_val % 400),
                'error': str(e),
                'source': 'fallback_mock'
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
        logger.info("Cache cleared")


# Module-level singleton
_client: Optional[AlphaVantageClient] = None


def get_av_client(deterministic: bool = None) -> AlphaVantageClient:
    """Get or create the client singleton."""
    global _client
    if _client is None:
        _client = AlphaVantageClient(deterministic=deterministic)
    return _client
