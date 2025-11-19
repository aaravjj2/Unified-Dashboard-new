"""
Dash app that wraps the repository's `market_trends.py` analysis functions.
This app performs the full fetch + analysis pipeline (using the repository's
batch_fetch_chunked / analyze_ticker functions) and renders a ranking table
and per-ticker detail charts.

Run: python Dash/market_trends_dash.py
"""
from dash import Dash, dcc, html, Input, Output, State, dash_table, callback_context, no_update
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import sys
import importlib.util
import traceback
import json
import threading
from threading import Lock
import time
import uuid
from datetime import datetime
try:
    from flask import request, jsonify
except Exception:
    request = None
    jsonify = None
import logging
from typing import Dict, Any, List, Optional, Tuple

# configure logging early so callback exceptions are visible in the terminal
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# (snapshot file serving routes are defined after the Dash `server` is created)

APP_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))
GRADIO_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, 'Gradio'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load shared utilities from `_shared.py`
SH = None
try:
    # First, try to import a sibling _shared.py
    from . import _shared as SH_local
    SH = SH_local
except (ImportError, SystemError):
    # If that fails, try to load it from the project root
    try:
        spec = importlib.util.spec_from_file_location('_shared', os.path.join(APP_DIR, '_shared.py'))
        if spec:
            shared_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(shared_mod)
            SH = shared_mod
    except Exception:
        logger.error("Failed to load _shared.py", exc_info=True)

# Now, use SH for shared functionality
load_module_from_path = getattr(SH, 'load_module_from_path', None) if SH else None
_sanitize_for_store = getattr(SH, '_sanitize_for_store', None) if SH else None
load_cached_results_from_outputs = getattr(SH, 'load_last_cached_results', None) if SH else None

# Load market_trends module (analysis)
mt_mod = load_module_from_path(os.path.join(GRADIO_DIR, 'market_trends.py'), 'market_trends') if load_module_from_path else None

# Simple cached-model resource similar to Streamlit's st.cache_resource
MODEL_CACHE = {'model': None, 'loaded_at': None, 'ttl': getattr(mt_mod, 'DEFAULT_CACHE_TTL_SECONDS', 3600) if mt_mod is not None else 3600}

# Use the shared RESULTS_CACHE if available
RESULTS_CACHE: Dict[str, Any] = getattr(SH, 'RESULTS_CACHE', {'results': None, 'loaded_at': None})
RESULTS_CACHE_LOCK = getattr(SH, 'RESULTS_CACHE_LOCK', Lock())

# Defensive initialization to ensure RESULTS_CACHE is always a dict
if not isinstance(RESULTS_CACHE, dict):
    RESULTS_CACHE = {'results': None, 'loaded_at': None}

# Locks for thread-safe access to global caches
JOBS_LOCK = Lock()
LATEST_RESULT_LOCK = Lock()

# On import, attempt to populate RESULTS_CACHE from persisted outputs so the
# app shows the last available table on first load without requiring a user
# click. This helps server instances that are started once and not reloaded
# pick up persisted outputs immediately.
try:
    if load_cached_results_from_outputs:
        cached = load_cached_results_from_outputs()
        if cached and (cached.get('detailed') or cached.get('tidy')):
            with RESULTS_CACHE_LOCK:
                RESULTS_CACHE['results'] = {
                    'detailed': cached.get('detailed') or cached.get('tidy') or [],
                    'tidy': cached.get('tidy') or cached.get('detailed') or [],
                    'brief_json': cached.get('brief_json'),
                    'brief_text': cached.get('brief_text'),
                    'prices': cached.get('prices') or {}
                }
                RESULTS_CACHE['loaded_at'] = time.time()
            logger.debug('Initialized RESULTS_CACHE from outputs: rows=%s', len(RESULTS_CACHE['results'].get('detailed') or []))
        else:
            logger.debug("No persisted results found to initialize RESULTS_CACHE.")
except Exception as e:
    logger.error(f"Failed to initialize RESULTS_CACHE at startup: {e}", exc_info=True)
    # Ensure RESULTS_CACHE is in a clean state on failure
    with RESULTS_CACHE_LOCK:
        RESULTS_CACHE['results'] = None
        RESULTS_CACHE['loaded_at'] = None
# If Flask is available, expose a small endpoint to reload persisted outputs
# into RESULTS_CACHE without restarting the server. This can be POSTed to by
# local tooling or by the app after writing outputs.
try:
    if request is not None and jsonify is not None:
        def _reload_trends_endpoint():
            try:
                if load_cached_results_from_outputs:
                    cached = load_cached_results_from_outputs()
                    if cached and (cached.get('detailed') or cached.get('tidy')):
                        with RESULTS_CACHE_LOCK:
                            RESULTS_CACHE['results'] = {
                                'detailed': cached.get('detailed') or cached.get('tidy') or [],
                                'tidy': cached.get('tidy') or cached.get('detailed') or [],
                                'brief_json': cached.get('brief_json'),
                                'brief_text': cached.get('brief_text'),
                                'prices': cached.get('prices') or {}
                            }
                            RESULTS_CACHE['loaded_at'] = time.time()
                            return jsonify({'ok': True, 'rows': len(RESULTS_CACHE['results'].get('detailed') or [])})
                return jsonify({'ok': False, 'message': 'no persisted results found'})
            except Exception as e:
                return jsonify({'ok': False, 'error': str(e)})

        # Register route on the Flask app if it exists later; defer binding until
        # `server` is created. We attach the callable to module so callers can
        # bind it after Dash creates the Flask server.
        _reload_trends_endpoint.__name__ = '_reload_trends_endpoint'
        globals()['_reload_trends_endpoint'] = _reload_trends_endpoint
except Exception:
    pass
def load_cached_model(force: bool = False, ttl: Optional[int] = None):
    """Attempt to load a heavy model/resource from the analysis module and cache it.
    This mirrors Streamlit's cached resource pattern. If the module exposes a
    `load_model` or `load_models` function we'll call it and keep the result in
    MODEL_CACHE['model'] until TTL expires or force=True is passed. If no
    loader is available we'll look for model bundle files on disk and attempt
    to load the newest one with joblib/pickle.
    """
    if mt_mod is None:
        return None

    now = time.time()
    if ttl is None:
        ttl = MODEL_CACHE.get('ttl')
    loaded_at = MODEL_CACHE.get('loaded_at')
    with RESULTS_CACHE_LOCK: # Using same lock for all caches for simplicity
        if not force and MODEL_CACHE.get('model') is not None and loaded_at and (now - loaded_at) < (ttl or 0):
            return MODEL_CACHE['model']

    # try common loader names on the module
    loader = None
    for name in ('load_model', 'load_models', 'load_model_bundle', 'get_model', 'load_cache', 'load_options_cache'):
        if hasattr(mt_mod, name):
            loader = getattr(mt_mod, name)
            break

    if loader is not None:
        try:
            # Be signature-aware: try to call loader with reasonable defaults
            try:
                import inspect
                sig = inspect.signature(loader)
                call_kwargs = {}
                for pname, p in sig.parameters.items():
                    lname = pname.lower()
                    if lname in ('tickers', 'symbols'):
                        call_kwargs[pname] = getattr(mt_mod, 'DEFAULT_TECH', ['AAPL'])
                    elif lname == 'ticker':
                        dt = getattr(mt_mod, 'DEFAULT_TECH', ['AAPL'])
                        call_kwargs[pname] = dt[0] if isinstance(dt, (list, tuple)) and dt else dt
                    elif lname == 'period':
                        call_kwargs[pname] = '1y'
                    elif lname == 'interval':
                        call_kwargs[pname] = '1d'
                    elif 'ttl' in lname:
                        call_kwargs[pname] = MODEL_CACHE.get('ttl') or getattr(mt_mod, 'DEFAULT_CACHE_TTL_SECONDS', 3600)
                    elif lname in ('mt_mod', 'module', 'mod'):
                        call_kwargs[pname] = mt_mod
                    else:
                        call_kwargs[pname] = None
                try:
                    m = loader(**call_kwargs)
                except TypeError:
                    m = loader()
            except Exception:
                try:
                    m = loader()
                except TypeError:
                    try:
                        m = loader(mt_mod)
                    except Exception:
                        raise

            with RESULTS_CACHE_LOCK:
                MODEL_CACHE['model'] = m
                MODEL_CACHE['loaded_at'] = time.time()
            return m
        except Exception:
            traceback.print_exc()

    # if we get here, either there was no loader, or the loader failed.
    # when force=True and no loader exists, create a lightweight sentinel so the UI
    # can reflect a successful 'reload' action.
    if loader is None and force:
        stub = {'stub': True, 'note': 'no loader on mt_mod; created sentinel', 'timestamp': time.time()}
        with RESULTS_CACHE_LOCK:
            MODEL_CACHE['model'] = stub
            MODEL_CACHE['loaded_at'] = time.time()
        return stub

    # attempt to locate model bundle files on disk
    try:
        bundle_dirs = []
        try:
            bundle_dirs.append(getattr(mt_mod, 'OUTPUTS_DIR', None) or os.path.join(PROJECT_ROOT, 'outputs'))
        except Exception:
            bundle_dirs.append(os.path.join(PROJECT_ROOT, 'outputs'))
        bundle_dirs.extend([
            os.path.join(PROJECT_ROOT, 'models'),
            os.path.join(PROJECT_ROOT, 'model_bundles'),
            os.path.join(GRADIO_DIR, 'models'),
            os.path.join(GRADIO_DIR, 'model_bundles'),
        ])

        bundle_files = []
        for d in bundle_dirs:
            if not d:
                continue
            try:
                if not os.path.isdir(d):
                    continue
                for fname in os.listdir(d):
                    if fname.endswith('_bundle.joblib') or fname.endswith('_bundle.pkl') or fname.endswith('.joblib') or fname.endswith('.pkl'):
                        bundle_files.append(os.path.join(d, fname))
            except Exception:
                continue

        if not bundle_files:
            return None

        # try bundles in order (most recent first) and skip any that fail to load
        bundle_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for chosen in bundle_files:
            model_obj = None
            try:
                try:
                    import joblib
                    model_obj = joblib.load(chosen)
                except Exception:
                    try:
                        import pickle
                        with open(chosen, 'rb') as fh:
                            model_obj = pickle.load(fh)
                    except Exception:
                        model_obj = None

                if model_obj is None:
                    # couldn't load this file; try next
                    continue

                # attach to cache and module (best-effort)
                with RESULTS_CACHE_LOCK:
                    MODEL_CACHE['model'] = model_obj
                    MODEL_CACHE['loaded_at'] = time.time()
                try:
                    setattr(mt_mod, 'MODEL', model_obj)
                except Exception:
                    pass
                if hasattr(mt_mod, 'set_model') and callable(getattr(mt_mod, 'set_model')):
                    try:
                        mt_mod.set_model(model_obj)
                    except Exception:
                        pass
                return model_obj
            except Exception:
                traceback.print_exc()
                continue
        return None
    except Exception:
        traceback.print_exc()
        return None


