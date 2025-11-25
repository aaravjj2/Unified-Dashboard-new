#!/usr/bin/env python3
"""Populate market fields (last_price, market_cap) for an enriched features parquet.

Approach:
 - Use yfinance.download in chunks to fetch recent Close prices for many tickers efficiently.
 - Optionally call yfinance.Ticker(t).info to fetch marketCap for up to --limit-info tickers (default 500) to avoid very long runs.

Writes an updated parquet to --out (defaults to overwrite input with .bak saved).
"""
import argparse
import time
from pathlib import Path
import pandas as pd


def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--features', required=True, help='Input features parquet (e.g. data/weekly_enriched_with_sentiment.parquet)')
    p.add_argument('--out', default=None, help='Output parquet path (defaults to overwrite input)')
    p.add_argument('--price-chunk', type=int, default=200, help='Number of tickers per yf.download batch')
    p.add_argument('--sleep', type=float, default=0.05, help='Sleep between Ticker.info calls')
    p.add_argument('--limit-info', type=int, default=500, help='Max number of per-ticker info calls to fetch market_cap (0 = none, default 500)')
    args = p.parse_args()

    try:
        import yfinance as yf
    except Exception:
        print('yfinance not available. Install with: pip install yfinance', flush=True)
        return

    features_path = Path(args.features)
    if not features_path.exists():
        print('Features file not found:', features_path)
        return

    out_path = Path(args.out) if args.out else features_path
    bak_path = features_path.with_suffix(features_path.suffix + '.bak')
    if not bak_path.exists():
        features_path.replace(bak_path)
        # work from backup
        src = bak_path
    else:
        src = bak_path

    df = pd.read_parquet(src)
    if 'ticker' not in df.columns:
        # try common alternatives
        for c in ('Symbol', 'symbol', 'Ticker'):
            if c in df.columns:
                df = df.rename(columns={c: 'ticker'})
                break

    tickers = df['ticker'].astype(str).str.strip().unique().tolist()
    print(f'Found {len(tickers)} tickers to update')

    # fetch prices in chunks via yf.download
    prices = {}
    for batch in chunked(tickers, args.price_chunk):
        try:
            data = yf.download(batch, period='5d', interval='1d', threads=False, progress=False)
        except Exception as e:
            print('yf.download failed for batch:', e)
            time.sleep(1.0)
            continue
        # data may be MultiIndex columns if multiple tickers
        for tk in batch:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    series = data['Close'][tk].dropna()
                else:
                    # single-ticker download returns series-like; fall back
                    if 'Close' in data:
                        series = data['Close'].dropna()
                    else:
                        series = pd.Series(dtype=float)
                prices[tk] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                prices[tk] = None
        # be polite
        time.sleep(0.25)

    # assign last_price
    df['last_price'] = df['ticker'].astype(str).map(lambda t: prices.get(t, None)).astype(float)

    # fetch market_cap via per-ticker info up to limit
    n_info = int(args.limit_info)
    if n_info > 0:
        print(f'Fetching market_cap info for up to {n_info} tickers (may be slow)')
        count = 0
        for t in tickers:
            if count >= n_info:
                break
            try:
                tkr = yf.Ticker(t)
                info = None
                try:
                    info = tkr.fast_info if hasattr(tkr, 'fast_info') else None
                except Exception:
                    info = None
                mcap = None
                if info and isinstance(info, dict) and 'market_cap' in info:
                    mcap = info.get('market_cap')
                else:
                    try:
                        ii = tkr.info
                        mcap = ii.get('marketCap') if isinstance(ii, dict) else None
                    except Exception:
                        mcap = None
                if mcap is not None:
                    df.loc[df['ticker'].astype(str) == t, 'market_cap'] = float(mcap)
                count += 1
            except KeyboardInterrupt:
                raise
            except Exception:
                pass
            time.sleep(args.sleep)
    else:
        print('Skipping per-ticker market_cap fetch (limit-info=0)')

    # fill NaNs with sensible defaults
    if 'market_cap' not in df.columns:
        df['market_cap'] = 0.0
    df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce').fillna(0.0)
    df['last_price'] = pd.to_numeric(df['last_price'], errors='coerce').fillna(0.0)

    # write out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print('Wrote updated features to:', out_path)


if __name__ == '__main__':
    main()
