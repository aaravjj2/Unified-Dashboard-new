"""Shared utilities and caches for Dash tab modules.
Keep shared state (MODEL_CACHE, RESULTS_CACHE) and small helpers used by multiple tabs.
"""
import os
import sys
import json
import time
import importlib.util
import traceback
import pandas as pd
from pathlib import Path
import re as _re
import threading
import types
import logging
import shutil

RESULTS_CACHE = {}

# Module logger
logger = logging.getLogger(__name__)

# Preload trends cache helper (call deferred until OUT_ROOT is available)
def _preload_trends():
    global RESULTS_CACHE
    root = OUT_ROOT
    keys = {}
    # Load brief JSON and text
    brief_json = Path(root, 'market_brief.json')
    if brief_json.exists():
        try:
            with open(brief_json, 'r') as f:
                keys['brief_json'] = json.load(f)
        except Exception:
            pass
    # If a computed market_trend_latest.json exists in OUT_ROOT, prefer its
    # 'trend.label' when presenting a cached brief so the UI reflects the
    # latest computed Trend even if the persisted brief contains an older
    # regime string.
    try:
        mt_fn = os.path.join(root, 'market_trend_latest.json')
        if os.path.exists(mt_fn) and keys.get('brief_json') and isinstance(keys.get('brief_json'), dict):
            try:
                with open(mt_fn, 'r', encoding='utf-8') as _mf:
                    mt = json.load(_mf)
                tlabel = mt.get('trend', {}).get('label')
                if tlabel:
                    keys['brief_json']['regime'] = tlabel
            except Exception:
                pass
    except Exception:
        pass
    brief_text = Path(root, 'market_brief.txt')
    if brief_text.exists():
        try:
            with open(brief_text, 'r') as f:
                txt = f.read()
            # sanitize any persisted debug wrapper markers
            try:
                txt = _re.sub(r'<div[^>]*id=["\"]?brief-reload-[^"\">*["\"]?[^>]*>.*?</div>', '', txt, flags=_re.S | _re.I)
            except Exception:
                pass
            txt = _re.sub(r'BRIEF-ID:.*\n?', '', txt)
            txt = _re.sub(r'brief-reload-[^\s<>]*', '', txt)
            keys['brief_text'] = txt.strip()
        except Exception:
            pass
    # Load tidy and detailed CSVs
    tidy = Path(root, 'tech_summary.csv')
    if tidy.exists():
        try:
            tidy_df = pd.read_csv(tidy)
            keys['tidy'] = tidy_df.fillna('').to_dict(orient='records')
            keys['tidy_df'] = tidy_df
        except Exception:
            pass
    detailed = Path(root, 'tech_report_detailed.csv')
    if detailed.exists():
        try:
            detailed_df = pd.read_csv(detailed)
            keys['detailed'] = detailed_df.fillna('').to_dict(orient='records')
            keys['detailed_df'] = detailed_df
        except Exception:
            pass
    # Load any persisted price caches created by background jobs (Option B).
    # Try multiple candidate output dirs (OUT_ROOT, /app/outputs, PROJECT_ROOT/outputs, repo-level outputs)
    try:
        cand_dirs = [Path(root), Path('/app/outputs'), Path(PROJECT_ROOT) / 'outputs', Path(DASH_ROOT) / 'outputs', Path('outputs')]
        for d in cand_dirs:
            try:
                if not d or not d.exists():
                    continue
                for price_fn in ('prices_monthly.json', 'prices_weekly.json'):
                    pf = d / price_fn
                    if not pf.exists():
                        continue
                    try:
                        with pf.open('r', encoding='utf-8') as _pf:
                            pj = json.load(_pf)
                        # Handle both wrapped {"prices": {...}} and direct {...} formats
                        if isinstance(pj, dict):
                            if 'prices' in pj:
                                # Wrapped format
                                pmap = pj['prices']
                            else:
                                # Direct format (PriceClient.get_prices saves this way)
                                pmap = pj
                        else:
                            pmap = None
                            
                        if isinstance(pmap, dict) and pmap:
                            # Normalize per-file start_price into explicit week/month keys
                            normalized = {}
                            for ticker_sym, entry in pmap.items():
                                try:
                                    e = dict(entry) if isinstance(entry, dict) else {}
                                except Exception:
                                    e = {}
                                # If this file represents monthly prices, map its start_price
                                # to month_start_price. If weekly, map to week_start_price.
                                if price_fn == 'prices_monthly.json':
                                    if 'start_price' in e and 'month_start_price' not in e:
                                        e['month_start_price'] = e.get('start_price')
                                elif price_fn == 'prices_weekly.json':
                                    if 'start_price' in e and 'week_start_price' not in e:
                                        e['week_start_price'] = e.get('start_price')
                                normalized[ticker_sym] = e

                            existing = keys.get('prices') or {}
                            # Merge normalized entries per-ticker so we don't overwrite
                            # previously loaded monthly/week-specific fields.
                            for tck, ent in normalized.items():
                                prev = existing.get(tck, {})
                                if not isinstance(prev, dict):
                                    prev = {}
                                try:
                                    prev.update(ent)
                                except Exception:
                                    prev = ent
                                existing[tck] = prev
                            keys['prices'] = existing
                    except Exception:
                        # ignore corrupt/unreadable price file and continue
                        continue
            except Exception:
                continue
    except Exception:
        pass
    if keys:
        RESULTS_CACHE['results'] = keys