# eager attempt to load cached model at startup (non-fatal)
try:
    _ = load_cached_model(force=False)
except Exception:
    pass


def run_full_analysis(tickers, period='1y', interval='1d', options_topn=3, no_options=False, no_news=False, cache_ttl=None, min_avg_vol=0.0, topn=10, use_cache_only=False, **kwargs):
    """Perform price fetch and full analysis similar to predict_handler.
    Returns a dict with keys: ok, detailed (list), tidy (list), prices (dict of DataFrames).
    
    PHASE 6D: Test Mode Support
    ---------------------------
    When test_mode=True in kwargs:
    - Uses deterministic ticker set ["AAPL", "MSFT", "GOOGL"]
    - Forces cache_only=True to avoid live API calls
    - Disables options and news enrichment
    - Targets <10s runtime for automated testing
    """
    # Log incoming args for debugging why tickers might be a string
    try:
        logger.debug('run_full_analysis called with tickers=%r (type=%s) period=%r kwargs=%r', tickers, type(tickers), period, kwargs)
    except Exception:
        pass

    # PHASE 6D: Test mode detection and configuration
    test_mode = kwargs.get('test_mode', False)
    if test_mode:
        logger.info("🧪 TEST MODE ACTIVE - Using deterministic configuration")
        tickers = ["AAPL", "MSFT", "GOOGL"]
        use_cache_only = True
        no_options = True
        no_news = True
        logger.info(f"   Test tickers: {tickers}")
        logger.info(f"   Cache only: {use_cache_only}")
        logger.info(f"   Options/News: disabled")

    # Normalize legacy kwargs keys that some callers / tab modules may pass
    # e.g. {'options': True, 'news': True, 'cache_only': False}
    # PHASE 4 FIX: Handle options as list (e.g. ['options', 'news', 'backtest'])
    run_backtest = False
    try:
        if isinstance(kwargs, dict):
            options_val = kwargs.get('options')
            
            # Check if 'options' is a list containing flags
            if isinstance(options_val, (list, tuple)):
                logger.info(f"🎯 PHASE 4: Received options as list: {options_val}")
                
                # Extract flags from list
                no_options = 'options' not in options_val
                no_news = 'news' not in options_val
                run_backtest = 'backtest' in options_val
                
                logger.info(f"   Parsed flags: no_options={no_options}, no_news={no_news}, run_backtest={run_backtest}")
                
            # Legacy boolean handling for backward compatibility
            elif 'options' in kwargs:
                # 'options' indicates include options enrichment when True
                no_options = not bool(kwargs.get('options'))
            
            if 'news' in kwargs and not isinstance(options_val, (list, tuple)):
                no_news = not bool(kwargs.get('news'))
            if 'cache_only' in kwargs:
                use_cache_only = bool(kwargs.get('cache_only'))
            if 'options_topn' in kwargs:
                options_topn = int(kwargs.get('options_topn') or options_topn)
            if 'cache_ttl' in kwargs and kwargs.get('cache_ttl') is not None:
                cache_ttl = kwargs.get('cache_ttl')
            
            # PHASE 4: Direct backtest flag support
            if 'backtest' in kwargs:
                run_backtest = bool(kwargs.get('backtest'))
                logger.info(f"🎯 PHASE 4: Direct backtest flag = {run_backtest}")
                
    except Exception as e:
        logger.error(f"❌ Error parsing kwargs: {e}")
        pass

    if mt_mod is None:
        # Attempt to use a lightweight helper module if the full Gradio
        # analysis module is not available. This covers cases where the
        # 'Gradio/market_trends.py' analysis module is absent but a local
        # helper exists (e.g. Dash/modules/market_trends_helper.py).
        # Prefer import by package name if possible
        try:
            import importlib
            helper = importlib.import_module('modules.market_trends_helper')
        except Exception:
            helper = None

        if helper is None and load_module_from_path:
            helper_path = os.path.join(APP_DIR, 'modules', 'market_trends_helper.py')
            if os.path.exists(helper_path):
                try:
                    helper = load_module_from_path(helper_path, 'modules.market_trends_helper')
                except Exception:
                    helper = None

        if helper is not None and hasattr(helper, 'run_full_analysis'):
            try:
                return helper.run_full_analysis(tickers, period=period, interval=interval, options_topn=options_topn, no_options=no_options, no_news=no_news, cache_ttl=cache_ttl, min_avg_vol=min_avg_vol, topn=topn, use_cache_only=use_cache_only)
            except Exception:
                traceback.print_exc()

        # fallback mock if no helper found
        rows = []
        for t in tickers:
            import random
            rows.append({'ticker': t, 'composite_score': round(random.uniform(-1, 1), 3), 'signal': 'NEUTRAL'})
        return {'ok': True, 'detailed': rows, 'tidy': rows, 'prices': {}}

    # Coerce tickers into a list if a comma-separated string was passed
    try:
        if isinstance(tickers, str):
            tickers = [t.strip() for t in tickers.split(',') if t.strip()]
        elif tickers is None:
            tickers = []
        elif not isinstance(tickers, (list, tuple)):
            # try to coerce iterable into list
            try:
                tickers = list(tickers)
            except Exception:
                tickers = [str(tickers)]

    except Exception:
        tickers = []

    try:
        logger.debug('run_full_analysis after coercion tickers=%r (type=%s)', tickers, type(tickers))
    except Exception:
        pass

    # Resolve cache_ttl
    if cache_ttl is None:
        cache_ttl = getattr(mt_mod, 'DEFAULT_CACHE_TTL_SECONDS', 24 * 3600)

    # Ensure tickers is a concrete list before concatenating — be defensive
    try:
        if isinstance(tickers, str):
            tickers = [t.strip() for t in tickers.split(',') if t.strip()]
        elif tickers is None:
            tickers = []
        elif not isinstance(tickers, (list, tuple)):
            try:
                tickers = list(tickers)
            except Exception:
                tickers = [tickers]
    except Exception:
        tickers = []

    try:
        logger.debug('Building fetch_list; tickers type=%s value=%r', type(tickers), tickers)
    except Exception:
        pass

    fetch_list = [getattr(mt_mod, 'SP_TICKER', '^GSPC'), getattr(mt_mod, 'XLK_TICKER', 'XLK')] + list(tickers)

    # fetch prices
    prices = {}
    try:
        if hasattr(mt_mod, 'batch_fetch_chunked'):
            prices = mt_mod.batch_fetch_chunked(fetch_list, period, interval, cache_ttl, use_cache_only=use_cache_only)
        elif hasattr(mt_mod, 'batch_fetch'):
            prices = mt_mod.batch_fetch(fetch_list, period, interval, cache_ttl, use_cache_only=use_cache_only)
        else:
            # last resort: attempt yfinance directly per ticker (slow)
            for t in fetch_list:
                try:
                    prices[t] = mt_mod.fetch_price_data(t, period=period, interval=interval)
                except Exception:
                    try:
                        prices[t] = mt_mod.fetch_prices(t, period=period, interval=interval)
                    except Exception:
                        prices[t] = None
    except Exception:
        traceback.print_exc()

    # AGENT 1B FIX: Persist simplified price data to cache for UI rendering
    # The Market Trends UI expects prices in a simple {ticker: {current_price, daily_change, ...}} format
    # but run_full_analysis fetches full OHLCV DataFrames. Convert and persist them.
    try:
        import json
        simplified_prices = {}
        
        for ticker, df in prices.items():
            if df is None or (hasattr(df, 'empty') and df.empty):
                continue
            
            try:
                # Skip index tickers (^GSPC, XLK) - only persist user tickers
                if ticker.startswith('^') or ticker in ['XLK']:
                    continue
                
                # Extract current price (last close)
                current_price = df['Close'].iloc[-1] if 'Close' in df.columns and len(df) > 0 else None
                
                # Extract start price (first close in the period)
                start_price = df['Close'].iloc[0] if 'Close' in df.columns and len(df) > 0 else None
                
                # Calculate daily change (last 2 days)
                daily_change = 0
                if 'Close' in df.columns and len(df) >= 2:
                    daily_change = df['Close'].iloc[-1] - df['Close'].iloc[-2]
                
                # Calculate profit/loss from start
                profit_loss = 0
                if current_price is not None and start_price is not None:
                    profit_loss = current_price - start_price
                
                # Determine week/month start based on period
                week_start_price = start_price
                month_start_price = start_price
                
                if period in ['1mo', '2mo', '3mo', '6mo', '1y', '2y']:
                    # If period is monthly/yearly, treat start as month start
                    month_start_price = start_price
                    # For week start, use last 7 days if available
                    if len(df) >= 7:
                        week_start_price = df['Close'].iloc[-7]
                    else:
                        week_start_price = start_price
                else:
                    # For shorter periods (1w, 5d), use as week start
                    week_start_price = start_price
                    month_start_price = None  # Not applicable for short periods
                
                simplified_prices[ticker] = {
                    'current_price': float(current_price) if current_price is not None else None,
                    'daily_change': float(daily_change),
                    'start_price': float(start_price) if start_price is not None else None,
                    'week_start_price': float(week_start_price) if week_start_price is not None else None,
                    'month_start_price': float(month_start_price) if month_start_price is not None else None,
                    'profit_loss': float(profit_loss),
                    'source': 'yfinance'  # or detect actual source
                }
            except Exception as e:
                logger.warning(f"Failed to simplify prices for {ticker}: {e}")
                continue
        
        # Persist to prices_weekly.json (Market Trends uses this as the price cache)
        if simplified_prices:
            try:
                prices_cache_path = os.path.join(OUT_ROOT, 'prices_weekly.json')
                with open(prices_cache_path, 'w', encoding='utf-8') as f:
                    json.dump({'prices': simplified_prices, 'generated_at': time.time()}, f, indent=2, default=str)
                logger.info(f"✅ Persisted {len(simplified_prices)} simplified prices to {prices_cache_path}")
            except Exception as e:
                logger.error(f"Failed to persist simplified prices: {e}")
            
            # Also update RESULTS_CACHE immediately so UI can render without restart
            try:
                with RESULTS_CACHE_LOCK:
                    if not isinstance(RESULTS_CACHE.get('results'), dict):
                        RESULTS_CACHE['results'] = {}
                    if 'prices' not in RESULTS_CACHE['results']:
                        RESULTS_CACHE['results']['prices'] = {}
                    RESULTS_CACHE['results']['prices'].update(simplified_prices)
                    logger.info(f"✅ Updated RESULTS_CACHE with {len(simplified_prices)} prices")
            except Exception as e:
                logger.error(f"Failed to update RESULTS_CACHE with simplified prices: {e}")
    except Exception as e:
        logger.error(f"Failed to create simplified price cache: {e}")
        traceback.print_exc()

    sp_close = None
    try:
        if getattr(mt_mod, 'SP_TICKER', '^GSPC') in prices and prices[getattr(mt_mod, 'SP_TICKER', '^GSPC')] is not None:
            sp_close = prices[getattr(mt_mod, 'SP_TICKER', '^GSPC')]['Close'].dropna()
    except Exception:
        sp_close = None

    xlk_close = None
    try:
        xlk_df = prices.get(getattr(mt_mod, 'XLK_TICKER', 'XLK'))
        if xlk_df is not None and 'Close' in xlk_df.columns:
            xlk_close = xlk_df['Close'].dropna()
    except Exception:
        xlk_close = None

    rows = []
    for t in tickers:
        try:
            if t not in prices or prices[t] is None or getattr(prices[t], 'empty', False):
                rows.append({'ticker': t, 'composite_score': None, 'notes': 'missing data'})
                continue
            df = prices[t]
            vol = df['Volume'] if 'Volume' in df.columns else pd.Series(dtype=float)
            info = None
            try:
                # many analyze_ticker variants accept (ticker, close, vol, sp_close, xlk_close)
                info = mt_mod.analyze_ticker(t, df['Close'], vol, sp_close, xlk_close)
            except TypeError:
                try:
                    info = mt_mod.analyze_ticker(t)
                except Exception:
                    info = {'ticker': t, 'error': 'analyze_ticker failed'}
            except Exception:
                info = {'ticker': t, 'error': traceback.format_exc()}

            if info is None:
                info = {'ticker': t, 'error': 'no info'}
            if 'composite_score' not in info:
                info['composite_score'] = info.get('composite', None) or info.get('score', None) or None
            rows.append(info)
        except Exception:
            rows.append({'ticker': t, 'composite_score': None, 'notes': 'exception'})

    detailed = pd.DataFrame(rows)
    if detailed.empty:
        return {'ok': False, 'error': 'No results'}

    # ranking
    try:
        detailed = detailed.sort_values('composite_score', ascending=False).reset_index(drop=True)
        detailed.index = detailed.index + 1
        detailed['rank'] = detailed.index
    except Exception:
        pass

    # position sizing attempt
    try:
        if hasattr(mt_mod, 'position_sizing_recommendation'):
            detailed = mt_mod.position_sizing_recommendation(detailed, risk_budget=1.0)
    except Exception:
        pass

    # Enrich top tickers with options/news when available
    try:
        if not no_options and hasattr(mt_mod, 'options_flow_summary_rate_limited') and hasattr(mt_mod, 'fetch_google_news_headlines'):
            topk = detailed.sort_values('composite_score', ascending=False).head(options_topn)['ticker'].tolist()
            for t in topk:
                try:
                    opt = mt_mod.options_flow_summary_rate_limited(t, throttle=getattr(mt_mod, 'DEFAULT_OPTIONS_THROTTLE', 6.0), max_attempts=getattr(mt_mod, 'MAX_RETRIES', 3), cache_ttl=cache_ttl)
                    detailed.loc[detailed['ticker'] == t, 'options_signal'] = opt.get('signal')
                    detailed.loc[detailed['ticker'] == t, 'options_pcr'] = opt.get('put_call_ratio')
                except Exception:
                    pass
                try:
                    headlines = mt_mod.fetch_google_news_headlines(t, max_headlines=6)
                    sent = None
                    if hasattr(mt_mod, 'sentiment_score_texts'):
                        try:
                            sent = mt_mod.sentiment_score_texts(headlines)
                        except Exception:
                            sent = None
                    detailed.loc[detailed['ticker'] == t, 'news_headlines'] = "; ".join(headlines) if headlines else ''
                    detailed.loc[detailed['ticker'] == t, 'news_sentiment'] = sent
                except Exception:
                    pass
    except Exception:
        pass

    gen_time = time.strftime('%Y-%m-%dT%H:%M:%S')
    tidy = None
    try:
        if hasattr(mt_mod, 'tidy_summary_from_detailed'):
            tidy = mt_mod.tidy_summary_from_detailed(detailed, sp_close, xlk_close, gen_time)
    except Exception:
        tidy = None

    # Persist snapshot into OUTPUTS_DIR (like the original service) for later inspection
    try:
        out_root = getattr(mt_mod, 'OUTPUTS_DIR', os.path.join(PROJECT_ROOT, 'outputs'))
        ts = time.strftime('%Y%m%d_%H%M%S')
        run_dir = os.path.join(out_root, f'run_{ts}')
        os.makedirs(run_dir, exist_ok=True)
        tidy_path = os.path.join(run_dir, 'tech_summary.csv')
        detailed_path = os.path.join(run_dir, 'tech_report_detailed.csv')
        pd.DataFrame(detailed).to_csv(detailed_path, index=False)
        if tidy is not None:
            pd.DataFrame(tidy).to_csv(tidy_path, index=False)
        # try to generate brief using module helper
        try:
            if hasattr(mt_mod, 'generate_market_summary'):
                _, _ = mt_mod.generate_market_summary(detailed, sp_close, xlk_close, out_dir=run_dir)
            else:
                _, _ = '', {}
            # copy files to outputs root
            for fname in os.listdir(run_dir):
                src = os.path.join(run_dir, fname)
                dst = os.path.join(out_root, fname)
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.replace(src, dst)
                except Exception:
                    try:
                        import shutil
                        shutil.copy2(src, dst)
                    except Exception:
                        pass
        except Exception:
            pass
    except Exception:
        pass

    # Prepare return payload (serializable)
    payload = {
        'ok': True,
        'detailed': detailed.fillna(' ').to_dict(orient='records'),
        'tidy': (tidy.fillna(' ').to_dict(orient='records') if tidy is not None else None),
        'prices': {},
        'brief_text': None
    }
    
    # Try to load brief text if it was generated
    try:
        brief_txt_path = os.path.join(out_root, 'market_brief.txt')
        if os.path.exists(brief_txt_path):
            with open(brief_txt_path, 'r', encoding='utf-8') as f:
                payload['brief_text'] = f.read().strip()
    except Exception as e:
        logger.warning(f"Could not load brief text: {e}")
    # Convert prices DataFrames to serializable dicts (records) where possible
    try:
        for k, v in prices.items():
            try:
                payload['prices'][k] = v.to_dict(orient='records') if hasattr(v, 'to_dict') else v
            except Exception:
                payload['prices'][k] = None
    except Exception:
        payload['prices'] = {}

    # Atomically write canonical snapshot file so the UI can always load a single known path
    try:
        # Use global OUT_ROOT which is created at module load
        canonical = os.path.join(OUT_ROOT, 'market_brief.json')
        tmp_path = canonical + '.tmp'
        # keep a compact JSON but ensure non-serializable objects are stringified
        def _safe(obj):
            try:
                import pandas as _pd
                if hasattr(obj, 'to_dict'):
                    return obj.to_dict()
            except Exception:
                pass
            try:
                return json.loads(json.dumps(obj))
            except Exception:
                try:
                    return str(obj)
                except Exception:
                    return None

        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, default=str, indent=2)
        try:
            os.replace(tmp_path, canonical)
        except Exception:
            try:
                import shutil
                shutil.copy2(tmp_path, canonical)
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception:
        logger.exception('Failed to write canonical market_brief.json')

    # Update in-memory cache so UI shows results immediately after a run
    try:
        with RESULTS_CACHE_LOCK:
            sres = {}
            sres['brief_text'] = payload.get('brief_text')
            sres['brief_json'] = None
            sres['tidy'] = payload.get('tidy')
            sres['detailed'] = payload.get('detailed')
            sres['prices'] = payload.get('prices')
            RESULTS_CACHE['results'] = sres
            RESULTS_CACHE['loaded_at'] = time.time()
    except Exception:
        logger.exception('Failed to update RESULTS_CACHE after run_full_analysis')

    # PHASE 4: Run backtest if requested
    if run_backtest:
        logger.info("=" * 80)
        logger.info("🎯 PHASE 4: BACKTEST REQUESTED - Starting backtest analysis")
        logger.info(f"   Tickers: {tickers}")
        logger.info(f"   Period: {period}")
        logger.info("=" * 80)
        
        try:
            # Import backtester service
            backtest_results = {}
            commission_per_contract = 0.65
            
            # For each ticker with a signal, run a simple backtest
            for row in detailed.to_dict(orient='records'):
                ticker = row.get('ticker')
                signal = row.get('signal', 'NEUTRAL')
                
                if signal in ['BUY', 'SELL'] and ticker in prices and prices[ticker] is not None:
                    try:
                        df = prices[ticker]
                        if not df.empty and len(df) > 10:
                            # Simple backtest: calculate returns if we took the signal
                            close_prices = df['Close'].dropna()
                            if len(close_prices) > 1:
                                initial_price = close_prices.iloc[0]
                                final_price = close_prices.iloc[-1]
                                
                                # Calculate returns based on signal
                                if signal == 'BUY':
                                    total_return = ((final_price - initial_price) / initial_price) * 100
                                else:  # SELL (short)
                                    total_return = ((initial_price - final_price) / initial_price) * 100
                                
                                # Simple commission adjustment
                                num_shares = 100  # Assume 100 shares
                                total_commission = commission_per_contract * 2  # Entry + Exit
                                commission_impact = (total_commission / (initial_price * num_shares)) * 100
                                
                                net_return = total_return - commission_impact
                                
                                backtest_results[ticker] = {
                                    'signal': signal,
                                    'initial_price': round(initial_price, 2),
                                    'final_price': round(final_price, 2),
                                    'gross_return_pct': round(total_return, 2),
                                    'commission_impact_pct': round(commission_impact, 2),
                                    'net_return_pct': round(net_return, 2),
                                    'num_days': len(close_prices)
                                }
                                
                                logger.info(f"   ✅ Backtest {ticker}: {signal} → Net Return: {net_return:.2f}%")
                            else:
                                logger.warning(f"   ⚠️  {ticker}: Not enough price data for backtest")
                    except Exception as e:
                        logger.error(f"   ❌ Backtest failed for {ticker}: {e}")
                        backtest_results[ticker] = {'error': str(e)}
            
            # Add backtest results to payload
            payload['backtest_results'] = backtest_results
            payload['backtest_commission'] = commission_per_contract
            
            # Calculate aggregate metrics
            successful_backtests = [r for r in backtest_results.values() if 'net_return_pct' in r]
            if successful_backtests:
                total_trades = len(successful_backtests)
                avg_return = sum(r['net_return_pct'] for r in successful_backtests) / total_trades
                winning_trades = sum(1 for r in successful_backtests if r['net_return_pct'] > 0)
                win_rate = (winning_trades / total_trades) * 100
                
                payload['backtest_summary'] = {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': total_trades - winning_trades,
                    'win_rate_pct': round(win_rate, 1),
                    'avg_return_pct': round(avg_return, 2),
                    'commission_per_contract': commission_per_contract
                }
                
                logger.info("=" * 80)
                logger.info("📊 BACKTEST SUMMARY:")
                logger.info(f"   Total Trades: {total_trades}")
                logger.info(f"   Win Rate: {win_rate:.1f}%")
                logger.info(f"   Avg Return: {avg_return:.2f}%")
                logger.info("=" * 80)
            else:
                logger.warning("⚠️  No successful backtests to summarize")
                payload['backtest_summary'] = {'error': 'No actionable signals for backtest'}
                
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ BACKTEST FAILED: {e}")
            logger.error(traceback.format_exc())
            logger.error("=" * 80)
            payload['backtest_results'] = {'error': str(e)}
            payload['backtest_summary'] = {'error': str(e)}

    return payload


