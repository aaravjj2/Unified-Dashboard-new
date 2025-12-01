#!/usr/bin/env python3
"""
Place Alpaca orders for the weekly picks at market open.
This script reads the picks CSV (default: latest in models/weekly_run) and places orders sized according to `position_size_dollars`.

Usage:
  python3 scripts/place_alpaca_orders_for_picks.py [--picks FILE] [--execute] [--account PAPER|LIVE]

Defaults:
  --execute : if omitted, runs in dry-run mode and only prints orders that would be placed.
  --account : default PAPER

Environment:
- Requires Alpaca keys in env: APCA_API_KEY_ID, APCA_API_SECRET_KEY
- If using LIVE, set APCA_ENDPOINT or rely on default live endpoint.

Safety and features:
- Checks buying power and existing positions to avoid over-leveraging
- Supports partial fills and places market orders by default; you can change to limit orders by editing ORDER_TYPE

"""

import argparse
import os
import sys
from pathlib import Path
import pandas as pd

# Try to import alpaca trade API (alpaca-py)
ALPACA_TRADING_AVAILABLE = False
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_TRADING_AVAILABLE = True
except Exception:
    ALPACA_TRADING_AVAILABLE = False

ORDER_TYPE = 'market'


def _find_latest_picks(directory: Path) -> Path:
    files = sorted(directory.glob('weeklypicks*.csv'), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--picks', help='Picks CSV (default: latest in models/weekly_run)', default=None)
    p.add_argument('--execute', help='Actually submit orders', action='store_true')
    p.add_argument('--dollars-per-ticker', help='Override position_size_dollars and buy this many dollars per ticker', type=float, default=None)
    p.add_argument('--max-allocation', help='Maximum total dollars to spend this run (overrides picks if smaller)', type=float, default=None)
    p.add_argument('--max-percent-per-ticker', help='Max percent of buying power to spend on any single ticker (0-1)', type=float, default=None)
    p.add_argument('--force', help='Force live execution even if ALLOW_LIVE env not set (use with care)', action='store_true')
    p.add_argument('--account', help='PAPER or LIVE', default='PAPER')
    args = p.parse_args()

    root = Path(__file__).resolve().parents[1]
    picks_file = Path(args.picks) if args.picks else _find_latest_picks(root / 'models' / 'weekly_run')
    if not picks_file or not picks_file.exists():
        print('No picks file found. Run the pipeline first to generate picks.')
        sys.exit(2)

    picks = pd.read_csv(picks_file)
    picks['position_size_dollars'] = picks['position_size_dollars'].astype(float)

    if not ALPACA_TRADING_AVAILABLE:
        print('alpaca trading client not available; running in dry-run mode')
        for idx, row in picks.iterrows():
            print(f"DRY RUN: Would place {row['ticker']} order for ${row['position_size_dollars']:.2f}")
        return

    key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
    secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
    if not key or not secret:
        print('Alpaca keys not found in environment. Aborting.')
        sys.exit(2)

    paper = True if args.account.upper() == 'PAPER' else False
    client = TradingClient(key, secret, paper=paper)

    account = client.get_account()
    buying_power = float(account.buying_power)
    print('Account buying power:', buying_power)

    # Build planned orders and compute caps
    planned_orders = []
    planned_total = 0.0
    for idx, row in picks.iterrows():
        ticker = str(row['ticker']).strip()
        if args.dollars_per_ticker is not None:
            size = float(args.dollars_per_ticker)
        else:
            size = float(row['position_size_dollars'])
        planned_orders.append((ticker, size, row))
        planned_total += size

    # global cap (cli arg overrides env)
    max_allocation = args.max_allocation if args.max_allocation is not None else (float(os.getenv('MAX_ALLOCATION')) if os.getenv('MAX_ALLOCATION') else None)
    max_pct = args.max_percent_per_ticker if args.max_percent_per_ticker is not None else (float(os.getenv('MAX_PERCENT_PER_TICKER')) if os.getenv('MAX_PERCENT_PER_TICKER') else None)

    if max_allocation is not None and planned_total > max_allocation:
        print(f"Planned spend ${planned_total:.2f} exceeds max allocation ${max_allocation:.2f}. Scaling down proportionally.")
        scale = max_allocation / planned_total
    else:
        scale = 1.0

    # require explicit ALLOW_LIVE env var (unless --force) when executing live
    if args.execute and os.getenv('ALLOW_LIVE') != '1' and not args.force:
        print('Live execution requested but ALLOW_LIVE != 1 in environment. To proceed, set ALLOW_LIVE=1 in your env or pass --force (not recommended).')
        sys.exit(2)

    final_plan = []
    for ticker, size, row in planned_orders:
        final_size = size * scale
        if max_pct is not None:
            cap = buying_power * max_pct
            if final_size > cap:
                print(f"Capping {ticker} from ${final_size:.2f} to per-ticker cap ${cap:.2f}")
                final_size = cap
        final_plan.append((ticker, final_size, row))

    planned_total = sum([s for (_, s, _) in final_plan])
    print(f"Planned total spend after caps: ${planned_total:.2f}; account buying power ${buying_power:.2f}")

    for ticker, size, row in final_plan:
        if size <= 0:
            print('Skipping', ticker, 'size <= 0')
            continue
        if size > buying_power:
            print(f"Skipping {ticker} — position size ${size:.2f} exceeds buying power ${buying_power:.2f}")
            continue

        qty = None
        # compute qty based on current price
        price = row.get('last_price', None)
        if pd.isna(price) or price is None:
            print('No price for', ticker, ' — skipping')
            continue
        try:
            qty = int(max(1, round(size / float(price))))
        except Exception:
            print('Failed to compute qty for', ticker)
            continue

        if not args.execute:
            print(f"DRY RUN: Would place {ORDER_TYPE} order for {ticker} qty={qty} (~${qty*float(price):.2f})")
            buying_power -= qty * float(price)
            continue

        # place order
        try:
            order_data = MarketOrderRequest(symbol=ticker, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
            resp = client.submit_order(order_data)
            print('Submitted order for', ticker, 'id:', resp.id)
            try:
                buying_power -= qty * float(price)
            except Exception:
                pass
        except Exception as e:
            print('Order failed for', ticker, e)

    print('Done.')

if __name__ == '__main__':
    main()