# Prevent Pillow's ImageTk (which imports tkinter and hooks into its
# finalizers) from being loaded in this server process. When background
# threads import image/plotting libraries they can trigger tkinter finalizer
# errors like "main thread is not in main loop". We insert a lightweight
# stub for PIL.ImageTk early so any later `import PIL.ImageTk` will get the
# stub instead of the real module. The stub raises if used so any code that
# actually needs ImageTk will fail fast rather than silently creating
# tkinter objects on a non-main thread.
try:
    if 'PIL.ImageTk' not in sys.modules:
        dummy = types.ModuleType('PIL.ImageTk')
        class _DisabledPhotoImage:
            def __init__(self, *args, **kwargs):
                raise RuntimeError('PIL.ImageTk is disabled in this server environment')
        dummy.PhotoImage = _DisabledPhotoImage
        dummy.BitmapImage = _DisabledPhotoImage
        sys.modules['PIL.ImageTk'] = dummy
except Exception:
    # If anything goes wrong here, don't block startup; the app may still
    # function but Tk-related finalizer errors could appear.
    pass

APP_DIR = os.path.dirname(__file__)
DASH_ROOT = APP_DIR  # The Dash directory is the root for most resources (models, outputs, etc.)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))  # Parent directory for Gradio and shared resources
GRADIO_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, 'Gradio'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def load_module_from_path(path, name=None):
    if not os.path.exists(path):
        return None
    try:
        name = name or os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        traceback.print_exc()
        return None


# Lazy-load analysis module to avoid blocking dashboard startup
# The module will be loaded on-demand when first accessed via get_mt_mod()
_mt_mod_cache = {'mod': None, 'attempted': False}

def get_mt_mod():
    """Lazy-load the market_trends module from Gradio directory.
    Returns None if module cannot be loaded."""
    if not _mt_mod_cache['attempted']:
        _mt_mod_cache['attempted'] = True
        try:
            _mt_mod_cache['mod'] = load_module_from_path(
                os.path.join(GRADIO_DIR, 'market_trends.py'), 
                'market_trends'
            )
        except Exception:
            pass
    return _mt_mod_cache['mod']

# For backward compatibility, expose mt_mod as a property that lazy-loads
mt_mod = None  # Will be set on first access via get_mt_mod()

# shared caches
MODEL_CACHE = {'model': None, 'loaded_at': None, 'ttl': 3600}
RESULTS_CACHE = {'results': None, 'loaded_at': None}

# Default output root (can be overridden by mt_mod when loaded)
# FIX: Use DASH_ROOT instead of PROJECT_ROOT so outputs/ is relative to the Dash app directory
# This ensures Docker containers look in /app/outputs/ not /outputs/
OUT_ROOT = os.path.join(DASH_ROOT, 'outputs')
os.makedirs(OUT_ROOT, exist_ok=True)

