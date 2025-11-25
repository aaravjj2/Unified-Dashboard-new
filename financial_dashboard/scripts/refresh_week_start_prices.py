#!/usr/bin/env python3
"""
Refresh and persist week-start prices for the latest weekly picks.

Usage:
  python3 scripts/refresh_week_start_prices.py \
      --picks models/weekly_run/weeklypicks_latest.csv \
      --out data/weekly_weekstart_$(date +%Y%m%d).json

This script looks up recent history via yfinance and determines the first
available close within the current ISO week (Monday-start). If that is not
available (thin/no data), it falls back to the earliest available close in
the requested window.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
import sys
import logging
try:
    import yfinance as yf
except Exception:
    yf = None

logging.basicConfig(level=logging.INFO)


def compute_week_start_from_series(close_series, ref_date=None):
    # close_series: pd.Series indexed by datetime (Close prices)
    # ref_date: datetime.date used to determine the target week
    if close_series is None or close_series.empty:
        return None, None
    dates = pd.to_datetime(close_series.index).normalize()
    df = pd.DataFrame({'Close': close_series.values}, index=dates)

    # Determine target week Monday using ref_date (or last available date)
    if ref_date is None:
        last_date = df.index[-1].date()
    else:
        last_date = pd.to_datetime(ref_date).date()

    # week Monday
    from datetime import timedelta
    week_monday = last_date - timedelta(days=last_date.weekday())

    # Search forward from Monday to Thursday for first available close (handle Mon holiday)
    for delta in range(0, 4):
        d = pd.Timestamp(week_monday + timedelta(days=delta))
        if d in df.index:
            return float(df.loc[d]['Close']), d.strftime('%Y-%m-%d')

    # If not found, try searching backward to Friday (-1,-2,-3)
    for delta in range(1, 4):
        d = pd.Timestamp(week_monday - timedelta(days=delta))
        if d in df.index:
            return float(df.loc[d]['Close']), d.strftime('%Y-%m-%d')

    # Final fallback: earliest available close in the series
    d = df.index[0]
    return float(df.iloc[0]['Close']), d.strftime('%Y-%m-%d')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--picks', default='models/weekly_run/weeklypicks_latest.csv', help='Picks CSV to read tickers from')
    p.add_argument('--out', default=None, help='Output JSON file path')
    p.add_argument('--days', type=int, default=14, help='History window in days to download from yfinance')
    p.add_argument('--interval', default='1d', help='yfinance interval')
    p.add_argument('--threads', type=int, default=4, help='yfinance threads')
    p.add_argument('--use-today', action='store_true', help='Force reference date to today for week-start computation')
    args = p.parse_args()

    if yf is None:
        logging.error('yfinance not available. Install with: pip install yfinance')
        sys.exit(2)

    picks_path = Path(args.picks)
    if not picks_path.exists():
        logging.error('Picks file not found: %s', picks_path)
        sys.exit(1)

    df = pd.read_csv(picks_path)
    if 'ticker' not in df.columns:
        logging.error('Picks CSV does not contain ticker column')
        sys.exit(1)

    tickers = sorted(set(df['ticker'].dropna().astype(str).str.strip().tolist()))
    logging.info('Refreshing week-start prices for %d tickers', len(tickers))

    # batch-download
    tickers_str = ' '.join(tickers)
    try:
        data = yf.download(tickers_str, period=f'{args.days}d', interval=args.interval, progress=False, threads=True, group_by='ticker')
    except Exception as e:
        logging.error('yfinance batch download failed: %s', e)
        data = None

    results = {}
    # If picks CSV includes a 'date' column, map tickers to that date (use latest occurrence)
    pick_dates = {}
    if 'date' in df.columns:
        try:
            tmp = df[['ticker', 'date']].dropna()
            for _, row in tmp.iterrows():
                pick_dates[row['ticker'].strip()] = row['date']
        except Exception:
            pass

    # compute today string once
    today_str = pd.Timestamp.today().strftime('%Y-%m-%d')

    for t in tickers:
        try:
            if data is None:
                # fall back to single ticker fetch
                hist = yf.Ticker(t).history(period=f'{args.days}d', interval=args.interval)
                close = hist['Close'] if 'Close' in hist.columns else pd.Series()
            else:
                if isinstance(data.columns, pd.MultiIndex):
                    # grouped by ticker: tickers are usually in level 0
                    try:
                        # prefer level=0 (Ticker)
                        close = data.xs(t, axis=1, level=0)['Close']
                    except Exception:
                        # fallback: try locating by first level values
                        lvl0 = list(data.columns.get_level_values(0))
                        if t in lvl0:
                            try:
                                close = data[t]['Close']
                            except Exception:
                                close = pd.Series()
                        else:
                            close = pd.Series()
                else:
                    # single-ticker DataFrame with flat columns
                    if 'Close' in data.columns:
                        close = data['Close']
                    else:
                        close = pd.Series()

            if args.use_today:
                ref_date = today_str
            else:
                ref_date = pick_dates.get(t)
            ws_price, ws_date = compute_week_start_from_series(close, ref_date=ref_date)
            results[t] = {
                'week_start_price': ws_price,
                'week_start_date': ws_date
            }
        except Exception as e:
            logging.exception('Failed computing week-start for %s', t)
            results[t] = {'week_start_price': None, 'week_start_date': None, 'error': str(e)}

    out_path = Path(args.out) if args.out else Path('data') / f'weekly_weekstart_{pd.Timestamp.today().strftime("%Y%m%d")}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump({'generated': pd.Timestamp.now().isoformat(), 'data': results}, f, indent=2)

    logging.info('Wrote week-start prices to %s', out_path)


if __name__ == '__main__':
    main()
