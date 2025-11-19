"""
Simple compute script for Market Trends.
- Fetches SPY price via yfinance
- Computes r1m (21 trading days) and ma50_vs_200 gap
- Builds a tiny deterministic composite and regime label
- Writes JSON to output/market_trends/regime_pred_{date}.json

Usage: run as module or call compute_and_write() from Dash module
"""
import os, json, time
from datetime import datetime, timedelta

try:
    import yfinance as yf
except Exception:
    yf = None

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'market_trends')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

# Keys: read keys.env if present for finnhub
KEYS_PATH = os.path.join(BASE_DIR, '..', 'keys.env')


def read_keys():
    keys = {}
    try:
        if os.path.exists(KEYS_PATH):
            with open(KEYS_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=',1)
                        keys[k.strip()] = v.strip()
    except Exception:
        pass
    return keys


def fetch_history_for_tickers(tickers, days=365):
    if yf is None:
        raise RuntimeError('yfinance not installed in venv')
    end = datetime.utcnow().date()
    start = end - timedelta(days=days*2)
    # yfinance can accept a list of tickers and returns a multi-column DataFrame
    data = yf.download(tickers, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(), progress=False)
    if data is None or data.empty:
        raise RuntimeError(f'Failed to fetch {tickers}')
    out = {}
    # Multiple tickers case
    if isinstance(tickers, (list, tuple)) and len(tickers) > 1:
        # data columns may be MultiIndex (attr, ticker) or flat with ticker suffixes
        try:
            if hasattr(data.columns, 'levels') and len(data.columns.levels) >= 2:
                symbols = list(data.columns.levels[1])
                for sym in symbols:
                    try:
                        df_sym = data.xs(sym, axis=1, level=1, drop_level=False)
                    except Exception:
                        # some yfinance versions use (ticker, attr) ordering
                        try:
                            df_sym = data.xs(sym, axis=1, level=0, drop_level=False)
                        except Exception:
                            continue
                    # flatten columns to attribute names
                    flat_cols = []
                    for c in df_sym.columns:
                        if isinstance(c, tuple):
                            flat_cols.append('_'.join([str(x) for x in c if x is not None and str(x) != '']))
                        else:
                            flat_cols.append(str(c))
                    df_sym.columns = flat_cols
                    out[sym] = df_sym
            else:
                # Fallback: try splitting by column suffix or download individually
                for sym in tickers:
                    cols = [c for c in data.columns if sym in str(c)]
                    if cols:
                        df_sym = data[cols].copy()
                        out[sym] = df_sym
                    else:
                        df_sym = yf.download(sym, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(), progress=False)
                        if hasattr(df_sym, 'columns'):
                            flat_cols = [('_'.join([str(x) for x in c if x is not None and str(x) != '']) if isinstance(c, tuple) else str(c)) for c in df_sym.columns]
                            df_sym.columns = flat_cols
                        out[sym] = df_sym
        except Exception:
            # best-effort: try per-symbol download
            for sym in tickers:
                df_sym = yf.download(sym, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(), progress=False)
                if hasattr(df_sym, 'columns'):
                    flat_cols = [('_'.join([str(x) for x in c if x is not None and str(x) != '']) if isinstance(c, tuple) else str(c)) for c in df_sym.columns]
                    df_sym.columns = flat_cols
                out[sym] = df_sym
    else:
        # single ticker
        sym = tickers[0] if isinstance(tickers, (list, tuple)) else tickers
        df = data
        out[sym] = df
    return out


def compute_composite_from_df(df):
    # df is historical OHLCV with DatetimeIndex
    out = {}
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    # ensure sorted
    df = df.sort_index()
    # pick a reasonable close column robustly
    if 'Close' in df.columns:
        close = df['Close']
    elif 'Adj Close' in df.columns:
        close = df['Adj Close']
    else:
        # fallback: if single-column DataFrame, use that
        if df.shape[1] == 1:
            close = df.iloc[:, 0]
        else:
            # try common names
            for c in df.columns:
                if 'close' in str(c).lower():
                    close = df[c]
                    break
            else:
                raise RuntimeError(f'No close column found. Columns: {list(df.columns)}')
    n = len(close)
    if n < 60:
        raise RuntimeError('Not enough history')
    # r1m: approx 21 trading days
    # ensure scalar arithmetic
    try:
        last = float(close.iloc[-1])
        prev21 = float(close.iloc[-21])
        r1m = (last / prev21) - 1
    except Exception:
        # fallback to pandas arithmetic then coerce
        r1m = ((close.iloc[-1]) / (close.iloc[-21])) - 1
    ma50 = close.rolling(50).mean().iloc[-1]
    ma200 = close.rolling(200).mean().iloc[-1]
    try:
        if pd.isna(ma200) or float(ma200) == 0.0:
            ma50_vs200 = 0.0
        else:
            ma50_vs200 = float((ma50 - ma200) / ma200)
    except Exception:
        ma50_vs200 = 0.0
    out['r1m'] = float(r1m)
    out['ma50_vs200'] = float(ma50_vs200)
    # simple composite: weighted sum
    composite = 0.6 * float(r1m) + 0.4 * float(ma50_vs200)
    out['composite'] = float(composite)
    # thresholds
    if composite >= 0.04:
        label = 'Strong Bull'
    elif composite >= 0.01:
        label = 'Bull'
    elif composite > -0.01:
        label = 'Neutral'
    elif composite > -0.04:
        label = 'Bear'
    else:
        label = 'Strong Bear'
    out['label'] = label
    out['generated_at'] = datetime.utcnow().isoformat()
    return out


# pandas is imported near the top to support computation

def compute_and_write(tickers=None):
    # tickers: None or list of tickers (strings). If None, default to ['SPY']
    if tickers is None or (isinstance(tickers, (list, tuple)) and len(tickers) == 0):
        tickers = ['SPY']
    # fetch history for tickers
    fetched = fetch_history_for_tickers(tickers, days=365)
    detailed = []
    prices = {}
    for sym, df in fetched.items():
        try:
            res = compute_composite_from_df(df)
            res['ticker'] = sym
            detailed.append(res)
            # coerce df to simple records for storage
            try:
                df_to_store = df.copy()
                # reset index and ensure column names are strings
                df_to_store = df_to_store.reset_index()
                df_to_store.columns = [('_'.join([str(x) for x in c]) if isinstance(c, tuple) else str(c)) for c in df_to_store.columns]
                # coerce values to JSON-serializable types
                def _safe_val(v):
                    try:
                        if pd.isna(v):
                            return None
                    except Exception:
                        pass
                    # pandas Timestamp or datetime
                    try:
                        import pandas as _pd
                        if isinstance(v, (_pd.Timestamp,)):
                            return v.isoformat()
                    except Exception:
                        pass
                    try:
                        if isinstance(v, datetime):
                            return v.isoformat()
                    except Exception:
                        pass
                    # numpy scalar -> python scalar
                    try:
                        import numpy as _np
                        if isinstance(v, (_np.generic,)):
                            return v.item()
                    except Exception:
                        pass
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        return v
                    return str(v)

                df_to_store = df_to_store.map(_safe_val)
                prices[sym] = df_to_store.to_dict(orient='records')
            except Exception:
                # fallback: try converting rows manually
                try:
                    rows = []
                    for _, r in df.reset_index().iterrows():
                        row = {}
                        for k, v in r.items():
                            try:
                                if pd.isna(v):
                                    row[str(k)] = None
                                    continue
                            except Exception:
                                pass
                            if isinstance(v, datetime):
                                row[str(k)] = v.isoformat()
                            else:
                                try:
                                    import numpy as _np
                                    if isinstance(v, (_np.generic,)):
                                        row[str(k)] = v.item()
                                    else:
                                        row[str(k)] = v if isinstance(v, (str, int, float, bool)) else str(v)
                                except Exception:
                                    row[str(k)] = v if isinstance(v, (str, int, float, bool)) else str(v)
                        rows.append(row)
                    prices[sym] = rows
                except Exception:
                    prices[sym] = None
        except Exception:
            # skip symbols that fail
            try:
                prices[sym] = None
            except Exception:
                pass

    out = {
        'ok': True,
        'generated_at': datetime.utcnow().isoformat(),
        'detailed': detailed,
        'prices': prices
    }
    date = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(OUTPUT_DIR, f'regime_pred_{date}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    return path


if __name__ == '__main__':
    p = compute_and_write()
    print('Wrote', p)