def _preload_persisted_prices():
    """Load persisted weekly/monthly price cache files into RESULTS_CACHE on startup.
    
    SUPER-AGENT FIX: Enhanced with centralized key management and fallback fetching.
    
    This ensures the UI has price data immediately without waiting for background jobs.
    If Market Trends tickers are missing, attempts to fetch them via yfinance.
    """
    import json
    import time
    global RESULTS_CACHE
    
    # Ensure RESULTS_CACHE structure exists
    if not isinstance(RESULTS_CACHE.get('results'), dict):
        RESULTS_CACHE['results'] = {}
    if 'prices' not in RESULTS_CACHE['results']:
        RESULTS_CACHE['results']['prices'] = {}
    
    # Try to load weekly prices
    weekly_cache_path = os.path.join(OUT_ROOT, 'prices_weekly.json')
    if os.path.exists(weekly_cache_path):
        try:
            with open(weekly_cache_path, 'r', encoding='utf-8') as f:
                weekly_data = json.load(f)
                # Handle both formats: {"prices": {...}} and direct {...}
                if isinstance(weekly_data, dict):
                    if 'prices' in weekly_data:
                        # Wrapped format
                        RESULTS_CACHE['results']['prices'].update(weekly_data['prices'])
                        RESULTS_CACHE['loaded_at'] = weekly_data.get('generated_at', time.time())
                    else:
                        # Direct format (PriceClient.get_prices saves directly)
                        RESULTS_CACHE['results']['prices'].update(weekly_data)
                        RESULTS_CACHE['loaded_at'] = time.time()
                    logger.info(f"✅ Preloaded {len(RESULTS_CACHE['results']['prices'])} weekly prices from cache")
                    print(f"[_shared.py] ✅ Preloaded {len(RESULTS_CACHE['results']['prices'])} weekly prices", flush=True)
        except Exception as e:
            logger.warning(f"Could not preload weekly prices: {e}")
    
    # Try to load monthly prices
    monthly_cache_path = os.path.join(OUT_ROOT, 'prices_monthly.json')
    if os.path.exists(monthly_cache_path):
        try:
            with open(monthly_cache_path, 'r', encoding='utf-8') as f:
                monthly_data = json.load(f)
                # Handle both formats
                if isinstance(monthly_data, dict):
                    if 'prices' in monthly_data:
                        RESULTS_CACHE['results']['prices'].update(monthly_data['prices'])
                    else:
                        RESULTS_CACHE['results']['prices'].update(monthly_data)
                    logger.info(f"✅ Preloaded {len(RESULTS_CACHE['results']['prices'])} total prices (including monthly)")
        except Exception as e:
            logger.warning(f"Could not preload monthly prices: {e}")
    
    # SUPER-AGENT FIX: Validate Market Trends ticker completeness
    try:
        from financial_dashboard.utils.keys_manager import validate_cache, log_cache_status, get_market_trends_tickers
        from financial_dashboard.utils.price_fetcher import update_cache_with_missing
        
        # Check cache completeness
        validation = validate_cache(RESULTS_CACHE['results'])
        
        if not validation['complete']:
            missing = validation['missing_tickers']
            invalid = validation['invalid_tickers']
            
            logger.warning(f"[PRELOAD] Cache incomplete - Missing: {missing}, Invalid: {invalid}")
            
            # Attempt to fetch missing Market Trends tickers
            market_trends_tickers = get_market_trends_tickers()
            updated_cache, fetched = update_cache_with_missing(
                RESULTS_CACHE['results'],
                market_trends_tickers
            )
            
            if fetched:
                RESULTS_CACHE['results'] = updated_cache
                logger.info(f"✅ [PRELOAD] Fetched missing tickers: {', '.join(fetched)}")
                
                # Attempt to persist updated cache (WSL2-aware)
                try:
                    from financial_dashboard.utils.cache_persistence import write_cache
                    
                    cache_to_save = {
                        'prices': RESULTS_CACHE['results']['prices'],
                        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    if write_cache(cache_to_save, 'prices_weekly.json'):
                        logger.info("✅ [PRELOAD] Persisted updated cache to prices_weekly.json")
                except Exception as persist_err:
                    logger.warning(f"[PRELOAD] Could not persist updated cache: {persist_err}")
        
        # Log final cache status
        log_cache_status(RESULTS_CACHE['results'], "Startup Cache")
        
    except Exception as e:
        logger.warning(f"[PRELOAD] Could not validate/update cache: {e}")

# Preload persisted prices on module import
_preload_persisted_prices()


def refresh_prices_cache(force_fetch_missing: bool = True):
    """
    Manually refresh the RESULTS_CACHE prices.
    
    SUPER-AGENT FIX: Allows callbacks to trigger cache refresh without restart.
    
    Args:
        force_fetch_missing: If True, fetch missing Market Trends tickers via yfinance
        
    Returns:
        Dictionary with refresh status:
        {
            'success': bool,
            'tickers_before': int,
            'tickers_after': int,
            'fetched': List[str],
            'validation': dict
        }
    """
    global RESULTS_CACHE
    import json
    
    logger.info("[REFRESH_CACHE] Starting cache refresh...")
    
    result = {
        'success': False,
        'tickers_before': len(RESULTS_CACHE.get('results', {}).get('prices', {})),
        'tickers_after': 0,
        'fetched': [],
        'validation': {}
    }
    
    try:
        # Reload from disk
        weekly_cache_path = os.path.join(OUT_ROOT, 'prices_weekly.json')
        if os.path.exists(weekly_cache_path):
            with open(weekly_cache_path, 'r', encoding='utf-8') as f:
                weekly_data = json.load(f)
                if isinstance(weekly_data, dict):
                    if 'prices' in weekly_data:
                        RESULTS_CACHE['results']['prices'] = weekly_data['prices'].copy()
                    else:
                        RESULTS_CACHE['results']['prices'] = weekly_data.copy()
        
        # Optionally fetch missing Market Trends tickers
        if force_fetch_missing:
            from financial_dashboard.utils.keys_manager import get_market_trends_tickers, validate_cache
            from financial_dashboard.utils.price_fetcher import update_cache_with_missing
            
            market_trends_tickers = get_market_trends_tickers()
            updated_cache, fetched = update_cache_with_missing(
                RESULTS_CACHE['results'],
                market_trends_tickers
            )
            
            if fetched:
                RESULTS_CACHE['results'] = updated_cache
                result['fetched'] = fetched
                logger.info(f"✅ [REFRESH_CACHE] Fetched {len(fetched)} missing tickers")
            
            # Validate final state
            result['validation'] = validate_cache(RESULTS_CACHE['results'])
        
        result['tickers_after'] = len(RESULTS_CACHE.get('results', {}).get('prices', {}))
        result['success'] = True
        
        logger.info(
            f"✅ [REFRESH_CACHE] Complete: {result['tickers_before']} → {result['tickers_after']} tickers"
        )
        
    except Exception as e:
        logger.error(f"❌ [REFRESH_CACHE] Failed: {e}")
        result['error'] = str(e)
    
    return result


# Diagnostic: expose module alias and log identity for cross-process debugging
try:
    import sys as _sys
    SH = _sys.modules[__name__]
    try:
        logger.warning(f"[_shared] SH id: {id(SH)}, RESULTS_CACHE id: {id(RESULTS_CACHE)}, SH.__file__: {getattr(SH, '__file__', 'n/a')}")
        # Also emit to stdout to help capture logs when gunicorn stdout is visible
        print(f"[_shared] SH id: {id(SH)}, RESULTS_CACHE id: {id(RESULTS_CACHE)}, SH.__file__: {getattr(SH, '__file__', 'n/a')}", flush=True)
    except Exception as _e:
        logger.warning(f"[_shared] Could not emit diagnostic ids: {_e}")
except Exception:
    # Defensive: do not block module import on diagnostic failures
    pass

# Canonical cache directory resolution
# Prefer an absolute runtime cache at /app/cache when available (containers).
# If /app/cache is missing but repository cache copies exist under the package,
# populate /app/cache from the first available repo cache so all modules can
# consistently read from /app/cache. This makes cache resolution deterministic
# across modules that reference different paths (/app/cache vs financial_dashboard/cache).
CACHE_DIR_CANDIDATES = [
    Path('/app/cache'),
    Path(DASH_ROOT, 'cache'),
    Path(PROJECT_ROOT, 'cache'),
    Path('/app/financial_dashboard/cache'),
]

def ensure_canonical_cache():
    """Ensure /app/cache exists and is populated from an existing repo cache.

    Returns the Path to the canonical cache directory (prefer /app/cache).
    """
    target = Path('/app/cache')
    try:
        # If target exists and is a directory, return it immediately
        if target.exists() and target.is_dir():
            return target

        # Find the first existing candidate with files
        for cand in CACHE_DIR_CANDIDATES[1:]:
            try:
                if cand.exists() and cand.is_dir():
                    # Create target dir and copy files into it
                    target.mkdir(parents=True, exist_ok=True)
                    for item in cand.iterdir():
                        dest = target / item.name
                        if item.is_dir():
                            # copytree requires dest not exist
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
                    return target
            except Exception:
                # Try next candidate
                continue

        # As a final fallback, ensure target exists (empty)
        target.mkdir(parents=True, exist_ok=True)
        return target
    except Exception:
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return target

# Populate canonical cache at module import time so modules reading /app/cache
# during startup will find files.
CANONICAL_CACHE_DIR = ensure_canonical_cache()

# Standardized representation for missing values in UI
# Keep as 'N/A' by default for tests, but callers may override if they
# prefer an empty string or different sentinel when rendering.
NA_REPR = 'N/A'


def display_value(v, na_rep=None):
    """Return a string suitable for display in the UI for value v.

    - If v is None or NaN, return na_rep (or NA_REPR).
    - Otherwise return str(v).
    This centralizes the policy for how missing values are presented.
    """
    import pandas as _pd
    if na_rep is None:
        na_rep = NA_REPR
    try:
        if v is None:
            return na_rep
        # pandas NA check covers numpy.nan and pd.NA
        if hasattr(_pd, 'isna') and _pd.isna(v):
            return na_rep
    except Exception:
        # If pandas isn't available or check fails, fall back to simple test
        if v is None:
            return na_rep
    return str(v)


def records_from_df(df, numeric_fill=0, object_fill=None):
    """Return list-of-dicts from DataFrame with missing values normalized.

    - numeric_fill: value to fill numeric columns (default 0)
    - object_fill: value to fill object/string columns (default NA_REPR)
    """
    import pandas as _pd
    if object_fill is None:
        object_fill = NA_REPR
    if df is None or df.empty:
        return []
    out = df.copy()
    for col in out.columns:
        try:
            if _pd.api.types.is_numeric_dtype(out[col].dtype):
                out[col] = out[col].fillna(numeric_fill)
            else:
                out[col] = out[col].fillna(object_fill)
        except Exception:
            try:
                out[col] = out[col].fillna(object_fill)
            except Exception:
                # Give up on this column
                continue
    return out.to_dict(orient='records')

# centralized job registry for tabs to schedule background work
JOBS = {}

# Now that OUT_ROOT exists, attempt to preload trends cached outputs so the
# Trends tab can show persisted results immediately without requiring a run.
try:
    _preload_trends()
    RESULTS_CACHE['loaded_at'] = time.time()
except Exception:
    pass


def start_background_job(target, args=(), kwargs=None, job_name=None):
    """Start a daemon thread running target(*args, **(kwargs)) and register it in JOBS.
    Returns job_id. JOBS[job_id] holds {'name','status','thread','started','result'}.
    
    PHASE 6E: Added module identity and cache diagnostics."""
    if kwargs is None:
        kwargs = {}
    job_id = f"job_{int(time.time() * 1000)}"
    JOBS[job_id] = {'name': job_name or getattr(target, '__name__', 'job'), 'status': 'queued', 'thread': None, 'started': time.time(), 'result': None}

    # ensure module logger is at DEBUG so diagnostic logs appear
    try:
        logging.getLogger(__name__).setLevel(logging.DEBUG)
    except Exception:
        pass
    
    # PHASE 6E: Log module identity before job starts
    logger.warning(f"[start_background_job] Starting job {job_id}")
    logger.warning(f"[start_background_job] SH module: {__file__}, id(RESULTS_CACHE): {id(RESULTS_CACHE)}")
    cache_prices = RESULTS_CACHE.get("results", {}).get("prices", {})
    logger.warning(f"[start_background_job] Cache has {len(cache_prices)} price entries before job start")

    def _runner(jid):
        """Enhanced background job runner with comprehensive diagnostic logging and timeout protection."""
        import logging as _logging
        _logger = _logging.getLogger(__name__)
        
        JOBS[jid]['status'] = 'running'
        
        # PHASE 4 DIAGNOSTIC: Log job start with full context
        _logger.info("=" * 80)
        _logger.info(f"🚀 BACKGROUND JOB STARTED: {jid}")
        _logger.info(f"   Target: {getattr(target, '__name__', str(target))}")
        _logger.info(f"   Module: {getattr(target, '__module__', 'unknown')}")
        _logger.info(f"   Args: {args}")
        _logger.info(f"   Kwargs keys: {list(kwargs.keys()) if isinstance(kwargs, dict) else type(kwargs)}")
        if isinstance(kwargs, dict):
            for key, val in kwargs.items():
                if key == 'tickers':
                    _logger.info(f"      tickers: {val} (type={type(val)})")
                else:
                    _logger.info(f"      {key}: {val}")
        _logger.info("=" * 80)
        
        try:
            # Normalize common legacy kwargs before invoking target
            try:
                if isinstance(kwargs, dict) and 'tickers' in kwargs:
                    t = kwargs.get('tickers')
                    if isinstance(t, str):
                        # comma-separated string -> list
                        kwargs['tickers'] = [x.strip() for x in t.split(',') if x.strip()]
                        _logger.info(f"✅ Normalized tickers from string to list: {kwargs['tickers']}")
                    elif t is None:
                        kwargs['tickers'] = []
                        _logger.info("⚠️  tickers was None - set to empty list")
                    elif not isinstance(t, (list, tuple)):
                        try:
                            kwargs['tickers'] = list(t)
                            _logger.info(f"✅ Converted tickers to list: {kwargs['tickers']}")
                        except Exception:
                            kwargs['tickers'] = [str(t)]
                            _logger.warning(f"⚠️  Could not convert tickers - using string: {kwargs['tickers']}")
            except Exception as norm_err:
                _logger.error(f"❌ Ticker normalization failed: {norm_err}")
            
            # PHASE 4 ENHANCEMENT: Add timeout protection
            import signal
            from contextlib import contextmanager
            
            class TimeoutException(Exception):
                pass
            
            @contextmanager
            def time_limit(seconds):
                def signal_handler(signum, frame):
                    raise TimeoutException(f"Job exceeded {seconds}s timeout")
                # Note: signal.alarm only works on Unix systems (not Windows)
                # For cross-platform timeout, we'll use threading.Timer fallback
                timer = None
                try:
                    # Only use the SIGALRM mechanism when running in the main
                    # thread of the main interpreter. Calling signal.signal from
                    # a non-main thread raises ValueError. In threads we use a
                    # threading.Timer fallback which raises the TimeoutException
                    # inside the timer thread (we capture it as a timeout event
                    # instead of interrupting the target thread).
                    is_main_thread = threading.current_thread() is threading.main_thread()
                    if hasattr(signal, 'SIGALRM') and is_main_thread:
                        signal.signal(signal.SIGALRM, signal_handler)
                        signal.alarm(seconds)
                    else:
                        # Fallback for non-main threads or platforms without SIGALRM
                        def timeout_handler():
                            # We can't raise in the target thread from here; mark
                            # the timeout by raising inside the timer thread so
                            # the runner treats it as a timeout event.
                            raise TimeoutException(f"Job exceeded {seconds}s timeout")
                        timer = threading.Timer(seconds, timeout_handler)
                        timer.daemon = True
                        timer.start()
                    yield
                finally:
                    if hasattr(signal, 'SIGALRM') and (threading.current_thread() is threading.main_thread()):
                        signal.alarm(0)
                    elif timer:
                        timer.cancel()
            
            # PHASE 6D: Configurable timeout via environment variable (default 300s)
            job_timeout = int(os.environ.get('JOB_TIME_LIMIT', 300))
            _logger.info(f"⏱️  Starting job execution with {job_timeout}s timeout...")
            start_time = time.time()
            
            try:
                with time_limit(job_timeout):
                    res = target(*args, **kwargs)
                    elapsed = time.time() - start_time
                    _logger.info(f"✅ Job completed successfully in {elapsed:.2f}s")
                    
                    # Log result structure for diagnostics
                    if isinstance(res, dict):
                        _logger.info(f"   Result keys: {list(res.keys())}")
                        if 'detailed' in res:
                            _logger.info(f"   Detailed records: {len(res['detailed']) if res['detailed'] else 0}")
                    else:
                        _logger.info(f"   Result type: {type(res)}")
                    
                    JOBS[jid]['result'] = res
                    JOBS[jid]['status'] = 'done'
                    _logger.info(f"📝 Job {jid} marked as 'done'")
                    
            except TimeoutException as te:
                elapsed = time.time() - start_time
                _logger.error("=" * 80)
                _logger.error(f"⏰ TIMEOUT: Job {jid} exceeded {job_timeout} seconds")
                _logger.error(f"   Elapsed: {elapsed:.2f}s")
                _logger.error(f"   Target: {getattr(target, '__name__', 'unknown')}")
                _logger.error("=" * 80)
                JOBS[jid]['result'] = {
                    'ok': False,
                    'error': f'Job timeout after {elapsed:.1f}s',
                    'timeout': True,
                    'elapsed': elapsed
                }
                JOBS[jid]['status'] = 'error'
                
        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            _logger.error("=" * 80)
            _logger.error(f"❌ EXCEPTION: Job {jid} failed")
            _logger.error(f"   Exception type: {type(e).__name__}")
            _logger.error(f"   Exception message: {str(e)}")
            _logger.error(f"   Elapsed: {elapsed:.2f}s")
            _logger.error(f"   Traceback:")
            _logger.error(traceback.format_exc())
            _logger.error("=" * 80)
            
            JOBS[jid]['result'] = {
                'ok': False,
                'error': str(e),
                'trace': traceback.format_exc(),
                'elapsed': elapsed
            }
            JOBS[jid]['status'] = 'error'

    th = threading.Thread(target=_runner, args=(job_id,), daemon=True)
    JOBS[job_id]['thread'] = th
    th.start()
    return job_id


def get_job_status(job_id):
    """Return a normalized job status dict for the given job_id.

    Normalizes internal status names to the values expected by tab callbacks:
    - 'running' for queued/running
    - 'completed' for done
    - 'failed' for error
    Returns a dict like {'status': <str>, 'result': <any>, 'error': <str or None>} or None if not found.
    """
    jd = JOBS.get(job_id)
    if not jd:
        return None
    s = jd.get('status')
    mapped = None
    if s in ('running', 'queued'):
        mapped = 'running'
    elif s in ('done',):
        mapped = 'completed'
    elif s in ('error', 'failed'):
        mapped = 'failed'
    else:
        mapped = s
    return {'status': mapped, 'result': jd.get('result'), 'error': jd.get('result', {}).get('error') if isinstance(jd.get('result'), dict) else None}


def _sanitize_for_store(obj):
    try:
        if isinstance(obj, pd.DataFrame):
            return obj.fillna('').to_dict(orient='records')
        if isinstance(obj, pd.Series):
            return obj.fillna('').to_dict()
    except Exception:
        pass
    try:
        import numpy as _np
        if isinstance(obj, _np.generic):
            return obj.item()
        if isinstance(obj, (_np.ndarray,)):
            return obj.tolist()
    except Exception:
        pass
    try:
        from datetime import datetime as _dt
        if isinstance(obj, _dt):
            return obj.isoformat()
    except Exception:
        pass
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            try:
                out[k] = _sanitize_for_store(v)
            except Exception:
                out[k] = None
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            try:
                out.append(_sanitize_for_store(v))
            except Exception:
                out.append(None)
        return out
    try:
        json.dumps(obj)
        return obj
    except Exception:
        try:
            return str(obj)
        except Exception:
            return None


def sanitize_brief_text(txt):
    """Return a cleaned brief text string with any debug wrapper divs or BRIEF-ID markers removed.
    Designed to be idempotent and safe for non-string inputs.
    """
    try:
        if not isinstance(txt, str):
            return txt
        try:
            txt = _re.sub(r'<div[^>]*id=["\"]?brief-reload-[^"\">*["\"]?[^>]*>.*?</div>', '', txt, flags=_re.S | _re.I)
        except Exception:
            pass
        txt = _re.sub(r'BRIEF-ID:.*\n?', '', txt)
        txt = _re.sub(r'brief-reload-[^\s<>]*', '', txt)
        return txt.strip()
    except Exception:
        try:
            return str(txt)
        except Exception:
            return txt


def load_cached_results_from_outputs():
    """Load persisted outputs if present (brief JSON/text and CSVs). Returns dict."""
    try:
        out_dir = OUT_ROOT
        brief_json_path = os.path.join(out_dir, 'market_brief.json')
        brief_txt_path = os.path.join(out_dir, 'market_brief_text.txt')
        tidy_csv = os.path.join(out_dir, 'tech_summary.csv')
        detailed_csv = os.path.join(out_dir, 'tech_report_detailed.csv')
        cached = {}
        if os.path.exists(brief_json_path):
            try:
                with open(brief_json_path, 'r', encoding='utf-8') as fh:
                    cached['brief_json'] = json.load(fh)
                    cached['brief_text'] = f"Market brief (cached) — generated at {cached['brief_json'].get('generated_at', 'unknown')}"
            except Exception:
                cached['brief_json'] = None
        if os.path.exists(brief_txt_path):
            try:
                with open(brief_txt_path, 'r', encoding='utf-8') as fh:
                    txt = fh.read()
                # sanitize any leftover debug markers or wrapper divs from older persisted briefs
                try:
                    if txt and isinstance(txt, str):
                        try:
                            txt = _re.sub(r'<div[^>]*id=["\"]?brief-reload-[^"\">*["\"]?[^>]*>.*?</div>', '', txt, flags=_re.S | _re.I)
                        except Exception:
                            pass
                        txt = _re.sub(r'BRIEF-ID:.*\\n?', '', txt)
                        txt = _re.sub(r'brief-reload-[^\s<>]*', '', txt)
                        txt = txt.strip()
                except Exception:
                    pass
                if txt and txt.strip():
                    cached['brief_text'] = txt
                else:
                    cached.setdefault('brief_text', txt)
            except Exception:
                cached['brief_text'] = cached.get('brief_text') or None
        if os.path.exists(tidy_csv):
            try:
                td = pd.read_csv(tidy_csv)
                try:
                    cached['tidy'] = td.fillna(' ').to_dict(orient='records')
                except Exception:
                    cached['tidy'] = td.to_dict(orient='records')
                cached['tidy_df'] = td
            except Exception:
                cached['tidy_df'] = None
        if os.path.exists(detailed_csv):
            try:
                df = pd.read_csv(detailed_csv)
                try:
                    cached['detailed'] = df.fillna(' ').to_dict(orient='records')
                except Exception:
                    cached['detailed'] = df.to_dict(orient='records')
                cached['detailed_df'] = df
            except Exception:
                cached['detailed_df'] = None
        # --- also attempt to discover forecast outputs produced by market_forecast.main()
        try:
            import glob
            # candidate dirs: OUT_ROOT and a repo-level 'forecast_outputs'
            extra_dirs = [out_dir, os.path.join(PROJECT_ROOT, 'forecast_outputs')]
            found_rows = []
            for d in extra_dirs:
                try:
                    if not os.path.exists(d):
                        continue
                    # look for CSVs that match forecast outputs (e.g., {TICKER}_forecast_{Nd}.csv)
                    patterns = [os.path.join(d, '*_forecast_*.csv'), os.path.join(d, '*_backtest_*.csv')]
                    for pat in patterns:
                        for p in glob.glob(pat):
                            try:
                                df2 = pd.read_csv(p)
                                # annotate ticker if present in filename
                                base = os.path.basename(p)
                                maybe_t = base.split('_forecast_')[0] if '_forecast_' in base else None
                                recs = df2.fillna(' ').to_dict(orient='records')
                                for r in recs:
                                    if maybe_t and 'ticker' not in r:
                                        r['ticker'] = maybe_t
                                    found_rows.append(r)
                            except Exception:
                                continue
                    # also check for last_backtest_meta.json which may point to CSV/png paths
                    meta = os.path.join(d, 'last_backtest_meta.json')
                    if os.path.exists(meta):
                        try:
                            with open(meta, 'r', encoding='utf-8') as fh:
                                jm = json.load(fh)
                            csvp = jm.get('csv')
                            if csvp and os.path.exists(csvp):
                                try:
                                    df3 = pd.read_csv(csvp)
                                    recs = df3.fillna(' ').to_dict(orient='records')
                                    for r in recs:
                                        found_rows.append(r)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
            if found_rows and not cached.get('detailed'):
                cached['detailed'] = found_rows
                try:
                    cached['detailed_df'] = pd.DataFrame(found_rows)
                except Exception:
                    cached['detailed_df'] = None
        except Exception:
            pass

        return cached
    except Exception:
        return {}


def load_last_cached_results():
    """Try to load last persisted results from OUT_ROOT (market_brief.json, detailed CSV, or tidy CSV).
    Returns a dict similar to the run_full_analysis/predict output or None.
    """
    # This function centralizes the logic for finding the latest analysis output.
    # It prioritizes the most complete artifacts first.
    try:
        # 1. Prefer the comprehensive market_brief.json
        jp = os.path.join(OUT_ROOT, 'market_brief.json')
        if os.path.exists(jp):
            with open(jp, 'r', encoding='utf-8') as hf:
                result = json.load(hf)
            
            # Also try to load brief_text from disk if a brief text file exists.
            # Some runner scripts write 'market_brief.txt' while others write
            # 'market_brief_text.txt' — accept either for compatibility.
            try:
                import re
                txt_candidates = [os.path.join(OUT_ROOT, 'market_brief.txt'), os.path.join(OUT_ROOT, 'market_brief_text.txt')]
                for txt_path in txt_candidates:
                    if os.path.exists(txt_path):
                        try:
                            with open(txt_path, 'r', encoding='utf-8') as tf:
                                txt = tf.read()
                            # Sanitize debug markers
                            try:
                                txt = re.sub(r'<div[^>]*id=["\']?brief-reload-[^"\'>]*["\']?[^>]*>.*?</div>', '', txt, flags=re.S | re.I)
                            except Exception:
                                pass
                            txt = re.sub(r'BRIEF-ID:.*\n?', '', txt)
                            txt = re.sub(r'brief-reload-[^\s<>]*', '', txt)
                            result['brief_text'] = txt.strip()
                            break
                        except Exception:
                            # try next candidate
                            continue
            except Exception:
                pass
            
            return result
    except Exception:
        pass
    # Fallback to CSVs if JSON is missing or corrupt
    return load_trends_cached_results_from_outputs()


def load_trends_cached_results_from_outputs():
    """Load persisted Trends-only outputs if present (brief JSON/text and CSVs).
    This is a restricted loader that does NOT attempt to discover Forecast
    CSVs or backtest artifacts. Use this from the Trends tab and dashboard
    code paths that should not mix Forecast outputs into Trends results.
    """
    try:
        out_dir = OUT_ROOT
        brief_json_path = os.path.join(out_dir, 'market_brief.json')
        brief_txt_path = os.path.join(out_dir, 'market_brief_text.txt')
        tidy_csv = os.path.join(out_dir, 'tech_summary.csv')
        detailed_csv = os.path.join(out_dir, 'tech_report_detailed.csv')
        cached = {}
        if os.path.exists(brief_json_path):
            try:
                with open(brief_json_path, 'r', encoding='utf-8') as fh:
                    cached['brief_json'] = json.load(fh)
                    cached['brief_text'] = f"Market brief (cached) — generated at {cached['brief_json'].get('generated_at', 'unknown')}"
            except Exception:
                cached['brief_json'] = None
        if os.path.exists(brief_txt_path):
            try:
                with open(brief_txt_path, 'r', encoding='utf-8') as fh:
                    txt = fh.read()
                if txt and txt.strip():
                    cached['brief_text'] = txt
                else:
                    cached.setdefault('brief_text', txt)
            except Exception:
                cached['brief_text'] = cached.get('brief_text') or None
        if os.path.exists(tidy_csv):
            try:
                td = pd.read_csv(tidy_csv)
                try:
                    cached['tidy'] = td.fillna(' ').to_dict(orient='records')
                except Exception:
                    cached['tidy'] = td.to_dict(orient='records')
                cached['tidy_df'] = td
            except Exception:
                cached['tidy_df'] = None
        if os.path.exists(detailed_csv):
            try:
                df = pd.read_csv(detailed_csv)
                try:
                    cached['detailed'] = df.fillna(' ').to_dict(orient='records')
                except Exception:
                    cached['detailed'] = df.to_dict(orient='records')
                cached['detailed_df'] = df
            except Exception:
                cached['detailed_df'] = None
        return cached
    except Exception:
        return {}


def load_persisted_prices():
    """Discover and load persisted price maps from common output locations.

    Returns a dict mapping ticker -> price-dict (may be empty).
    """
    out = {}
    try:
        cand_dirs = [Path(OUT_ROOT), Path('/app/outputs'), Path(PROJECT_ROOT) / 'outputs', Path(DASH_ROOT) / 'outputs', Path('outputs')]
        for d in cand_dirs:
            try:
                if not d or not d.exists():
                    continue
                for price_fn in ('prices_monthly.json', 'prices_weekly.json'):
                    pf = d / price_fn
                    if not pf.exists():
                        continue
                    try:
                        with pf.open('r', encoding='utf-8') as _pf:
                            pj = json.load(_pf)
                        pmap = pj.get('prices') if isinstance(pj, dict) else None
                        if isinstance(pmap, dict) and pmap:
                            out.update(pmap)
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return out