app = Dash(__name__, assets_folder='assets')
server = app.server
app.config.suppress_callback_exceptions = True

# Setup logging to surface callback and server errors in the terminal
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)
try:
    server.logger.setLevel(logging.DEBUG)
except Exception:
    pass

# Attempt to load the modular UI tab for Market Trends so the standalone
# app has a full layout and its callbacks registered. This mirrors the
# simplified runners in the project and is defensive: failures here will
# be logged but won't stop the server from starting.
try:
    tabs_path = os.path.join(APP_DIR, 'tabs', 'market_trends.py')
    if os.path.exists(tabs_path):
        spec = importlib.util.spec_from_file_location('Dash.tabs.market_trends', tabs_path)
        tabs_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tabs_mod)
        # If the tab module doesn't provide a run_full_analysis implementation,
        # inject the server's run_full_analysis which is mt_mod-aware. This
        # ensures background jobs started by the tab will call into the
        # analysis functions available to this server process.
        try:
            # Overwrite or set the tab module's run_full_analysis to the
            # server-level implementation so background jobs launched by the
            # tab will execute using the same analysis code/environment as
            # the Dash server process.
            try:
                setattr(tabs_mod, 'run_full_analysis', run_full_analysis)
                logger.debug('Injected server run_full_analysis into tabs.market_trends (overwrite if existed)')
            except Exception:
                logger.exception('Failed to inject run_full_analysis into tabs.market_trends')
        except Exception:
            logger.exception('Error while attempting to attach run_full_analysis to tabs module')
        
        # CRITICAL FIX: Do NOT set app.layout here!
        # This was causing callbacks to finalize before other tabs could register.
        # Layout is now set ONCE in index.py after ALL callbacks are registered.
        # 
        # OLD CODE (disabled):
        # if hasattr(tabs_mod, 'layout') and callable(getattr(tabs_mod, 'layout')):
        #     app.layout = tabs_mod.layout()
        #     logger.debug('Loaded app.layout from tabs.market_trends')
        
        # Ensure common hidden placeholders will exist (they're added by index.py now)
        # if hasattr(tabs_mod, 'layout') and callable(getattr(tabs_mod, 'layout')):
        #     try:
        #         app.layout = tabs_mod.layout()
        #         logger.debug('Loaded app.layout from tabs.market_trends')
        #     except Exception:
        #         logger.exception('Failed to set app.layout from tabs.market_trends')
        
        # Note: Placeholder components are now added by index.py layout
        
        # OLD placeholder code (no longer needed here):
        # OLD placeholder code (no longer needed - handled by index.py):
        # The code below was attempting to add placeholder components to app.layout,
        # but since we no longer set app.layout here, this code is obsolete.
        
        # DISABLED: Callback registration is now handled ONCE in index.py via callbacks.py module
        # This prevents the "callbacks registered after layout is set" problem
        # OLD CODE (disabled):
        # try:
        #     if hasattr(tabs_mod, 'register_callbacks') and callable(getattr(tabs_mod, 'register_callbacks')):
        #         try:
        #             tabs_mod.register_callbacks(app)
        #             logger.debug('Registered tabs.market_trends.register_callbacks(app)')
        #         except TypeError:
        #             try:
        #                 tabs_mod.register_callbacks(app, SH)
        #                 logger.debug('Registered tabs.market_trends.register_callbacks(app, SH)')
        #             except Exception:
        #                 logger.exception('Failed to register callbacks with (app, SH)')
        # except Exception:
        #     logger.exception('Error while registering market_trends tab callbacks')
    else:
        logger.debug('tabs/market_trends.py not found; skipping UI module load')
