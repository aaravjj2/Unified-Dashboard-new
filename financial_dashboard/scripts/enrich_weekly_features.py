#!/usr/bin/env python3
"""
Enrich a list of tickers with time-series-derived features using yfinance.

This script is intentionally conservative to respect yfinance rate limits:
- caches each ticker to `--cache-dir/{TICKER}.parquet`
- sleeps between requests (configurable)
- skips tickers that fail and records errors

Outputs a single parquet/csv of features (one row per ticker) suitable for `train_or_update_weekly.py`.

Features produced (per ticker):
- last_price
- vol_21 (std of daily returns)
- ret_1d, ret_5d, ret_21d
- ma5_rel, ma20_rel  (ma/last_price - 1)
- avg_dollar_vol_21

Keep the script small and robust; user warned about yfinance limits.
"""
import argparse
import time
import sys
import traceback
from pathlib import Path

import pandas as pd

try:
    import yfinance as yf
except Exception:
    yf = None


def safe_history(ticker, period, interval, auto_adjust=True):
    # wrapper for yfinance history that catches common failures
    t = yf.Ticker(ticker)
    # Sometimes yfinance throws on Ticker() for malformed symbols; protect
    # Note: some yfinance versions don't accept the 'threads' kwarg; avoid it for compatibility
    return t.history(period=period, interval=interval, auto_adjust=auto_adjust)


def compute_features(df):
    # df must contain a 'Close' column and 'Volume'
    out = {}
    if df is None or df.empty or 'Close' not in df.columns:
        return None
    close = df['Close'].dropna()
    vol = df['Volume'].dropna() if 'Volume' in df.columns else None
    if len(close) < 2:
        return None

    # returns
    ret = close.pct_change().fillna(0)
    def pct_ret(n):
        if len(close) > n:
            return (close.iloc[-1] / close.iloc[-n-1] - 1)
        else:
            return float('nan')

    out['last_price'] = float(close.iloc[-1])
    out['ret_1d'] = pct_ret(1)
    out['ret_5d'] = pct_ret(5)
    out['ret_21d'] = pct_ret(21)

    # moving averages relative to last price
    def ma_rel(n):
        if len(close) >= n:
            return float(close.iloc[-n:].mean() / close.iloc[-1] - 1)
        return float('nan')

    out['ma5_rel'] = ma_rel(5)
    out['ma20_rel'] = ma_rel(20)

    # volatility (std of daily returns)
    out['vol_21'] = float(ret.iloc[-21:].std()) if len(ret) >= 21 else float('nan')

    # avg dollar volume
    if vol is not None and len(vol) >= 21:
        recent_close = close.iloc[-21:]
        recent_vol = vol.iloc[-21:]
        out['avg_dollar_vol_21'] = float((recent_close * recent_vol).mean())
    else:
        out['avg_dollar_vol_21'] = float('nan')

    # RSI (14)
    try:
        window = 14
        delta = close.diff()
        up = delta.clip(lower=0).fillna(0)
        down = -1 * delta.clip(upper=0).fillna(0)
        ma_up = up.rolling(window=window, min_periods=window).mean()
        ma_down = down.rolling(window=window, min_periods=window).mean()
        rs = ma_up / ma_down
        rsi = 100 - (100 / (1 + rs))
        out['rsi_14'] = float(rsi.iloc[-1]) if not rsi.empty and not pd.isna(rsi.iloc[-1]) else float('nan')
    except Exception:
        out['rsi_14'] = float('nan')

    # ATR (14) - average true range using high/low/close
    try:
        if 'High' in df.columns and 'Low' in df.columns:
            high = df['High'].astype(float)
            low = df['Low'].astype(float)
            prev_close = close.shift(1)
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=14, min_periods=14).mean()
            out['atr_14'] = float(atr.iloc[-1]) if not atr.empty and not pd.isna(atr.iloc[-1]) else float('nan')
        else:
            out['atr_14'] = float('nan')
    except Exception:
        out['atr_14'] = float('nan')
    # price_start_of_week: first available close within the current ISO week (Monday-start)
    try:
        df2 = df.copy()
        # Suppress the UserWarning about dropping timezone information
        with pd.option_context('mode.chained_assignment', None), pd.option_context('mode.copy_on_write', True):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                if 'Close' in df2.columns and 'Date' in df2.columns:
                    df2['Date'] = pd.to_datetime(df2['Date'])
                    df2['week'] = df2['Date'].dt.to_period('W-MON')
                    current_week = df2['Date'].iloc[-1].to_period('W-MON')
                    sub = df2[df2['week'] == current_week]
                    if not sub.empty:
                        out['price_start_of_week'] = float(sub.sort_values('Date').iloc[0]['Close'])
                    else:
                        out['price_start_of_week'] = float('nan')
                else:
                    # if Date absent, try index as datetime (some yfinance versions put dates in the index)
                    try:
                        idx = df.index
                        if hasattr(idx, 'to_datetime') or hasattr(idx, 'to_pydatetime'):
                            dates = pd.to_datetime(idx)
                            df2 = df.copy()
                            df2['Date'] = dates
                            df2['week'] = df2['Date'].dt.to_period('W-MON')
                            current_week = df2['Date'].iloc[-1].to_period('W-MON')
                            sub = df2[df2['week'] == current_week]
                            if not sub.empty:
                                out['price_start_of_week'] = float(sub.sort_values('Date').iloc[0]['Close'])
                            else:
                                out['price_start_of_week'] = float('nan')
                        else:
                            out['price_start_of_week'] = float('nan')
                    except Exception:
                        out['price_start_of_week'] = float('nan')
    except Exception:
        out['price_start_of_week'] = float('nan')

    return out


