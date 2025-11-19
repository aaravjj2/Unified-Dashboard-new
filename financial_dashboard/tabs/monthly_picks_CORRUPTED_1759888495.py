"""Monthly Picks tab - minimal, clean implementation.

Exports:
- layout()
- register_callbacks(app, SH=None)

This module provides a lightweight UI for previewing and downloading the latest
monthly picks CSV produced by the pipeline. It keeps top-level imports small so
loading the tab module is cheap.
"""

import os
import time
import threading
import traceback
import logging
import pandas as pd
from datetime import datetime
from dash import dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import _shared as SH
from utils.events_helper import get_ticker_events

JOBS = {}

# By default do not pin to a specific picks CSV so the tab picks up the
# latest available picks artifact under `models/` automatically. For
# development you may set the ATTACHED_PICKS_PATH environment variable to
# an absolute path to pin to a specific CSV. Previously this code pinned
# to a 2025-09-14 CSV which caused stale data to appear in the UI.
ATTACHED_PICKS_PATH = os.environ.get('ATTACHED_PICKS_PATH') or None


def _start_local_job(target, args=(), kwargs=None, name=None):
    if kwargs is None:
        kwargs = {}
    jid = f"job_{int(time.time() * 1000)}"
    JOBS[jid] = {'name': name or getattr(target, '__name__', 'job'), 'status': 'queued', 'thread': None, 'result': None}

    def _runner(j):
        JOBS[j]['status'] = 'running'
        try:
            JOBS[j]['result'] = target(*args, **kwargs)
            JOBS[j]['status'] = 'done'
        except Exception as e:
            JOBS[j]['result'] = {'ok': False, 'error': str(e), 'trace': traceback.format_exc()}
            JOBS[j]['status'] = 'error'

    th = threading.Thread(target=_runner, args=(jid,), daemon=True)
    JOBS[jid]['thread'] = th
    th.start()
    return jid


def _find_latest_picks(base_dir=None):
    # Try multiple candidate locations similar to app.preview_tab so the
    # standalone table matches what the preview endpoint shows.
    # Prefer an attached/pinned CSV when present.
    try:
        if os.path.exists(ATTACHED_PICKS_PATH):
            return ATTACHED_PICKS_PATH
    except Exception:
        pass
    candidates = []
    try:
        import glob
        sh_out = getattr(SH, 'OUT_ROOT', None)
        sh_proj_root = getattr(SH, 'PROJECT_ROOT', None)
    except Exception:
        sh_out = None
        sh_proj_root = None

    cand_patterns = []
    if sh_out:
        cand_patterns.append(os.path.join(sh_out, 'picks_*.csv'))
    # Use shared PROJECT_ROOT when available, otherwise compute from file path.
    proj_root = sh_proj_root or SH.PROJECT_ROOT
    # Also consider the local Dash app directory (two levels up from this file
    # when inside tabs/) so modules work when PROJECT_ROOT points to a parent
    # folder. The Dash app normally places models under <app_dir>/models.
    local_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    cand_patterns.extend([
        os.path.join(proj_root, 'models', 'preview', 'picks_*.csv'),
        os.path.join(proj_root, 'models', 'full_run', 'picks_*.csv'),
        os.path.join(local_app_dir, 'models', 'preview', 'picks_*.csv'),
        os.path.join(local_app_dir, 'models', 'full_run', 'picks_*.csv'),
        os.path.join(local_app_dir, 'models', 'picks', 'picks_*.csv'),
    ])
    for pat in cand_patterns:
        try:
            candidates.extend(glob.glob(pat))
        except Exception:
            continue
    if not candidates:
        return None

    # Prefer filename date when available (YYYYMMDD). If multiple files have
    # a date in the name, pick the newest date. De-prioritize files with
    # '.open' in their name (they may be partial/in-progress). Fall back to
    # mtime if no filename dates are found.
    import re
    def _parse_date_from_name(path):
        m = re.search(r'(20\d{6})', os.path.basename(path))
        if not m:
            return None
        s = m.group(1)
        try:
            from datetime import datetime
            return datetime.strptime(s, '%Y%m%d').date()
        except Exception:
            return None

    dated = []
    undated = []
    for c in candidates:
        dt = _parse_date_from_name(c)
        if dt is not None:
            dated.append((dt, c))
        else:
            undated.append(c)

    if dated:
        dated.sort(key=lambda x: (x[0], ('.open' not in os.path.basename(x[1]))), reverse=True)
        return dated[0][1]

    non_open = [p for p in undated if '.open' not in os.path.basename(p)]
    candidates_by_mtime = non_open if non_open else undated
    try:
        latest = max(candidates_by_mtime, key=lambda p: os.path.getmtime(p))
        return latest
    except Exception:
        candidates = sorted(candidates)
        return candidates[-1] if candidates else None


def _load_picks_df(path=None):
    p = path or _find_latest_picks()
    if not p:
        return None, 'No picks CSV found'
    try:
        import pandas as pd
        df = pd.read_csv(p)
        return df, p
    except Exception as e:
        return None, str(e)


def _format_df_for_display(df):
    """Return a copy of df with nicely formatted strings for display in the DataTable.
    Numeric columns are rounded/commas applied for readability but original df remains unchanged.
    """
    try:
        import pandas as _pd
        d = df.copy()
        def _fmt(col, fmt):
            if col in d.columns:
                try:
                    d[col] = d[col].apply(lambda v: (fmt.format(v) if (v is not None and not _pd.isna(v)) else ''))
                except Exception:
                    try:
                        d[col] = d[col].map(lambda v: (fmt.format(v) if v is not None else ''))
                    except Exception:
                        pass

        # 4-decimal floats
        four = "{:.4f}"
        for c in ('score', 'pred_sigma', 'pred_lower_95', 'pred_upper_95', 'predicted_return_net', 'lgb_pred', 'ng_pred', 'model_confidence', 'expected_slippage_pct'):
            _fmt(c, four)

        # 2-decimal currency/price
        two = "{:, .2f}".replace(' ', '')
        for c in ('last_price', 'position_size_dollars', 'avg_dollar_vol', 'max_notional'):
            _fmt(c, two)

        # position size small decimal
        _fmt('position_size', '{:.6f}')

        # mark booleans and missing
        for c in d.columns:
            if d[c].dtype == 'bool':
                try:
                    d[c] = d[c].map(lambda v: str(v))
                except Exception:
                    pass

        return d
    except Exception:
        return df.copy()


