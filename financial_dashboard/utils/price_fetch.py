"""
Price fetching helpers: yfinance (primary) then Finnhub fallback, with disk cache and key rotation.

Mission A3 ENV HOTFIX: Always load environment and validate keys before any price fetch.

Enhanced features:
    - Finnhub API key rotation (2 keys, round-robin)
    - TTL tiers: live (60s), daily (120s), weekly (6h), monthly (24h)
    - Rate limiting per source
    - Batch fetching with parallelism

Usage:
    from Dash.utils.price_fetch import fetch_prices_batch, get_price_single

Environment:
    Set FINNHUB_API_KEY and FINNHUB2_API_KEY in keys.env or environment
"""
import os
import time
import math
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

# ENV HOTFIX: Always load environment and validate keys
try:
    from .load_env import load_environment
except ImportError as exc:  # pragma: no cover - hard failure if loader missing
    raise RuntimeError("[price_fetch] ENV loader not available") from exc

try:
    env_status = load_environment(raise_on_missing=True)
    print(f"[price_fetch] ENV loaded: {env_status}")
except Exception as exc:
    raise RuntimeError(f"[price_fetch] ENV load failed: {exc}") from exc

# Try to load Doppler secrets early so environment variables are present
try:
    from financial_dashboard._shared_env import load_doppler_env
    try:
        load_doppler_env(project='dash', config='dev')
    except Exception:
        # non-fatal; proceed
        pass
except Exception:
    pass

try:
    from diskcache import Cache
except Exception:
    Cache = None
try:
    import yfinance as yf
except Exception:
    yf = None

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration and Key Rotation
# ============================================================================

FINNHUB_QUOTE = "https://finnhub.io/api/v1/quote"
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache_price'))
cache = Cache(CACHE_DIR) if Cache is not None else None

# Load Finnhub API keys for rotation
FINNHUB_KEYS: List[str] = []
FINNHUB_KEY_INDEX = 0

def _load_finnhub_keys():
    """Load Finnhub API keys from keys.env and environment."""
    global FINNHUB_KEYS
    keys_env_path = os.path.join(os.path.dirname(__file__), '..', 'keys.env')
    
    # First: support a comma-separated FINNHUB_KEYS environment variable (preferred)
    env_bulk = os.environ.get('FINNHUB_KEYS', '')
    if env_bulk:
        for k in [x.strip() for x in env_bulk.split(',') if x.strip()]:
            if k and k not in FINNHUB_KEYS:
                FINNHUB_KEYS.append(k)
        if FINNHUB_KEYS:
            logger.info(f"Loaded {len(FINNHUB_KEYS)} Finnhub API keys from FINNHUB_KEYS env")
            return FINNHUB_KEYS

    # Load from keys.env file
    if os.path.exists(keys_env_path):
        with open(keys_env_path) as f:
            for line in f:
                line = line.strip()
                # Accept multiple key names for compatibility
                if '=' in line and not line.startswith('#'):
                    kname, kval = line.split('=', 1)
                    kname = kname.strip()
                    kval = kval.strip()
                    if kname in ('FINNHUB_API_KEY', 'FINNHUB2_API_KEY', 'FINNHUB_KEY') and kval and kval not in FINNHUB_KEYS:
                        FINNHUB_KEYS.append(kval)

    # Also check environment variables
    # Legacy single-key env vars
    for env_var in ['FINNHUB_API_KEY', 'FINNHUB2_API_KEY', 'FINNHUB_KEY']:
        key = os.environ.get(env_var, '')
        if key and key not in FINNHUB_KEYS:
            FINNHUB_KEYS.append(key)
    
    if FINNHUB_KEYS:
        logger.info(f"Loaded {len(FINNHUB_KEYS)} Finnhub API keys for rotation")
    return FINNHUB_KEYS


# =========================================================================
# Rate Limiting (moved up to avoid NameError)
# =========================================================================