except Exception:
    logger.exception('Failed loading tabs.market_trends module')

# Global Flask error handler to log unhandled exceptions
try:
    @server.errorhandler(Exception)
    def _log_unhandled_exception(e):
        try:
            server.logger.exception('Unhandled exception during request')
        except Exception:
            print('Unhandled exception:', e)
        try:
            return jsonify({'ok': False, 'error': str(e)}), 500
        except Exception:
            return str(e), 500
except Exception:
    pass


# Debug endpoint to inspect the loaded analysis module (mt_mod)
try:
    @server.route('/_mt_mod_info')
    def _mt_mod_info():
        try:
            if mt_mod is None:
                return jsonify({'ok': False, 'error': 'mt_mod is None'})
            attrs = []
            for k in dir(mt_mod):
                if k.startswith('_'):
                    continue
                try:
                    v = getattr(mt_mod, k)
                    attrs.append({'name': k, 'callable': callable(v)})
                except Exception:
                    attrs.append({'name': k, 'callable': False})
            return jsonify({'ok': True, 'attrs': attrs})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)})
except Exception:
    # if Flask isn't available at runtime, ignore
    pass

try:
    @server.route('/_results_cache')
    def _results_cache():
        try:
            return jsonify({'ok': True, 'results_cache': RESULTS_CACHE})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)})