def _prepare_display_df(df):
    """Build the Monthly Picks display DataFrame using Flask-equivalent logic."""
    try:
        import pandas as _pd
        import numpy as _np
        import logging

        if df is None:
            return _pd.DataFrame()

        working = df.copy()
        ticker_col = 'ticker' if 'ticker' in working.columns else None
        if ticker_col is None:
            return working

        tickers = [t for t in working[ticker_col].dropna().unique().tolist() if t]
        price_map = {}
        if tickers:
            try:
                from utils.price_fetcher import get_live_prices
                price_map = get_live_prices(tickers, investment=1000.0, batch_size=8)
            except Exception as exc:
                logging.warning(f"Monthly picks live-price fetch failed: {exc}")
                price_map = {}

        def _info(t, key):
            payload = price_map.get(t) or {}
            return payload.get(key)

        working['price_live'] = working[ticker_col].map(lambda t: _info(t, 'current_price'))
        working['price_start_of_month'] = working[ticker_col].map(lambda t: _info(t, 'month_start_price'))
        working['month_start_source'] = working[ticker_col].map(lambda t: _info(t, 'month_start_source'))
        working['month_start_date'] = working[ticker_col].map(lambda t: _info(t, 'month_start_date'))
        working['profit_loss'] = working[ticker_col].map(lambda t: _info(t, 'profit_loss'))
        working['daily_change'] = working[ticker_col].map(lambda t: _info(t, 'daily_change'))

        if 'daily_change' in working.columns:
            try:
                working['daily_change'] = _pd.to_numeric(working['daily_change'], errors='coerce') / 100.0
            except Exception:
                working['daily_change'] = _pd.to_numeric(working['daily_change'], errors='ignore')

        if 'price_live' in working.columns:
            missing_live = working['price_live'].isna()
            if missing_live.any():
                fallback_cols = [c for c in ('last_price', 'last_price_x', 'last_price_y') if c in working.columns]
                for col in fallback_cols:
                    working.loc[missing_live & working[col].notna(), 'price_live'] = _pd.to_numeric(working.loc[missing_live & working[col].notna(), col], errors='coerce')
                    missing_live = working['price_live'].isna()
                    if not missing_live.any():
                        break

        if 'price_start_of_month' in working.columns:
            missing_start = working['price_start_of_month'].isna()
            if missing_start.any():
                alt_cols = [c for c in ('month_start', 'price_start_of_week', 'price_start') if c in working.columns]
                for col in alt_cols:
                    working.loc[missing_start & working[col].notna(), 'price_start_of_month'] = _pd.to_numeric(working.loc[missing_start & working[col].notna(), col], errors='coerce')
                    missing_start = working['price_start_of_month'].isna()
                    if not missing_start.any():
                        break

        working['month_start'] = working['price_start_of_month']

        try:
            ms_series = _pd.to_numeric(working['price_start_of_month'], errors='coerce')
            live_series = _pd.to_numeric(working['price_live'], errors='coerce')
            shares = 1000.0 / ms_series
            computed_pl = (live_series - ms_series) * shares
            if 'profit_loss' in working.columns:
                working.loc[working['profit_loss'].isna(), 'profit_loss'] = computed_pl[working['profit_loss'].isna()]
            else:
                working['profit_loss'] = computed_pl
        except Exception:
            working['profit_loss'] = working.get('profit_loss', None)

        try:
            ms_series = _pd.to_numeric(working['price_start_of_month'], errors='coerce')
            live_series = _pd.to_numeric(working['price_live'], errors='coerce')
            working['overall_change'] = (live_series - ms_series) / ms_series
        except Exception:
            working['overall_change'] = None

        if 'date' in working.columns:
            try:
                working['start_date'] = _pd.to_datetime(working['date']).dt.strftime('%Y-%m-%d')
            except Exception:
                working['start_date'] = working['date']

        working.insert(0, 'Rank', list(range(1, len(working) + 1)))

        # Order columns to match monthly_picks_flask.py template
        # Flask displays: Rank, Ticker, Current Price, Daily Change %, Month Start Price, Month Start Source, Month Start Date, Profit/Loss
        front_cols = ['Rank', ticker_col, 'price_live', 'daily_change', 'price_start_of_month', 'month_start_source', 'month_start_date', 'profit_loss', 'start_date']
        remaining = [c for c in working.columns if c not in front_cols]
        ordered = [c for c in front_cols + remaining if c in working.columns]
        working = working[ordered]

        try:
            col_map = {}
            for idx, name in enumerate(list(working.columns)):
                col_map.setdefault(name, []).append(idx)
            for name, positions in col_map.items():
                if len(positions) <= 1:
                    continue
                series_list = [working.iloc[:, pos] for pos in positions]
                combined = _pd.concat(series_list, axis=1)
                working = working.drop(columns=[working.columns[pos] for pos in positions])
                working[name] = combined.apply(lambda row: next((v for v in row if not _pd.isna(v)), None), axis=1)
        except Exception:
            pass

        return working
    except Exception:
        return df.copy()