_rate_limits = {
    'finnhub': {'requests': [], 'limit': 60},  # 60 RPM (free tier limit)
    'yfinance': {'requests': [], 'limit': 1800}  # Generous limit for yfinance
}

# Load keys on module import
_load_finnhub_keys()

if not FINNHUB_KEYS:
    raise RuntimeError("No Finnhub API keys found. Set FINNHUB_API_KEY or FINNHUB_KEYS in env.")

logger.info(
    "[price_fetch] Providers available: Finnhub (%s keys), yfinance",
    len(FINNHUB_KEYS)
)

# Dynamically adjust finnhub rate limit based on number of keys (60 RPM per key)
try:
    if FINNHUB_KEYS:
        _rate_limits['finnhub']['limit'] = max(
            _rate_limits['finnhub'].get('limit', 60),
            60 * max(1, len(FINNHUB_KEYS))
        )
        logger.info(
            "Set finnhub combined RPM limit to %s based on %s keys",
            _rate_limits['finnhub']['limit'],
            len(FINNHUB_KEYS)
        )
except Exception:
    pass

# Legacy single key support (deprecated but kept for backward compatibility)
FINNHUB_KEY = FINNHUB_KEYS[0] if FINNHUB_KEYS else ''

def _get_next_finnhub_key():
    """Get next Finnhub API key using round-robin rotation."""
    global FINNHUB_KEY_INDEX
    if not FINNHUB_KEYS:
        return None
    key = FINNHUB_KEYS[FINNHUB_KEY_INDEX]
    FINNHUB_KEY_INDEX = (FINNHUB_KEY_INDEX + 1) % len(FINNHUB_KEYS)
    return key

# ============================================================================
# Rate Limiting
# ============================================================================

_rate_limits = {
    'finnhub': {'requests': [], 'limit': 60},  # 60 RPM (free tier limit)
    'yfinance': {'requests': [], 'limit': 1800}  # Generous limit for yfinance
}

def _check_rate_limit(source: str) -> bool:
    """Check if we're within rate limits."""
    now = time.time()
    state = _rate_limits.get(source, {})
    if not state:
        return True
    
    # Remove requests older than 1 minute
    state['requests'] = [t for t in state.get('requests', []) if now - t < 60]
    
    # Check limit
    if len(state['requests']) >= state.get('limit', 1000):
        logger.warning(f"Rate limit reached for {source}: {len(state['requests'])}/{state['limit']} RPM")
        return False
    return True

def _record_request(source: str):
    """Record a request for rate limiting."""
    state = _rate_limits.get(source)
    if state:
        state['requests'].append(time.time())

# ============================================================================
# TTL Tiers (in seconds)
# ============================================================================

TTL_LIVE = 60  # Live quotes: 1 minute
TTL_DAILY = 120  # Daily data in live mode: 2 minutes
TTL_WEEKLY = 6 * 3600  # Weekly data: 6 hours
TTL_MONTHLY = 24 * 3600  # Monthly data: 24 hours

def get_ttl_for_context(context: str = 'live') -> int:
    """Get appropriate TTL for data context."""
    if context == 'monthly':
        return TTL_MONTHLY
    elif context == 'weekly':
        return TTL_WEEKLY
    elif context == 'daily':
        return TTL_DAILY
    else:
        return TTL_LIVE


def normalize_ticker_for_yf(ticker: str) -> str:
    if not isinstance(ticker, str):
        return ticker
    return ticker.replace('.', '-')


def _cache_key(ticker: str) -> str:
    """Return a normalized cache key for a ticker so variants like 'BRK.B' and 'BRK-B'
    map to the same stored entry."""
    if not isinstance(ticker, str):
        return f'price:{ticker}'
    # normalize to yf form (dots -> dash) and upper-case for consistency
    return f"price:{normalize_ticker_for_yf(ticker).upper()}"