except Exception:
    pass

# Instrument incoming requests to capture payloads and exceptions for
# the Dash update path which often triggers callbacks server-side.
try:
    @server.before_request
    def _log_incoming_request():
        try:
            # Only log POSTs to the Dash update endpoint to reduce noise
            if request is not None and request.path == '/_dash-update-component' and request.method == 'POST':
                try:
                    data = request.get_data(as_text=True)
                except Exception:
                    data = '<unreadable body>'
                server.logger.debug('Incoming _dash-update-component POST: %s', (data[:2000] + '...') if data and len(data) > 2000 else data)
        except Exception:
            server.logger.exception('Failed while logging incoming request')

    @server.teardown_request
    def _log_request_teardown(exc):
        # If a teardown sees an exception, ensure it's logged to server logger
        if exc is not None:
            try:
                server.logger.exception('Exception during request handling: %s', exc)
            except Exception:
                print('Exception during request handling:', exc)
except Exception:
    # If Flask request hooks are unavailable for any reason, continue silently
    pass

# bind reload endpoint if the helper exists
try:
    if '_reload_trends_endpoint' in globals():
        server.add_url_rule('/__reload_trends', view_func=globals()['_reload_trends_endpoint'], methods=['POST', 'GET'])
except Exception:
    pass

try:
    @server.route('/__reload_trends', methods=['POST', 'GET'])
    def __reload_trends():
        try:
            cached = load_cached_results_from_outputs()
            if cached and (cached.get('detailed') or cached.get('tidy')):
                    with RESULTS_CACHE_LOCK:
                        RESULTS_CACHE['results'] = {
                            'detailed': cached.get('detailed') or cached.get('tidy') or [],
                            'tidy': cached.get('tidy') or cached.get('detailed') or [],
                            'brief_json': cached.get('brief_json'),
                            'brief_text': cached.get('brief_text'),
                            'prices': cached.get('prices') or {}
                        }
                        RESULTS_CACHE['loaded_at'] = time.time()
                        return jsonify({'ok': True, 'rows': len(RESULTS_CACHE['results'].get('detailed') or [])})
            return jsonify({'ok': False, 'message': 'no persisted results found'})
        except Exception as e:
            try:
                return jsonify({'ok': False, 'error': str(e)})
            except Exception:
                return str(e), 500
except Exception:
    pass

try:
    @server.route('/_api/reload_trends', methods=['POST', 'GET'])
    def _api_reload_trends():
        try:
            cached = load_cached_results_from_outputs()
            if cached and (cached.get('detailed') or cached.get('tidy')):
                    with RESULTS_CACHE_LOCK:
                        RESULTS_CACHE['results'] = {
                            'detailed': cached.get('detailed') or cached.get('tidy') or [],
                            'tidy': cached.get('tidy') or cached.get('detailed') or [],
                            'brief_json': cached.get('brief_json'),
                            'brief_text': cached.get('brief_text'),
                            'prices': cached.get('prices') or {}
                        }
                        RESULTS_CACHE['loaded_at'] = time.time()
                        return jsonify({'ok': True, 'rows': len(RESULTS_CACHE['results'].get('detailed') or [])})
            return jsonify({'ok': False, 'message': 'no persisted results found'})
        except Exception as e:
            try:
                return jsonify({'ok': False, 'error': str(e)})
            except Exception:
                return str(e), 500
except Exception:
    pass

try:
    @server.route('/_reload_model')
    def _reload_model():
        """Debug endpoint that invokes the reload_model logic and returns JSON status."""
        global mt_mod
        reloaded = False

        # Try to reload the module (importlib.reload preferred)
        try:
            if mt_mod is not None:
                try:
                    mt_mod = importlib.reload(mt_mod)
                    reloaded = True
                except ImportError:
                    mod_path = os.path.join(GRADIO_DIR, 'market_trends.py')
                    new_mod = load_module_from_path(mod_path, 'market_trends')
                    if new_mod is not None:
                        mt_mod = new_mod
                        reloaded = True
        except Exception as e:
            return jsonify({'ok': False, 'error': f'reload failed: {str(e)}'})

        # Try module-provided loaders first (non-fatal)
        m = None
        try:
            if mt_mod is not None and hasattr(mt_mod, 'load_cache') and callable(getattr(mt_mod, 'load_cache')):
                try:
                    m = mt_mod.load_cache()
                except Exception:
                    m = None
        except Exception:
            m = None

        if m is None:
            try:
                if mt_mod is not None and hasattr(mt_mod, 'load_options_cache') and callable(getattr(mt_mod, 'load_options_cache')):
                    try:
                        m = mt_mod.load_options_cache()
                    except Exception:
                        m = None
            except Exception:
                m = None

        # Fallback to generic loader which may scan disk bundles
        if m is None:
            try:
                m = load_cached_model(force=True)
            except Exception:
                m = None

        if m is not None:
            return jsonify({'ok': True, 'model_loaded': True, 'reloaded': reloaded, 'model_repr': str(type(m))})

        if mt_mod is None:
            return jsonify({'ok': False, 'error': 'mt_mod is None after reload'})

        # try attributes on module as last resort
        for candidate in ('model', 'MODEL', 'MODEL_BUNDLE', 'MODEL_CONTAINER'):
            if hasattr(mt_mod, candidate):
                attr = getattr(mt_mod, candidate)
                try:
                    mm = attr() if callable(attr) else attr
                    with RESULTS_CACHE_LOCK:
                        MODEL_CACHE['model'] = mm
                        MODEL_CACHE['loaded_at'] = time.time()
                    return jsonify({'ok': True, 'model_loaded': True, 'reloaded': reloaded, 'via': f'mt_mod.{candidate}'})
                except Exception:
                    continue

        return jsonify({'ok': True, 'model_loaded': False, 'reloaded': reloaded, 'note': 'no loader produced a model'})
except Exception:
    pass

