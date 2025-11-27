"""Monthly Picks tab - Dash version exactly matching Flask styling.

Matches monthly_picks_flask.py output including:
- 6 summary boxes (Total Picks, Investment, P/L, ROI%, Winners, Losers)
- 20 stocks (not 200)
- Same columns, colors, styling
"""

import os
import logging
import pandas as pd
import time
import json
from datetime import datetime
from dash import dcc, html, Input, Output, State, dash_table, no_update
from dash.exceptions import PreventUpdate
from financial_dashboard import _shared as SH
from pathlib import Path

logger = logging.getLogger(__name__)

INVESTMENT_PER_STOCK = 1000.0  # Must match Flask version exactly
ATTACHED_MONTHLY_PATH = os.environ.get('ATTACHED_MONTHLY_PATH') or None

# PHASE 4C: API RATE LIMIT FIX - Add caching to prevent excessive API calls
_PICKS_CACHE = {
    'data': None,
    'timestamp': None,
    'ttl': 300  # 5 minutes - prevents rate limit exhaustion
}

# Prevent duplicate monthly price fetch jobs
_MONTHLY_PRICES_JOB = {
    'job_id': None,
    'tickers': None,
    'started_at': None
}
_MP_LAST_LOADED = None


def _background_fetch_monthly_prices(tickers, lookback_days=30, investment_per_ticker=INVESTMENT_PER_STOCK):
    """Background job to fetch monthly pick prices and populate SH.RESULTS_CACHE."""
    try:
        logger.info(f"[monthly-prices-job] Starting price fetch for {tickers}")
        from utils.price_client import PriceClient
        # Use purpose-specific Alpaca key for monthly fetches when available
        pc = PriceClient(alpaca_key_id=os.getenv('ALPACA_KEY_MONTHLY'), alpaca_secret=os.getenv('ALPACA_SECRET_MONTHLY'))
        # Persisted output path so UI can read cached results without hitting providers
        try:
            out_dir = getattr(SH, 'OUT_ROOT', None) or os.path.join(os.path.dirname(__file__), '..', 'outputs')
            out_path = os.path.join(out_dir, 'prices_monthly.json')
        except Exception:
            out_path = None
        fetched = pc.get_prices(tickers, lookback_days=lookback_days, investment_per_ticker=investment_per_ticker, save_to_path=out_path)
        try:
            if not isinstance(getattr(SH, 'RESULTS_CACHE', None), dict):
                SH.RESULTS_CACHE = {'results': None, 'loaded_at': None}
        except Exception:
            pass
        results = SH.RESULTS_CACHE.get('results') or {}
        prices_map = results.get('prices') or {}
        for t, val in (fetched or {}).items():
            prices_map[t] = {
                'current_price': val.get('current_price'),
                'daily_change': val.get('daily_change'),
                'start_price': val.get('start_price') or val.get('month_start_price'),
                'profit_loss': val.get('profit_loss'),
                'source': val.get('source') or 'Live'
            }
        results['prices'] = prices_map
        SH.RESULTS_CACHE['results'] = results
        SH.RESULTS_CACHE['loaded_at'] = time.time()
        logger.info(f"[monthly-prices-job] Stored {len(prices_map)} tickers into RESULTS_CACHE")
        # Also persist a lightweight prices JSON under OUT_ROOT for quick UI reads
        try:
            if out_path:
                with open(out_path, 'w', encoding='utf-8') as _f:
                    json.dump({'prices': prices_map, 'generated_at': time.time()}, _f, default=str)
        except Exception:
            logger.exception("Failed to persist monthly prices to disk")
        return {'ok': True, 'count': len(prices_map)}
    except Exception as e:
        logger.exception(f"[monthly-prices-job] failed: {e}")
        return {'ok': False, 'error': str(e)}