def finnhub_quote(ticker: str, timeout=8):
    """Fetch quote from Finnhub with key rotation and rate limiting."""
    api_key = _get_next_finnhub_key()
    if not api_key:
        raise RuntimeError('No Finnhub API keys available')
    
    # Check rate limit
    if not _check_rate_limit('finnhub'):
        raise RuntimeError('Finnhub rate limit exceeded')
    
    _record_request('finnhub')
    params = {"symbol": ticker, "token": api_key}
    r = requests.get(FINNHUB_QUOTE, params=params, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    # sanitize: treat non-positive or NaN values as missing
    def _safe(v):
        try:
            if v is None:
                return None
            fv = float(v)
            if fv <= 0 or math.isnan(fv):
                return None
            return fv
        except Exception:
            return None

    return {
        'last_price': _safe(j.get('c')),
        'high': _safe(j.get('h')),
        'low': _safe(j.get('l')),
        'open': _safe(j.get('o')),
        'prev_close': _safe(j.get('pc')),
        'volume': j.get('v', None),
        'timestamp': j.get('t'),
        'source': 'finnhub'
    }


def yfinance_snapshot(ticker: str):
    """Fetch snapshot from yfinance with rate limiting."""
    if yf is None:
        return None
    
    # Check rate limit
    if not _check_rate_limit('yfinance'):
        logger.warning(f"yfinance rate limit hit for {ticker}")
        time.sleep(0.5)  # Brief backoff
    
    _record_request('yfinance')
    yf_t = normalize_ticker_for_yf(ticker)
    tk = yf.Ticker(yf_t)
    try:
        hist = tk.history(period='2d', interval='1d', actions=False)
    except Exception:
        return None
    if hist is None or len(hist) == 0:
        return None
    last_row = hist.iloc[-1]
    prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else last_row['Close']
    # coerce numeric fields and treat zero/negative prices as missing
    def _num(v):
        try:
            if v is None:
                return None
            fv = float(v)
            if fv <= 0 or math.isnan(fv):
                return None
            return fv
        except Exception:
            return None

    out = {
        'last_price': _num(last_row.get('Close')),
        'high': _num(last_row.get('High')),
        'low': _num(last_row.get('Low')),
        'open': _num(last_row.get('Open')),
        'prev_close': _num(prev_close),
        'volume': int(last_row['Volume']) if 'Volume' in last_row and last_row['Volume'] is not None and not math.isnan(last_row['Volume']) else None,
        'timestamp': int(time.time()),
        'source': 'yfinance'
    }
    return out


def _format_output(ticker, out):
    return {
        'ticker': ticker,
        'last_price': out.get('last_price'),
        'prev_close': out.get('prev_close'),
        'open': out.get('open'),
        'high': out.get('high'),
        'low': out.get('low'),
        'volume': out.get('volume'),
        'timestamp': out.get('timestamp'),
        'source': out.get('source'),
        'currency': 'USD'
    }


def get_price_single(ticker: str, use_cache=True, ttl=None, context='live'):
    """Fetch single price with intelligent caching.
    
    Args:
        ticker: Stock ticker symbol
        use_cache: Whether to use cache
        ttl: Cache TTL in seconds (overrides context-based TTL)
        context: Data context ('live', 'daily', 'weekly', 'monthly') for automatic TTL selection
    
    Returns:
        Dict with price data or error info
    """
    # Use context-based TTL if not explicitly provided
    if ttl is None:
        ttl = get_ttl_for_context(context)
    
    key = _cache_key(ticker)
    if use_cache and cache is not None:
        val = cache.get(key)
        if isinstance(val, dict) and '_fetched_at' in val and (time.time() - val.get('_fetched_at', 0) < ttl):
            return val.get('payload')
    # Priority order: Finnhub → Alpaca → yfinance (as requested by user)
    # Try Finnhub first when configured
    if FINNHUB_KEYS:
        try:
            out = finnhub_quote(ticker)
            if out and out.get('last_price') is not None:
                payload = _format_output(ticker, out)
                if cache is not None:
                    cache.set(key, {'payload': payload, '_fetched_at': time.time()}, expire=ttl)
                return payload
        except Exception as e:
            logger.debug(f"Finnhub failed for {ticker}: {e}")
    
    # Try Alpaca as secondary source (if configured)
    try:
        try:
            from config import get_cfg
            alpaca_key = get_cfg('ALPACA_API_KEY') or get_cfg('APCA_API_KEY_ID')
            alpaca_secret = get_cfg('ALPACA_API_SECRET') or get_cfg('APCA_API_SECRET_KEY')
        except Exception:
            alpaca_key = os.getenv('ALPACA_API_KEY') or os.getenv("APCA_API_KEY_ID")
            alpaca_secret = os.getenv('ALPACA_API_SECRET') or os.getenv("APCA_API_SECRET_KEY")
        
        if alpaca_key and alpaca_secret:
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockLatestQuoteRequest
                
                client = StockHistoricalDataClient(alpaca_key, alpaca_secret)
                request = StockLatestQuoteRequest(symbol_or_symbols=ticker)
                quotes = client.get_stock_latest_quote(request)
                
                if ticker in quotes:
                    quote = quotes[ticker]
                    out = {
                        'last_price': float(quote.ask_price) if quote.ask_price else float(quote.bid_price),
                        'high': None,
                        'low': None,
                        'open': None,
                        'prev_close': None,
                        'volume': None,
                        'timestamp': int(time.time()),
                        'source': 'alpaca'
                    }
                    payload = _format_output(ticker, out)
                    if cache is not None:
                        cache.set(key, {'payload': payload, '_fetched_at': time.time()}, expire=ttl)
                    return payload
            except Exception as e:
                logger.debug(f"Alpaca failed for {ticker}: {e}")
    except Exception:
        pass
    
    # Fallback to yfinance as last resort
    last_exc = None
    if yf is not None:
        try:
            for attempt in range(2):
                try:
                    out = yfinance_snapshot(ticker)
                    if out is None or out.get('last_price') is None:
                        # retry once briefly
                        time.sleep(0.15)
                        continue
                    payload = _format_output(ticker, out)
                    if cache is not None:
                        cache.set(key, {'payload': payload, '_fetched_at': time.time()}, expire=ttl)
                    return payload
                except Exception as ye:
                    last_exc = ye
                    time.sleep(0.15)
                    continue
        except Exception:
            pass

    # All sources failed
    if last_exc is not None:
        return {'ticker': ticker, 'last_price': None, 'source': 'all_sources_failed', 'error': str(last_exc)}
    return {'ticker': ticker, 'last_price': None, 'source': 'error', 'error': 'All price sources failed'}


def fetch_prices_batch(tickers, parallelism=8, cache_ttl=None, context='live'):
    """Fetch prices for multiple tickers with intelligent caching.
    
    Args:
        tickers: List of ticker symbols
        parallelism: Number of parallel workers
        cache_ttl: Cache TTL in seconds (overrides context-based TTL)
        context: Data context ('live', 'daily', 'weekly', 'monthly')
    
    Returns:
        Dict mapping ticker to price data
    """
    if cache_ttl is None:
        cache_ttl = get_ttl_for_context(context)
    
    results = {}
    to_fetch = []
    tnow = time.time()
    for t in tickers:
        key = _cache_key(t)
        if cache is not None:
            v = cache.get(key)
            if isinstance(v, dict) and '_fetched_at' in v and (tnow - v.get('_fetched_at', 0) < cache_ttl):
                results[t] = v.get('payload')
                continue
        to_fetch.append(t)

    if not to_fetch:
        return results

    def _worker(sym):
        try:
            payload = get_price_single(sym, use_cache=False, ttl=cache_ttl, context=context)
            return sym, payload
        except Exception as e:
            return sym, {'ticker': sym, 'last_price': None, 'source': 'error', 'error': str(e)}

    with ThreadPoolExecutor(max_workers=parallelism) as ex:
        futures = {ex.submit(_worker, s): s for s in to_fetch}
        for fut in as_completed(futures):
            sym, payload = fut.result()
            results[sym] = payload
            if cache is not None:
                cache.set(_cache_key(sym), {'payload': payload, '_fetched_at': time.time()}, expire=cache_ttl)

    return results


def get_week_open_map(tickers, lookback_days=7, parallelism=6):
    """Return a dict ticker -> first trading day's open price over the lookback period.
    Uses yfinance.history; returns None for tickers when unavailable.
    """
    out = {}
    if yf is None:
        return {t: None for t in tickers}

    def _worker(sym):
        try:
            yf_t = normalize_ticker_for_yf(sym)
            tk = yf.Ticker(yf_t)
            hist = tk.history(period=f"{lookback_days}d", interval='1d', actions=False)
            if hist is None or len(hist) == 0:
                return sym, None
            first = hist.iloc[0]
            return sym, float(first['Open']) if 'Open' in first else (float(first['Close']) if 'Close' in first else None)
        except Exception:
            return sym, None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=parallelism) as ex:
        futures = {ex.submit(_worker, s): s for s in tickers}
        for fut in as_completed(futures):
            sym, val = fut.result()
            out[sym] = val
    return out