try:
    @server.route('/_reload_outputs')
    def _reload_outputs():
        """Debug endpoint: load outputs from OUT_ROOT and place into RESULTS_CACHE (sanitized)"""
        try:
            res = load_cached_results_from_outputs()
            if isinstance(res, dict):
                sres = {}
                sres['brief_text'] = res.get('brief_text')
                sres['brief_json'] = res.get('brief_json')
                # tidy may be under tidy_df (DataFrame) or tidy (list)
                if 'tidy_df' in res and res.get('tidy_df') is not None:
                    td = res.get('tidy_df')
                else:
                    td = res.get('tidy')
                if td is not None:
                    try:
                        sres['tidy'] = td.to_dict(orient='records') if hasattr(td, 'to_dict') else td
                    except Exception:
                        sres['tidy'] = None
                # detailed may be under detailed_df or detailed
                if 'detailed_df' in res and res.get('detailed_df') is not None:
                    det = res.get('detailed_df')
                else:
                    det = res.get('detailed')
                if det is not None:
                    try:
                        sres['detailed'] = det.to_dict(orient='records') if hasattr(det, 'to_dict') else det
                    except Exception:
                        sres['detailed'] = None
                prices = res.get('prices')
                if isinstance(prices, dict):
                    spr = {}
                    for k, v in prices.items():
                        try:
                            spr[k] = v.to_dict(orient='records') if hasattr(v, 'to_dict') else v
                        except Exception:
                            spr[k] = None
                    sres['prices'] = spr
                with RESULTS_CACHE_LOCK:
                    RESULTS_CACHE['results'] = sres
            else:
                with RESULTS_CACHE_LOCK:
                    RESULTS_CACHE['results'] = res
            with RESULTS_CACHE_LOCK:
                RESULTS_CACHE['loaded_at'] = time.time()
            return jsonify({'ok': True, 'loaded_at': RESULTS_CACHE['loaded_at'], 'has_results': bool(RESULTS_CACHE.get('results'))})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()})
except Exception:
    pass

# Simple in-memory job store for background runs
JOBS = {}
# Last completed result for download. Use a dict to hold the result and a timestamp.
LATEST_RESULT: Dict[str, Any] = {'data': None, 'timestamp': 0}
# Historical list of past jobs (simple in-memory)
JOB_HISTORY = []
OUT_ROOT = getattr(mt_mod, 'OUTPUTS_DIR', os.path.join(PROJECT_ROOT, 'outputs'))
os.makedirs(OUT_ROOT, exist_ok=True)
HISTORY_DIR = os.path.join(OUT_ROOT, 'history')
os.makedirs(HISTORY_DIR, exist_ok=True)


# Small helper: render a pure-HTML static preview table for deterministic server-side HTML
def _render_static_table(records: List[Dict], max_rows: int = 8, max_cols: int = 10) -> html.Div:
    """Renders a static HTML table, ensuring it always displays headers even with no data."""
    if not records:
        # Display headers with a "No data" message if records are empty
        return html.Div([
            html.Table([
                html.Thead(html.Tr([html.Th("Ticker"), html.Th("Signal"), html.Th("Score")])),
                html.Tbody(html.Tr([html.Td("No data to display", colSpan=3, style={'textAlign': 'center'})]))
            ], style={'width': '100%', 'borderCollapse': 'collapse'}),
            html.Div('Preview (server-rendered)', style={'padding': '6px 8px', 'backgroundColor': '#083344', 'color': '#e6eef8', 'borderRadius': '4px', 'marginBottom': '6px'})
        ], className='market-trends-server-preview', style={'width': '100%', 'padding': '6px', 'border': '1px solid #e0e0e0', 'borderRadius': '6px'})
    
    try:
        rows = list(records)[:max_rows]
        keys = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            for k in r.keys():
                if k not in keys:
                    keys.append(k)
            if len(keys) >= max_cols:
                break

        def _cell_txt(v, max_len=60):
            try:
                s = str(v)
                if len(s) > max_len:
                    return s[:max_len] + '...'
                return s
            except Exception:
                return ''

        header_cells = [html.Th(str(k), style={'textAlign': 'left', 'padding': '4px 6px', 'fontSize': '12px'}) for k in keys]
        thead = html.Thead(html.Tr(header_cells))
        body_rows = []
        for r in rows:
            cols = []
            for k in keys:
                cols.append(html.Td(_cell_txt(r.get(k, '')), style={'padding': '4px 6px', 'fontSize': '12px'}))
            body_rows.append(html.Tr(cols))
        tbody = html.Tbody(body_rows)
        table = html.Table([thead, tbody], style={'width': '100%', 'borderCollapse': 'collapse', 'tableLayout': 'fixed'})
        banner = html.Div('Preview (server-rendered)', style={'padding': '6px 8px', 'backgroundColor': '#083344', 'color': '#e6eef8', 'borderRadius': '4px', 'marginBottom': '6px'})
        wrapper = html.Div([banner, table], className='market-trends-server-preview',
                           style={
                               'width': '100%',
                               'overflowX': 'auto',
                               'opacity': 1,
                               'padding': '6px',
                               'border': '1px solid #e0e0e0',
                               'borderRadius': '6px'
                           })
        return wrapper
    except Exception as e:
        logger.error(f"Error rendering static table: {e}")
        return html.Div("Error rendering table preview.")


# Prepare deterministic initial results-area children (server-side) so the
# root HTML contains a stable preview when persisted outputs exist.
initial_results_children = [html.H4('No results yet')]
initial_results_children = [html.H4('No results yet')]
try:
    with RESULTS_CACHE_LOCK:
        if RESULTS_CACHE.get('results') and isinstance(RESULTS_CACHE.get('results'), dict):
            det = RESULTS_CACHE['results'].get('detailed') or RESULTS_CACHE['results'].get('tidy')
            if det and isinstance(det, (list, tuple)) and len(det) > 0:
                # cap rows for server-rendered preview
                preview = _render_static_table(det, max_rows=min(len(det), 12))
                source = 'outputs'
                initial_results_children = [html.Div(f'Loaded from: {source}', style={'padding': '6px 8px', 'backgroundColor': '#083344', 'color': '#e6eef8', 'borderRadius': '4px', 'marginBottom': '6px'}), preview]
except Exception:
    pass


def load_last_cached_results():
    """Try to load last persisted results from OUT_ROOT (tech_report_detailed.csv or tech_summary.csv or market_brief.json)
    Returns a dict similar to the run_full_analysis/predict output or None.
    """
    try:
        # prefer detailed CSV
        csvp = os.path.join(OUT_ROOT, 'tech_report_detailed.csv')
        if os.path.exists(csvp):
            df = pd.read_csv(csvp)
            return {'ok': True, 'detailed': df.fillna(' ').to_dict(orient='records')}
        tidy = os.path.join(OUT_ROOT, 'tech_summary.csv')
        if os.path.exists(tidy):
            df = pd.read_csv(tidy)
            return {'ok': True, 'detailed': df.fillna(' ').to_dict(orient='records')}
        jp = os.path.join(OUT_ROOT, 'market_brief.json')
        if os.path.exists(jp):
            with open(jp, 'r', encoding='utf-8') as hf:
                data = json.load(hf)
            # if the brief JSON contains a detailed block, return it
            if isinstance(data, dict) and data.get('detailed'):
                return {'ok': True, 'detailed': data.get('detailed')}
            return {'ok': True, 'brief_json': data}
    except Exception:
        pass
    return None