def ticker_to_safe(t):
    # yfinance expects tickers like 'BRK-B' -> 'BRK-B' works; keep as-is
    return t.strip()


def main():
    p = argparse.ArgumentParser(description='Enrich tickers using yfinance and produce features file')
    p.add_argument('--tickers-file', required=True, help='CSV/TSV file listing tickers (column Symbol or symbol or ticker)')
    p.add_argument('--out', required=True, help='Output features file (parquet or csv). Example: data/weekly_enriched.parquet')
    p.add_argument('--cache-dir', default='data/weekly_enriched_cache', help='Per-ticker cache directory')
    p.add_argument('--period', default='1y', help='yfinance history period (default 1y)')
    p.add_argument('--interval', default='1d', help='yfinance interval (default 1d)')
    p.add_argument('--sleep', type=float, default=0.5, help='Seconds to sleep between yfinance calls')
    p.add_argument('--sample', type=int, default=0, help='If >0, only process first N tickers (useful for tests)')
    p.add_argument('--force', action='store_true', help='Re-download even if cache exists')
    args = p.parse_args()

    if yf is None:
        print('yfinance not installed. Install with: pip install yfinance', file=sys.stderr)
        sys.exit(2)

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # read tickers
    tickers = []
    if Path(args.tickers_file).exists():
        df_in = pd.read_csv(args.tickers_file)
        # try to find a ticker column
        ticker_col = None
        for c in ('Symbol', 'symbol', 'Ticker', 'ticker', 'symbol_ticker'):
            if c in df_in.columns:
                ticker_col = c
                break
        if ticker_col is None:
            # assume first column
            ticker_col = df_in.columns[0]
        tickers = df_in[ticker_col].astype(str).str.strip().unique().tolist()
    else:
        # Fallback: if tickers file not found, try to get tickers from headlines parquet
        headlines_path = Path('data/weekly_headlines_all.parquet')
        if headlines_path.exists():
            print(f"Tickers file '{args.tickers_file}' not found. Falling back to tickers from '{headlines_path}'.")
            df_headlines = pd.read_parquet(headlines_path)
            if 'ticker' in df_headlines.columns:
                tickers = df_headlines['ticker'].astype(str).str.strip().unique().tolist()

    if args.sample and args.sample > 0:
        tickers = tickers[: args.sample]

    rows = []
    errors = {}
    for i, t in enumerate(tickers, start=1):
        safe_t = ticker_to_safe(t)
        cache_file = cache_dir / f"{safe_t}.parquet"
        try:
            if cache_file.exists() and not args.force:
                # load cached history and compute features
                hist = pd.read_parquet(cache_file)
            else:
                hist = safe_history(safe_t, period=args.period, interval=args.interval)
                # Ensure columns are present and save
                if hist is None or hist.empty:
                    raise RuntimeError('no history')
                # store the relevant columns (Close, Volume, Open, High, Low)
                hist_out = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                hist_out.to_parquet(cache_file)
                hist = hist_out

            feats = compute_features(hist)
            if feats is None:
                raise RuntimeError('insufficient data')
            feats['ticker'] = safe_t
            rows.append(feats)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            errors[safe_t] = str(e)
            # log the traceback to stderr for debugging but continue
            print(f"[WARN] {safe_t}: {e}", file=sys.stderr)
            # write traceback
            traceback.print_exc(file=sys.stderr)
        # sleep to be polite to yfinance / Yahoo
        if i < len(tickers):
            time.sleep(args.sleep)

    out_df = pd.DataFrame(rows)
    # set ticker as first column
    if not out_df.empty:
        cols = ['ticker'] + [c for c in out_df.columns if c != 'ticker']
        out_df = out_df[cols]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() in ('.parquet', '.pq'):
        out_df.to_parquet(out_path, index=False)
    else:
        out_df.to_csv(out_path, index=False)

    meta = {
        'n_requested': len(tickers),
        'n_succeeded': len(out_df),
        'n_failed': len(errors),
        'errors_sample': dict(list(errors.items())[:10]),
    }

    meta_path = out_path.with_name(out_path.stem + '_meta.json')
    import json

    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    print(f'Wrote features: {out_path}  success={len(out_df)} failed={len(errors)} meta={meta_path}')


if __name__ == '__main__':
    main()