def _find_latest_monthly_picks():
    """Find the most recent monthly picks CSV."""
    if ATTACHED_MONTHLY_PATH and os.path.exists(ATTACHED_MONTHLY_PATH):
        logger.info(f"Using ATTACHED_MONTHLY_PATH: {ATTACHED_MONTHLY_PATH}")
        return ATTACHED_MONTHLY_PATH

    try:
        dash_root = SH.DASH_ROOT
    except Exception as e:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_root = os.path.dirname(base_dir)
        logger.info(f"SH.DASH_ROOT not available ({e}), using derived path: {dash_root}")

    import glob
    import re
    from datetime import datetime

    patterns = ['models/**/picks_*.csv', 'picks/picks_*.csv', 'models/**/monthlypicks*.csv']
    candidates = []
    for pattern in patterns:
        path = os.path.join(dash_root, pattern)
        found = glob.glob(path, recursive=True)
        candidates.extend(found)
    
    if not candidates:
        logger.warning(f"No candidates found in {dash_root} with patterns {patterns}")
        # Fallback: check canonical cache directory (populated by _shared.ensure_canonical_cache)
        try:
            cache_dir = getattr(SH, 'CANONICAL_CACHE_DIR', None)
            if cache_dir:
                p = Path(cache_dir)
                if p.exists():
                    cache_candidates = list(p.glob('**/picks_*.csv')) + list(p.glob('**/monthlypicks*.csv')) + list(p.glob('**/picks_monthly*.csv'))
                    if cache_candidates:
                        cache_candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        selected = str(cache_candidates[0])
                        logger.info(f"Selected monthly picks file from canonical cache: {selected}")
                        return selected
        except Exception:
            logger.debug('Fallback search in CANONICAL_CACHE_DIR failed', exc_info=True)
        return None

    def _parse_date_from_name(path):
        filename = os.path.basename(path)
        m_yyyymmdd = re.search(r'(\d{8})', filename)
        if m_yyyymmdd:
            try: return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except ValueError: pass
        return None

    def _in_full_run(p):
        return ('models' + os.sep + 'full_run') in p or '/full_run/' in p or '\\full_run\\' in p

    def _is_picks_prefix(p):
        return os.path.basename(p).lower().startswith('picks_')

    def _sort_key(p):
        parsed = _parse_date_from_name(p) or datetime.min.date()
        mtime = os.path.getmtime(p)
        return (_is_picks_prefix(p), _in_full_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    selected = candidates[0]
    logger.info(f"Selected monthly picks file: {selected}")
    return selected


def format_cell(value, col_name, is_currency=True, is_percent=False):
    """
    Format a cell value with data attributes for robust testing.
    Returns dict with 'display', 'value', and 'label' keys.
    """
    if value is None or value == 'N/A' or (isinstance(value, float) and pd.isna(value)):
        return {
            "display": "Data Unavailable",
            "value": "",
            "label": "Data Unavailable"
        }
    
    try:
        if is_currency:
            num_val = float(value)
            return {
                "display": f"${num_val:,.2f}",
                "value": f"{num_val:.2f}",
                "label": f"${num_val:,.2f}"
            }
        elif is_percent:
            num_val = float(value)
            return {
                "display": f"{num_val:+.2f}%",
                "value": f"{num_val:.2f}",
                "label": f"{num_val:+.2f}%"
            }
        else:
            return {
                "display": str(value),
                "value": str(value),
                "label": str(value)
            }
    except (ValueError, TypeError):
        return {
            "display": "Data Unavailable",
            "value": "",
            "label": "Data Unavailable"
        }


def _load_and_enrich_picks():
    """Load picks CSV and enrich with live price data.
    
    PHASE 4C: Now includes aggressive caching (5min TTL) to prevent API rate limit exhaustion.
    Without caching, each tab switch makes 40+ API calls (20 tickers × 2 endpoints).
    """
    import time
    
    # PHASE 4C: Check cache first
    if _PICKS_CACHE['data'] is not None and _PICKS_CACHE['timestamp'] is not None:
        age = time.time() - _PICKS_CACHE['timestamp']
        if age < _PICKS_CACHE['ttl']:
            logger.info(f"✅ CACHE HIT: Using cached monthly picks (age: {age:.1f}s / TTL: {_PICKS_CACHE['ttl']}s)")
            return _PICKS_CACHE['data']
        else:
            logger.info(f"⏰ CACHE EXPIRED: Age {age:.1f}s exceeds TTL {_PICKS_CACHE['ttl']}s")
    
    logger.info("⏳ CACHE MISS: Fetching fresh monthly picks data with API calls...")
    
    def format_price(val):
        """Format price as currency string (legacy - kept for backward compat)."""
        if val == 'N/A' or val is None or (isinstance(val, float) and pd.isna(val)):
            return 'N/A'
        try:
            return f"${float(val):,.2f}"
        except (ValueError, TypeError):
            return 'N/A'
    
    def format_percent(val):
        """Format value as percentage string (legacy - kept for backward compat)."""
        if val == 'N/A' or val is None or (isinstance(val, float) and pd.isna(val)):
            return 'N/A'
        try:
            num = float(val)
            return f"{num:+.2f}%"
        except (ValueError, TypeError):
            return 'N/A'
    
    try:
        # First attempt: read from Postgres via utils.db_utils (DB-first)
        try:
            from utils import db_utils
            engine = db_utils._DB.get_engine()
            if engine is not None:
                query = "SELECT date, ticker, score FROM picks WHERE pick_type='monthly' ORDER BY date DESC LIMIT 20"
                try:
                    rows = pd.read_sql_query(query, engine)
                except Exception:
                    rows = None
            else:
                rows = None

            if isinstance(rows, pd.DataFrame) and not rows.empty:
                df = rows.copy()
                # Normalize date and ticker
                if 'date' in df.columns:
                    try:
                        df['date'] = pd.to_datetime(df['date'])
                    except Exception:
                        df['date'] = pd.to_datetime(df['date'], errors='coerce')
                else:
                    df['date'] = pd.NaT
                if 'ticker' not in df.columns:
                    return None, 'DB: no ticker column', None

                # Ensure required helper columns exist
                df['sector'] = df.get('sector', '')
                df['industry'] = df.get('industry', '')
                df['market_cap'] = df.get('market_cap', 0)
                df['volume'] = df.get('volume', 0)

                # Limit to 20 and add rank
                df = df.head(20)
                df.insert(0, 'rank', range(1, len(df) + 1))

                tickers = df['ticker'].tolist()
                # Do not perform blocking live fetches here; prefer server-side cache.
                price_data = {}
                try:
                    cached_results = (SH.RESULTS_CACHE.get('results') if isinstance(getattr(SH, 'RESULTS_CACHE', None), dict) else None)
                    cached_prices = (cached_results.get('prices') if isinstance(cached_results, dict) else None) or {}
                    # If no cached prices in memory, try to read persisted JSON from OUT_ROOT
                    try:
                        if not cached_prices:
                            try:
                                persisted = SH.load_persisted_prices()
                                if persisted:
                                    cached_prices = persisted
                                    try:
                                        SH.RESULTS_CACHE['results'] = {'prices': cached_prices}
                                        SH.RESULTS_CACHE['loaded_at'] = time.time()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass
                    for t in tickers:
                        entry = cached_prices.get(t) or {}
                        price_data[t] = {
                            'current_price': entry.get('current_price') or 'N/A',
                            'daily_change': entry.get('daily_change') or 'N/A',
                            'start_price': entry.get('start_price') or entry.get('month_start_price') or 'N/A',
                            'profit_loss': entry.get('profit_loss') or 'N/A',
                            'source': entry.get('source') or ('Loading' if not entry else 'Local')
                        }
                except Exception:
                    price_data = {}

                df['current_price'] = df['ticker'].map(lambda t: format_price(price_data.get(t, {}).get('current_price', 'N/A')))
                df['daily_change'] = df['ticker'].map(lambda t: format_percent(price_data.get(t, {}).get('daily_change', 'N/A')))
                df['month_start_price'] = df['ticker'].map(lambda t: format_price(price_data.get(t, {}).get('start_price', 'N/A')))
                df['profit_loss'] = df['ticker'].map(lambda t: format_price(price_data.get(t, {}).get('profit_loss', 'N/A')))

                summary = {
                    'total': len(tickers),
                    'total_spent': f"{len(tickers) * INVESTMENT_PER_STOCK:,.0f}",
                    'total_pl': f"{sum([float(price_data.get(t, {}).get('profit_loss', 0) or 0) for t in tickers]):+.2f}",
                    'roi': f"0.00",
                    'csv_path': None,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }

                # PHASE 4C: Update cache with DB result
                result = (df, None, summary)
                _PICKS_CACHE['data'] = result
                _PICKS_CACHE['timestamp'] = time.time()
                logger.info(f"✅ CACHED: Monthly picks data (DB source) saved for {_PICKS_CACHE['ttl']}s")
                
                return result
        except Exception:
            logger.debug('Monthly Picks: DB read failed or DB unavailable; falling back to CSV')

        # Fallback: load from CSV
        csv_path = _find_latest_monthly_picks()
        if not csv_path:
            return None, "No monthly picks CSV found", None

        logger.info(f"Loading monthly picks from: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # PHASE 18B: ML Integration - Map CSV columns to match Weekly Picks schema
        # This ensures Monthly Picks displays ML scores like Weekly Picks
        if 'composite' in df.columns:
            # composite is the combined ML score (0-1 scale) - scale to 0-100
            df['combined_score'] = df['composite'] * 100
            df['score'] = df['combined_score']  # Backward compat
            
            # Derive component scores from available columns
            if 'r1m' in df.columns:
                # r1m is 1-month momentum return (0-1 scale) - use as momentum score
                df['momentum_score'] = df['r1m'] * 100
            else:
                df['momentum_score'] = df['combined_score'] * 0.5  # Fallback: 50% of combined
            
            if 'ma50_vs200' in df.columns:
                # ma50_vs200 is technical indicator (0-1 scale) - use as fundamental score
                df['fundamental_score'] = df['ma50_vs200'] * 100
            else:
                df['fundamental_score'] = df['combined_score'] * 0.3  # Fallback: 30% of combined
            
            # Sentiment score - derived as residual to match combined score
            df['sentiment_score'] = df['combined_score'] - (df['momentum_score'] * 0.5 + df['fundamental_score'] * 0.3) / 0.8
            df['sentiment_score'] = df['sentiment_score'].clip(lower=0, upper=100)
            
            logger.info("✅ PHASE 18B: Mapped CSV composite score to ML schema (combined_score, momentum_score, sentiment_score, fundamental_score)")
        else:
            logger.warning("⚠️ CSV missing 'composite' column - cannot map to ML schema")
            df['combined_score'] = 0
            df['score'] = 0
            df['momentum_score'] = 0
            df['sentiment_score'] = 0
            df['fundamental_score'] = 0
        
        # Data quality fix - replace N/A values with defaults
        if isinstance(df, pd.DataFrame):
            df = df.fillna({
                'sector': 'Unknown',
                'industry': 'Unknown',
                'market_cap': 0,
                'volume': 0,
                'price': 0.0,
                'change_pct': 0.0
            })
            # Fill remaining numeric columns with 0
            numeric_cols = df.select_dtypes(include=['number']).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            # Fill remaining text columns with empty string (no N/A placeholders)
            object_cols = df.select_dtypes(include=['object']).columns
            df[object_cols] = df[object_cols].fillna('')

        
        # Limit to 20 tickers (matching Flask version)
        df = df.head(20)
        
        # Add rank column if not present
        if 'rank' not in df.columns:
            df.insert(0, 'rank', range(1, len(df) + 1))
        
        # Get tickers
        tickers = df['ticker'].tolist() if 'ticker' in df.columns else []

        # PHASE 18B FIX: Trigger background price fetch if prices not in cache OR incomplete
        try:
            cached_results = (SH.RESULTS_CACHE.get('results') if isinstance(getattr(SH, 'RESULTS_CACHE', None), dict) else None)
            cached_prices = (cached_results.get('prices') if isinstance(cached_results, dict) else None) or {}
            
            # Check if we have complete prices for these tickers (must have month_start_price)
            missing_or_incomplete = []
            for t in tickers:
                if t not in cached_prices:
                    missing_or_incomplete.append(t)
                else:
                    entry = cached_prices.get(t, {})
                    # Check if month_start_price is missing or invalid
                    month_start = entry.get('month_start_price')
                    if month_start is None or month_start == '-' or month_start == 'N/A' or (isinstance(month_start, str) and month_start.strip() == ''):
                        missing_or_incomplete.append(t)
            
            if missing_or_incomplete:
                logger.info(f"🔄 {len(missing_or_incomplete)}/{len(tickers)} tickers need price fetch (missing or incomplete), triggering background fetch...")
                # Trigger background fetch in a thread to avoid blocking
                import threading
                thread = threading.Thread(target=_background_fetch_monthly_prices, args=(tickers, 30, INVESTMENT_PER_STOCK))
                thread.daemon = True
                thread.start()
                logger.info(f"✅ Background price fetch started for {len(tickers)} tickers")
            else:
                logger.info(f"✅ All {len(tickers)} tickers have complete cached prices, skipping fetch")
        except Exception as e:
            logger.warning(f"⚠️ Could not trigger background price fetch: {e}")

        # Attempt to read prices from server-side RESULTS_CACHE populated by background jobs.
        price_data = {}
        try:
            cached_results = (SH.RESULTS_CACHE.get('results') if isinstance(getattr(SH, 'RESULTS_CACHE', None), dict) else None)
            cached_prices = (cached_results.get('prices') if isinstance(cached_results, dict) else None) or {}
            for t in tickers:
                entry = cached_prices.get(t) or {}
                price_data[t] = {
                    'current_price': entry.get('current_price', 'N/A'),
                    'daily_change': entry.get('daily_change', 'N/A'),
                    'start_price': entry.get('start_price') or entry.get('month_start_price') or 'N/A',
                    'profit_loss': entry.get('profit_loss', 'N/A'),
                    'source': entry.get('source') or ('Loading' if not entry else 'Local')
                }
        except Exception:
            price_data = {}
        # Ensure DataFrame has expected price columns before selecting display columns
        try:
            df['current_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', 'N/A'))
            df['daily_change'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', 'N/A'))
            df['month_start_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('start_price', 'N/A'))
            df['profit_loss'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('profit_loss', 'N/A'))
        except Exception:
            df['current_price'] = 'N/A'
            df['daily_change'] = 'N/A'
            df['month_start_price'] = 'N/A'
            df['profit_loss'] = 'N/A'
        
        # PHASE 18B: Select columns to display - INCLUDE ML SCORES for parity with Weekly Picks
        display_cols = [
            'rank', 
            'ticker', 
            'combined_score',     # ML combined score
            'momentum_score',     # ML momentum component
            'sentiment_score',    # ML sentiment component
            'fundamental_score',  # ML fundamental component
            'current_price', 
            'daily_change', 
            'month_start_price', 
            'profit_loss'
        ]
        
        # Add other CSV columns except excluded ones (composite, r1m, ma50_vs200 already used in scoring)
        csv_cols = [c for c in df.columns if c not in [
            'rank', 'ticker', 'score', 'pred_rank', 
            'current_price', 'daily_change', 'month_start_price', 'profit_loss',
            'combined_score', 'momentum_score', 'sentiment_score', 'fundamental_score',
            'composite', 'r1m', 'ma50_vs200'  # Exclude source columns used in scoring
        ]]
        display_cols.extend(csv_cols)
        
        # Ensure only columns that exist in df are selected
        display_cols = [c for c in display_cols if c in df.columns]
        df = df[display_cols]
        
        # Calculate summary stats (matching Flask exactly)
        total = len(tickers)
        total_spent = total * INVESTMENT_PER_STOCK
        
        # Calculate total P/L, winners, losers
        total_pl = 0
        winners = 0
        losers = 0
        for ticker in tickers:
            pl = price_data.get(ticker, {}).get('profit_loss', 'N/A')
            if pl != 'N/A':
                try:
                    pl_val = float(pl)
                    total_pl += pl_val
                    if pl_val > 0:
                        winners += 1
                    elif pl_val < 0:
                        losers += 1
                except:
                    pass
        
        roi = (total_pl / total_spent * 100) if total_spent > 0 else 0
        
        summary = {
            'total': total,
            'total_spent': f"{total_spent:,.0f}",
            'total_pl': f"{total_pl:+,.2f}",
            'roi': f"{roi:+.2f}",
            'winners': winners,
            'losers': losers,
            'csv_path': csv_path,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # PHASE 4C: Update cache with fresh data
        result = (df, None, summary)
        _PICKS_CACHE['data'] = result
        _PICKS_CACHE['timestamp'] = time.time()
        logger.info(f"✅ CACHED: Monthly picks data saved for {_PICKS_CACHE['ttl']}s")
        
        return result
        
    except Exception as e:
        logger.error(f"Error loading monthly picks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}", None


def _build_datatable(df):
    """Build Dash DataTable from picks dataframe."""
    df = df.head(20)
    # PHASE 18B: Include ML scores for parity with Weekly Picks
    core_cols = [
        'rank', 'ticker',
        'combined_score', 'momentum_score', 'sentiment_score', 'fundamental_score',  # ML scores
        'current_price', 'daily_change', 'month_start_price', 'profit_loss'
    ]
    df_display = df[[col for col in core_cols if col in df.columns]].copy()
    
    # Format ML scores (0-100 scale with 1 decimal)
    for ml_col in ['combined_score', 'momentum_score', 'sentiment_score', 'fundamental_score']:
        if ml_col in df_display.columns:
            df_display[ml_col] = df_display[ml_col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    
    # Format price/change columns
    # Preserve raw numeric values for robust testing
    df_display['current_price_raw'] = df_display['current_price']
    df_display['daily_change_raw'] = df_display['daily_change']
    df_display['month_start_price_raw'] = df_display['month_start_price']
    df_display['profit_loss_raw'] = df_display['profit_loss']

    # Also include a hidden JSON blob of the raw prices derived from the
    # DataFrame itself. This ensures automated tests can read authoritative
    # numeric values even when SH.RESULTS_CACHE is empty for this process.
    try:
        import json as _json
        price_map = {}
        for _, r in df_display[['ticker', 'current_price_raw', 'month_start_price_raw', 'profit_loss_raw']].iterrows():
            t = r.get('ticker') if 'ticker' in r else None
            if not t:
                continue
            price_map[t] = {
                'current_price': r.get('current_price_raw'),
                'month_start_price': r.get('month_start_price_raw'),
                'profit_loss': r.get('profit_loss_raw')
            }
        hidden_json = html.Pre(_json.dumps({'prices': price_map}, default=str), id='mp-prices-json', style={'display': 'none'})
    except Exception:
        hidden_json = html.Div(id='mp-prices-json', style={'display': 'none'})

    # Format price/change columns
    df_display['current_price'] = df_display['current_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    df_display['daily_change'] = df_display['daily_change'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
    df_display['month_start_price'] = df_display['month_start_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    df_display['profit_loss'] = df_display['profit_loss'].apply(lambda x: f"${x:+.2f}" if pd.notna(x) else "N/A")

    df_display = df_display.rename(columns={
        'rank': 'Rank',
        'ticker': 'Ticker',
        'combined_score': 'Combined',
        'momentum_score': 'Momentum',
        'sentiment_score': 'Sentiment',
        'fundamental_score': 'Fundamental',
        'current_price': 'Current Price',
        'daily_change': 'Daily Change',
        'month_start_price': 'Month Start',
        'profit_loss': 'Profit/Loss',
        'current_price_raw': 'Current Price Raw',
        'daily_change_raw': 'Daily Change Raw',
        'month_start_price_raw': 'Month Start Raw',
        'profit_loss_raw': 'Profit/Loss Raw'
    })
    
    return dash_table.DataTable(
        id='monthly-table',
        columns=[{"name": col, "id": col} for col in df_display.columns],
        data=df_display.to_dict('records'),
        hidden_columns=['Current Price Raw', 'Daily Change Raw', 'Month Start Raw', 'Profit/Loss Raw'],
        style_table={'overflowX': 'auto', 'marginTop': '20px'},
        style_header={'backgroundColor': '#333', 'color': '#e0e0e0', 'fontWeight': 'bold'},
        style_cell={'backgroundColor': '#2c2c2c', 'color': '#e0e0e0'},
        style_data_conditional=[
            {'if': {'filter_query': '{Profit/Loss} contains "+"', 'column_id': 'Profit/Loss'}, 'color': '#4CAF50', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Profit/Loss} contains "-"', 'column_id': 'Profit/Loss'}, 'color': '#ff6b6b', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Daily Change} contains "+"', 'column_id': 'Daily Change'}, 'color': '#4CAF50'},
            {'if': {'filter_query': '{Daily Change} contains "-"', 'column_id': 'Daily Change'}, 'color': '#ff6b6b'}
        ],
        export_format='xlsx',
        sort_action='native',
        filter_action='native',
        page_size=20
    )


def layout():
    """Create layout for Monthly Picks tab.
    
    NOTE: Pre-loads DataTable during server-side render (layout creation).
    Callback handles refresh button clicks only.
    """
    # Load data during layout creation (server-side render)
    df, error, summary = _load_and_enrich_picks()
    
    # Generate initial content
    if error:
        initial_content = html.Div([
            html.P(f"⚠️ {error}", style={'color': '#ff6b6b', 'marginTop': '20px'}),
            html.P(summary or "Unable to load picks data", style={'color': '#888'})
        ])
    elif df is not None and not df.empty:
        initial_content = _build_datatable(df)
    else:
        initial_content = html.Div("⚠️ No picks data available", style={'color': '#888', 'marginTop': '20px'})
    
    # Build hidden JSON of prices from server-side DataFrame so tests can read
    try:
        import json as _json
        hidden_prices = {}
        if df is not None and hasattr(df, 'iterrows') and 'ticker' in df.columns:
            for _, row in df.iterrows():
                t = row.get('ticker')
                if not t:
                    continue
                hidden_prices[t] = {
                    'current_price': row.get('current_price') if 'current_price' in df.columns else None,
                    'month_start_price': row.get('month_start_price') if 'month_start_price' in df.columns else None,
                    'profit_loss': row.get('profit_loss') if 'profit_loss' in df.columns else None
                }
        hidden_json = html.Pre(_json.dumps({'prices': hidden_prices}, default=str), id='mp-prices-json', style={'display': 'none'})
    except Exception:
        hidden_json = html.Div(id='mp-prices-json', style={'display': 'none'})

    return html.Div([
        # Header
        html.H1("📊 Monthly Stock Picks", style={
            'color': '#2196F3',
            'fontFamily': 'Arial, sans-serif',
            'marginBottom': '10px'
        }),
        
        html.Div([
            "✨ Using ML composite scores from: ",
            html.Code("models/full_run/picks_20251001.csv", style={'color': '#4CAF50'}),
            " — Click Regenerate to create new picks"
        ], style={
            'color': '#FFD700',
            'fontWeight': '600',
            'marginTop': '6px',
            'marginBottom': '20px'
        }),
        
        # Action buttons
        html.Div([
            html.Button("🔄 Refresh Prices", id='mp-refresh-btn', n_clicks=0, style={
                'padding': '10px 20px',
                'background': '#2196F3',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'marginRight': '10px'
            }),
            html.Button("🔮 Regenerate Picks", id='mp-regenerate-btn', n_clicks=0, style={
                'padding': '10px 20px',
                'background': '#9C27B0',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'fontSize': '14px'
            }),
        ], style={'marginBottom': '20px'}),
        
        # Container with pre-loaded content (server-side render)
        html.Div(initial_content, id='mp-content'),
        
    # Auto-refresh interval (checks for cache updates and triggers refresh)
    dcc.Interval(id='mp-auto-refresh', interval=5000, n_intervals=0),

    # Store for data
    dcc.Store(id='mp-data-store', data=df.to_dict('records') if df is not None and not df.empty else None)
        
    ], style={
        'fontFamily': 'Arial, sans-serif',
        'padding': '20px',
        'minHeight': '100vh'
    })


def register_callbacks(app, SH=None):
    """Register callbacks."""
    # Idempotency guard
    if getattr(app, '_monthly_picks_callbacks_registered', False):
        logger.info("🔒 Monthly Picks callbacks already registered, skipping")
        return
    setattr(app, '_monthly_picks_callbacks_registered', True)
    
    # Refresh callback - fires only when refresh button clicked
    @app.callback(
        [Output('mp-data-store', 'data'),
         Output('mp-content', 'children')],
        Input('mp-refresh-btn', 'n_clicks'),
        Input('mp-auto-refresh', 'n_intervals'),
        prevent_initial_call=False  # allow interval to trigger; we'll guard inside
    )
    def refresh_picks(n_clicks, n_intervals):
        """Refresh picks data when button clicked or when auto-refresh interval fires."""
        # Guard: do nothing on initial render unless user clicked or interval fired
        if not n_clicks and (not n_intervals or n_intervals == 0):
            raise PreventUpdate

        logger.info(f"🔵 Monthly Picks refresh triggered: n_clicks={n_clicks}, n_intervals={n_intervals}")
        print(f"[MonthlyPicks] Refresh triggered! n_clicks={n_clicks}, n_intervals={n_intervals}", flush=True)
        # If interval triggered, only continue when cache 'loaded_at' changes
        try:
            global _MP_LAST_LOADED
            cache_obj = getattr(SH, 'RESULTS_CACHE', None)
            loaded_at = None
            if isinstance(cache_obj, dict):
                loaded_at = cache_obj.get('loaded_at')
            if not n_clicks and n_intervals and n_intervals > 0:
                if not loaded_at or loaded_at == _MP_LAST_LOADED:
                    raise PreventUpdate
            if loaded_at:
                _MP_LAST_LOADED = loaded_at
        except PreventUpdate:
            raise
        except Exception:
            logger.exception('Error while checking RESULTS_CACHE loaded_at for monthly picks')
        try:
            df, error, summary = _load_and_enrich_picks()
            
            if error:
                return None, html.Div(error, style={'color': '#ff6b6b', 'padding': '20px'})
            
            if df is None or df.empty:
                return None, html.Div("No data available", style={'color': '#ff6b6b', 'padding': '20px'})
            
            # Build summary boxes (6 boxes matching Flask exactly)
            summary_boxes = html.Div([
                html.Div([
                    html.H3("📈 Total Picks", style={'color': '#2196F3', 'fontSize': '16px', 'margin': '0 0 10px 0'}),
                    html.Div(str(summary['total']), style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0'})
                ], style={'background': '#2c2c2c', 'border': '2px solid #444', 'borderRadius': '8px', 'padding': '20px', 'minWidth': '200px', 'flex': '1'}),
                
                html.Div([
                    html.H3("💰 Total Investment", style={'color': '#2196F3', 'fontSize': '16px', 'margin': '0 0 10px 0'}),
                    html.Div(f"${summary['total_spent']}", style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0'})
                ], style={'background': '#2c2c2c', 'border': '2px solid #444', 'borderRadius': '8px', 'padding': '20px', 'minWidth': '200px', 'flex': '1'}),
                
                html.Div([
                    html.H3("📊 Total P/L", style={'color': '#2196F3', 'fontSize': '16px', 'margin': '0 0 10px 0'}),
                    html.Div(f"${summary['total_pl']}", style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0', 'color': '#4CAF50' if summary['total_pl'].startswith('+') else '#ff6b6b'})
                ], style={'background': '#2c2c2c', 'border': '2px solid #444', 'borderRadius': '8px', 'padding': '20px', 'minWidth': '200px', 'flex': '1'}),
                
                html.Div([
                    html.H3("🎯 Total ROI %", style={'color': '#2196F3', 'fontSize': '16px', 'margin': '0 0 10px 0'}),
                    html.Div(f"{summary['roi']}%", style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0', 'color': '#4CAF50' if summary['roi'].startswith('+') else '#ff6b6b'})
                ], style={'background': '#2c2c2c', 'border': '2px solid #444', 'borderRadius': '8px', 'padding': '20px', 'minWidth': '200px', 'flex': '1'}),
                
                html.Div([
                    html.H3("📈 Winners", style={'color': '#2196F3', 'fontSize': '16px', 'margin': '0 0 10px 0'}),
                    html.Div(str(summary['winners']), style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0', 'color': '#4CAF50'})
                ], style={'background': '#2c2c2c', 'border': '2px solid #444', 'borderRadius': '8px', 'padding': '20px', 'minWidth': '200px', 'flex': '1'}),
                
                html.Div([
                    html.H3("📉 Losers", style={'color': '#2196F3', 'fontSize': '16px', 'margin': '0 0 10px 0'}),
                    html.Div(str(summary['losers']), style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0', 'color': '#ff6b6b'})
                ], style={'background': '#2c2c2c', 'border': '2px solid #444', 'borderRadius': '8px', 'padding': '20px', 'minWidth': '200px', 'flex': '1'}),
            ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px', 'flexWrap': 'wrap'})
            
            # Build info line (matching Flask styling)
            info_line = html.Div([
                html.Div(f"Investment per stock: $1,000 | P/L calculated from month start", 
                        style={'color': '#888', 'fontSize': '12px', 'margin': '10px 0'}),
                html.Div([
                    html.Span(f"CSV file: {os.path.basename(summary['csv_path'])}", style={'marginRight': '20px'}),
                    html.Span(f"Last updated: {summary['update_time']}")
                ], style={'color': '#888', 'fontSize': '12px', 'marginTop': '20px'})
            ])
            
            # 🔧 REMEDIATION: Build Dash DataTable (not HTML table) for paste functionality
            logger.info(f"🔵 [MonthlyPicks] Rendering {len(df)} rows with columns: {list(df.columns)}")
            print(f"[MonthlyPicks] DataTable callback fired - building table with {len(df)} rows", flush=True)
            
            # Prepare display DataFrame
            core_cols = ['rank', 'ticker', 'current_price', 'daily_change', 'month_start_price', 'profit_loss']
            df_display = df[[col for col in core_cols if col in df.columns]].copy()
            # Defensive re-map: prefer freshest numeric values from SH.RESULTS_CACHE
            try:
                cached_results = (SH.RESULTS_CACHE.get('results') if isinstance(getattr(SH, 'RESULTS_CACHE', None), dict) else None) or {}
                cached_prices = (cached_results.get('prices') if isinstance(cached_results, dict) else None) or {}
                for col in ['current_price', 'daily_change', 'month_start_price', 'profit_loss']:
                    if 'ticker' in df_display.columns:
                        def _map_val(t, c=col):
                            entry = cached_prices.get(t, {})
                            if c == 'month_start_price':
                                return entry.get('start_price') if entry.get('start_price') is not None else entry.get('month_start_price')
                            return entry.get(c)
                        df_display[col] = df_display['ticker'].map(lambda t: _map_val(t))
                # coerce numeric
                for col in ['current_price', 'daily_change', 'month_start_price', 'profit_loss']:
                    if col in df_display.columns:
                        df_display[col] = pd.to_numeric(df_display[col], errors='coerce')
            except Exception:
                logger.exception('Failed to remap monthly prices from RESULTS_CACHE')
            
            # Preserve raw numeric values for robust testing
            df_display['current_price_raw'] = df_display['current_price']
            df_display['daily_change_raw'] = df_display['daily_change']
            df_display['month_start_price_raw'] = df_display['month_start_price']
            df_display['profit_loss_raw'] = df_display['profit_loss']

            # Construct hidden JSON from the DataFrame's raw columns so the
            # refresh callback returns a deterministic machine-readable blob
            # even if SH.RESULTS_CACHE isn't populated in this process.
            try:
                import json as _json
                price_map = {}
                for _, r in df_display[['ticker', 'current_price_raw', 'month_start_price_raw', 'profit_loss_raw']].iterrows():
                    t = r.get('ticker') if 'ticker' in r else None
                    if not t:
                        continue
                    price_map[t] = {
                        'current_price': r.get('current_price_raw'),
                        'month_start_price': r.get('month_start_price_raw'),
                        'profit_loss': r.get('profit_loss_raw')
                    }
                hidden_json = html.Pre(_json.dumps({'prices': price_map}, default=str), id='mp-prices-json', style={'display': 'none'})
            except Exception:
                hidden_json = html.Div(id='mp-prices-json', style={'display': 'none'})

            # Format data for display
            df_display['current_price'] = df_display['current_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
            df_display['daily_change'] = df_display['daily_change'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
            df_display['month_start_price'] = df_display['month_start_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
            df_display['profit_loss'] = df_display['profit_loss'].apply(lambda x: f"${x:+.2f}" if pd.notna(x) else "N/A")

            # Rename columns for display
            df_display = df_display.rename(columns={
                'rank': 'Rank',
                'ticker': 'Ticker',
                'current_price': 'Current Price',
                'daily_change': 'Daily Change',
                'month_start_price': 'Month Start',
                'profit_loss': 'Profit/Loss',
                'current_price_raw': 'Current Price Raw',
                'daily_change_raw': 'Daily Change Raw',
                'month_start_price_raw': 'Month Start Raw',
                'profit_loss_raw': 'Profit/Loss Raw'
            })
            
            table = dash_table.DataTable(
                id='monthly-table',
                columns=[{"name": col, "id": col} for col in df_display.columns],
                data=df_display.to_dict('records'),
                hidden_columns=['Current Price Raw', 'Daily Change Raw', 'Month Start Raw', 'Profit/Loss Raw'],
                style_table={
                    'overflowX': 'auto',
                    'marginTop': '20px'
                },
                style_header={
                    'backgroundColor': '#333',
                    'color': '#e0e0e0',
                    'fontWeight': 'bold',
                    'fontSize': '12px',
                    'padding': '12px',
                    'border': '1px solid #444'
                },
                style_cell={
                    'backgroundColor': '#2c2c2c',
                    'color': '#e0e0e0',
                    'fontSize': '13px',
                    'padding': '12px',
                    'border': '1px solid #444',
                    'textAlign': 'left'
                },
                style_data_conditional=[
                    # Highlight profit/loss cells
                    {
                        'if': {
                            'filter_query': '{Profit/Loss} contains "+"',
                            'column_id': 'Profit/Loss'
                        },
                        'color': '#4CAF50',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{Profit/Loss} contains "-"',
                            'column_id': 'Profit/Loss'
                        },
                        'color': '#ff6b6b',
                        'fontWeight': 'bold'
                    },
                    # Highlight daily change cells
                    {
                        'if': {
                            'filter_query': '{Daily Change} contains "+"',
                            'column_id': 'Daily Change'
                        },
                        'color': '#4CAF50'
                    },
                    {
                        'if': {
                            'filter_query': '{Daily Change} contains "-"',
                            'column_id': 'Daily Change'
                        },
                        'color': '#ff6b6b'
                    }
                ],
                # Enable copy/paste
                export_format='xlsx',
                export_headers='display',
                # Enable column sorting
                sort_action='native',
                # Enable filtering
                filter_action='native',
                page_size=20
            )
            
            logger.info(f"✅ [MonthlyPicks] DataTable created with {len(df_display)} rows")
            
            content = html.Div([
                summary_boxes,
                info_line,
                table,
                hidden_json
            ])
            
            return df.to_dict('records'), content
            
        except Exception as e:
            logger.error(f"Error in load_monthly_picks callback: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, html.Div(f"Error loading picks: {str(e)}", style={'color': '#ff6b6b', 'padding': '20px'})
    
    # Regenerate callback - runs ML model to create new picks
    @app.callback(
        Output('mp-content', 'children', allow_duplicate=True),
        Input('mp-regenerate-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def regenerate_picks(n_clicks):
        """Regenerate picks by running ML model."""
        logger.info(f"🔮 Monthly Picks regenerate clicked: n_clicks={n_clicks}")
        
        try:
            # Import picker modules
            from picker.universe import StockUniverse
            from picker.ensemble_picker import EnsemblePicker, save_monthly_picks
            from datetime import date
            
            # Get stock universe (S&P 500 + NASDAQ top stocks)
            universe = StockUniverse.get_combined_universe()
            logger.info(f"Using universe of {len(universe)} stocks")
            
            # Create picker with default weights
            picker = EnsemblePicker()
            
            # Generate picks (will take 30-60 seconds)
            logger.info("Generating monthly picks...")
            picks = picker.generate_monthly_picks(universe, n=20)
            
            # Save to database
            today = date.today()
            month_start = date(today.year, today.month, 1)
            save_monthly_picks(picks, month_start)
            
            # Clear cache to force refresh
            _PICKS_CACHE['data'] = None
            _PICKS_CACHE['timestamp'] = None
            
            # Reload data
            df, error, summary = _load_and_enrich_picks()
            
            if error:
                result_msg = html.Div([
                    html.Span("⚠️ ", style={'fontSize': '20px'}),
                    html.Span(f"Generator completed but error loading data: {error}", style={
                        'color': '#ff6b6b',
                        'fontSize': '14px'
                    })
                ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #ff6b6b'})
                return result_msg
            
            # Build new table
            new_table = _build_datatable(df)
            
            # Success message
            result_msg = html.Div([
                html.Div([
                    html.Span("✅ ", style={'fontSize': '20px'}),
                    html.Span(f"Successfully generated 20 new monthly picks!", style={
                        'color': '#4CAF50',
                        'fontWeight': 'bold',
                        'fontSize': '14px'
                    })
                ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #4CAF50', 'marginBottom': '20px'}),
                new_table
            ])
            
            return result_msg
            
        except Exception as e:
            logger.exception(f"Regenerate picks error: {e}")
            
            error_msg = html.Div([
                html.Span("❌ ", style={'fontSize': '20px'}),
                html.Span(f"Error generating picks: {str(e)}", style={
                    'color': '#ff6b6b',
                    'fontSize': '14px'
                })
            ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #ff6b6b'})
            
            return error_msg