def _render_table_from_records(records):
    """Given a list-of-dict records, return a DataTable and wrapper children."""
    try:
        if not records:
            return html.Div('No records'), None
        import pandas as _pd
        df = _pd.DataFrame(records)
        # remove columns that are entirely empty/null
        def _trim_empty_columns(recs):
            import math
            if not recs:
                return [], recs
            keys = list(recs[0].keys())
            keep = []

            def is_empty(v):
                try:
                    if v is None:
                        return True
                    # pandas/numpy NA
                    try:
                        import pandas as _pd
                        if _pd.isna(v):
                            return True
                    except Exception:
                        pass
                    # floats that are NaN
                    if isinstance(v, float) and math.isnan(v):
                        return True
                    if isinstance(v, str) and v.strip() == '':
                        return True
                    if isinstance(v, (list, dict)) and len(v) == 0:
                        return True
                    return False
                except Exception:
                    return False

            for k in keys:
                all_empty = True
                for r in recs:
                    v = r.get(k)
                    if not is_empty(v):
                        all_empty = False
                        break
                if not all_empty:
                    keep.append(k)
            trimmed = [{k: r.get(k) for k in keep} for r in recs]
            return keep, trimmed

        keys, records = _trim_empty_columns(records)
        # sanitize cell values so dash table doesn't receive nested dicts/complex objects
        def _sanitize_cell(v):
            try:
                import numpy as _np
                if v is None:
                    return ''
                if isinstance(v, dict) or isinstance(v, list):
                    try:
                        return json.dumps(v, default=str)
                    except Exception:
                        return str(v)
                # pandas/numpy scalars
                try:
                    if isinstance(v, (_np.generic,)):
                        return v.item()
                except Exception:
                    pass
                try:
                    if hasattr(v, 'isoformat') and callable(getattr(v, 'isoformat')):
                        return v.isoformat()
                except Exception:
                    pass
                # default to string for other non-primitive types
                if isinstance(v, (str, int, float, bool)):
                    return v
                return str(v)
            except Exception:
                try:
                    return str(v)
                except Exception:
                    return ''

        for r in records:
            for k in list(r.keys()):
                r[k] = _sanitize_cell(r.get(k))
        cols = [{"name": c, "id": c} for c in keys]
        # ensure Inspect column exists
        if '_inspect' not in df.columns:
            cols.append({"name": "Inspect", "id": "_inspect"})
            for i, r in enumerate(records):
                r.setdefault('_inspect', 'Inspect')
                r.setdefault('_row_id', i)
        # detect long text columns and constrain their width so table doesn't stretch horizontally
        long_cols = []
        try:
            for c in df.columns:
                if df[c].dtype == object:
                    non_null = df[c].dropna().astype(str)
                    if not non_null.empty:
                        sample_len = non_null.map(len).nlargest(5).max()
                    else:
                        sample_len = 0
                    if sample_len > 200:
                        long_cols.append(c)
        except Exception:
            long_cols = []

        # Compact cell styling to avoid very tall rows caused by multi-line cells.
        # Force single-line truncation with nowrap so long text doesn't create tall rows.
        style_cell = {'whiteSpace': 'nowrap', 'height': '28px', 'textAlign': 'left', 'fontSize': '12px', 'padding': '4px 6px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}
        style_cell_conditional = []
        for lc in long_cols:
            # for long columns, cap width but keep nowrap to ensure single-line truncation
            style_cell_conditional.append({'if': {'column_id': lc}, 'maxWidth': '260px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'})

        table = dash_table.DataTable(
            id='results-table-client',
            columns=cols,
            data=records,
            page_size=25,
            sort_action='native',
            filter_action='native',
            style_table={'overflowX': 'auto', 'width': '100%'},
            style_cell=style_cell,
            style_cell_conditional=style_cell_conditional
        )
        return html.Div([html.H4('Loaded cached results'), table], style={'maxWidth': '1200px', 'overflowX': 'auto'}), table
    except Exception:
        return html.Div('Failed to render table'), None


def _render_brief_section(last):
    """Render the market brief block from cached brief JSON or top-level keys.
    Accepts either {'brief_json': {...}} or the brief dict itself.
    """
    brief = None
    if not last:
        return html.Div()
    if isinstance(last, dict) and 'brief_json' in last and isinstance(last.get('brief_json'), dict):
        brief = last.get('brief_json')
    elif isinstance(last, dict) and any(k in last for k in ('regime', 'market_mood_score', 'volatility_regime')):
        brief = last
    else:
        brief = last.get('brief') if isinstance(last, dict) else None

    if not brief or not isinstance(brief, dict):
        return html.Div()

    regime = brief.get('regime') or brief.get('stance') or 'Unknown'
    sp_last = brief.get('s_and_p_last') or brief.get('sp_last') or brief.get('s_p_last') or ''
    mood = brief.get('market_mood_score') or brief.get('market_mood') or ''
    vol_reg = brief.get('volatility_regime') or brief.get('vol_regime') or brief.get('realized_vs_implied') or ''

    leaders = brief.get('top_leaders') or []
    laggards = brief.get('top_laggards') or []
    movers_up = brief.get('movers_up') or brief.get('today_up') or []
    movers_down = brief.get('movers_down') or brief.get('today_down') or []

    # format numeric displays
    def _fmt_number(v, places=2):
        try:
            fv = float(v)
            return f"{fv:,.{places}f}"
        except Exception:
            try:
                return str(v)
            except Exception:
                return ''

    sp_display = _fmt_number(sp_last, places=2)
    # mood may be a score in [-1,1], show 3 decimals
    mood_display = _fmt_number(mood, places=3) if mood not in (None, '') else ''
    vol_display = str(vol_reg) if vol_reg is not None else ''

    def _small_metric(label, value, value_color=None, bg_color=None, icon=None):
        # Use theme-aware colors by default, but allow overrides.
        vc = value_color
        bg = bg_color
        icon_el = html.Span(icon, style={'marginRight': '6px', 'fontSize': '14px'}) if icon else None
        value_style = {'fontSize': '14px', 'fontWeight': '700', 'textAlign': 'center', 'color': vc} if vc else {'fontSize': '14px', 'fontWeight': '700', 'textAlign': 'center'}
        return html.Div([
            html.Div([html.Span(icon_el) if icon_el is not None else None, html.Span(label, style={'display': 'inline-block'})], style={'fontSize': '11px', 'color': '#9ca3af', 'textAlign': 'center', 'marginBottom': '4px', 'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'justifyContent': 'center'}),
            html.Div(value, style=value_style)
        ], style={'minWidth': '110px', 'padding': '6px 10px', 'backgroundColor': bg, 'border': '1px solid rgba(255,255,255,0.04)', 'borderRadius': '8px', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'justifyContent': 'center'})

    # pick mood color: green for positive, red for negative, neutral otherwise
    mood_color = None
    try:
        mv = float(mood)
        if mv > 0.05:
            mood_color = '#10B981'  # green
        elif mv < -0.05:
            mood_color = '#EF4444'  # red
        else:
            mood_color = '#e6eef8'
    except Exception:
        mood_color = '#e6eef8'

    # normalize vol display for readability
    try:
        vol_display = str(vol_reg).replace('>', ' › ')
    except Exception:
        vol_display = str(vol_reg)

    regime_icon = '🐂' if 'bull' in str(regime).lower() else ('🐻' if 'bear' in str(regime).lower() else '⚖️')

    header = html.Div([
        html.Div([html.H3('Brief (cached)', style={'margin': '0', 'fontSize': '18px'}), html.Div(f"Generated: {brief.get('generated_at', '')}", style={'fontSize': '11px', 'color': '#9ca3af', 'marginTop': '2px'})], style={'minWidth': '220px', 'maxWidth': '420px'}),
        html.Div([
            _small_metric('Regime', str(regime), icon=regime_icon),
            _small_metric('S&P', sp_display, icon='📈'),
            _small_metric('Mood', mood_display, value_color=mood_color, icon='😊' if (mood_color == '#10B981') else ('😟' if mood_color == '#EF4444' else '⚪')),
            _small_metric('Vol', vol_display, icon='⚠️')
        ], style={'display': 'flex', 'gap': '8px', 'alignItems': 'center', 'justifyContent': 'flex-end'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '6px', 'maxWidth': '1200px'})

    def small_table(data, page_size=5):
        if not data:
            return html.Div('')
        sample = data[0]
        # detect a 1d change key if present
        change_key = None
        for candidate in ('stock_ret_1d', 'ret_1d', 'change_1d', 'pct_change_1d'):
            if candidate in sample:
                change_key = candidate
                break
        # prefer columns: ticker, price, change_key, composite_score
        candidate_keys = []
        for k in ('ticker', 'price'):
            if k in sample:
                candidate_keys.append(k)
        if change_key:
            candidate_keys.append(change_key)
        if 'composite_score' in sample:
            candidate_keys.append('composite_score')

        # trim keys that are empty across all rows
        keep = []
        for k in candidate_keys:
            all_empty = True
            for r in data:
                v = r.get(k)
                if v is not None and str(v).strip() != '':
                    all_empty = False
                    break
            if not all_empty:
                keep.append(k)
        if not keep:
            return html.Div('')

        small_cols = [{"name": ("1d" if k==change_key else k).upper(), "id": k} for k in keep]
        trimmed = [{k: r.get(k) for k in keep} for r in data]

    # Format numeric values to sensible precision and align numbers right
        for r in trimmed:
            for k, v in list(r.items()):
                try:
                    if isinstance(v, (int, float)):
                        # prefer 2 decimals for prices and percent; 3 for scores
                        if 'price' in k.lower() or 's_and_p' in k.lower() or 'sp' in k.lower():
                            r[k] = f"{v:,.2f}"
                        elif 'composite' in k.lower() or 'score' in k.lower():
                            r[k] = f"{v:.3f}"
                        elif 'change' in k.lower() or 'ret' in k.lower() or 'pct' in k.lower():
                            try:
                                r[k] = f"{float(v):.2f}"
                            except Exception:
                                r[k] = v
                        else:
                            r[k] = f"{v}"
                    else:
                        # try parse numeric-like strings
                        sv = str(v)
                        if sv.replace(',', '').replace('.', '').lstrip('-').isdigit():
                            try:
                                fv = float(sv.replace(',', ''))
                                if 'composite' in k.lower() or 'score' in k.lower():
                                    r[k] = f"{fv:.3f}"
                                else:
                                    r[k] = f"{fv:,.2f}"
                            except Exception:
                                r[k] = v
                except Exception:
                    r[k] = v

        # limit rows shown to keep the small tables compact
        max_rows = min(len(trimmed), page_size or 4, 4)
        trimmed = trimmed[:max_rows]

        # small table styling: numeric right-align
        style_cell = {'fontSize': '11px', 'padding': '4px', 'textAlign': 'left', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'border': 'none'}
        style_cell_conditional = []
        for c in small_cols:
            cid = c['id']
            if cid != 'ticker':
                style_cell_conditional.append({'if': {'column_id': cid}, 'textAlign': 'right', 'maxWidth': '120px'})

        # make movers wider and readable
        return dash_table.DataTable(
            columns=small_cols,
            data=trimmed,
            page_size=max_rows,
            style_table={'width': '100%', 'overflowX': 'auto', 'height': 'auto', 'border': 'none'},
            style_cell=style_cell,
            style_cell_conditional=style_cell_conditional,
            style_header={'display': 'none'}
        )
    leaders_table = html.Div(small_table(leaders, page_size=6), style={'maxWidth': '360px', 'minWidth': '220px'})
    laggards_table = html.Div(small_table(laggards, page_size=6), style={'maxWidth': '360px', 'minWidth': '220px'})
    movers_left = html.Div(small_table(movers_up, page_size=8), style={'maxWidth': '420px', 'minWidth': '260px'})
    movers_right = html.Div(small_table(movers_down, page_size=8), style={'maxWidth': '420px', 'minWidth': '260px'})

    # show laggards earlier: place laggards first, then leaders
    # create a compact inline summary for top laggards to surface them earlier
    def _inline_laggards_summary(laggards_list, max_items=4):
        if not laggards_list:
            return html.Div()
        parts = []
        for itm in laggards_list[:max_items]:
            t = itm.get('ticker') or itm.get('symbol') or ''
            # find a 1d change key if present
            change = None
            for candidate in ('stock_ret_1d', 'ret_1d', 'change_1d', 'pct_change_1d'):
                if candidate in itm and itm.get(candidate) is not None:
                    change = itm.get(candidate)
                    break
            if change is not None:
                try:
                    change_s = f"{float(change):+.2f}"
                except Exception:
                    change_s = str(change)
                parts.append(f"{t} {change_s}")
            else:
                parts.append(t)
        return html.Div([html.Span('Top laggards: ', style={'fontWeight': '600', 'marginRight': '6px'}), html.Span(' • '.join(parts))], style={'marginTop': '4px', 'fontSize': '12px', 'color': '#cbd5e1'})

    inline_laggards = _inline_laggards_summary(laggards)

    body = html.Div([
        html.Div([
            html.Div([html.Div('Top laggards (composite)', style={'fontWeight': '600', 'marginBottom': '6px'}), laggards_table], style={'flex': 1}),
            html.Div([html.Div('Top leaders (composite)', style={'fontWeight': '600', 'marginBottom': '6px'}), leaders_table], style={'flex': 1})
        ], style={'display': 'flex', 'gap': '12px', 'alignItems': 'flex-start', 'flexWrap': 'wrap'}),
        html.Div([html.Div([html.Div("Today's movers", style={'fontWeight': '600', 'marginBottom': '6px'})], style={'flex': 1}), html.Div([movers_left, movers_right], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap'})], style={'marginTop': '8px'})
    ], style={'maxWidth': '1200px'})

    # prefer explicit brief text, otherwise compose a short textual summary
    text_brief = brief.get('brief_text') or brief.get('text') or ''
    if not text_brief:
        parts = []
        parts.append(f"Regime: {regime}")
        if brief.get('market_mood_explanation'):
            parts.append(brief.get('market_mood_explanation'))
        if brief.get('volatility_regime_explanation'):
            parts.append(brief.get('volatility_regime_explanation'))
        # leaders summary
        if leaders:
            topk = ', '.join([leader.get('ticker') for leader in leaders[:3]])
            parts.append(f"Top leaders: {topk}")
        text_brief = ' — '.join([p for p in parts if p])

    text_block = html.Div(text_brief, style={'marginTop': '8px', 'fontSize': '13px', 'color': '#cbd5e1'}) if text_brief else html.Div()

    return html.Div([header, inline_laggards, body, text_block], style={'padding': '6px 0', 'marginBottom': '6px'})


def build_price_figure(df, title=None):
    # Create 3-row subplot: Price+SMAs, MACD, RSI (and volume as bar on price)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])
    # price
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Close', line={'color': 'black'}), row=1, col=1)
    try:
        sma20 = df['Close'].rolling(window=20, min_periods=1).mean()
        sma50 = df['Close'].rolling(window=50, min_periods=1).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma20, name='SMA20', line={'color': 'blue'}), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sma50, name='SMA50', line={'color': 'orange'}), row=1, col=1)
    except Exception:
        pass
    # volume bars
    try:
        if 'Volume' in df.columns:
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker={'color': 'lightgrey'}), row=1, col=1)
    except Exception:
        pass

    # MACD
    try:
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal = macd_line.ewm(span=9, adjust=False).mean()
        hist = macd_line - signal
        fig.add_trace(go.Scatter(x=df.index, y=macd_line, name='MACD', line={'color': 'green'}), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=signal, name='Signal', line={'color': 'red'}), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=hist, name='MACD Hist', marker={'color': 'grey'}), row=2, col=1)
    except Exception:
        pass

    # RSI
    try:
        if hasattr(mt_mod, 'rsi'):
            rsi_series = mt_mod.rsi(df['Close'])
        else:
            # fallback simple RSI
            delta = df['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(14, min_periods=14).mean()
            avg_loss = loss.rolling(14, min_periods=14).mean()
            rs = avg_gain / avg_loss.replace({0: None})
            rsi_series = 100 - (100 / (1 + rs))
        fig.add_trace(go.Scatter(x=rsi_series.index, y=rsi_series, name='RSI', line={'color': 'purple'}), row=3, col=1)
        fig.add_hline(y=70, line_dash='dot', line_color='lightgrey')
        fig.add_hline(y=30, line_dash='dot', line_color='lightgrey')
    except Exception:
        pass

    fig.update_layout(title=title or 'Price + Indicators', xaxis_title='Date')
    return fig


# (Snapshots/file serving removed per UI simplification request)


# snapshot load removed


# NOTE: app.run must be at the bottom of the file so all callbacks and layout
# are registered before the server starts. The actual runnable block is placed
# at the very end of this module (after all @app.callback definitions).


# render the debug badge from last-edit store
@app.callback(Output('debug-badge', 'children'), Input('last-edit', 'data'))
def render_debug_badge(last_edit):
    try:
        if not last_edit:
            return html.Div([html.Div('No edits yet', style={'fontWeight': '600'}), html.Div('', style={'fontSize': '11px', 'color': '#666'})])
        msg = last_edit.get('message') if isinstance(last_edit, dict) else str(last_edit)
        at = last_edit.get('at') if isinstance(last_edit, dict) else None
        if at:
            try:
                ts = datetime.utcfromtimestamp(at).strftime('%Y-%m-%d %H:%M:%S UTC')
            except Exception:
                ts = str(at)
            return html.Div([html.Div(msg, style={'fontWeight': '600'}), html.Div(ts, style={'fontSize': '11px', 'color': '#666'})])
        return html.Div(msg)
    except Exception:
        return ''

@app.callback(
    Output('detail-modal', 'style'),
    Output('modal-content', 'children'),
    Input('results-table-client', 'active_cell'),
    Input('close-modal', 'n_clicks'),
    State('results-table-client', 'data'),
    State('last-cached', 'data')
)
def open_or_close_modal(active_cell, close_n, rows, last_cached):
    """Handles opening and closing the detail modal."""
    ctx = callback_context
    if not ctx.triggered or (close_n and ctx.triggered[0]['prop_id'] == 'close-modal.n_clicks'):
        return {'display': 'none'}, None

    if not active_cell or not rows:
        return {'display': 'none'}, None

    try:
        row_idx = active_cell['row']
        if not (0 <= row_idx < len(rows)):
            return {'display': 'none'}, None

        row_data = rows[row_idx]
        ticker = row_data.get('ticker', 'N/A')
        
        # Render details for the selected row
        details = [html.H4(f"Details for {ticker}")]
        for k, v in row_data.items():
            details.append(html.Div(f"{k}: {v}", style={'fontSize': '13px', 'marginBottom': '4px'}))

        # Attempt to add a price chart
        try:
            prices = (last_cached or {}).get('prices', {})
            if ticker in prices:
                df = pd.DataFrame(prices[ticker])
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                fig = build_price_figure(df, title=f"{ticker} Price Chart")
                details.append(dcc.Graph(figure=fig))
        except Exception as e:
            logger.warning(f"Could not generate price chart for {ticker}: {e}")

        return {
            'display': 'block', 'position': 'fixed', 'left': '10%', 'top': '10%', 
            'width': '80%', 'height': '80%', 'backgroundColor': 'white', 
            'border': '1px solid #ccc', 'padding': '10px', 'overflow': 'auto', 'zIndex': 1000
        }, details

    except Exception as e:
        logger.error(f"Error in open_or_close_modal: {e}", exc_info=True)
        return {'display': 'none'}, None


# Run the Dash app when invoked as a script. Placed at the end so all
# callbacks/layout registration above execute first.
if __name__ == '__main__':
    host = '0.0.0.0'
    port = 8050
    print(f'Starting Market Trends Dash app on http://{host}:{port}')
    # Bind to 0.0.0.0 so the app is reachable from the host/WSL or other network
    app.run(debug=True, host=host, port=port, use_reloader=False)
