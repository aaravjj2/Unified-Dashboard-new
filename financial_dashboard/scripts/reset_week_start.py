#!/usr/bin/env python3
"""Reset weekly start prices for the latest weekly picks.

This script loads the latest weekly picks CSV, attempts to fetch recent
price series (using the app helpers), derives a reasonable
`price_start_of_week` for each ticker, and writes `data/weekly_enriched.parquet`.

It is safe to re-run; it will overwrite the parquet with newly-derived values.
"""
import os
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

def main():
    try:
        import pandas as pd
        import importlib
        wp = importlib.import_module('Dash.tabs.weekly_picks')
        # load latest picks
        df, p = wp._load_weekly_df()
        if df is None:
            print('No weekly picks found:', p)
            return 1
        # load shared if available to give fetch helper access to mt_mod
        SH = None
        try:
            SH = importlib.import_module('Dash._shared')
        except Exception:
            SH = None

        print('Loaded picks:', p, 'rows:', len(df))

        # fetch live prices and week_start where possible
        fetched = wp._fetch_live_prices_for_week_df(df, SH=SH)

        # build enrichment dataframe
        edf = pd.DataFrame()
        if 'ticker' in fetched.columns:
            edf['ticker'] = fetched['ticker']
        else:
            # fallback to index-based
            edf['ticker'] = fetched.index.astype(str)

        # prefer explicit week_start from fetched; if missing, derive from last_price/ret fields
        def _choose_week_start(row):
            # fetched may have week_start col
            ws = row.get('week_start') if 'week_start' in row.index else None
            if ws is not None and not pd.isna(ws):
                return ws
            # prefer price_start_of_week if present (from other sources)
            if 'price_start_of_week' in row.index:
                x = row.get('price_start_of_week')
                if x is not None and not pd.isna(x):
                    return x
            # try derive from last_price and ret_5d/ret_1w/ret_7d
            lp = None
            for c in ('price_live','last_price','last_price_x','last_price_y'):
                if c in row.index:
                    v = row.get(c)
                    try:
                        if v is not None and not pd.isna(v):
                            vv = float(v)
                            if vv > 0:
                                lp = vv
                                break
                    except Exception:
                        continue
            r5 = None
            for c in ('ret_5d','ret_1w','ret_7d'):
                if c in row.index:
                    v = row.get(c)
                    try:
                        if v is not None and not pd.isna(v):
                            r5 = float(v); break
                    except Exception:
                        continue
            if lp is not None and r5 is not None:
                denom = 1.0 + float(r5)
                if denom != 0:
                    try:
                        return float(lp) / denom
                    except Exception:
                        pass
            # as a last resort, if fetched had a sequence in prices_map we can't access here,
            # return None to indicate unknown
            return None

        edf['price_start_of_week'] = fetched.apply(_choose_week_start, axis=1)
        edf['generated_utc'] = datetime.utcnow().isoformat()

        # write to data/weekly_enriched.parquet
        out_dir = os.path.join(ROOT, 'data')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'weekly_enriched.parquet')
        try:
            edf.to_parquet(out_path, index=False)
            print('Wrote', out_path)
        except Exception as e:
            print('Failed to write parquet, falling back to csv:', e)
            out_csv = os.path.join(out_dir, 'weekly_enriched.csv')
            edf.to_csv(out_csv, index=False)
            print('Wrote', out_csv)
        # summary
        nonnull = int(edf['price_start_of_week'].notna().sum())
        print('Computed price_start_of_week for', nonnull, 'of', len(edf))
        return 0
    except Exception as e:
        print('Error:', e)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
