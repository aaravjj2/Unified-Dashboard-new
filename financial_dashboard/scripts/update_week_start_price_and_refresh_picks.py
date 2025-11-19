#!/usr/bin/env python3
"""
Update "price_start_of_week" for picks at market open (9:30 AM) and refresh picks file.
Intended to be run by cron at 09:30 on Mondays (or the next trading day).

Behavior:
- Loads latest picks CSV under models/weekly_run (uses most recent weeklypicks*.csv)
- For each ticker in picks, attempts to fetch the minute bar at market open (09:30 US/Eastern) via Alpaca
- Falls back to latest trade/quote or yfinance if Alpaca is unavailable
- Writes an updated picks CSV and (optionally) merged features parquet with `price_start_of_week`

Usage:
  python3 scripts/update_week_start_price_and_refresh_picks.py [--picks FILE] [--features FILE] [--out FILE]

Environment / keys:
- Expects Alpaca keys in env: APCA_API_KEY_ID, APCA_API_SECRET_KEY (and optionally APCA_ENDPOINT)
- If no Alpaca available, will try yfinance to get the current price

Safety:
- This script only updates files and does NOT place orders. Use the separate order script to submit orders.
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, time
import pandas as pd
import pytz

# Try to import Alpaca (alpaca-py)
ALPACA_AVAILABLE = False
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    # correct import for TimeFrame
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except Exception:
    ALPACA_AVAILABLE = False

# fallback to yfinance
try:
    import yfinance as yf
except Exception:
    yf = None


def _find_latest_picks(directory: Path) -> Path:
    files = sorted(directory.glob('weeklypicks*.csv'), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def get_open_minute_price_alpaca(client, ticker, target_date, tz='US/Eastern'):
    # target_date is a date (datetime.date) representing the trading day we want
    # markets open at 09:30 eastern
    local_tz = pytz.timezone(tz)
    open_dt = local_tz.localize(datetime.combine(target_date, time(9, 30)))
    # convert to UTC ISO
    start = open_dt.astimezone(pytz.UTC)
    end = (open_dt + timedelta(minutes=1)).astimezone(pytz.UTC)
    try:
        req = StockBarsRequest(symbol_or_symbols=[ticker], timeframe=TimeFrame.Minute, start=start, end=end)
        bars = client.get_stock_bars(req)
        df = bars.df
        if not df.empty:
            # df may contain multiple ticks if symbol list; filter
            df = df.reset_index()
            # pick first bar close
            price = float(df['close'].iloc[0])
            return price
    except Exception:
        return None
    return None


def get_latest_price_yf(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='2d', interval='1m')
        if hist is not None and not hist.empty:
            # use last available Close
            return float(hist['Close'].iloc[-1])
    except Exception:
        return None
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--picks', help='Picks CSV (default: latest in models/weekly_run)', default=None)
    p.add_argument('--features', help='Features parquet to update (optional)', default=None)
    p.add_argument('--out', help='Output updated picks CSV (optional)', default=None)
    p.add_argument('--wait-seconds', help='Seconds to wait between retries when waiting for open minute bar', type=float, default=30.0)
    p.add_argument('--retries', help='Number of retries to wait for open minute bar before falling back', type=int, default=4)
    args = p.parse_args()

    root = Path(__file__).resolve().parents[1]
    picks_file = Path(args.picks) if args.picks else _find_latest_picks(root / 'models' / 'weekly_run')
    if not picks_file or not picks_file.exists():
        print('No picks file found. Run the pipeline first to generate picks.')
        sys.exit(2)

    print('Using picks file:', picks_file)
    picks = pd.read_csv(picks_file)

    # Determine target date: if today is Monday use today, else next Monday? The caller (cron) should schedule.
    target_date = datetime.now(pytz.timezone('US/Eastern')).date()

    # Prepare Alpaca client if available
    alpaca_client = None
    if ALPACA_AVAILABLE:
        apca_key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
        apca_secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
        apca_base = os.getenv("APCA_ENDPOINT") if os.getenv("APCA_ENDPOINT") else None
        if apca_key and apca_secret:
            try:
                # The alpaca-py constructor changed between releases. Try common signatures.
                try:
                    alpaca_client = StockHistoricalDataClient(apca_key, apca_secret, base_url=apca_base)
                except TypeError:
                    try:
                        alpaca_client = StockHistoricalDataClient(apca_key, apca_secret)
                    except TypeError:
                        # Some versions use a single credential object or keyword names
                        try:
                            alpaca_client = StockHistoricalDataClient(key=apca_key, secret=apca_secret, base_url=apca_base)
                        except Exception:
                            alpaca_client = StockHistoricalDataClient()
                print('Alpaca data client initialized')
            except Exception as e:
                print('Failed to init Alpaca client:', e)
                alpaca_client = None
        else:
            print('Alpaca keys not found in environment; will fall back to yfinance')

    updated_prices = {}
    for idx, row in picks.iterrows():
        tk = str(row['ticker']).strip()
        price = None
        # Attempt retries for Alpaca minute bar if client available
        if alpaca_client:
            attempt = 0
            while attempt <= args.retries:
                price = get_open_minute_price_alpaca(alpaca_client, tk, target_date)
                if price is not None:
                    break
                attempt += 1
                if attempt > args.retries:
                    break
                print(f'Open bar not available for {tk} yet; retrying in {args.wait_seconds} seconds (attempt {attempt}/{args.retries})')
                try:
                    time.sleep(args.wait_seconds)
                except Exception:
                    pass

        # fallback to yfinance if no price from Alpaca
        if price is None and yf is not None:
            price = get_latest_price_yf(tk)

        if price is None:
            print(f'Could not fetch open price for {tk}; leaving existing last_price')
            continue

        updated_prices[tk] = price
        # update picks dataframe
        picks.at[idx, 'price_start_of_week'] = price
        # also update last_price to reflect open price
        picks.at[idx, 'last_price'] = price

    # write updated picks to out file or overwrite
    out_path = Path(args.out) if args.out else picks_file
    picks.to_csv(out_path, index=False)
    print('Wrote updated picks with price_start_of_week to', out_path)

    # Optionally update features parquet if provided
    if args.features:
        feats_path = Path(args.features)
        if feats_path.exists():
            feats = pd.read_parquet(feats_path)
            feats['ticker'] = feats['ticker'].astype(str).str.strip()
            for tk, price in updated_prices.items():
                mask = feats['ticker'] == tk
                if mask.any():
                    feats.loc[mask, 'price_start_of_week'] = price
            feats.to_parquet(feats_path, index=False)
            print('Updated features file with price_start_of_week:', feats_path)

    print('Done.')

if __name__ == '__main__':
    main()