def get_price_on_date(ticker, date_obj):
    """Return the open price for ticker on the ISO-week Monday for the given
    date_obj (datetime.date or 'YYYY-MM-DD' string). If the market is closed on
    Monday (holiday/weekend), this will search forward up to 7 calendar days and
    return the first available trading day's Open. If Open is unavailable, it
    falls back to that day's Close. Returns None if no data found or yfinance
    is not available.
    """
    if yf is None:
        return None
    try:
        import datetime as _dt
        # normalize incoming date
        if isinstance(date_obj, str):
            date_obj = _dt.datetime.strptime(date_obj, '%Y-%m-%d').date()
        # compute ISO-week Monday for the given date
        # date_obj.isoweekday(): Monday=1 .. Sunday=7
        wk_mon = date_obj - _dt.timedelta(days=(date_obj.isoweekday() - 1))

        yf_t = normalize_ticker_for_yf(ticker)
        tk = yf.Ticker(yf_t)

        # search forward from Monday up to 7 calendar days to find the first
        # trading day. Use a single history call over a 8-day window for
        # efficiency, then choose the first available row whose date >= wk_mon.
        start = wk_mon
        end = wk_mon + _dt.timedelta(days=8)
        hist = tk.history(start=str(start), end=str(end), interval='1d', actions=False)
        if hist is None or len(hist) == 0:
            return None
        # ensure index is datetime-like and iterate in ascending order
        try:
            # when hist is a DataFrame with DatetimeIndex
            hist = hist.sort_index()
            for idx, row in hist.iterrows():
                row_date = idx.date() if hasattr(idx, 'date') else None
                if row_date is None:
                    continue
                if row_date >= wk_mon:
                    if 'Open' in row and not (_is_nan(row['Open'])):
                        return float(row['Open'])
                    if 'Close' in row and not (_is_nan(row['Close'])):
                        return float(row['Close'])
            return None
        except Exception:
            # fallback to older access patterns
            row = hist.iloc[0]
            if 'Open' in row and not (_is_nan(row['Open'])):
                return float(row['Open'])
            if 'Close' in row and not (_is_nan(row['Close'])):
                return float(row['Close'])
            return None
    except Exception:
        return None


