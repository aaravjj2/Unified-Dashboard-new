"""Weekly Picks tab - Dash version matching Flask styling and structure.

Clean implementation using utils.price_fetcher_weekly for live price data.
"""

import os
import logging
import pandas as pd
from datetime import datetime
import time
from dash import dcc, html, Input, Output, State, dash_table, no_update
from dash.exceptions import PreventUpdate
from financial_dashboard import _shared as SH
from pathlib import Path
from utils import db_utils

logger = logging.getLogger(__name__)

INVESTMENT_PER_STOCK = 250.0
ATTACHED_WEEKLY_PATH = os.environ.get('ATTACHED_WEEKLY_PATH') or None

# Simple in-process cache to avoid repeated heavy fetches during UI render
_PICKS_CACHE = {
    'data': None,
    'timestamp': None,
    'ttl': 300  # seconds
}

# Track background job for weekly price fetches to avoid duplicate scheduling
_WEEKLY_PRICES_JOB = {
    'job_id': None,
    'tickers': None,
    'started_at': None
}
_WP_LAST_LOADED = None


def _background_fetch_weekly_prices(tickers, lookback_days=7, investment_per_ticker=INVESTMENT_PER_STOCK):
    """Background job to fetch weekly pick prices and populate SH.RESULTS_CACHE and a persisted JSON file."""
    try:
        logger.info(f"[weekly-prices-job] Starting price fetch for {tickers}")
        from utils.price_client import PriceClient
        # Use purpose-specific Alpaca key for weekly fetches when available
        pc = PriceClient(alpaca_key_id=os.getenv('ALPACA_KEY_WEEKLY'), alpaca_secret=os.getenv('ALPACA_SECRET_WEEKLY'))

        try:
            out_dir = getattr(SH, 'OUT_ROOT', None) or os.path.join(os.path.dirname(__file__), '..', 'outputs')
            out_path = os.path.join(out_dir, 'prices_weekly.json')
        except Exception:
            out_path = None

        fetched = pc.get_prices(tickers, lookback_days=lookback_days, investment_per_ticker=investment_per_ticker, save_to_path=out_path)

        # Update shared cache
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
                'start_price': val.get('start_price') or val.get('week_start_price'),
                'profit_loss': val.get('profit_loss'),
                'source': val.get('source') or 'Live'
            }
        results['prices'] = prices_map
        SH.RESULTS_CACHE['results'] = results
        SH.RESULTS_CACHE['loaded_at'] = time.time()
        logger.info(f"[weekly-prices-job] Stored {len(prices_map)} tickers into RESULTS_CACHE")
        # Persist to disk as backup
        try:
            if out_path:
                import json
                with open(out_path, 'w', encoding='utf-8') as _f:
                    json.dump({'prices': prices_map, 'generated_at': time.time()}, _f, default=str)
        except Exception:
            logger.exception("Failed to persist weekly prices to disk")
        return {'ok': True, 'count': len(prices_map)}
    except Exception as e:
        logger.exception(f"[weekly-prices-job] failed: {e}")
        return {'ok': False, 'error': str(e)}

def format_cell(value, col_name, is_currency=True, is_percent=False):
    """
    Format a cell value with data attributes for robust testing.
    Returns dict with 'display', 'value', and 'label' keys.
    """
    if value is None or value == '-' or (isinstance(value, float) and pd.isna(value)):
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

ATTACHED_WEEKLY_PATH = os.environ.get('ATTACHED_WEEKLY_PATH') or None


