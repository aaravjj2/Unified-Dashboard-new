"""
Unified Price Client for Financial Dashboard

This module consolidates all price fetching logic into a single, robust client with
fallback priority: Alpaca → Finnhub → yfinance

Usage:
    from financial_dashboard.utils.price_client import PriceClient
    
    client = PriceClient()
    
    # For monthly picks (1-month lookback)
    monthly_data = client.get_prices(tickers=['AAPL', 'MSFT'], lookback_days=30, investment_per_ticker=1000.0)
    
    # For weekly picks (1-week lookback)
    weekly_data = client.get_prices(tickers=['TSLA', 'NVDA'], lookback_days=7, investment_per_ticker=250.0)

Returns:
    dict mapping ticker -> {
        'current_price': float,
        'daily_change': float (percent),
        'start_price': float (price at lookback start),
        'profit_loss': float (dollar P/L based on investment),
        'source': str ('alpaca', 'finnhub', or 'yfinance'),
        'start_date': str (ISO date of start price)
    }
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
from collections import deque
from threading import Lock
import json
from pathlib import Path
from typing import Any

# Optional dependencies with graceful degradation
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


def _safe_float(val):
    """Convert a pandas Series/scalar to float robustly.

    Handles cases where callers accidentally pass a single-element Series.
    """
    try:
        # pandas Series or DataFrame
        import pandas as _pd
        if isinstance(val, (_pd.Series, _pd.DataFrame)):
            # take first element safely
            try:
                return float(val.iloc[0])
            except Exception:
                try:
                    return float(val.values[0])
                except Exception:
                    return None
    except Exception:
        pass

    try:
        return float(val)
    except Exception:
        return None


class ProviderRateLimitException(Exception):
    """Raised when an upstream provider returns a 429 or rate-limit condition."""
    pass


class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.
    
    Tracks request timestamps and enforces maximum requests per time window.
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


class PriceClient:
    """
    Unified price fetching client with multi-source fallback.
    
    Priority order:
    1. Alpaca (fast, reliable, requires APCA_API_KEY_ID + APCA_API_SECRET_KEY)
       Rate limit: 200 requests per minute
       Free tier: IEX exchange data only, last 15 minutes historical
    2. Finnhub (current prices, requires FINNHUB_API_KEY)
       Rate limit: 60 requests per minute per key
       Free tier: /quote endpoint only (NO historical /candle access)
       Available: Company profile, quotes, news
       Forbidden: Historical OHLC candles (requires paid plan)
    3. yfinance (free, no key, but slower and rate-limited)
       Full historical data available
    
    NOTE: Free tier Finnhub keys do NOT support historical candle data.
    Use /quote for current prices only. For historical data, use yfinance.
    """
    
    # API Rate limits (requests per minute)
    ALPACA_RATE_LIMIT = 200  # 200 requests per minute (free tier)
    FINNHUB_RATE_LIMIT = 60   # 60 requests per minute per key (free tier)
    
    def __init__(self, auto_validate: bool = True, alpaca_key_id: Optional[str] = None, alpaca_secret: Optional[str] = None):
        """
        Initialize PriceClient with API credentials from environment.
        
        Args:
            auto_validate: If True, ensure environment is loaded via load_env
        """
        # Always load environment and validate keys
        from .load_env import load_environment
        env_status = load_environment(raise_on_missing=True)
        # Alpaca credentials (normalize ALPACA_API_KEY → APCA_API_KEY_ID)
        # Allow explicit keys to be passed to the client for per-purpose keys
        self.alpaca_key_id = alpaca_key_id or os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY', '')
        self.alpaca_secret = alpaca_secret or os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_SECRET', '')
        self.alpaca_base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        # Finnhub credentials (support dual key strategy)
        self.finnhub_key = os.getenv('FINNHUB_API_KEY') or os.getenv('FINNHUB_KEY', '')
        self.finnhub_key_2 = os.getenv('FINNHUB_API_KEY_2') or os.getenv('FINNHUB2_API_KEY', '')
        # If keys are missing, do NOT raise here — allow the client to be
        # instantiated for tests and UI paths that will fall back to other
        # providers (yfinance) or mock providers. Record availability flags
        # and log warnings so callers can make informed decisions.
        self.alpaca_available = bool(self.alpaca_key_id and self.alpaca_secret)
        self.finnhub_available = bool(self.finnhub_key)
        if not self.alpaca_available:
            logger.warning("Alpaca credentials not set - Alpaca will be skipped (fallbacks enabled)")
        if not self.finnhub_available:
            logger.warning("FINNHUB_API_KEY not set - Finnhub will be skipped (fallbacks enabled)")
        # Initialize rate limiters
        self.alpaca_limiter = RateLimiter(
            max_requests=self.ALPACA_RATE_LIMIT,
            window_seconds=60
        )
        self.finnhub_limiter = RateLimiter(
            max_requests=self.FINNHUB_RATE_LIMIT,
            window_seconds=60
        ) if self.finnhub_available else None
        self.finnhub_limiter_2 = RateLimiter(
            max_requests=self.FINNHUB_RATE_LIMIT,
            window_seconds=60
        ) if (self.finnhub_key_2 and self.finnhub_available) else None
        self.finnhub_key_index = 0
        # Log available sources
        sources_available = [
            f'Alpaca ({self.ALPACA_RATE_LIMIT}/min)',
            f'Finnhub-1 ({self.FINNHUB_RATE_LIMIT}/min)'
        ]
        if self.finnhub_key_2:
            sources_available.append(f'Finnhub-2 ({self.FINNHUB_RATE_LIMIT}/min)')
        logger.info(f"[PriceClient] Providers available: {', '.join(sources_available)}")
        if yf is not None:
            sources_available.append('yfinance')
        
        logger.info(f"PriceClient initialized with sources: {', '.join(sources_available) if sources_available else 'NONE'}")
        
        if not sources_available:
            logger.warning("No price data sources available! Check API keys and yfinance installation.")

        # Simple in-memory cache to avoid repeated full fetches across jobs
        # Keyed by (tickers_tuple, lookback_days, investment_per_ticker)
        self._cache = {}
        self._cache_lock = Lock()
    
    def get_prices(
        self,
        tickers: List[str],
        lookback_days: int = 30,
        investment_per_ticker: float = 1000.0,
        batch_size: int = 5,
        delay_between_batches: float = 0.2,
        cache_ttl: int = 300,
        save_to_path: Optional[str] = None,
    ) -> Dict[str, Dict]:
        """
        Fetch prices for multiple tickers with automatic fallback between sources.
        
        Args:
            tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'TSLA'])
            lookback_days: Number of days to look back for start price (30 for monthly, 7 for weekly)
            investment_per_ticker: Dollar amount invested per ticker
            batch_size: Number of tickers to fetch per batch (to avoid rate limits)
            delay_between_batches: Seconds to wait between batches
            
        Returns:
            Dict mapping ticker -> price data dict
        """
        results = {}

        # Normalize tickers list
        if not tickers:
            return results

        tickers_key = tuple(sorted(tickers))

        # Try to serve from in-process cache to avoid repeat provider calls
        try:
            with self._cache_lock:
                cached = self._cache.get((tickers_key, lookback_days, investment_per_ticker))
                if cached:
                    ts, payload = cached
                    if (time.time() - ts) < cache_ttl:
                        logger.debug(f"PriceClient cache hit for {len(tickers)} tickers (age={(time.time()-ts):.1f}s)")
                        return payload.copy()
        except Exception:
            pass

        # Implement a simple retry/backoff loop on provider rate limit errors
        max_attempts = 3
        attempt = 0
        current_batch_size = max(1, int(batch_size))
        current_delay = float(delay_between_batches)

        while attempt < max_attempts:
            attempt += 1
            try:
                results.clear()
                # Process in batches
                for i in range(0, len(tickers), current_batch_size):
                    batch = tickers[i:i+current_batch_size]

                    # Try Alpaca first
                    if self.alpaca_key_id and self.alpaca_secret:
                        try:
                            batch_results = self._fetch_from_alpaca(batch, lookback_days, investment_per_ticker)
                            results.update(batch_results)

                            # If we got all tickers, skip to next batch
                            if all(ticker in results for ticker in batch):
                                if i + current_batch_size < len(tickers):
                                    time.sleep(current_delay)
                                continue
                        except ProviderRateLimitException as pe:
                            logger.warning(f"Attempt {attempt}: Alpaca rate-limited: {pe}")
                            # escalate to outer retry/backoff
                            raise
                        except Exception as e:
                            logger.warning(f"Alpaca fetch failed for batch {i//current_batch_size + 1}: {e}")

                    # Try Finnhub for any missing tickers
                    missing_tickers = [t for t in batch if t not in results]
                    if missing_tickers and self.finnhub_key:
                        try:
                            batch_results = self._fetch_from_finnhub(missing_tickers, lookback_days, investment_per_ticker)
                            results.update(batch_results)

                            # Update missing list
                            missing_tickers = [t for t in batch if t not in results]
                        except ProviderRateLimitException as pe:
                            logger.warning(f"Attempt {attempt}: Finnhub rate-limited: {pe}")
                            raise
                        except Exception as e:
                            logger.warning(f"Finnhub fetch failed for batch {i//current_batch_size + 1}: {e}")

                    # Fall back to yfinance for remaining tickers
                    if missing_tickers and yf is not None:
                        try:
                            batch_results = self._fetch_from_yfinance(missing_tickers, lookback_days, investment_per_ticker)
                            results.update(batch_results)
                        except Exception as e:
                            logger.error(f"yfinance fetch failed for batch {i//current_batch_size + 1}: {e}")

                    # Add delay between batches (except after last batch)
                    if i + current_batch_size < len(tickers):
                        time.sleep(current_delay)

                # Completed without rate limit exception - break out
                break
            except ProviderRateLimitException:
                # Exponential backoff: reduce batch size and increase delay
                logger.warning(f"Provider rate limit encountered on attempt {attempt}. Backing off and retrying.")
                # Reduce batch size to lower concurrency and pressure
                current_batch_size = max(1, current_batch_size // 2)
                current_delay = current_delay * 2 if current_delay > 0 else 0.5
                # wait a bit before retrying
                time.sleep(0.5 * (2 ** (attempt - 1)))
                continue
            except Exception as e:
                # Non-rate-limit error: log and break to process what we have
                logger.exception(f"Unexpected error in price fetch attempt {attempt}: {e}")
                break
        
        # Handle GOOG/GOOGL alias - if GOOG missing but GOOGL exists, copy it
        if 'GOOG' in tickers and 'GOOG' not in results and 'GOOGL' in results:
            results['GOOG'] = results['GOOGL'].copy()
            logger.info("GOOG not found, using GOOGL data as alias")
        
        # Add placeholder for any tickers that completely failed
        for ticker in tickers:
            if ticker not in results:
                results[ticker] = {
                    'current_price': None,
                    'daily_change': None,
                    'start_price': None,
                    'profit_loss': None,
                    'week_start_price': None,
                    'month_start_price': None,
                    'source': 'Local',
                    'start_date': ''
                }
                logger.error(f"Failed to fetch price data for {ticker} from all sources")
        
        # BUGFIX: Add week_start_price via explicit yfinance fetch for first trading day of week
        # This fixes the issue where week_start_price was None due to missing start_price
        for ticker, data in results.items():
            if data.get('source') != 'Local':
                # Always try to fetch week_start_price explicitly using yfinance (7-day lookback)
                try:
                    week_start = self._fetch_week_start_price(ticker)
                    if week_start is not None:
                        data['week_start_price'] = week_start
                        logger.debug(f"Fetched week_start_price for {ticker}: {week_start}")
                    else:
                        # Fallback to start_price if week_start fetch failed
                        data['week_start_price'] = data.get('start_price')
                except Exception as e:
                    logger.warning(f"Failed to fetch week_start_price for {ticker}: {e}")
                    data['week_start_price'] = data.get('start_price')
                
                # Set month_start_price based on lookback_days
                if lookback_days >= 25:
                    data['month_start_price'] = data.get('start_price')
                else:
                    data['month_start_price'] = None
        
        # MISSION A2: Track provider summary for debugging
        self._log_provider_summary(results, tickers)
        # Store into simple in-process cache for short TTL to reduce repeated loads
        try:
            with self._cache_lock:
                self._cache[(tickers_key, lookback_days, investment_per_ticker)] = (time.time(), results.copy())
        except Exception:
            pass

        # If requested, persist results to disk (atomic write). This enables
        # background jobs to write aggregated results to a file that the UI can
        # read without blocking the server.
        if save_to_path:
            try:
                p = Path(save_to_path).expanduser()
                if not p.parent.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix('.tmp')
                with tmp.open('w', encoding='utf-8') as fh:
                    json.dump(results, fh, default=_json_default, ensure_ascii=False, indent=2)
                # Atomic replace
                tmp.replace(p)
                logger.info(f"Saved price results to {p}")
            except Exception as e:
                logger.exception(f"Failed to save price results to {save_to_path}: {e}")

        return results
    
    def _fetch_week_start_price(self, ticker: str) -> Optional[float]:
        """
        Fetch the week-start (Monday/first trading day) open price for a ticker using yfinance.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Week start open price, or None if fetch fails
            
        Notes:
            Fetches last 7 days of data and returns the earliest trading day's open price.
            This provides accurate week-start price for weekly return calculations.
        """
        if yf is None:
            logger.warning("yfinance not available for week_start_price fetch")
            return None
        
        try:
            # Fetch 7 days of data (ensures we get Monday even if today is Tuesday)
            data = yf.download(ticker, period="7d", interval="1d", progress=False)
            
            if not data.empty and 'Open' in data.columns:
                # Get the first trading day's open price (use safe float)
                week_start = _safe_float(data['Open'].iloc[0])
                logger.debug(f"Week start price for {ticker}: {week_start}")
                return week_start
            else:
                logger.warning(f"No data returned from yfinance for {ticker} week_start_price")
                return None
        
        except Exception as e:
            logger.error(f"Error fetching week_start_price for {ticker}: {e}")
            return None
    
    def _log_provider_summary(self, results: Dict[str, Dict], requested_tickers: List[str]) -> None:
        """Log provider usage summary - MISSION A2."""
        provider_counts = {'alpaca': 0, 'finnhub': 0, 'yfinance': 0, 'Local': 0}
        for data in results.values():
            source = data.get('source', 'Local')
            provider_counts[source] = provider_counts.get(source, 0) + 1
        
        logger.info(
            f"Price fetch complete: {len(results)}/{len(requested_tickers)} tickers | "
            f"Alpaca: {provider_counts['alpaca']} | Finnhub: {provider_counts['finnhub']} | "
            f"yfinance: {provider_counts['yfinance']} | Local: {provider_counts['Local']}"
        )
    
    def _fetch_from_alpaca(
        self,
        tickers: List[str],
        lookback_days: int,
        investment_per_ticker: float
    ) -> Dict[str, Dict]:
        """
        Fetch prices from Alpaca API.
        
        Alpaca provides high-quality, real-time market data with excellent reliability.
        Uses the v2 bars API endpoint.
        
        FREE TIER LIMITATIONS:
        - Rate limit: 200 requests per minute
        - Market data: IEX exchange data only (use feed=iex)
        - Historical: Last 15 minutes only for real-time
        - Daily bars should work for longer historical periods
        
        Note: If you get 404 errors, ensure you're using the correct base URL
        for paper trading: https://paper-api.alpaca.markets
        or data API: https://data.alpaca.markets
        """
        if not requests:
            raise RuntimeError("requests library not available")
        
        results = {}
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=lookback_days + 5)  # Add buffer for weekends/holidays
        
        headers = {
            'APCA-API-KEY-ID': self.alpaca_key_id,
            'APCA-API-SECRET-KEY': self.alpaca_secret
        }
        
        for ticker in tickers:
            # Enforce rate limit before making request
            if self.alpaca_limiter:
                self.alpaca_limiter.acquire()
            
            try:
                # Use data API base URL (not paper-api) for market data
                # Free tier requires feed=iex parameter
                url = f"https://data.alpaca.markets/v2/stocks/{ticker}/bars"
                params = {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'timeframe': '1Day',
                    'limit': 10000,
                    'adjustment': 'all',
                    'feed': 'iex'  # REQUIRED for free tier - IEX exchange data only
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                # Handle 404 specifically (common on free tier if endpoint not available)
                if response.status_code == 404:
                    logger.warning(f"Alpaca: Endpoint not found for {ticker} (404) - may need data subscription")
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                bars = data.get('bars', [])
                
                if len(bars) < 2:
                    logger.warning(f"Alpaca: Insufficient data for {ticker} ({len(bars)} bars)")
                    continue
                
                # Latest bar is current price
                latest_bar = bars[-1]
                current_price = latest_bar['c']  # close price
                
                # Find start price (lookback_days ago)
                start_bar = bars[0] if len(bars) <= lookback_days else bars[-(lookback_days + 1)]
                start_price = start_bar['c']
                start_date_str = start_bar['t'][:10]  # Extract date from timestamp
                
                # Calculate daily change (last 2 bars)
                prev_close = bars[-2]['c'] if len(bars) >= 2 else start_price
                daily_change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                
                # Calculate P/L
                shares = investment_per_ticker / start_price if start_price > 0 else 0.0
                profit_loss = (current_price - start_price) * shares if shares > 0 else 0.0
                
                results[ticker] = {
                    'current_price': round(current_price, 2),
                    'daily_change': round(daily_change_pct, 2),
                    'start_price': round(start_price, 2),
                    'profit_loss': round(profit_loss, 2),
                    'source': 'alpaca',
                    'start_date': start_date_str
                }
                
            except requests.exceptions.HTTPError as e:
                # Raise a specific exception on rate limit to allow caller to backoff
                try:
                    status = int(e.response.status_code)
                except Exception:
                    status = None
                if status == 429:
                    logger.warning(f"Alpaca rate limited for {ticker} (429)")
                    raise ProviderRateLimitException(f"Alpaca 429 for {ticker}")
                if status == 404:
                    logger.warning(f"Alpaca: Data not available for {ticker} (404) - free tier limitation")
                elif status == 403:
                    logger.warning(f"Alpaca: Access forbidden for {ticker} (403) - check subscription")
                else:
                    logger.warning(f"Alpaca HTTP error for {ticker}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Alpaca fetch failed for {ticker}: {e}")
                continue
        
        return results
    
    def _fetch_from_finnhub(
        self,
        tickers: List[str],
        lookback_days: int,
        investment_per_ticker: float
    ) -> Dict[str, Dict]:
        """
        Fetch prices from Finnhub API.
        
        Finnhub provides good coverage and reliability for US equities.
        Uses the stock/candle endpoint for OHLC data.
        
        Rate limit: 60 requests per minute per key (enforced by internal rate limiter)
        Supports dual-key rotation strategy for 2x throughput (120 req/min total)
        """
        if not requests:
            raise RuntimeError("requests library not available")
        
        results = {}
        end_timestamp = int(datetime.now().timestamp())
        start_timestamp = int((datetime.now() - timedelta(days=lookback_days + 5)).timestamp())
        
        for ticker in tickers:
            # Select API key and rate limiter (rotate if dual keys available)
            if self.finnhub_key_2 and self.finnhub_limiter_2:
                # Rotate between keys for load balancing
                if self.finnhub_key_index == 0:
                    current_key = self.finnhub_key
                    current_limiter = self.finnhub_limiter
                    self.finnhub_key_index = 1
                else:
                    current_key = self.finnhub_key_2
                    current_limiter = self.finnhub_limiter_2
                    self.finnhub_key_index = 0
            else:
                # Single key mode
                current_key = self.finnhub_key
                current_limiter = self.finnhub_limiter
            
            # Enforce rate limit before making request (60 calls/minute on free tier)
            if current_limiter:
                current_limiter.acquire()
            
            try:
                # NOTE: Free tier does NOT support /stock/candle endpoint (403 Forbidden)
                # Use /quote endpoint instead which provides current price and daily change
                url = "https://finnhub.io/api/v1/quote"
                params = {
                    'symbol': ticker,
                    'token': current_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                # Handle 403 specifically (endpoint not available on free tier)
                if response.status_code == 403:
                    logger.warning(f"Finnhub: /quote endpoint forbidden for {ticker} (403) - skipping")
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Quote response format:
                # {
                #   "c": current_price,
                #   "d": change (dollar amount),
                #   "dp": change_percent,
                #   "h": high_of_day,
                #   "l": low_of_day,
                #   "o": open_price,
                #   "pc": previous_close
                # }
                
                if not data or 'c' not in data or data['c'] == 0:
                    logger.warning(f"Finnhub: No quote data for {ticker}")
                    continue
                
                current_price = data['c']  # Current price
                previous_close = data.get('pc', current_price)  # Previous close
                daily_change_pct = data.get('dp', 0.0)  # Daily change percent
                
                # For P/L calculation, we need historical start price
                # Since /candle is forbidden, we'll use previous close as proxy
                # This is a limitation of free tier - we can't get historical data
                start_price = previous_close
                start_date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # Calculate P/L based on 1-day change (limitation of free tier)
                shares = investment_per_ticker / start_price if start_price > 0 else 0.0
                profit_loss = (current_price - start_price) * shares if shares > 0 else 0.0
                
                results[ticker] = {
                    'current_price': round(current_price, 2),
                    'daily_change': round(daily_change_pct, 2),
                    'start_price': round(start_price, 2),
                    'profit_loss': round(profit_loss, 2),
                    'source': 'finnhub',
                    'start_date': start_date_str,
                    'note': 'Free tier: 1-day data only'  # Indicate limitation
                }
                
            except requests.exceptions.HTTPError as e:
                try:
                    status = int(e.response.status_code)
                except Exception:
                    status = None
                if status == 429:
                    logger.warning(f"Finnhub rate limited for {ticker} (429)")
                    raise ProviderRateLimitException(f"Finnhub 429 for {ticker}")
                if status == 403:
                    logger.warning(f"Finnhub: Endpoint forbidden for {ticker} (403) - free tier limitation")
                else:
                    logger.warning(f"Finnhub HTTP error for {ticker}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Finnhub fetch failed for {ticker}: {e}")
                continue
        
        return results
    
    def _fetch_from_yfinance(
        self,
        tickers: List[str],
        lookback_days: int,
        investment_per_ticker: float,
        max_retries: int = 3,
        max_batch_size: int = 50
    ) -> Dict[str, Dict]:
        """
        Fetch prices from yfinance (Yahoo Finance) - MISSION A2 ENHANCED.
        
        Free, no API key required. Now includes:
        - Retry logic with exponential backoff (0.5s, 1s, 2s)
        - Batch limiting (max 50 tickers per call)
        - Per-ticker fallback for single-ticker fetch on batch failures
        - Proper source metadata tracking
        """
        if yf is None:
            raise RuntimeError("yfinance not available")
        
        if pd is None:
            raise RuntimeError("pandas not available (required for yfinance)")
        
        results = {}
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=lookback_days + 5)
        
        # Process in smaller batches to avoid rate limits
        for batch_start in range(0, len(tickers), max_batch_size):
            batch_tickers = tickers[batch_start:batch_start + max_batch_size]
            
            # Try batch download with retries
            batch_success = False
            for attempt in range(max_retries):
                try:
                    batch_results = self._yfinance_batch_download(
                        batch_tickers, start_date, end_date, lookback_days, investment_per_ticker
                    )
                    results.update(batch_results)
                    batch_success = True
                    break
                except Exception as e:
                    wait_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                    logger.warning(f"yfinance batch attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
            
            # If batch failed completely, try individual tickers with retries
            if not batch_success:
                logger.info(f"Batch download failed, trying individual ticker fetches for {len(batch_tickers)} tickers")
                for ticker in batch_tickers:
                    if ticker in results:
                        continue
                    
                    for attempt in range(max_retries):
                        try:
                            ticker_result = self._yfinance_single_ticker(
                                ticker, start_date, end_date, lookback_days, investment_per_ticker
                            )
                            if ticker_result:
                                results[ticker] = ticker_result
                                break
                        except Exception as e:
                            wait_time = 0.5 * (2 ** attempt)
                            if attempt < max_retries - 1:
                                time.sleep(wait_time)
            
            # Small delay between batches
            if batch_start + max_batch_size < len(tickers):
                time.sleep(0.2)
        
        return results
    
    def _yfinance_single_ticker(
        self,
        ticker: str,
        start_date,
        end_date,
        lookback_days: int,
        investment_per_ticker: float
    ) -> Optional[Dict]:
        """Fetch single ticker from yfinance with fallback to Ticker.history()."""
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period='10d', interval='1d', actions=False)
            
            if hist.empty or 'Close' not in hist.columns:
                logger.warning(f"yfinance: No data for {ticker}")
                return None
            
            closes = hist['Close'].dropna()
            if len(closes) < 2:
                logger.warning(f"yfinance: Insufficient data for {ticker}")
                return None
            
            current_price = _safe_float(closes.iloc[-1])
            start_price = _safe_float(closes.iloc[0] if len(closes) <= lookback_days else closes.iloc[-(lookback_days + 1)])
            start_date_str = closes.index[0 if len(closes) <= lookback_days else -(lookback_days + 1)].strftime('%Y-%m-%d')

            # If any critical price is missing, bail out for this ticker
            if current_price is None or start_price is None:
                logger.warning(f"yfinance: parsed prices missing for {ticker} (current={current_price}, start={start_price})")
                return None
            
            prev_close = _safe_float(closes.iloc[-2]) if len(closes) >= 2 else start_price
            daily_change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
            
            shares = investment_per_ticker / start_price if start_price > 0 else 0.0
            profit_loss = (current_price - start_price) * shares if shares > 0 else 0.0
            
            return {
                'current_price': round(current_price, 2),
                'daily_change': round(daily_change_pct, 2),
                'start_price': round(start_price, 2),
                'profit_loss': round(profit_loss, 2),
                'source': 'yfinance',
                'start_date': start_date_str
            }
        except Exception as e:
            logger.warning(f"yfinance single ticker fetch failed for {ticker}: {e}")
            return None
    
    def _yfinance_batch_download(
        self,
        tickers: List[str],
        start_date,
        end_date,
        lookback_days: int,
        investment_per_ticker: float
    ) -> Dict[str, Dict]:
        """Batch download from yfinance - improved with threads=False for stability."""
        results = {}
        
        try:
            tickers_str = ' '.join(tickers)
            # Batch download for efficiency
            tickers_str = ' '.join(tickers)
            # Use threads=False for reliability - MISSION A2 FIX
            data = yf.download(
                tickers_str,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                progress=False,
                group_by='ticker',
                threads=False,  # CHANGED: More stable for single/small batches
                auto_adjust=True
            )
            
            # Handle single ticker case (different data structure)
            if len(tickers) == 1:
                ticker = tickers[0]
                if 'Close' not in data.columns or data.empty:
                    logger.warning(f"yfinance: No data for {ticker}")
                    return results
                
                closes = data['Close'].dropna()
                if len(closes) < 2:
                    logger.warning(f"yfinance: Insufficient data for {ticker}")
                    return results
                
                current_price = _safe_float(closes.iloc[-1])
                start_price = _safe_float(closes.iloc[0] if len(closes) <= lookback_days else closes.iloc[-(lookback_days + 1)])
                start_date_str = closes.index[0 if len(closes) <= lookback_days else -(lookback_days + 1)].strftime('%Y-%m-%d')

                if current_price is None or start_price is None:
                    logger.warning(f"yfinance(single): parsed prices missing for {ticker} (current={current_price}, start={start_price})")
                    return results
                
                prev_close = _safe_float(closes.iloc[-2]) if len(closes) >= 2 else start_price
                daily_change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                
                shares = investment_per_ticker / start_price if start_price > 0 else 0.0
                profit_loss = (current_price - start_price) * shares if shares > 0 else 0.0
                
                results[ticker] = {
                    'current_price': round(current_price, 2),
                    'daily_change': round(daily_change_pct, 2),
                    'start_price': round(start_price, 2),
                    'profit_loss': round(profit_loss, 2),
                    'source': 'yfinance',
                    'start_date': start_date_str
                }
                
                return results
            
            # Multi-ticker case
            for ticker in tickers:
                try:
                    if ticker not in data.columns.get_level_values(0):
                        logger.warning(f"yfinance: No data for {ticker}")
                        continue
                    
                    ticker_data = data[ticker]
                    if 'Close' not in ticker_data.columns or ticker_data.empty:
                        logger.warning(f"yfinance: No close data for {ticker}")
                        continue
                    
                    closes = ticker_data['Close'].dropna()
                    if len(closes) < 2:
                        logger.warning(f"yfinance: Insufficient data for {ticker}")
                        continue
                    
                    current_price = _safe_float(closes.iloc[-1])
                    start_price = _safe_float(closes.iloc[0] if len(closes) <= lookback_days else closes.iloc[-(lookback_days + 1)])
                    start_date_str = closes.index[0 if len(closes) <= lookback_days else -(lookback_days + 1)].strftime('%Y-%m-%d')

                    if current_price is None or start_price is None:
                        logger.warning(f"yfinance: parsed prices missing for {ticker} (current={current_price}, start={start_price})")
                        continue
                    
                    prev_close = _safe_float(closes.iloc[-2]) if len(closes) >= 2 else start_price
                    daily_change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                    
                    shares = investment_per_ticker / start_price if start_price > 0 else 0.0
                    profit_loss = (current_price - start_price) * shares if shares > 0 else 0.0
                    
                    results[ticker] = {
                        'current_price': round(current_price, 2),
                        'daily_change': round(daily_change_pct, 2),
                        'start_price': round(start_price, 2),
                        'profit_loss': round(profit_loss, 2),
                        'source': 'yfinance',
                        'start_date': start_date_str
                    }
                    
                except Exception as e:
                    logger.warning(f"yfinance parsing failed for {ticker}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"yfinance batch download failed: {e}")
        
        return results


# Convenience function for backward compatibility
def get_prices(tickers: List[str], lookback_days: int = 30, investment_per_ticker: float = 1000.0, save_to_path: Optional[str] = None) -> Dict[str, Dict]:
    """
    Convenience function for quick price fetching without explicit client instantiation.
    
    Args:
        tickers: List of ticker symbols
        lookback_days: Lookback period (30 for monthly, 7 for weekly)
        investment_per_ticker: Investment amount per ticker
        
    Returns:
        Dict mapping ticker -> price data
    """
    client = PriceClient()
    return client.get_prices(tickers, lookback_days, investment_per_ticker, save_to_path=save_to_path)


def _json_default(o: Any):
    """JSON serializer for non-serializable objects (numpy types, pandas scalars).

    Tries common conversions (numpy/pandas scalars -> native Python types), otherwise
    falls back to string representation.
    """
    try:
        # numpy scalar
        return float(o)
    except Exception:
        try:
            # pandas scalar (has .item())
            return o.item()
        except Exception:
            return str(o)


# ============================================================================
# NEW: Picks Pipeline Unified Data Fetching Functions
# ============================================================================

FALLBACK_LOG = Path(__file__).parent.parent.parent / 'reports' / 'picks' / 'diagnostics' / 'fallback_sources.log'


def log_fallback_event(message: str):
    """Append fallback event to log file."""
    FALLBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FALLBACK_LOG, 'a') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"[{timestamp}] {message}\n")


def fetch_prices_unified(tickers: List[str]) -> tuple[Dict[str, Dict], Dict[str, bool]]:
    """
    Fetch prices with fallback logic: Alpaca → yFinance.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Tuple of (prices_dict, sources_used_dict)
    """
    from services.picks.alpaca_prices import fetch_alpaca_prices, is_alpaca_available
    from services.picks.ingest_yfinance import fetch_prices as fetch_yfinance_prices
    
    sources_used = {'alpaca': False, 'yfinance': False}
    
    # Try Alpaca first if available
    if is_alpaca_available():
        alpaca_prices = fetch_alpaca_prices(tickers)
        
        if alpaca_prices and len(alpaca_prices) >= len(tickers) * 0.8:
            print("✅ Using Alpaca as primary price source")
            sources_used['alpaca'] = True
            return alpaca_prices, sources_used
        else:
            log_fallback_event("Alpaca prices insufficient, falling back to yfinance")
    
    # Fallback to yFinance
    log_fallback_event("Using yfinance for prices (Alpaca not available or failed)")
    yfinance_prices = fetch_yfinance_prices(tickers)
    sources_used['yfinance'] = True
    
    return yfinance_prices, sources_used


def fetch_news_unified(tickers: List[str]) -> tuple[Dict[str, List[Dict]], Dict[str, bool]]:
    """
    Fetch news with fallback logic: Finnhub → yFinance.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Tuple of (news_dict, sources_used_dict)
    """
    from services.picks.ingest_finnhub import fetch_news_for_universe, get_news_count_24h
    from services.picks.ingest_yfinance import fetch_news_for_universe_fallback
    
    sources_used = {'finnhub': False, 'yfinance': False, 'fixtures': False}
    
    # Try Finnhub first
    try:
        news_data = fetch_news_for_universe(tickers)
        news_count = sum(1 for articles in news_data.values() if articles)
        
        if news_count >= len(tickers) * 0.5:
            print(f"✅ Using Finnhub for news ({news_count}/{len(tickers)} tickers)")
            sources_used['finnhub'] = True
            return news_data, sources_used
        else:
            log_fallback_event(f"Finnhub coverage low ({news_count}/{len(tickers)}), trying yfinance")
            
    except ValueError as e:
        log_fallback_event(f"Finnhub unavailable: {e}")
    except Exception as e:
        log_fallback_event(f"Finnhub error: {e}")
    
    # Fallback to yFinance news
    try:
        log_fallback_event("Falling back to yfinance for news")
        news_data = fetch_news_for_universe_fallback(tickers)
        sources_used['yfinance'] = True
        
        news_count = sum(1 for articles in news_data.values() if articles)
        if news_count > 0:
            print(f"✅ Using yfinance for news ({news_count}/{len(tickers)} tickers)")
            return news_data, sources_used
            
    except Exception as e:
        log_fallback_event(f"YFinance news error: {e}")
    
    # Last resort: empty news
    log_fallback_event("No news sources available, using empty news")
    sources_used['fixtures'] = True
    return {ticker: [] for ticker in tickers}, sources_used


def enrich_tickers_with_data(tickers: List[str]) -> tuple[List[Dict], Dict[str, bool]]:
    """
    Enrich tickers with prices and news from all available sources.
    
    Returns:
        Tuple of (enriched_records, sources_used)
    """
    from services.picks.ingest_finnhub import get_latest_news_summary, get_news_count_24h
    
    # Fetch prices
    prices, price_sources = fetch_prices_unified(tickers)
    
    # Fetch news
    news_data, news_sources = fetch_news_unified(tickers)
    
    # Combine sources
    all_sources = {**price_sources, **news_sources}
    
    # Build enriched records
    enriched = []
    
    for ticker in tickers:
        price_info = prices.get(ticker, {})
        ticker_news = news_data.get(ticker, [])
        
        record = {
            'ticker': ticker,
            'last_price': price_info.get('last_price', 0),
            'last_price_timestamp': price_info.get('last_price_timestamp', datetime.now().isoformat()),
            'avg_daily_volume': price_info.get('avg_daily_volume', 0),
            'marketcap': price_info.get('marketcap', 0),
            'price_provenance': price_info.get('price_provenance', 'unknown'),
            'last_news': get_latest_news_summary(ticker_news, max_items=3),
            'news_count_24h': get_news_count_24h(ticker, ticker_news),
            'fetched_at': datetime.now().isoformat()
        }
        
        enriched.append(record)
    
    print(f"\n✅ Enriched {len(enriched)} tickers")
    print(f"   Sources used: {json.dumps(all_sources, indent=2)}")
    
    return enriched, all_sources