def _fetch_live_prices_for_df(df, SH=None, ticker_col='ticker'):
    """Attempt to fetch recent price series for tickers in df.
    Prefer using SH.mt_mod.batch_fetch or batch_fetch_chunked if available.
    Falls back to the yfinance helper in Dash/market_dashboard.py when
    mt_mod is not present. Returns a copy of df with updated
    'price_live', 'daily_change', and 'month_start' where available.
    This function is defensive and will leave df unchanged on any error.
    """
    try:
        import pandas as _pd
        out = df.copy()
        # collect tickers
        if ticker_col in out.columns:
            tickers = [t for t in out[ticker_col].dropna().unique().tolist() if t]
        elif 'ticker' in out.columns:
            tickers = [t for t in out['ticker'].dropna().unique().tolist() if t]
        else:
            return out

        # Fast-path: when SH is not provided or mt_mod is absent/disabled,
        # use the local utils.price_fetcher directly to populate live prices.
        # This mirrors the Flask implementation and keeps the Dash tab in sync.
        try:
            has_mt = False
            try:
                has_mt = bool(getattr(SH, 'mt_mod', None))
            except Exception:
                has_mt = False
            if SH is None or not has_mt:
                key_col = ticker_col if ticker_col in out.columns else ('ticker' if 'ticker' in out.columns else None)
                if key_col is None:
                    return out
                from utils.price_fetcher import get_live_prices
                pf_map = get_live_prices(tickers, investment=1000.0, batch_size=8)
                out['price_live'] = out[key_col].map(lambda t: pf_map.get(t, {}).get('current_price'))
                # Convert daily change percent (from helper) into decimal ratio for downstream usage
                out['daily_change'] = out[key_col].map(lambda t: (pf_map.get(t, {}).get('daily_change') / 100.0) if pf_map.get(t, {}).get('daily_change') not in (None, '') else None)
                out['month_start'] = out[key_col].map(lambda t: pf_map.get(t, {}).get('month_start_price'))
                try:
                    out['price_start_of_month'] = out['month_start']
                except Exception:
                    pass
                out['profit_loss'] = out[key_col].map(lambda t: pf_map.get(t, {}).get('profit_loss'))
                return out
        except Exception:
            # fall through to other fetch strategies if local helper fails
            pass

        prices_map = {}
        # Try SH.mt_mod first
        try:
            if SH is not None and getattr(SH, 'mt_mod', None) is not None:
                mt = SH.mt_mod
                # prefer chunked batch fetch when available
                if hasattr(mt, 'batch_fetch_chunked'):
                    fetched = mt.batch_fetch_chunked(tickers, period='1mo', interval='1d', cache_ttl=60, use_cache_only=False)
                elif hasattr(mt, 'batch_fetch'):
                    fetched = mt.batch_fetch(tickers, period='1mo', interval='1d', cache_ttl=60, use_cache_only=False)
                else:
                    fetched = None
                if isinstance(fetched, dict):
                    for tk, dfp in fetched.items():
                        try:
                            if isinstance(dfp, _pd.DataFrame):
                                # prefer adj_close or Close
                                if 'adj_close' in dfp.columns:
                                    prices_map[tk] = dfp['adj_close'].dropna().tolist()
                                elif 'Close' in dfp.columns:
                                    prices_map[tk] = dfp['Close'].dropna().tolist()
                                elif 'close' in dfp.columns:
                                    prices_map[tk] = dfp['close'].dropna().tolist()
                                else:
                                    prices_map[tk] = []
                        except Exception:
                            prices_map[tk] = []
        except Exception:
            prices_map = {}

        # If mt_mod didn't yield results, prefer the local price_fetch helper
        if not prices_map:
            try:
                # dynamically load the local utils/price_fetch.py to ensure we
                # call the up-to-date functions in this workspace (avoids stale
                # package imports when running standalone dev scripts).
                import importlib.util
                import os
                # Determine project root defensively: prefer SH.PROJECT_ROOT when available
                proj_root = None
                try:
                    proj_root = getattr(SH, 'PROJECT_ROOT', None)
                except Exception:
                    proj_root = None
                if not proj_root:
                    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                pf_path = os.path.join(proj_root, 'utils', 'price_fetch.py')
                # If a local file exists, load it; otherwise try package import; then fallback to utils.price_fetcher
                if os.path.exists(pf_path):
                    spec = importlib.util.spec_from_file_location('dash_local_price_fetch', pf_path)
                    pf = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(pf)
                    fetched = pf.fetch_prices_batch(tickers, parallelism=8, cache_ttl=60)
                else:
                    try:
                        from utils.price_fetch import fetch_prices_batch
                        fetched = fetch_prices_batch(tickers, parallelism=8, cache_ttl=60)
                    except Exception:
                        # If the older price_fetch helper isn't available or fails,
                        # try the newer utils.price_fetcher.get_live_prices helper
                        try:
                            from utils.price_fetcher import get_live_prices as _get_live_prices
                            # call with a modest batch size to avoid long waits here
                            fetched_pf = _get_live_prices(tickers, investment=1000.0, batch_size=8)
                            # normalize into the fetched mapping format used below
                            fetched = {}
                            for tk, info in (fetched_pf or {}).items():
                                fetched[tk] = {
                                    'last_price': info.get('current_price'),
                                    'prev_close': None,
                                    'month_start': info.get('month_start_price'),
                                    'profit_loss': info.get('profit_loss'),
                                    'meta': info,
                                }
                        except Exception:
                            fetched = {}
            except Exception:
                # If the older price_fetch helper isn't available or fails,
                # try the newer utils.price_fetcher.get_live_prices helper
                try:
                    from utils.price_fetcher import get_live_prices as _get_live_prices
                    # call with a modest batch size to avoid long waits here
                    fetched_pf = _get_live_prices(tickers, investment=1000.0, batch_size=8)
                    # normalize into the fetched mapping format used below
                    fetched = {}
                    for tk, info in (fetched_pf or {}).items():
                        fetched[tk] = {
                            'last_price': info.get('current_price'),
                            'prev_close': None,
                            'month_start': info.get('month_start_price'),
                            'profit_loss': info.get('profit_loss'),
                            'meta': info,
                        }
                except Exception:
                    fetched = {}
                # fetched: ticker -> payload dict
                def _pick_last(tk):
                    p = fetched.get(tk)
                    return p.get('last_price') if isinstance(p, dict) else None

                def _pick_prev_close(tk):
                    p = fetched.get(tk)
                    return p.get('prev_close') if isinstance(p, dict) else None

                key_col = ticker_col if ticker_col in out.columns else ('ticker' if 'ticker' in out.columns else None)
                if key_col is None:
                    return out
                out['price_live'] = out[key_col].map(lambda t: _pick_last(t))
                # daily change approximate from prev_close
                out['daily_change'] = out[key_col].map(lambda t: (_pick_last(t) - _pick_prev_close(t)) / _pick_prev_close(t) if (_pick_prev_close(t) not in (None, 0)) else None)
                # month_start: best-effort use prev_close as a simple fallback (accurate for pre/post market)
                out['month_start'] = out[key_col].map(lambda t: _pick_prev_close(t))
                # Fill any remaining missing values from the market_dashboard helper if available
                try:
                    import importlib.util
                    import os
                    md = None
                    md_path = os.path.join(SH.PROJECT_ROOT, 'market_dashboard.py')
                    if os.path.exists(md_path):
                        spec = importlib.util.spec_from_file_location('market_dashboard', md_path)
                        md = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(md)
                    if md is not None and hasattr(md, '_populate_market_fields_for_df'):
                        prices_map = {}
                        # instrumentation: record which path was used to fetch prices
                        fetch_path = None
                        if ticker_col in temp.columns:
                            temp = temp.rename(columns={ticker_col: 'Ticker'})
                        temp2 = md._populate_market_fields_for_df(temp, ticker_col='Ticker', force=True)
                        if not isinstance(temp2, (list, tuple)):
                            if 'Price (live)' in temp2.columns:
                                out['price_live'] = out['price_live'].fillna(temp2['Price (live)'])
                            if 'Daily change' in temp2.columns:
                                out['daily_change'] = out['daily_change'].fillna(temp2['Daily change'])
                            if 'Price start of month' in temp2.columns:
                                out['month_start'] = out['month_start'].fillna(temp2['Price start of month'])
                except Exception:
                    pass
                return out
            except Exception:
                pass

        # If we have per-ticker series lists, pick values (prefer mt_mod series)
        try:
            live_vals = {}
            daily_vals = {}
            month_start_vals = {}
            for tk in tickers:
                seq = prices_map.get(tk) or []
                if not seq:
                    live_vals[tk] = None
                    daily_vals[tk] = None
                    month_start_vals[tk] = None
                    continue
                # seq is ordered by date ascending (assumption). Last element is latest
                try:
                    last = float(seq[-1])
                except Exception:
                    last = None
                try:
                    prev = float(seq[-2]) if len(seq) >= 2 else None
                except Exception:
                    prev = None
                try:
                    # month start -> first element in sequence
                    start = float(seq[0]) if seq else None
                except Exception:
                    start = None
                live_vals[tk] = last
                if prev is not None and prev != 0 and last is not None:
                    try:
                        daily_vals[tk] = (last - prev) / prev
                    except Exception:
                        daily_vals[tk] = None
                else:
                    daily_vals[tk] = None
                month_start_vals[tk] = start

            # map back onto DataFrame only if we actually fetched values
            key_col = ticker_col if ticker_col in out.columns else ('ticker' if 'ticker' in out.columns else None)
            if key_col is None:
                return out
            # only overwrite if there's at least one non-null fetched value
            try:
                has_live = any(v is not None for v in live_vals.values())
            except Exception:
                has_live = False
            try:
                has_daily = any(v is not None for v in daily_vals.values())
            except Exception:
                has_daily = False
            try:
                has_ms = any(v is not None for v in month_start_vals.values())
            except Exception:
                has_ms = False
            if has_live:
                out['price_live'] = out[key_col].map(lambda t: live_vals.get(t))
            if has_daily:
                out['daily_change'] = out[key_col].map(lambda t: daily_vals.get(t))
            if has_ms:
                out['month_start'] = out[key_col].map(lambda t: month_start_vals.get(t))
            # keep legacy column name used elsewhere for month-start price
            try:
                out['price_start_of_month'] = out['month_start']
            except Exception:
                pass
            # If many prices still missing, attempt to read local snapshots parquet as fallback
            try:
                missing = int(out['price_live'].isna().sum()) if 'price_live' in out.columns else len(out)
            except Exception:
                missing = 0
            if missing > 0:
                try:
                    import pandas as _pd
                    base = os.path.join(SH.PROJECT_ROOT, 'data')
                    cand = [os.path.join(base, 'snapshots_all_with_emb.parquet'), os.path.join(base, 'snapshots_all.parquet'), os.path.join(base, 'snapshots.parquet')]
                    snap = None
                    for c in cand:
                        if os.path.exists(c):
                            try:
                                snap = _pd.read_parquet(c)
                                break
                            except Exception:
                                continue
                    if snap is not None and 'ticker' in snap.columns:
                        # prefer adj_close then close
                        if 'adj_close' in snap.columns:
                            mapv = snap.sort_values('date').groupby('ticker').last()['adj_close'].to_dict()
                        elif 'close' in snap.columns:
                            mapv = snap.sort_values('date').groupby('ticker').last()['close'].to_dict()
                        else:
                            mapv = {}
                        # only fill missing ones
                        def _fill_price(row):
                            try:
                                if row.get('price_live') is not None and not _pd.isna(row.get('price_live')):
                                    return row.get('price_live')
                                t = row.get(key_col)
                                return mapv.get(t)
                            except Exception:
                                return row.get('price_live')
                        out['price_live'] = out.apply(_fill_price, axis=1)
                        # fill month_start from snapshots if missing
                        try:
                            ms_map = None
                            if 'price_start_of_month' in snap.columns:
                                ms_map = snap.sort_values('date').groupby('ticker').last()['price_start_of_month'].to_dict()
                            else:
                                # derive month_start as the first price in the month from the snapshot
                                snap['month'] = snap['date'].dt.to_period('M') if 'date' in snap.columns else None
                                # best-effort: use same latest month as price_live mapping
                                ms_map = {}
                            if ms_map:
                                def _fill_ms(row):
                                    try:
                                        if row.get('month_start') is not None and not _pd.isna(row.get('month_start')):
                                            return row.get('month_start')
                                        t = row.get(key_col)
                                        return ms_map.get(t)
                                    except Exception:
                                        return row.get('month_start')
                                out['month_start'] = out.apply(_fill_ms, axis=1)
                        except Exception:
                            pass
                except Exception:
                    pass
            return out
        except Exception:
            return out
    except Exception:
        return df