def _find_latest_weekly_picks():
    """Find the most recent weekly picks CSV."""
    if ATTACHED_WEEKLY_PATH and os.path.exists(ATTACHED_WEEKLY_PATH):
        logger.info(f"Using ATTACHED_WEEKLY_PATH: {ATTACHED_WEEKLY_PATH}")
        return ATTACHED_WEEKLY_PATH

    try:
        dash_root = SH.DASH_ROOT
    except Exception as e:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_root = os.path.dirname(base_dir)
        logger.info(f"SH.DASH_ROOT not available ({e}), using derived path: {dash_root}")

    import glob
    import re
    from datetime import datetime

    patterns = ['models/**/picks_*.csv', 'models/**/weeklypicks*.csv', 'models/**/picks_weekly*.csv']
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
                    # Look for typical picks filenames inside the canonical cache
                    cache_candidates = list(p.glob('**/picks_*.csv')) + list(p.glob('**/weeklypicks*.csv')) + list(p.glob('**/picks_weekly*.csv'))
                    if cache_candidates:
                        cache_candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        selected = str(cache_candidates[0])
                        logger.info(f"Selected weekly picks file from canonical cache: {selected}")
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
        m_mmdd = re.search(r'weeklypicks(\d{4})', filename)
        if m_mmdd:
            try:
                mmdd_str = m_mmdd.group(1)
                today = datetime.now()
                file_date = datetime.strptime(f"{today.year}{mmdd_str}", '%Y%m%d')
                if file_date > today: file_date = file_date.replace(year=today.year - 1)
                return file_date.date()
            except ValueError: pass
        return None

    def _in_weekly_run(p):
        return ('models' + os.sep + 'weekly_run') in p or '/weekly_run/' in p or '\\weekly_run\\' in p

    def _is_picks_prefix(p):
        return os.path.basename(p).lower().startswith('picks_')

    def _sort_key(p):
        parsed = _parse_date_from_name(p) or datetime.min.date()
        mtime = os.path.getmtime(p)
        return (_is_picks_prefix(p), _in_weekly_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    selected = candidates[0]
    logger.info(f"Selected weekly picks file: {selected}")
    return selected


def _load_and_enrich_picks():
    """Load picks CSV and enrich with live price data."""
    import time
    
    # PHASE 4C: Check cache first to prevent excessive API calls
    if _PICKS_CACHE['data'] is not None and _PICKS_CACHE['timestamp'] is not None:
        age = time.time() - _PICKS_CACHE['timestamp']
        if age < _PICKS_CACHE['ttl']:
            logger.info(f"✅ CACHE HIT: Using cached weekly picks (age: {age:.1f}s)")
            return _PICKS_CACHE['data']
        else:
            logger.info(f"⏰ CACHE EXPIRED: Weekly picks age {age:.1f}s exceeds {_PICKS_CACHE['ttl']}s TTL")
    
    logger.info("⏳ CACHE MISS: Fetching fresh weekly picks data from DB/CSV + live prices...")
    
    try:
        # First attempt: read from Postgres via utils.db_utils (new table: weekly_picks_production)
        try:
            engine = db_utils._DB.get_engine()
            rows = None
            if engine is not None:
                # Query the latest week's picks from the production table
                query = """
                    SELECT
                        week_start_date AS date,
                        ticker,
                        rank,
                        combined_score,
                        momentum_score,
                        sentiment_score,
                        fundamental_score,
                        rationale,
                        generated_at
                    FROM weekly_picks_production
                    WHERE week_start_date = (
                        SELECT MAX(week_start_date) 
                        FROM weekly_picks_production 
                        WHERE week_start_date <= CURRENT_DATE
                    )
                    ORDER BY rank ASC
                """
                try:
                    rows = pd.read_sql_query(query, engine)
                except Exception:
                    rows = None
            else:
                rows = None

            if isinstance(rows, pd.DataFrame) and not rows.empty:
                df = rows.copy()
                # Ensure ticker column exists
                if 'ticker' not in df.columns:
                    return None, 'DB: no ticker column', None

                # Normalize columns expected downstream
                if 'date' in df.columns:
                    try:
                        df['date'] = pd.to_datetime(df['date'])
                    except Exception:
                        df['date'] = pd.to_datetime(df['date'], errors='coerce')
                else:
                    df['date'] = pd.NaT

                # map combined_score -> score for downstream compatibility
                if 'combined_score' in df.columns:
                    df['score'] = df['combined_score']
                elif 'score' not in df.columns:
                    df['score'] = None

                # Fill missing helper columns with defaults so downstream code can run
                df['sector'] = df.get('sector', '')
                df['industry'] = df.get('industry', '')
                df['market_cap'] = df.get('market_cap', 0)
                df['volume'] = df.get('volume', 0)

                # Limit to 20
                df = df.head(20)

                # Ensure rank exists
                if 'rank' not in df.columns:
                    df.insert(0, 'rank', range(1, len(df) + 1))

                tickers = df['ticker'].tolist()

                # Do not perform blocking live fetches in the synchronous UI code path.
                # Prefer server-side cached prices populated by background jobs (SH.RESULTS_CACHE).
                # Coerce price fields to numeric types (or None) to avoid downstream
                # formatting errors when the cache contains '-' or None strings.
                def _coerce_num(v):
                    try:
                        if v is None:
                            return None
                        if isinstance(v, str) and v.strip() in ['', '-']:
                            return None
                        return float(v)
                    except Exception:
                        return None

                price_data = {}
                try:
                    cached_results = (SH.RESULTS_CACHE.get('results') if isinstance(getattr(SH, 'RESULTS_CACHE', None), dict) else None)
                    cached_prices = (cached_results.get('prices') if isinstance(cached_results, dict) else None) or {}
                    for t in tickers:
                        entry = cached_prices.get(t) or {}
                        cp = _coerce_num(entry.get('current_price'))
                        dc = _coerce_num(entry.get('daily_change'))
                        sp = _coerce_num(entry.get('start_price') or entry.get('week_start_price'))
                        pl = _coerce_num(entry.get('profit_loss'))
                        price_data[t] = {
                            'current_price': cp,
                            'daily_change': dc,
                            'start_price': sp,
                            'profit_loss': pl,
                            'source': entry.get('source') or ('Loading' if not entry else 'Local')
                        }
                except Exception:
                    price_data = {}

                # Map the numeric prices into the DataFrame so downstream layout
                # and formatting code can rely on these columns being present.
                try:
                    df['current_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', None))
                    df['daily_change'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', None))
                    df['week_start_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('start_price', None))
                    df['profit_loss'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('profit_loss', None))
                except Exception:
                    df['current_price'] = None
                    df['daily_change'] = None
                    df['week_start_price'] = None
                    df['profit_loss'] = None

                # Get the latest week from the dataframe
                latest_week = df['date'].max() if 'date' in df.columns and not df.empty else None
                latest_week_str = latest_week.strftime('%Y-%m-%d') if pd.notna(latest_week) else 'N/A'
                
                summary = {
                    'total': len(tickers),
                    'total_spent': f"{len(tickers) * INVESTMENT_PER_STOCK:,.0f}",
                    'total_pl': f"{sum([float(price_data.get(t, {}).get('profit_loss', 0) or 0) for t in tickers]):+.2f}",
                    'roi': f"0.00",
                    'csv_path': None,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'db',
                    'latest_week': latest_week_str
                }

                # PHASE 4C: Cache the result before returning
                result = (df, None, summary)
                _PICKS_CACHE['data'] = result
                _PICKS_CACHE['timestamp'] = time.time()
                logger.info(f"✅ CACHED: Weekly picks data (DB source) saved for {_PICKS_CACHE['ttl']}s")
                return result
        except Exception:
            # DB read failed; we'll fall back to CSV logic below
            logger.debug('DB read failed or DB unavailable; falling back to CSV')
        csv_path = _find_latest_weekly_picks()
        if not csv_path:
            return None, "No weekly picks CSV found", None
        
        logger.info(f"Loading weekly picks from: {csv_path}")
        df = pd.read_csv(csv_path)
        
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

        
        # Limit to 20 tickers
        df = df.head(20)
        
        # Add rank column
        df.insert(0, 'rank', range(1, len(df) + 1))
        
        # Get tickers
        tickers = df['ticker'].tolist() if 'ticker' in df.columns else []

        # PHASE 18B FIX: Trigger background price fetch if prices not in cache OR incomplete
        try:
            cached_results = (SH.RESULTS_CACHE.get('results') if isinstance(getattr(SH, 'RESULTS_CACHE', None), dict) else None)
            cached_prices = (cached_results.get('prices') if isinstance(cached_results, dict) else None) or {}
            
            # Check if we have complete prices for these tickers (must have week_start_price)
            missing_or_incomplete = []
            for t in tickers:
                if t not in cached_prices:
                    missing_or_incomplete.append(t)
                else:
                    entry = cached_prices.get(t, {})
                    # Check if week_start_price is missing or invalid
                    week_start = entry.get('week_start_price')
                    if week_start is None or week_start == '-' or week_start == 'N/A' or (isinstance(week_start, str) and week_start.strip() == ''):
                        missing_or_incomplete.append(t)
            
            if missing_or_incomplete:
                logger.info(f"🔄 {len(missing_or_incomplete)}/{len(tickers)} tickers need price fetch (missing or incomplete), triggering background fetch...")
                # Trigger background fetch in a thread to avoid blocking
                import threading
                thread = threading.Thread(target=_background_fetch_weekly_prices, args=(tickers, 7, INVESTMENT_PER_STOCK))
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
            logger.info(f"[ENRICH] cached_results type: {type(cached_results)}, cached_prices len: {len(cached_prices) if isinstance(cached_prices, dict) else 'N/A'}, keys sample: {list(cached_prices.keys())[:5] if isinstance(cached_prices, dict) else 'N/A'}")
            # If no in-memory cache, try to read persisted weekly prices JSON from OUT_ROOT
            try:
                if not cached_prices:
                    out_dir = getattr(SH, 'OUT_ROOT', None)
                    if out_dir:
                        p = os.path.join(out_dir, 'prices_weekly.json')
                        if os.path.exists(p):
                            try:
                                import json as _json
                                with open(p, 'r', encoding='utf-8') as _f:
                                    j = _json.load(_f)
                                persisted = j.get('prices') if isinstance(j, dict) else None
                                if isinstance(persisted, dict) and persisted:
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
                    'current_price': entry.get('current_price', '-'),
                    'daily_change': entry.get('daily_change', '-'),
                    'start_price': entry.get('start_price') or entry.get('week_start_price') or '-',
                    'profit_loss': entry.get('profit_loss', '-'),
                    'source': entry.get('source') or ('Loading' if not entry else 'Local')
                }
        except Exception:
            price_data = {}
        # Ensure DataFrame has the expected price columns before selecting display columns
        try:
            # Map numeric price values (or None) into the DataFrame so later
            # formatting can safely detect missing values.
            df['current_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', None))
            df['daily_change'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', None))
            df['week_start_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('start_price', None))
            df['profit_loss'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('profit_loss', None))
        except Exception:
            # If mapping fails, populate with None defaults to avoid KeyError downstream
            df['current_price'] = None
            df['daily_change'] = None
            df['week_start_price'] = None
            df['profit_loss'] = None
        
        # Select columns to display (exclude score, pred_rank)
        display_cols = ['rank', 'ticker', 'current_price', 'daily_change', 'week_start_price', 'profit_loss']
        
        # Add other CSV columns except excluded ones
        csv_cols = [c for c in df.columns if c not in ['rank', 'ticker', 'score', 'pred_rank', 'current_price', 'daily_change', 'week_start_price', 'profit_loss']]
        display_cols.extend(csv_cols)
        
        df = df[display_cols]
        
        # Calculate summary stats
        total = len(tickers)
        total_spent = total * INVESTMENT_PER_STOCK
        
        # Calculate total P/L (skip dashes and invalid values)
        total_pl = 0
        for ticker in tickers:
            pl = price_data.get(ticker, {}).get('profit_loss', '-')
            if pl != '-' and pl != '':
                try:
                    total_pl += float(pl)
                except:
                    pass
        
        roi = (total_pl / total_spent * 100) if total_spent > 0 else 0
        
        summary = {
            'total': total,
            'total_spent': f"{total_spent:,.0f}",
            'total_pl': f"{total_pl:+,.2f}",
            'roi': f"{roi:+.2f}",
            'csv_path': csv_path,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'csv'
        }
        
        # PHASE 4C: Cache the result before returning
        result = (df, None, summary)
        _PICKS_CACHE['data'] = result
        _PICKS_CACHE['timestamp'] = time.time()
        logger.info(f"✅ CACHED: Weekly picks data (CSV source) saved for {_PICKS_CACHE['ttl']}s")
        return result
        
    except Exception as e:
        logger.error(f"Error loading weekly picks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}", None


def _build_datatable(df):
    """Build Dash DataTable from picks dataframe.
    
    Returns:
        html.Div containing info, summary boxes, and DataTable
    """
    # Force limit to 20 rows
    df = df.head(20)
    
    # Only render core columns
    core_cols = ['rank', 'ticker', 'current_price', 'daily_change', 'week_start_price', 'profit_loss']
    df_display = df[[col for col in core_cols if col in df.columns]].copy()
    
    # Format data for display
    # Preserve raw numeric values for robust testing by adding hidden raw columns
    df_display['current_price_raw'] = df_display['current_price']
    df_display['daily_change_raw'] = df_display['daily_change']
    df_display['week_start_price_raw'] = df_display['week_start_price']
    df_display['profit_loss_raw'] = df_display['profit_loss']

    # Also include a hidden JSON blob of the raw prices derived from the
    # DataFrame itself. This makes the test harness deterministic even when
    # SH.RESULTS_CACHE is not yet populated in-memory for this process.
    try:
        import json as _json
        price_map = {}
        for _, r in df_display[['ticker', 'current_price_raw', 'week_start_price_raw', 'profit_loss_raw']].iterrows():
            t = r.get('ticker') if 'ticker' in r else None
            if not t:
                continue
            price_map[t] = {
                'current_price': r.get('current_price_raw'),
                'week_start_price': r.get('week_start_price_raw'),
                'profit_loss': r.get('profit_loss_raw')
            }
        hidden_json = html.Pre(_json.dumps({'prices': price_map}, default=str), id='wp-prices-json-weekly', style={'display': 'none'})
    except Exception:
        hidden_json = html.Div(id='wp-prices-json-weekly', style={'display': 'none'})

    # Format data for display
    df_display['current_price'] = df_display['current_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    df_display['daily_change'] = df_display['daily_change'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
    df_display['week_start_price'] = df_display['week_start_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    df_display['profit_loss'] = df_display['profit_loss'].apply(lambda x: f"${x:+.2f}" if pd.notna(x) else "N/A")
    
    # Rename columns for display
    df_display = df_display.rename(columns={
        'rank': 'Rank',
        'ticker': 'Ticker',
        'current_price': 'Current Price',
        'daily_change': 'Daily Change',
        'week_start_price': 'Week Start',
        'profit_loss': 'Profit/Loss',
        'current_price_raw': 'Current Price Raw',
        'daily_change_raw': 'Daily Change Raw',
        'week_start_price_raw': 'Week Start Raw',
        'profit_loss_raw': 'Profit/Loss Raw'
    })
    
    table = dash_table.DataTable(
        id='weekly-table',
        columns=[{"name": col, "id": col} for col in df_display.columns],
        data=df_display.to_dict('records'),
        hidden_columns=['Current Price Raw', 'Daily Change Raw', 'Week Start Raw', 'Profit/Loss Raw'],
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
    
    return table


def layout():
    """Create layout for Weekly Picks tab.
    
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
    
    # Build a hidden JSON blob from the server-side DataFrame so tests can find
    # authoritative numeric values immediately after the page loads.
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
                    'week_start_price': row.get('week_start_price') if 'week_start_price' in df.columns else None,
                    'profit_loss': row.get('profit_loss') if 'profit_loss' in df.columns else None
                }
        hidden_json = html.Pre(_json.dumps({'prices': hidden_prices}, default=str), id='wp-prices-json-weekly', style={'display': 'none'})
    except Exception:
        hidden_json = html.Div(id='wp-prices-json-weekly', style={'display': 'none'})

    return html.Div([
        # Header
        html.H1("📊 Weekly Picks Dashboard", style={
            'color': '#4CAF50',
            'fontFamily': 'Arial, sans-serif',
            'marginBottom': '10px'
        }),
        
        html.Div([
            html.Span(f"Latest picks for week of {summary.get('latest_week', 'N/A') if isinstance(summary, dict) else 'N/A'}", style={
                'color': '#888',
                'fontSize': '14px',
                'marginRight': '20px'
            }),
            html.Span(f"Total: {summary.get('total', 0) if isinstance(summary, dict) else 0} picks", style={
                'color': '#FFD700',
                'fontWeight': '600',
                'fontSize': '14px'
            })
        ], style={
            'marginTop': '6px',
            'marginBottom': '20px'
        }),
        
        # Action buttons
        html.Div([
            html.Button("🔄 Refresh Prices", id='wp-refresh-btn', n_clicks=0, style={
                'padding': '10px 20px',
                'background': '#4CAF50',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'marginRight': '10px'
            }),
            html.Button("🔮 Regenerate Picks", id='wp-regenerate-btn', n_clicks=0, style={
                'padding': '10px 20px',
                'background': '#FF9800',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'fontSize': '14px'
            }),
        ], style={'marginBottom': '20px'}),
        
        # Status message area
        html.Div(id='wp-status-message', style={'marginBottom': '15px'}),
        
    # Container with pre-loaded content (server-side render)
    html.Div(initial_content, id='wp-content'),
    # Hidden machine-readable prices blob for tests
    hidden_json,
        
    # Auto-refresh interval (checks for cache updates and triggers refresh)
    dcc.Interval(id='wp-auto-refresh', interval=5000, n_intervals=0),

    # Store for data
    dcc.Store(id='wp-data-store', data=df.to_dict('records') if df is not None and not df.empty else None)
        
    ], style={
        'fontFamily': 'Arial, sans-serif',
        'padding': '20px',
        'minHeight': '100vh'
    })


def register_callbacks(app, SH=None):
    """Register callbacks."""
    
    # Refresh callback - fires only when refresh button clicked
    @app.callback(
        Output('wp-content', 'children'),
        Output('wp-data-store', 'data'),
        Input('wp-refresh-btn', 'n_clicks'),
        Input('wp-auto-refresh', 'n_intervals'),
        prevent_initial_call=False  # allow interval to trigger; we'll guard inside
    )
    def refresh_picks(n_clicks, n_intervals):
        """Refresh picks data when button clicked or when auto-refresh interval fires."""
        # Guard: do nothing on initial render unless user clicked or interval fired
        if not n_clicks and (not n_intervals or n_intervals == 0):
            raise PreventUpdate

        logger.info(f"🔵 Weekly Picks refresh triggered: n_clicks={n_clicks}, n_intervals={n_intervals}")
        print(f"[WeeklyPicks] Refresh triggered! n_clicks={n_clicks}, n_intervals={n_intervals}", flush=True)
        
        # Diagnostic: log module identity and cache identity at callback entry
        mod = SH  # Default to module-level import
        try:
            if mod is None:
                mod = __import__('_shared')
            cache_obj = getattr(mod, 'RESULTS_CACHE', None)
            cache_prices = (cache_obj.get('results', {}).get('prices', {}) if isinstance(cache_obj, dict) else {})
            logger.warning(f"[CALLBACK] SH id: {id(mod)}, RESULTS_CACHE id: {id(cache_obj)}, SH.__file__: {getattr(mod, '__file__', 'n/a')}, cache_len: {len(cache_prices)}")
            print(f"[CALLBACK] SH id: {id(mod)}, RESULTS_CACHE id: {id(cache_obj)}, SH.__file__: {getattr(mod, '__file__', 'n/a')}, cache_len: {len(cache_prices)}", flush=True)
        except Exception as _e:
            logger.warning(f"[CALLBACK] Could not emit diagnostic ids: {_e}")

        # If cache appears empty in this process, attempt to preload persisted cache
        try:
            # Use `mod` (fallback-safe reference) instead of `SH` which may be None in some contexts
            cache_obj = getattr(mod, 'RESULTS_CACHE', None)
            has_prices = False
            if isinstance(cache_obj, dict):
                has_prices = bool(cache_obj.get('results') and cache_obj['results'].get('prices'))
            if not has_prices:
                logger.warning("[CALLBACK] RESULTS_CACHE empty in this process; calling _preload_persisted_prices() to hydrate cache")
                try:
                    # Call module-level preload - safe no-op if nothing to load
                    preload_func = getattr(mod, '_preload_persisted_prices', None)
                    if callable(preload_func):
                        preload_func()
                except Exception:
                    logger.exception("[CALLBACK] _preload_persisted_prices() failed")
        except Exception:
            logger.exception("[CALLBACK] Error while checking/loading RESULTS_CACHE")

        # If this trigger was from the interval, only continue if cache updated since last render
        try:
            global _WP_LAST_LOADED
            cache_obj = getattr(mod, 'RESULTS_CACHE', None)
            loaded_at = None
            if isinstance(cache_obj, dict):
                loaded_at = cache_obj.get('loaded_at')
            # If interval triggered and nothing new, skip
            if not n_clicks and n_intervals and n_intervals > 0:
                if not loaded_at or loaded_at == _WP_LAST_LOADED:
                    raise PreventUpdate
            # Record last seen loaded_at
            if loaded_at:
                _WP_LAST_LOADED = loaded_at
        except PreventUpdate:
            raise
        except Exception:
            logger.exception('Error while checking RESULTS_CACHE loaded_at')

        df, error, summary = _load_and_enrich_picks()
        # Defensive: ensure summary is a dict so downstream subscripting is safe
        if summary is None:
            summary = {}

        # Double-check DB presence: if picks table has rows, mark source as DB so UI reflects it
        try:
            engine = db_utils._DB.get_engine()
            if engine is not None:
                try:
                    cnt = pd.read_sql_query("SELECT count(*) as c FROM picks", engine)
                    logger.info(f"Weekly Picks: picks count query returned: {cnt}")
                    if isinstance(cnt, pd.DataFrame) and not cnt.empty and int(cnt['c'].iloc[0]) > 0:
                        summary['source'] = 'db'
                except Exception as e:
                    logger.info(f"Weekly Picks: DB presence check failed: {e}")
        except Exception as e:
            logger.info(f"Weekly Picks: DB engine get failed: {e}")
        # If we have a DB engine available, prefer showing the DB source marker
        try:
            engine = db_utils._DB.get_engine()
            if engine is not None:
                summary['source'] = 'db'
        except Exception:
            pass
        logger.info(f"Weekly Picks: summary source after DB check = {summary.get('source')}")
        
        if error:
            return html.Div(error, style={'color': '#ff6b6b', 'padding': '20px'}), None
        
        if df is None:
            return html.Div("No data available", style={'color': '#888'}), None
        
        # Info section (build list so we can conditionally include SOURCE marker)
        info_items = []
        csv_path_display = summary.get('csv_path') if summary.get('csv_path') else 'N/A'
        info_items.append(html.Div(f"Loaded: {csv_path_display}", style={'color': '#888', 'fontSize': '12px'}))
        info_items.append(html.Div(f"Total picks: {summary.get('total', 0)} | Price data updated: {summary.get('update_time', '')}", style={'color': '#888', 'fontSize': '12px'}))
        # Do not display internal source markers in production UI
        info_items.append(html.Div("Refresh page to update live prices", style={'color': '#888', 'fontSize': '11px', 'fontStyle': 'italic', 'marginTop': '5px'}))

        info_div = html.Div(info_items, style={'marginBottom': '20px'})
        
        # Summary boxes
        try:
            total_pl_val = float(summary['total_pl'].replace(',', '').replace('+', ''))
            roi_val = float(summary['roi'].replace('+', ''))
        except:
            total_pl_val = 0
            roi_val = 0
        
        summary_boxes = html.Div([
            # Total Spent
            html.Div([
                html.Div("Total Money Spent", style={
                    'color': '#888',
                    'fontSize': '12px',
                    'textTransform': 'uppercase',
                    'marginBottom': '10px'
                }),
                html.Div(f"${summary.get('total_spent', '0')}", style={
                    'fontSize': '28px',
                    'fontWeight': 'bold',
                    'color': '#2196F3'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'textAlign': 'center'
            }),

            # Total P/L
            html.Div([
                html.Div("Total Profit/Loss", style={
                    'color': '#888',
                    'fontSize': '12px',
                    'textTransform': 'uppercase',
                    'marginBottom': '10px'
                }),
                html.Div(f"${summary.get('total_pl', '0')}", style={
                    'fontSize': '28px',
                    'fontWeight': 'bold',
                    'color': '#4CAF50' if total_pl_val >= 0 else '#ff6b6b'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'textAlign': 'center'
            }),

            # Background fetch status box (scheduling happens later in the function)
            html.Div([
                html.Div(
                    "Background price fetch queued" if _WEEKLY_PRICES_JOB.get('job_id') else "Background price fetch idle",
                    style={'color': '#888', 'fontSize': '12px'}
                )
            ], style={
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'textAlign': 'center'
            })
        ], style={
            'display': 'flex',
            'gap': '20px',
            'marginBottom': '20px',
            'flexWrap': 'wrap'
        })
        
        # 🔧 REMEDIATION: Build Dash DataTable (not HTML table) for paste functionality
        # CRITICAL: Ensure we only render the expected columns and rows
        # Force limit to 20 rows and only render the core price columns
        df = df.head(20)
        
        # CRITICAL FIX: Only render core columns, ignore extra CSV columns
        # Extra CSV columns were causing duplicate/malformed rows in the table
        core_cols = ['rank', 'ticker', 'current_price', 'daily_change', 'week_start_price', 'profit_loss']
        df_display = df[[col for col in core_cols if col in df.columns]].copy()
        
        logger.info(f"🔵 [WeeklyPicks] Rendering {len(df_display)} rows with columns: {list(df_display.columns)}")
        print(f"[WeeklyPicks] DataTable callback fired - building table with {len(df_display)} rows", flush=True)

        # Defensive re-map: pull freshest numeric values directly from SH.RESULTS_CACHE
        try:
            cached_results = (SH.RESULTS_CACHE.get('results') if isinstance(getattr(SH, 'RESULTS_CACHE', None), dict) else None) or {}
            cached_prices = (cached_results.get('prices') if isinstance(cached_results, dict) else None) or {}
            # Ensure numeric columns reflect cache values (prefer live cache over earlier placeholders)
            for col in ['current_price', 'daily_change', 'week_start_price', 'profit_loss']:
                if 'ticker' in df_display.columns:
                    def _map_val(t, c=col):
                        entry = cached_prices.get(t, {})
                        if c == 'week_start_price':
                            # support both 'start_price' and 'week_start_price' keys in cache
                            return entry.get('start_price') if entry.get('start_price') is not None else entry.get('week_start_price')
                        return entry.get(c)
                    df_display[col] = df_display['ticker'].map(lambda t: _map_val(t))
            # coerce to numeric where possible
            for col in ['current_price', 'daily_change', 'week_start_price', 'profit_loss']:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce')
        except Exception:
            # If anything fails, continue with previously computed values
            logger.exception('Failed to remap prices from RESULTS_CACHE')

        # 🔧 REMEDIATION: Build Dash DataTable instead of HTML table
        # Preserve raw numeric values for robust testing by adding hidden raw columns
        df_display['current_price_raw'] = df_display['current_price']
        df_display['daily_change_raw'] = df_display['daily_change']
        df_display['week_start_price_raw'] = df_display['week_start_price']
        df_display['profit_loss_raw'] = df_display['profit_loss']

        # Construct hidden JSON from the DataFrame's raw columns so the
        # refresh callback returns a deterministic machine-readable blob
        # even if SH.RESULTS_CACHE is empty in this process.
        try:
            import json as _json
            price_map = {}
            for _, r in df_display[['ticker', 'current_price_raw', 'week_start_price_raw', 'profit_loss_raw']].iterrows():
                t = r.get('ticker') if 'ticker' in r else None
                if not t:
                    continue
                price_map[t] = {
                    'current_price': r.get('current_price_raw'),
                    'week_start_price': r.get('week_start_price_raw'),
                    'profit_loss': r.get('profit_loss_raw')
                }
            hidden_json = html.Pre(_json.dumps({'prices': price_map}, default=str), id='wp-prices-json-weekly', style={'display': 'none'})
        except Exception:
            hidden_json = html.Div(id='wp-prices-json-weekly', style={'display': 'none'})

        # Format data for display (apply formatting to DataFrame)
        df_display['current_price'] = df_display['current_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        df_display['daily_change'] = df_display['daily_change'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
        df_display['week_start_price'] = df_display['week_start_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        df_display['profit_loss'] = df_display['profit_loss'].apply(lambda x: f"${x:+.2f}" if pd.notna(x) else "N/A")

        # Rename columns for display
        df_display = df_display.rename(columns={
            'rank': 'Rank',
            'ticker': 'Ticker',
            'current_price': 'Current Price',
            'daily_change': 'Daily Change',
            'week_start_price': 'Week Start',
            'profit_loss': 'Profit/Loss',
            'current_price_raw': 'Current Price Raw',
            'daily_change_raw': 'Daily Change Raw',
            'week_start_price_raw': 'Week Start Raw',
            'profit_loss_raw': 'Profit/Loss Raw'
        })

        table = dash_table.DataTable(
            id='weekly-table',
            columns=[{"name": col, "id": col} for col in df_display.columns],
            data=df_display.to_dict('records'),
            hidden_columns=['Current Price Raw', 'Daily Change Raw', 'Week Start Raw', 'Profit/Loss Raw'],
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

        logger.info(f"✅ [WeeklyPicks] DataTable created with {len(df_display)} rows")

        content = html.Div([info_div, summary_boxes, table, hidden_json])

        return content, df.to_dict('records')
    
    # Regenerate picks callback
    @app.callback(
        Output('wp-status-message', 'children'),
        Output('wp-content', 'children', allow_duplicate=True),
        Output('wp-data-store', 'data', allow_duplicate=True),
        Input('wp-regenerate-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def regenerate_picks(n_clicks):
        """Run the weekly picks generator to create new picks for current week."""
        if not n_clicks:
            raise PreventUpdate
        
        logger.info(f"🔮 Regenerate picks clicked: n_clicks={n_clicks}")
        
        # Show loading message
        loading_msg = html.Div([
            html.Span("⏳ ", style={'fontSize': '20px'}),
            html.Span("Regenerating picks... This may take 20-30 seconds.", style={
                'color': '#FF9800',
                'fontWeight': 'bold',
                'fontSize': '14px'
            })
        ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #FF9800'})
        
        try:
            # Run the generator
            import subprocess
            result = subprocess.run(
                ['python3', '-m', 'jobs.weekly_picks_generator'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(Path(__file__).parent.parent.parent)
            )
            
            if result.returncode == 0:
                # Clear cache so next load fetches fresh data
                _PICKS_CACHE['data'] = None
                _PICKS_CACHE['timestamp'] = None
                
                # Reload data
                df, error, summary = _load_and_enrich_picks()
                
                if error:
                    status_msg = html.Div([
                        html.Span("⚠️ ", style={'fontSize': '20px'}),
                        html.Span(f"Generator completed but error loading data: {error}", style={
                            'color': '#ff6b6b',
                            'fontSize': '14px'
                        })
                    ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #ff6b6b'})
                    return status_msg, no_update, no_update
                
                # Build new table
                content = html.Div([info_div, summary_boxes, _build_datatable(df)])
                
                status_msg = html.Div([
                    html.Span("✅ ", style={'fontSize': '20px'}),
                    html.Span(f"Successfully generated {summary.get('total', 0)} new picks for week {summary.get('latest_week', 'N/A')}", style={
                        'color': '#4CAF50',
                        'fontWeight': 'bold',
                        'fontSize': '14px'
                    })
                ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #4CAF50'})
                
                return status_msg, content, df.to_dict('records') if df is not None else None
            else:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                status_msg = html.Div([
                    html.Span("❌ ", style={'fontSize': '20px'}),
                    html.Span(f"Generator failed: {error_msg}", style={
                        'color': '#ff6b6b',
                        'fontSize': '12px'
                    })
                ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #ff6b6b'})
                return status_msg, no_update, no_update
                
        except subprocess.TimeoutExpired:
            status_msg = html.Div([
                html.Span("⏱️ ", style={'fontSize': '20px'}),
                html.Span("Generator timed out after 60 seconds", style={
                    'color': '#ff6b6b',
                    'fontSize': '14px'
                })
            ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #ff6b6b'})
            return status_msg, no_update, no_update
        except Exception as e:
            logger.exception("Error running generator")
            status_msg = html.Div([
                html.Span("❌ ", style={'fontSize': '20px'}),
                html.Span(f"Error: {str(e)}", style={
                    'color': '#ff6b6b',
                    'fontSize': '14px'
                })
            ], style={'padding': '10px', 'background': '#2c2c2c', 'borderRadius': '4px', 'border': '2px solid #ff6b6b'})
            return status_msg, no_update, no_update