def _is_nan(v):
    try:
        import math
        return v is None or (isinstance(v, float) and math.isnan(v))
    except Exception:
        return v is None


# ============================================================================
# Historical Data Fetching (Alpaca + Finnhub fallback)
# ============================================================================

def fetch_historical_data(tickers, start_date, end_date, use_alpaca=True):
    """
    Fetch historical price data for multiple tickers using Alpaca first, then yfinance fallback.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date (datetime or string 'YYYY-MM-DD')
        end_date: End date (datetime or string 'YYYY-MM-DD')
        use_alpaca: Try Alpaca first (default: True)
    
    Returns:
        pandas DataFrame with adjusted close prices (tickers as columns)
    """
    import pandas as pd
    from datetime import datetime as _dt
    
    # Normalize dates
    if isinstance(start_date, str):
        start_date = _dt.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = _dt.strptime(end_date, '%Y-%m-%d')
    
    prices_df = pd.DataFrame()
    failed_tickers = []
    
    # Try Alpaca first if enabled
    if use_alpaca:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            # Load keys
            keys_env_path = os.path.join(os.path.dirname(__file__), '..', 'keys.env')
            if os.path.exists(keys_env_path):
                with open(keys_env_path) as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key_name, key_value = line.split('=', 1)
                            if key_name.strip() and key_value.strip():
                                os.environ.setdefault(key_name.strip(), key_value.strip())
            
            key = os.getenv("APCA_API_KEY_ID")
            secret = os.getenv("APCA_API_SECRET_KEY")
            
            if key and secret:
                client = StockHistoricalDataClient(key, secret)
                
                for ticker in tickers:
                    try:
                        request = StockBarsRequest(
                            symbol_or_symbols=ticker,
                            timeframe=TimeFrame.Day,
                            start=start_date,
                            end=end_date
                        )
                        bars = client.get_stock_bars(request)
                        
                        if bars and ticker in bars:
                            df = bars[ticker].df
                            if 'close' in df.columns:
                                prices_df[ticker] = df['close']
                                logger.info(f"Fetched {ticker} from Alpaca ({len(df)} days)")
                            else:
                                failed_tickers.append(ticker)
                        else:
                            failed_tickers.append(ticker)
                    except Exception as e:
                        logger.warning(f"Alpaca fetch failed for {ticker}: {e}")
                        failed_tickers.append(ticker)
        except Exception as e:
            logger.warning(f"Alpaca historical data not available: {e}")
            failed_tickers = tickers.copy()
    else:
        failed_tickers = tickers.copy()
    
    # Fallback to yfinance for failed tickers
    if failed_tickers and yf is not None:
        try:
            logger.info(f"Falling back to yfinance for {len(failed_tickers)} tickers")
            yf_tickers = [normalize_ticker_for_yf(t) for t in failed_tickers]
            data = yf.download(yf_tickers, start=start_date, end=end_date, progress=False, auto_adjust=False, threads=False, timeout=10)
            
            if not data.empty:
                # Handle different yfinance output structures
                if 'Adj Close' in data.columns:
                    yf_prices = data['Adj Close']
                elif len(data.columns.names) > 1:  # Multi-level columns
                    yf_prices = data.xs('Adj Close', axis=1, level=0)
                else:
                    yf_prices = data
                
                # Handle single ticker case
                if isinstance(yf_prices, pd.Series):
                    yf_prices = yf_prices.to_frame(name=failed_tickers[0])
                
                # Merge with Alpaca data
                for ticker in failed_tickers:
                    if ticker in yf_prices.columns and not yf_prices[ticker].isna().all():
                        prices_df[ticker] = yf_prices[ticker]
                        logger.info(f"Fetched {ticker} from yfinance (fallback)")
        except Exception as e:
            logger.error(f"yfinance fallback failed: {e}")
    
    # Drop tickers with insufficient data
    if not prices_df.empty:
        min_data_points = 20  # Require at least 20 days of data
        for col in prices_df.columns:
            if prices_df[col].notna().sum() < min_data_points:
                logger.warning(f"Dropping {col}: insufficient data ({prices_df[col].notna().sum()} points)")
                prices_df = prices_df.drop(columns=[col])
    
    return prices_df.dropna()