def _render_metrics(df):
    """Given the prepared display DataFrame, return a small row of three
    button-like metric elements: Overall spend, Total profit/loss, and ROI."""
    try:
        import pandas as _pd
        if df is None:
            return html.Div()
        # ensure numeric profit_loss
        pl_series = None
        if 'profit_loss' in df.columns:
            try:
                pl_series = _pd.to_numeric(df['profit_loss'], errors='coerce')
            except Exception:
                pl_series = None
        # number of tickers considered
        try:
            n = int(len(df))
        except Exception:
            n = 0

        overall_spend = 1000.0 * n
        total_pl = float(pl_series.sum()) if pl_series is not None else 0.0
        roi = None
        try:
            roi = (total_pl / overall_spend) if overall_spend else None
        except Exception:
            roi = None

        def _fmt_currency(v):
            try:
                return f"${v:,.2f}"
            except Exception:
                return str(v)

        def _fmt_percent(x):
            try:
                return f"{x*100:.2f}%" if x is not None else '-'
            except Exception:
                return str(x)

        card_style = {'padding': '10px 14px', 'backgroundColor': '#0b2a3a', 'border': '1px solid rgba(255,255,255,0.08)', 'borderRadius': '6px', 'minWidth': '160px', 'textAlign': 'center'}
        label_style = {'fontSize': '12px', 'color': '#cbd5e1'}
        value_style = {'fontSize': '16px', 'fontWeight': '700', 'color': '#e6eef8'}

        spend_el = html.Div([html.Div('Overall spend', style=label_style), html.Div(_fmt_currency(overall_spend), style=value_style)], style=card_style)
        pl_color = '#10B981' if total_pl > 0 else ('#EF4444' if total_pl < 0 else '#e6eef8')
        pl_vs = value_style.copy()
        pl_vs['color'] = pl_color
        pl_el = html.Div([html.Div('Total profit / loss', style=label_style), html.Div(_fmt_currency(total_pl), style=pl_vs)], style=card_style)
        roi_el = html.Div([html.Div('ROI', style=label_style), html.Div(_fmt_percent(roi), style=value_style)], style=card_style)

        container = html.Div([spend_el, pl_el, roi_el], id='mp-metrics-row', style={'display': 'flex', 'gap': '12px', 'marginTop': '12px', 'alignItems': 'center'})
        return container
    except Exception:
        return html.Div()


