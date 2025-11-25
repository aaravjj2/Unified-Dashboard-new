"""Recompute weekly_enriched.parquet from latest weekly picks CSV.

This script will:
- load the latest weekly picks CSV
- parse the pick dates robustly
- try to use mt_mod batch series to compute the first trading price in the pick's ISO week
- if mt_mod not available or series missing, derive price_start_of_week from last_price and ret_1w/ret_5d when possible
- write `data/weekly_enriched.parquet`
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import importlib.util
import pandas as pd

from pathlib import Path

WP = Path(__file__).resolve().parents[1] / 'models' / 'weekly_run'
def _find_latest_picks():
    import glob
    pats = ['picks_*.csv', 'picks_weekly_*.csv']
    candidates = []
    for p in pats:
        candidates += glob.glob(str(WP / p))
    return max(candidates, key=os.path.getmtime) if candidates else None

def main():
    p = _find_latest_picks()
    if not p:
        print('no picks found')
        return 1
    print('using picks:', p)
    df = pd.read_csv(p)
    if 'date' not in df.columns:
        df['date'] = pd.Timestamp.now()
    else:
        try:
            sample = df['date'].dropna().astype(str).iloc[0] if not df['date'].dropna().empty else None
            if sample and len(sample) == 8 and sample.isdigit():
                df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d', errors='coerce')
            else:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
        except Exception:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

    wk_map = {row['ticker']: row['date'].to_period('W-MON') if pd.notna(row['date']) else None for _, row in df[['ticker','date']].iterrows()}

    # try mt_mod if present
    prices_map = {}
    try:
        shm = sys.modules.get('Dash._shared')
        if shm is None:
            sh_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '_shared.py'))
            if os.path.exists(sh_path):
                spec = importlib.util.spec_from_file_location('Dash._shared', sh_path)
                shm = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(shm)
        if shm is not None and getattr(shm, 'mt_mod', None) is not None:
            mt = shm.mt_mod
            if hasattr(mt, 'batch_fetch_chunked'):
                fetched = mt.batch_fetch_chunked(list(wk_map.keys()), period='2mo', interval='1d', cache_ttl=0, use_cache_only=False)
            elif hasattr(mt, 'batch_fetch'):
                fetched = mt.batch_fetch(list(wk_map.keys()), period='2mo', interval='1d', cache_ttl=0, use_cache_only=False)
            else:
                fetched = {}
            for tk, ser in (fetched.items() if isinstance(fetched, dict) else []):
                try:
                    if not isinstance(ser, pd.DataFrame):
                        prices_map[tk] = None; continue
                    s = ser.copy()
                    if 'date' in s.columns:
                        s['date'] = pd.to_datetime(s['date'])
                    price_col = None
                    for c in ('adj_close','Close','close'):
                        if c in s.columns:
                            price_col = c; break
                    if price_col is None:
                        prices_map[tk] = None; continue
                    s['week'] = s['date'].dt.to_period('W-MON')
                    tw = wk_map.get(tk)
                    if tw is None:
                        prices_map[tk] = None; continue
                    sub = s[s['week'] == tw]
                    if sub.empty:
                        prices_map[tk] = None
                    else:
                        prices_map[tk] = float(sub.sort_values('date').iloc[0][price_col])
                except Exception:
                    prices_map[tk] = None
    except Exception:
        prices_map = {}

    # If mt_mod didn't provide series for many tickers, fall back to yfinance
    missing = [tk for tk in wk_map.keys() if prices_map.get(tk) is None]
    if missing:
        try:
            import yfinance as yf
            # download in reasonable-sized batches to avoid issues
            B = 50
            for i in range(0, len(missing), B):
                batch = missing[i:i+B]
                try:
                    data = yf.download(batch, period='2mo', interval='1d', threads=False, progress=False)
                except Exception:
                    data = None
                if data is None or data.empty:
                    continue
                # data may be DataFrame with MultiIndex columns when multiple tickers
                def _series(tk):
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            s = data['Close'][tk].dropna()
                        else:
                            s = data['Close'].dropna()
                        if s.empty:
                            return None
                        dfp = s.reset_index()
                        dfp.columns = ['date', 'Close']
                        dfp['date'] = pd.to_datetime(dfp['date'])
                        return dfp
                    except Exception:
                        return None

                for tk in batch:
                    try:
                        ser = _series(tk)
                        if ser is None:
                            prices_map[tk] = None
                            continue
                        ser['week'] = ser['date'].dt.to_period('W-MON')
                        tw = wk_map.get(tk)
                        if tw is None:
                            prices_map[tk] = None; continue
                        sub = ser[ser['week'] == tw]
                        if sub.empty:
                            prices_map[tk] = None
                        else:
                            prices_map[tk] = float(sub.sort_values('date').iloc[0]['Close'])
                    except Exception:
                        prices_map[tk] = None
        except Exception:
            pass

    # fallback derive from last_price and ret_1w/ret_5d; iterate rows defensively
    rows = []
    now = pd.Timestamp.now().isoformat()
    for _, row in df.iterrows():
        tk = row.get('ticker')
        if tk is None:
            continue
        psw = prices_map.get(tk)
        if psw is None:
            # try derive from last_price variants
            lp = None
            for c in ('last_price', 'last_price_x', 'last_price_y'):
                try:
                    val = row.get(c, None)
                    if val is not None and val != '':
                        lp = float(val); break
                except Exception:
                    continue
            # try available return fields
            r5 = None
            for c in ('ret_5d', 'ret_1w', 'ret_7d'):
                try:
                    val = row.get(c, None)
                    if val is not None and val != '':
                        r5 = float(val); break
                except Exception:
                    continue
            if lp is not None and r5 is not None:
                try:
                    psw = float(lp) / (1.0 + r5)
                except Exception:
                    psw = None
            else:
                psw = lp if lp is not None else None
        rows.append({'ticker': tk, 'price_start_of_week': psw, 'generated_utc': now})

    out = pd.DataFrame(rows)
    outp = os.path.join(os.path.dirname(__file__), '..', 'data', 'weekly_enriched.parquet')

    # if an existing enrichment file exists, merge to preserve old non-null values
    try:
        if os.path.exists(outp):
            old = pd.read_parquet(outp)
            if 'ticker' in old.columns and 'price_start_of_week' in old.columns:
                old_map = old.set_index('ticker')['price_start_of_week'].to_dict()
                def _merge_val(r):
                    if r['price_start_of_week'] is None or (isinstance(r['price_start_of_week'], float) and pd.isna(r['price_start_of_week'])):
                        return old_map.get(r['ticker'])
                    return r['price_start_of_week']
                out['price_start_of_week'] = out.apply(_merge_val, axis=1)
    except Exception:
        pass

    out.to_parquet(outp, index=False)
    print('wrote', outp, 'rows', len(out))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