# ============================================================================
# Utility Functions
# ============================================================================

def get_cache_stats():
    """Get cache statistics."""
    if cache is None:
        return {'enabled': False, 'reason': 'diskcache not installed'}
    try:
        return {
            'enabled': True,
            'size': len(cache),
            'volume': cache.volume(),
            'directory': CACHE_DIR
        }
    except Exception as e:
        return {'enabled': True, 'error': str(e)}


def clear_cache(pattern: str = None):
    """Clear cache entries matching pattern (or all if pattern is None)."""
    if cache is None:
        return
    try:
        if pattern:
            count = 0
            for key in list(cache.iterkeys()):
                if pattern in key:
                    del cache[key]
                    count += 1
            logger.info(f"Cleared {count} cache entries matching '{pattern}'")
        else:
            cache.clear()
            logger.info("Cleared all cache entries")
    except Exception as e:
        logger.error(f"Cache clear error: {e}")


def get_rate_limit_stats():
    """Get current rate limit statistics."""
    stats = {}
    now = time.time()
    for source, state in _rate_limits.items():
        # Count requests in last minute
        recent = [t for t in state.get('requests', []) if now - t < 60]
        stats[source] = {
            'requests_last_minute': len(recent),
            'limit_per_minute': state.get('limit', 0),
            'utilization_pct': (len(recent) / state.get('limit', 1)) * 100
        }
    return stats


