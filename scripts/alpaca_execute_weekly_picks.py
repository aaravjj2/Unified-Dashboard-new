#!/usr/bin/env python3
"""
Simple tool to execute a weekly-picks CSV in Alpaca by dollar amount (notional) per ticker.

Usage examples:
  # dry run, print intended orders
  python scripts/alpaca_execute_weekly_picks.py --csv tmp_first20.csv --dollar 200 --dry-run

  # real run (ensure APCA_API_KEY_ID and APCA_API_SECRET_KEY are set; use paper trading base URL)
  export APCA_API_KEY_ID=your_key
  export APCA_API_SECRET_KEY=your_secret
  export APCA_API_BASE_URL=https://paper-api.alpaca.markets
  python scripts/alpaca_execute_weekly_picks.py --csv tmp_first20.csv --dollar 200

Notes:
 - This script sends MARKET orders and uses the Orders API 'notional' field to size by dollars.
 - Notional (fractional) orders require a brokerage account that supports fractional shares. If the broker/account rejects the notional param, the script will report the error.
 - Always test with --dry-run and/or use Alpaca paper trading credentials.
"""

import os
import argparse
import time
import pandas as pd
import requests


def load_tickers(csv_path: str):
    df = pd.read_csv(csv_path)
    # Expect a column named 'ticker' (case-insensitive)
    cols = [c.lower() for c in df.columns]
    if 'ticker' in cols:
        ticker_col = df.columns[cols.index('ticker')]
        return [str(t).strip() for t in df[ticker_col].dropna().unique()]
    # Fallback: if single-column CSV, assume that column is tickers
    if df.shape[1] == 1:
        return [str(t).strip() for t in df.iloc[:, 0].dropna().unique()]
    raise ValueError("CSV must contain a 'ticker' column or be a single-column file of tickers")


def submit_notional_order(base_url, headers, symbol, dollar_amount, side='buy', dry_run=True):
    payload = {
        "symbol": symbol,
        "side": side,
        "type": "market",
        "time_in_force": "day",
        # Alpaca accepts a string or number for notional
        "notional": str(dollar_amount)
    }
    if dry_run:
        print(f"DRY-RUN order payload for {symbol}: {payload}")
        return {"status": "dry-run", "payload": payload}

    url = base_url.rstrip('/') + '/v2/orders'
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    if resp.ok:
        print(f"Order placed for {symbol} notional ${dollar_amount}: id={body.get('id')}")
        return {"status": "ok", "response": body}
    else:
        print(f"Order failed for {symbol}: status={resp.status_code} body={body}")
        return {"status": "error", "status_code": resp.status_code, "response": body}


def main():
    p = argparse.ArgumentParser(description="Execute weekly picks CSV in Alpaca sized by dollar amount per ticker")
    p.add_argument('--csv', '-c', default='tmp_first20.csv', help='Path to weekly picks CSV (default tmp_first20.csv)')
    p.add_argument('--dollar', '-d', type=float, default=500.0, help='Dollar amount per ticker (notional)')
    p.add_argument('--side', choices=['buy', 'sell'], default='buy', help='Order side')
    p.add_argument('--dry-run', action='store_true', help='Do not send orders, only print payloads')
    p.add_argument('--doppler', '-D', default=None, help='Path to doppler.env to load TICKERS/WEEKLY_TICKERS (optional)')
    p.add_argument('--sleep', type=float, default=0.15, help='Seconds to sleep between orders')
    args = p.parse_args()

    csv_path = args.csv
    tickers = []

    # First try: if Doppler CLI is available, use the repo's loader to populate env vars
    try:
        from financial_dashboard._shared_env import load_doppler_env
        # attempt to load; this will call doppler CLI if present and populate os.environ
        loaded = load_doppler_env()
        if loaded:
            print("Loaded environment from Doppler CLI (via financial_dashboard._shared_env)")
    except Exception:
        # If import fails or doppler CLI not available, continue to other fallbacks
        loaded = False

    # Next: read tickers from environment variables if present
    env_val = os.getenv('WEEKLY_TICKERS') or os.getenv('WEEKLY_PICKS') or os.getenv('TICKERS') or None
    if env_val:
        tickers = [t.strip() for t in env_val.split(',') if t.strip()]
        print(f"Loaded {len(tickers)} tickers from environment variable (WEEKLY_TICKERS/TICKERS)")

    # Next fallback: if a doppler export file is provided, parse it for ticker vars
    if not tickers and args.doppler:
        doppler_path = args.doppler
        if not os.path.exists(doppler_path):
            print(f"Doppler env file not found: {doppler_path}")
            return
        with open(doppler_path, 'r') as f:
            content = f.read()

        # If file appears to be a simple KEY=VALUE env export, parse for ticker var
        import re
        if re.search(r'\n?[^:]+=[^\n]+', content):
            m = re.search(r'(?m)^(?:TICKERS|WEEKLY_TICKERS|WEEKLY_PICKS)\s*=\s*(.+)$', content)
            if m:
                val = m.group(1).strip()
                # strip quotes
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                tickers = [t.strip() for t in val.split(',') if t.strip()]
                print(f"Loaded {len(tickers)} tickers from Doppler file: {doppler_path}")
            else:
                print("No TICKERS / WEEKLY_TICKERS / WEEKLY_PICKS var found in doppler file; falling back to CSV")
        else:
            # The doppler.env in this repo may be a binary/base64 blob (Doppler internal format)
            print("Provided doppler file does not appear to be a plain env file (looks encoded).")
            print("If you want to load secrets from Doppler, install the Doppler CLI and let the script call it, or provide a plain env file with TICKERS variable.")

    if not tickers:
        if not os.path.exists(csv_path):
            print(f"CSV not found: {csv_path}")
            return
        try:
            tickers = load_tickers(csv_path)
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return

    api_key = os.getenv('APCA_API_KEY_ID') or os.getenv('APCA_API_KEY')
    api_secret = os.getenv('APCA_API_SECRET_KEY') or os.getenv('APCA_API_SECRET')
    base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

    if not api_key or not api_secret:
        print("Missing Alpaca API credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in the environment. Using dry-run mode.")
        args.dry_run = True

    headers = {
        'APCA-API-KEY-ID': api_key or '',
        'APCA-API-SECRET-KEY': api_secret or '',
        'Content-Type': 'application/json'
    }

    print(f"Loaded {len(tickers)} tickers from {csv_path}. Preparing to place {args.side} orders of ${args.dollar} each (dry_run={args.dry_run})")

    results = []
    for symbol in tickers:
        try:
            res = submit_notional_order(base_url, headers, symbol, args.dollar, side=args.side, dry_run=args.dry_run)
            results.append((symbol, res))
        except Exception as e:
            print(f"Exception ordering {symbol}: {e}")
            results.append((symbol, {'status': 'exception', 'error': str(e)}))
        time.sleep(max(0.0, args.sleep))

    # summary
    ok = [r for s, r in results if r.get('status') == 'ok' or r.get('status') == 'dry-run']
    errs = [ (s,r) for s, r in results if r.get('status') not in ('ok','dry-run')]
    print(f"\nSummary: {len(ok)} success/dry-run, {len(errs)} errors")
    if errs:
        print("Errors:")
        for s, r in errs:
            print(f"  {s}: {r}")


if __name__ == '__main__':
    main()