def layout():
    return html.Div([
        html.Div([
            html.H3('Monthly picks September', style={'margin': 0}),
        html.Div([
            dcc.Input(id='mp-max-tickers', value=200, type='number', className='small-input', style={'width': '180px'}),
            html.Button('Run Monthly Picks', id='mp-run-btn', n_clicks=0),
            html.A('Download CSV', id='mp-download-link', href='', download='monthly_picks.csv', className='btn'),
            html.Button('Refresh prices', id='mp-refresh-prices', n_clicks=0),
        ], className='picks-header compact'),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
        html.Div(id='mp-status', style={'marginTop': 6}),
        html.Hr(),
        # Placeholder datatable so the DOM contains the element even before
        # the server-side callback populates it. This helps smoke tests and
        # Playwright determine when the table is available and avoids timing
        # races where the table is rendered client-side after our snapshot.
        html.Div(id='mp-standalone-table', children=[
            dash_table.DataTable(id='mp-datatable-placeholder', columns=[{'name': 'loading', 'id': 'loading'}], data=[], page_size=1, style_table={'display': 'none'}, style_as_list_view=True)
        ]),
        # store to capture page-load timestamp so table recomputes on full page reload
        dcc.Store(id='mp-page-load-ts', data=int(time.time())),
        dcc.Store(id='mp-current-job', data=''),
        dcc.Interval(id='mp-poll-interval', interval=2000, disabled=True),
        dcc.Loading(id='mp-loading', children=[html.Div(id='mp-results-area')], type='circle'),
        
        # Inspect Pick Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id='inspect-modal-title')),
            dbc.ModalBody([
                # Summary Card
                dbc.Card([
                    dbc.CardHeader("Pick Summary"),
                    dbc.CardBody(id='inspect-summary-body')
                ], className='mb-3'),
                
                # Price Chart
                dbc.Card([
                    dbc.CardHeader("Price Chart (6 months)"),
                    dbc.CardBody([
                        dcc.Graph(id='inspect-price-chart', config={'displayModeBar': False})
                    ])
                ], className='mb-3'),
                
                # SHAP Explanation Table
                dbc.Card([
                    dbc.CardHeader("SHAP Feature Contributions"),
                    dbc.CardBody([
                        html.Div(id='inspect-shap-table')
                    ])
                ], className='mb-3'),
                
                # Trade Sizing Info
                dbc.Card([
                    dbc.CardHeader("Trade Sizing & Execution"),
                    dbc.CardBody(id='inspect-trade-info')
                ], className='mb-3'),
                
                # Recent Events
                dbc.Card([
                    dbc.CardHeader("Recent Events"),
                    dbc.CardBody(id='inspect-events-body')
                ], className='mb-3'),
                
                # Audit Bundle Link
                dbc.Card([
                    dbc.CardHeader("Audit Trail"),
                    dbc.CardBody([
                        html.P(id='inspect-audit-info'),
                        html.A('Download Audit Bundle', id='inspect-audit-link', href='', download='', className='btn btn-primary')
                    ])
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Close", id='inspect-modal-close', className='ml-auto')
            )
        ], id='inspect-modal', size='xl', is_open=False),
        
        # Store to hold selected ticker for inspection
        dcc.Store(id='inspect-ticker-store', data=None),
    ])


def register_callbacks(app, SH=None):
    if SH is None:
        import _shared as SH

    def _demo_target(max_tickers):
        df, p = _load_picks_df()
        if df is None:
            return {'ok': False, 'error': p}
        return df

    # Only set the job store here. Let the poll callback manage status text and
    # poll enabling/disabled flags to avoid duplicate-output conflicts.
    @app.callback(Output('mp-current-job', 'data'), Input('mp-run-btn', 'n_clicks'), State('mp-max-tickers', 'value'), prevent_initial_call=True)
    def _run(n_clicks, max_tickers):
        if not n_clicks:
            raise PreventUpdate
        if SH is not None and hasattr(SH, 'start_background_job'):
            jid = SH.start_background_job(_demo_target, args=(max_tickers,), job_name='monthly_picks')
        else:
            jid = _start_local_job(_demo_target, args=(max_tickers,), name='monthly_picks')
        return jid

    @app.callback(Output('mp-results-area', 'children'), Output('mp-status', 'children'), Output('mp-poll-interval', 'disabled'), Input('mp-poll-interval', 'n_intervals'), State('mp-current-job', 'data'), prevent_initial_call=True, allow_duplicate=True)
    def _poll(n_intervals, current_job):
        if not current_job:
            raise PreventUpdate
        job = None
        if SH is not None and hasattr(SH, 'JOBS'):
            job = SH.JOBS.get(current_job)
        if job is None:
            job = JOBS.get(current_job)
        if not job:
            return html.Div(), 'Unknown job', True
        status = job.get('status')
        if status in ('queued', 'running'):
            return html.Div(), f'Job {current_job}: {status}', False
        if status == 'error':
            return html.Pre(str(job.get('result'))), f'Job {current_job} error', True
        if status == 'done':
            res = job.get('result')
            try:
                import pandas as pd
                if isinstance(res, pd.DataFrame):
                    df = _prepare_display_df(res)
                    records = df.fillna('').to_dict(orient='records')
                    cols = []
                    for c in df.columns:
                        col = {'name': c, 'id': c}
                        try:
                            if c in ('price_live', 'price_start_of_month'):
                                col.update({'type': 'numeric', 'format': {'specifier': ',.2f'}})
                            elif c in ('daily_change', 'overall_change_from_start_of_month'):
                                col.update({'type': 'numeric', 'format': {'specifier': '.4f'}})
                        except Exception:
                            pass
                        cols.append(col)

                    style_cell = {
                        'whiteSpace': 'nowrap',
                        'height': '28px',
                        'textAlign': 'left',
                        'fontSize': '11px',
                        'padding': '4px 6px',
                        'color': '#000',
                    }

                    style_data_conditional = []
                    if 'price_live' in df.columns:
                        style_data_conditional.append({'if': {'column_id': 'price_live'}, 'textAlign': 'right'})
                    for c in ('daily_change', 'overall_change_from_start_of_month'):
                        if c in df.columns:
                            style_data_conditional.append({'if': {'column_id': c}, 'textAlign': 'right'})
                            style_data_conditional.append({'if': {'filter_query': f'{{{c}}} > 0', 'column_id': c}, 'color': '#10B981'})
                            style_data_conditional.append({'if': {'filter_query': f'{{{c}}} < 0', 'column_id': c}, 'color': '#EF4444'})

                    table = dash_table.DataTable(
                        columns=cols,
                        data=records,
                        page_size=25,
                        style_table={'overflowX': 'auto', 'width': '100%'},
                        style_cell=style_cell,
                        style_data_conditional=style_data_conditional,
                        style_header={'fontSize': '11px', 'fontWeight': '600'},
                        style_as_list_view=True,
                    )
                    # Include metrics below the table
                    try:
                        metrics = _render_metrics(df)
                        results_children = html.Div([table, metrics])
                    except Exception:
                        results_children = table
                    return results_children, f'Job {current_job} completed', True
            except Exception:
                pass
            if isinstance(res, dict) and res.get('ok') is False:
                return html.Pre(str(res)), f'Job {current_job} failed', True
            return html.Pre(str(res)), f'Job {current_job} completed', True
        return html.Div(), f'Job {current_job}: {status}', False

    # Support both 'tabs' (legacy/standalone) and 'dashboard-tabs' (integrated dashboard)
    # Try to register with both, use allow_duplicate=True to handle conflicts
    try:
        @app.callback(
            Output('mp-standalone-table', 'children'),
            Input('dashboard-tabs', 'active_tab'),
            Input('mp-refresh-prices', 'n_clicks'),
            Input('mp-page-load-ts', 'data'),
            prevent_initial_call=False
        )
        def _load_standalone_table_integrated(active_tab_value, refresh_n, page_ts):
            return _load_standalone_table_impl(active_tab_value, refresh_n, page_ts)
    except Exception as e:
        logging.warning(f"Could not register integrated dashboard callback: {e}")
    
    try:
        @app.callback(
            Output('mp-standalone-table', 'children'),
            Input('tabs', 'value'),
            Input('mp-refresh-prices', 'n_clicks'),
            Input('mp-page-load-ts', 'data'),
            prevent_initial_call=False,
            allow_duplicate=True
        )
        def _load_standalone_table_legacy(active_tab_value, refresh_n, page_ts):
            return _load_standalone_table_impl(active_tab_value, refresh_n, page_ts)
    except Exception as e:
        logging.warning(f"Could not register legacy tabs callback: {e}")
    
    def _load_standalone_table_impl(active_tab_value, refresh_n, page_ts):
        # Accept several possible tab value formats used elsewhere in the app
        # (for example 'tab-monthly-picks' in market_dashboard). Trigger when
        # the active tab name indicates monthly picks.
        # Accept a broad set of possible tab value formats that may come from
        # different parts of the app or from renderer-shaped POSTs: hyphen, underscore,
        # prefixed with 'tab-' or 'tab_'. This avoids accidental PreventUpdate when the
        # client uses a slightly different naming convention.
        try:
            at = str(active_tab_value or '')
        except Exception:
            at = ''
        # debug log
        try:
            logging.info(f"[monthly_picks] _load_standalone_table active_tab_value={active_tab_value} at='{at}' refresh_n={refresh_n} page_ts={page_ts}")
        except Exception:
            pass
        ok_keys = ('monthly_picks', 'monthly-picks', 'monthlypicks', 'monthly')
        # Allow rendering when active_tab_value is falsy (some test runners
        # post without a concrete tab value). Only skip rendering when an
        # explicit non-matching tab value is present.
        if at and not any(k in at for k in ok_keys):
            # Return an empty Div so unrelated tab changes don't trigger work.
            return [html.Div()]
        df, p = _load_picks_df()
        try:
            print(f"[monthly_picks] _load_standalone_table loaded picks path={p} df_ok={df is not None}")
        except Exception:
            pass
        if df is None:
            return [html.Div(f'No picks available: {p}')]
        # Render as a Dash DataTable so we can apply conditional formatting
        try:
            # First, attempt to fetch live prices (prefer SH.mt_mod when available)
            try:
                # Always attempt to refresh live prices before preparing display.
                dfn = df.copy()
                dfn2 = None
                try:
                    _SH = SH
                    # attempt to fetch using SH if available
                    dfn2 = _fetch_live_prices_for_df(dfn, SH=_SH)
                except Exception:
                    dfn2 = None

                # If upstream helpers didn't populate live prices, call our new helper
                if dfn2 is None:
                    try:
                        # call the price_fetcher directly and merge results into the DataFrame
                        from utils.price_fetcher import get_live_prices
                        tickers = dfn['ticker'].dropna().unique().tolist() if 'ticker' in dfn.columns else []
                        if tickers:
                            pf_map = get_live_prices(tickers, investment=1000.0, batch_size=8)
                            # map fields back onto dfn
                            dfn['price_live'] = dfn['ticker'].map(lambda t: pf_map.get(t, {}).get('current_price'))
                            dfn['daily_change'] = dfn['ticker'].map(lambda t: pf_map.get(t, {}).get('daily_change'))
                            dfn['month_start'] = dfn['ticker'].map(lambda t: pf_map.get(t, {}).get('month_start_price'))
                            try:
                                dfn['price_start_of_month'] = dfn['month_start']
                            except Exception:
                                pass
                            dfn['profit_loss'] = dfn['ticker'].map(lambda t: pf_map.get(t, {}).get('profit_loss'))
                    except Exception:
                        pass
                else:
                    df = dfn2
                # If we updated dfn in-place above, use it as df
                try:
                    df = dfn
                except Exception:
                    pass
            except Exception:
                pass

            d = _prepare_display_df(df)
            try:
                # Instrumentation: log shape and a small sample to server logs so
                # we can verify what the UI receives (helps debug placeholder issue).
                try:
                    sam = d.head(5).to_dict(orient='records') if hasattr(d, 'head') else []
                    print(f"[monthly_picks] prepared display df shape={getattr(d, 'shape', None)} sample={sam}")
                except Exception:
                    print(f"[monthly_picks] prepared display df shape={getattr(d, 'shape', None)} (failed to stringify sample)")
            except Exception:
                pass
            # Ensure DataFrame columns are unique before building the DataTable
            try:
                d = d.loc[:, ~d.columns.duplicated()]
            except Exception:
                pass

            # build datatable columns with formats
            records = d.fillna('').to_dict(orient='records')
            cols = []
            display_name_map = {
                'Rank': 'Rank',
                'ticker': 'Ticker',
                'price_live': 'Current Price',
                'daily_change': 'Daily Change %',
                'price_start_of_month': 'Month Start Price',
                'month_start_source': 'Month Start Source',
                'month_start_date': 'Month Start Date',
                'profit_loss': 'Profit/Loss',
                'start_date': 'Start Date'
            }
            for c in d.columns:
                col = {'name': display_name_map.get(c, c), 'id': c}
                try:
                    if c in ('price_live', 'month_start', 'price_start_of_month'):
                        col.update({'type': 'numeric', 'format': {'specifier': ',.2f'}})
                    elif c in ('daily_change', 'overall_change', 'profit_loss'):
                        if c == 'profit_loss':
                            col.update({'type': 'numeric', 'format': {'specifier': ',.2f'}})
                        else:
                            col.update({'type': 'numeric', 'format': {'specifier': '.4f'}})
                except Exception:
                    pass
                cols.append(col)

            style_cell = {
                'whiteSpace': 'nowrap',
                'height': '28px',
                'textAlign': 'left',
                'fontSize': '11px',
                'padding': '4px 6px',
                'color': '#000',
            }

            style_data_conditional = []
            if 'price_live' in d.columns:
                style_data_conditional.append({'if': {'column_id': 'price_live'}, 'textAlign': 'right'})
            for c in ('daily_change', 'overall_change', 'profit_loss'):
                if c in d.columns:
                    style_data_conditional.append({'if': {'column_id': c}, 'textAlign': 'right'})
                    style_data_conditional.append({'if': {'filter_query': f'{{{c}}} > 0', 'column_id': c}, 'color': '#10B981'})
                    style_data_conditional.append({'if': {'filter_query': f'{{{c}}} < 0', 'column_id': c}, 'color': '#EF4444'})

            tbl = dash_table.DataTable(
                columns=cols,
                data=records,
                id='mp-datatable',
                page_size=25,
                style_table={'overflowX': 'auto', 'width': '100%'},
                style_cell=style_cell,
                style_data_conditional=style_data_conditional,
                style_header={'fontSize': '11px', 'fontWeight': '600'},
                style_as_list_view=True,
                row_selectable='single',  # Enable row selection
                selected_rows=[],
            )
            try:
                metrics = _render_metrics(d)
                info = html.Div(f'Loaded picks from: {p}', style={'fontSize': '90%', 'color': '#666', 'marginBottom': '6px'})
                # include fetch path instrumentation if present
                try:
                    fp = d.get('_fetch_path') if hasattr(d, 'get') else None
                    if not fp and hasattr(df, '_fetch_path'):
                        fp = getattr(df, '_fetch_path')
                    if fp:
                        info = html.Div([info, html.Div(f'price_fetch_path: {fp}', style={'fontSize': '85%', 'color': '#888', 'marginTop': '4px'})])
                except Exception:
                    pass
                return [html.Div([info, tbl, metrics])]
            except Exception:
                info = html.Div(f'Loaded picks from: {p}', style={'fontSize': '90%', 'color': '#666', 'marginBottom': '6px'})
                try:
                    fp = d.get('_fetch_path') if hasattr(d, 'get') else None
                    if not fp and hasattr(df, '_fetch_path'):
                        fp = getattr(df, '_fetch_path')
                    if fp:
                        info = html.Div([info, html.Div(f'price_fetch_path: {fp}', style={'fontSize': '85%', 'color': '#888', 'marginTop': '4px'})])
                except Exception:
                    pass
                return [html.Div([info, tbl])]
        except Exception:
            # Fallback to HTML if DataTable fails
            try:
                html_tbl = df.to_html(classes='table table-sm table-striped', index=False, escape=True)
                return [html.Div([html.Div(f'Loaded picks from: {p}', style={'fontSize': '90%', 'color': '#666', 'marginBottom': '6px'}), html.Div(dangerously_set_inner_html={'__html': html_tbl})])]
            except Exception:
                return [html.Div(f'Loaded picks from: {p} (failed to render table)')]

        # Ensure clicking the Refresh button updates a page-load timestamp store so
        # the table callback reliably recomputes (useful if the client caches results).
        @app.callback(Output('mp-page-load-ts', 'data'), Input('mp-refresh-prices', 'n_clicks'), State('mp-page-load-ts', 'data'))
        def _refresh_page_ts(n_clicks, current_ts):
            # When the refresh button is clicked, return a new timestamp to trigger
            # dependent callbacks (and avoid PreventUpdate so repeated clicks work).
            try:
                if not n_clicks:
                    # preserve existing value on initial load
                    raise PreventUpdate
            except Exception:
                raise PreventUpdate
            try:
                return int(time.time())
            except Exception:
                return current_ts

    @app.callback(Output('mp-download-link', 'href'), Input('mp-download-link', 'n_clicks'))
    def _download(n_clicks):
        if not n_clicks:
            raise PreventUpdate
        df, p = _load_picks_df()
        if df is None:
            raise PreventUpdate
        try:
            import base64
            csv = df.to_csv(index=False)
            b = base64.b64encode(csv.encode('utf-8')).decode('ascii')
            return f'data:text/csv;base64,{b}'
        except Exception:
            raise PreventUpdate

    # Modal callbacks for Inspect Pick feature
    @app.callback(
        Output('inspect-modal', 'is_open'),
        Output('inspect-ticker-store', 'data'),
        Input('mp-datatable', 'selected_rows'),
        Input('inspect-modal-close', 'n_clicks'),
        State('inspect-modal', 'is_open'),
        State('mp-datatable', 'data'),
        prevent_initial_call=True
    )
    def toggle_inspect_modal(selected_rows, close_clicks, is_open, table_data):
        """Open modal when row is selected, close when close button is clicked."""
        from dash import callback_context
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == 'inspect-modal-close':
            return False, None
        
        if triggered_id == 'mp-datatable' and selected_rows:
            # Get the ticker from the selected row
            try:
                row_idx = selected_rows[0]
                ticker = table_data[row_idx].get('ticker')
                return True, ticker
            except Exception:
                raise PreventUpdate
        
        raise PreventUpdate

    @app.callback(
        Output('inspect-modal-title', 'children'),
        Output('inspect-summary-body', 'children'),
        Output('inspect-price-chart', 'figure'),
        Output('inspect-shap-table', 'children'),
        Output('inspect-trade-info', 'children'),
        Output('inspect-events-body', 'children'),
        Output('inspect-audit-info', 'children'),
        Output('inspect-audit-link', 'download'),
        Input('inspect-ticker-store', 'data'),
        prevent_initial_call=True
    )
    def populate_inspect_modal(ticker):
        """Populate modal with detailed information about the selected pick."""
        if not ticker:
            raise PreventUpdate
        
        try:
            import pandas as pd
            import plotly.graph_objects as go
            from datetime import datetime, timedelta
            import sys
            import json
            
            # Load the picks dataframe
            df, picks_path = _load_picks_df()
            if df is None:
                raise PreventUpdate
            
            # Find the row for this ticker
            row = df[df['ticker'] == ticker]
            if row.empty:
                raise PreventUpdate
            row = row.iloc[0]
            
            # Modal title
            title = f"Inspect Pick: {ticker}"
            
            # Summary card content
            summary_items = []
            for field, label in [
                ('score', 'Model Score'),
                ('predicted_return_net', 'Net Return (after slippage)'),
                ('price_live', 'Current Price'),
                ('position_size_dollars', 'Position Size'),
                ('liquidity_flag', 'Liquidity'),
            ]:
                if field in row and row[field] is not None and not pd.isna(row[field]):
                    val = row[field]
                    if field == 'position_size_dollars':
                        val_str = f"${val:,.2f}"
                    elif field in ('score', 'predicted_return_net'):
                        val_str = f"{val:.4f}"
                    elif field == 'price_live':
                        val_str = f"${val:.2f}"
                    else:
                        val_str = str(val)
                    summary_items.append(html.P([html.Strong(f"{label}: "), val_str]))
            
            summary_body = html.Div(summary_items) if summary_items else html.P("No summary data available")
            
            # Price chart - try to load historical prices
            price_fig = go.Figure()
            try:
                # Try to load price history from various sources
                utils_path = os.path.join(SH.PROJECT_ROOT, 'utils')
                if utils_path not in sys.path:
                    sys.path.insert(0, utils_path)
                from price_fetch import get_price_single
                
                # Get 6 months of price history
                end_date = datetime.now()
                start_date = end_date - timedelta(days=180)
                
                # For now, create a placeholder chart
                price_fig.add_annotation(
                    text=f"Price chart for {ticker}<br>Historical data integration pending",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color='#666')
                )
                price_fig.update_layout(
                    title=f"{ticker} - 6 Month Price History",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    height=300,
                    margin=dict(l=40, r=40, t=40, b=40)
                )
            except Exception:
                price_fig.add_annotation(
                    text="Price chart unavailable",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            # SHAP table - try to load from utils/explain.py
            shap_content = html.P("SHAP explanations pending (numpy compatibility issue)")
            try:
                from explain import load_explanation, format_shap_for_ui
                shap_data = load_explanation(ticker)
                if shap_data and 'shap_values' in shap_data:
                    shap_ui = format_shap_for_ui(shap_data)
                    # Convert to simple table
                    shap_rows = []
                    for item in shap_ui[:10]:  # Top 10 features
                        shap_rows.append(html.Tr([
                            html.Td(item['feature']),
                            html.Td(f"{item['value']:.4f}"),
                            html.Td(f"{item['contribution']:.4f}", style={'color': '#10B981' if item['contribution'] > 0 else '#EF4444'})
                        ]))
                    shap_content = html.Table([
                        html.Thead(html.Tr([
                            html.Th('Feature'),
                            html.Th('Value'),
                            html.Th('SHAP Contribution')
                        ])),
                        html.Tbody(shap_rows)
                    ], style={'width': '100%', 'fontSize': '12px'})
            except Exception:
                pass
            
            # Trade sizing info
            trade_items = []
            for field, label in [
                ('position_size_dollars', 'Position Size'),
                ('expected_slippage_pct', 'Expected Slippage'),
                ('predicted_return_net', 'Net Return'),
                ('liquidity_flag', 'Liquidity Flag'),
                ('avg_dollar_vol', 'Avg Daily Volume'),
            ]:
                if field in row and row[field] is not None and not pd.isna(row[field]):
                    val = row[field]
                    if field == 'position_size_dollars':
                        val_str = f"${val:,.2f}"
                    elif field in ('expected_slippage_pct', 'predicted_return_net'):
                        val_str = f"{val:.4f} ({val*100:.2f}%)"
                    elif field == 'avg_dollar_vol':
                        val_str = f"${val:,.0f}"
                    else:
                        val_str = str(val)
                    trade_items.append(html.P([html.Strong(f"{label}: "), val_str]))
            
            # Add trade schedule if available
            if 'trade_schedule_json' in row and row['trade_schedule_json']:
                try:
                    schedule = json.loads(row['trade_schedule_json'])
                    trade_items.append(html.Hr())
                    trade_items.append(html.P([html.Strong("Trade Schedule (TWAP):"), ]))
                    for i, slot in enumerate(schedule[:5], 1):  # Show first 5 slots
                        trade_items.append(html.P(
                            f"  {slot['time']}: ${slot['notional']:,.2f}",
                            style={'fontSize': '11px', 'marginLeft': '10px'}
                        ))
                    if len(schedule) > 5:
                        trade_items.append(html.P(f"  ... and {len(schedule)-5} more slots", style={'fontSize': '11px', 'marginLeft': '10px', 'color': '#666'}))
                except Exception:
                    pass
            
            trade_info = html.Div(trade_items) if trade_items else html.P("No trade sizing data available")
            
            # Audit info
            date_str = row.get('date', datetime.now().strftime('%Y%m%d'))
            if isinstance(date_str, pd.Timestamp):
                date_str = date_str.strftime('%Y%m%d')
            elif isinstance(date_str, str) and '-' in date_str:
                date_str = date_str.replace('-', '')[:8]
            
            # Recent events for this ticker
            ticker_events = get_ticker_events(ticker, max_events=5)
            if ticker_events:
                events_items = []
                for evt in ticker_events:
                    severity_color = 'danger' if evt['severity'] == 'HIGH' else 'warning' if evt['severity'] == 'MEDIUM' else 'info'
                    severity_icon = '🔴' if evt['severity'] == 'HIGH' else '🟡' if evt['severity'] == 'MEDIUM' else '🔵'
                    
                    events_items.append(dbc.ListGroupItem([
                        html.Div([
                            dbc.Badge(evt['event_type'], color='primary', className="me-2"),
                            dbc.Badge(f"{severity_icon} {evt['severity']}", color=severity_color)
                        ], className="mb-2"),
                        html.P(evt['headline'], className="mb-1", style={'font-size': '14px'}),
                        html.Small(
                            f"{pd.to_datetime(evt['timestamp']).strftime('%b %d, %I:%M %p')}", 
                            className="text-muted"
                        )
                    ]))
                events_content = dbc.ListGroup(events_items, flush=True)
            else:
                events_content = html.P("No recent events", className="text-muted")
            
            audit_info = html.Div([
                html.P(f"Generated: {date_str}"),
                html.P(f"Ticker: {ticker}"),
                html.P("Audit bundle contains: model metadata, feature snapshot, SHAP explanations, trade parameters")
            ])
            
            audit_filename = f"audit_{ticker}_{date_str}.zip"
            
            return title, summary_body, price_fig, shap_content, trade_info, events_content, audit_info, audit_filename
            
        except Exception as e:
            import traceback
            err_msg = f"Error loading pick details: {str(e)}\n{traceback.format_exc()}"
            return f"Error: {ticker}", html.P(err_msg), go.Figure(), html.P("Error"), html.P("Error"), html.P("Error"), html.P("Error"), "error.zip"

    @app.callback(
        Output('inspect-audit-link', 'href'),
        Input('inspect-audit-link', 'n_clicks'),
        State('inspect-ticker-store', 'data'),
        prevent_initial_call=True
    )
    def generate_audit_download(n_clicks, ticker):
        """Generate and serve audit bundle ZIP when download link is clicked."""
        if not n_clicks or not ticker:
            raise PreventUpdate
        
        try:
            import pandas as pd
            import base64
            import sys
            
            # Load pick data
            df, picks_path = _load_picks_df()
            if df is None:
                raise PreventUpdate
            
            row = df[df['ticker'] == ticker]
            if row.empty:
                raise PreventUpdate
            
            pick_data = row.iloc[0].to_dict()
            
            # Get date
            date_str = pick_data.get('date', datetime.now().strftime('%Y%m%d'))
            if isinstance(date_str, pd.Timestamp):
                date_str = date_str.strftime('%Y%m%d')
            elif isinstance(date_str, str) and '-' in date_str:
                date_str = date_str.replace('-', '')[:8]
            
            # Generate audit bundle
            utils_path = os.path.join(SH.PROJECT_ROOT, 'utils')
            if utils_path not in sys.path:
                sys.path.insert(0, utils_path)
            
            from audit import generate_audit_bundle
            
            artifacts_dir = os.path.join(SH.PROJECT_ROOT, 'models', 'artifacts')
            os.makedirs(artifacts_dir, exist_ok=True)
            
            zip_path = generate_audit_bundle(
                ticker=ticker,
                date=date_str,
                pick_data=pick_data,
                output_dir=artifacts_dir,
                include_shap=True,
                include_snapshot=True
            )
            
            if not zip_path or not os.path.exists(zip_path):
                raise PreventUpdate
            
            # Read and encode ZIP file
            with open(zip_path, 'rb') as f:
                zip_data = f.read()
            
            b64 = base64.b64encode(zip_data).decode('ascii')
            return f'data:application/zip;base64,{b64}'
            
        except Exception as e:
            import logging
            logging.error(f"Failed to generate audit bundle: {e}", exc_info=True)
            raise PreventUpdate

    return None