def get_finnhub_key_status():
    """Get Finnhub key rotation status."""
    return {
        'keys_loaded': len(FINNHUB_KEYS),
        'current_index': FINNHUB_KEY_INDEX,
        'keys_available': FINNHUB_KEYS != []
    }


# ============================================================================
# Self-Test
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    
    print("Testing enhanced price_fetch module...\n")
    
    # Test 1: Finnhub key rotation
    print("Test 1: Finnhub key rotation")
    key_status = get_finnhub_key_status()
    print(f"  ✓ Keys loaded: {key_status['keys_loaded']}")
    print(f"  ✓ Keys available: {key_status['keys_available']}")
    print()
    
    # Test 2: Single quote with TTL tiers
    print("Test 2: Single quote (AAPL) with live context")
    quote = get_price_single('AAPL', context='live')
    if quote and quote.get('last_price'):
        print(f"  ✓ Price: ${quote['last_price']:.2f}")
        print(f"  ✓ Source: {quote.get('source', 'unknown')}")
    else:
        print(f"  ✗ Failed: {quote.get('error', 'no price')}")
    print()
    
    # Test 3: Batch fetch
    print("Test 3: Batch fetch (AAPL, MSFT, GOOGL)")
    quotes = fetch_prices_batch(['AAPL', 'MSFT', 'GOOGL'], context='daily')
    success = sum(1 for q in quotes.values() if q and q.get('last_price'))
    print(f"  ✓ Fetched {success}/3 quotes")
    for ticker, q in quotes.items():
        if q and q.get('last_price'):
            print(f"    {ticker}: ${q['last_price']:.2f} ({q.get('source', '?')})")
    print()
    
    # Test 4: Cache stats
    print("Test 4: Cache statistics")
    stats = get_cache_stats()
    if stats['enabled']:
        print(f"  ✓ Cache enabled")
        print(f"  ✓ Entries: {stats.get('size', 'N/A')}")
        print(f"  ✓ Directory: {stats.get('directory', 'N/A')}")
    else:
        print(f"  ⚠ Cache disabled: {stats.get('reason', 'unknown')}")
    print()
    
    # Test 5: Rate limit stats
    print("Test 5: Rate limit statistics")
    rate_stats = get_rate_limit_stats()
    for source, data in rate_stats.items():
        print(f"  {source}:")
        print(f"    Requests (last min): {data['requests_last_minute']}/{data['limit_per_minute']}")
        print(f"    Utilization: {data['utilization_pct']:.1f}%")
    print()
    
    # Test 6: TTL tiers
    print("Test 6: TTL tier selection")
    for context in ['live', 'daily', 'weekly', 'monthly']:
        ttl = get_ttl_for_context(context)
        ttl_min = ttl / 60 if ttl < 3600 else ttl / 3600
        unit = 'min' if ttl < 3600 else 'hr'
        print(f"  {context}: {ttl_min:.0f}{unit}")
    print()
    
    print("✅ All tests completed!")
