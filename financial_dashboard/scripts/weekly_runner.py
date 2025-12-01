"""
Weekly runner: fetch prices for a universe, rank tickers, optionally place buy orders via Alpaca.

Key features:
- Uses Finnhub (rotating keys) as primary; Alpaca as secondary; yfinance as fallback.
- Respects API rate limits by batching: Finnhub limit per key = 60/min.
- Alpaca order placement is gated behind --place-orders and --confirm to prevent accidental trades.
- Dry-run by default; prints actions and a CSV summary.

Usage (dry-run):
  source /mnt/c/Aarav/fin_env/.venv_local/bin/activate
  python3 financial_dashboard/scripts/weekly_runner.py --tickers-file data/weekly_universe.txt --batch-sleep 60

To place real orders (REQUIRES explicit confirmation):
  python3 financial_dashboard/scripts/weekly_runner.py --tickers-file data/weekly_universe.txt --place-orders --confirm

"""
import argparse
import logging
import time
import sys
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_dashboard.utils.price_fetch import fetch_prices_batch, get_finnhub_key_status, get_rate_limit_stats


def parse_args():
    p = argparse.ArgumentParser(description='Weekly runner: fetch, rank, (optionally) place Alpaca orders')
    p.add_argument('--tickers-file', type=str, help='File with one ticker per line', required=True)
    p.add_argument('--parallel', type=int, default=8, help='Parallel workers for fetch')
    p.add_argument('--batch-size', type=int, default=120, help='Tickers per batch (set to combined Finnhub capacity)')
    p.add_argument('--batch-sleep', type=int, default=60, help='Seconds to sleep between batches')
    p.add_argument('--context', type=str, default='live', choices=['live','daily','weekly','monthly'], help='Data context/TTL')
    p.add_argument('--place-orders', action='store_true', help='Place buy orders via Alpaca (requires --confirm)')
    p.add_argument('--confirm', action='store_true', help='Confirm placing live orders (dangerous)')
    p.add_argument('--debug', action='store_true', help='Enable debug logging')
    p.add_argument('--dollars-per-ticker', type=float, default=500.0, help='Notional dollars to allocate per ticker when placing orders')
    return p.parse_args()


def load_tickers(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Tickers file not found: {p}")
    return [line.strip().upper() for line in p.read_text().splitlines() if line.strip()]


def rank_by_weekly_momentum(prices: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simple ranking: percent change from prev_close to last_price. Higher is better."""
    out = []
    for t, v in prices.items():
        last = v.get('last_price')
        prev = v.get('prev_close')
        if last is None or prev is None:
            pct = None
        else:
            try:
                pct = (last - prev) / prev
            except Exception:
                pct = None
        out.append({'ticker': t, 'last_price': last, 'prev_close': prev, 'pct_change': pct, 'source': v.get('source')})
    # sort with None values last
    out = sorted(out, key=lambda x: (x['pct_change'] is None, -(x['pct_change'] or 0)))
    return out


def place_alpaca_orders(orders: List[Dict[str, Any]], api_key: str, api_secret: str):
    """Place market buy orders with Alpaca (one per ticker for given dollar amount).

    This function uses the new alpaca-py SDK if available; if not, it will
    raise an error. Caller must ensure orders is a list of dicts with keys:
    ticker, dollars.
    """
    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
    except Exception as e:
        raise RuntimeError('Alpaca trading SDK not available in environment: ' + str(e))

    client = TradingClient(api_key, api_secret, paper=True)
    results = []
    for o in orders:
        ticker = o['ticker']
        dollars = o['dollars']
        # Here we place a market order by size in dollars using 'notional' feature
        req = MarketOrderRequest(symbol=ticker, notional=str(dollars), side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
        try:
            resp = client.submit_order(order_data=req)
            results.append({'ticker': ticker, 'status': 'submitted', 'alpaca_resp': resp.__dict__})
        except Exception as e:
            results.append({'ticker': ticker, 'status': 'failed', 'error': str(e)})
    return results


def main():
    args = parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s: %(message)s')
    logger = logging.getLogger('weekly_runner')

    tickers = load_tickers(args.tickers_file)
    total = len(tickers)
    logger.info(f"Loaded {total} tickers from {args.tickers_file}")

    # Batch processing loop
    all_prices = {}
    i = 0
    while i < total:
        batch = tickers[i:i+args.batch_size]
        logger.info(f"Fetching batch {i // args.batch_size + 1}: {len(batch)} tickers")
        start = time.time()
        prices = fetch_prices_batch(batch, parallelism=args.parallel, context=args.context)
        took = time.time() - start
        logger.info(f"Batch fetched in {took:.2f}s")
        all_prices.update(prices)
        # Show intermediate stats
        logger.info(f"Rate limits: {get_rate_limit_stats()}")
        logger.info(f"Finnhub keys: {get_finnhub_key_status()}")
        i += args.batch_size
        if i < total:
            logger.info(f"Sleeping {args.batch_sleep}s to respect rate limits before next batch")
            time.sleep(args.batch_sleep)

    # Ranking
    ranked = rank_by_weekly_momentum(all_prices)
    logger.info(f"Ranked {len(ranked)} tickers; top 10:")
    for r in ranked[:10]:
        logger.info(f"{r['ticker']}: pct_change={r['pct_change']}, last={r['last_price']}, src={r['source']}")

    # Prepare orders: buy top N (for now we'll buy all with pct_change not None)
    to_buy = [r for r in ranked if r['pct_change'] is not None]
    logger.info(f"Preparing {len(to_buy)} candidate orders (dry-run unless --place-orders --confirm provided)")

    orders = [{'ticker': r['ticker'], 'dollars': args.dollars_per_ticker} for r in to_buy]

    # Short-circuit: do not place orders unless explicitly requested
    if args.place_orders:
        if not args.confirm:
            logger.error('Refusing to place orders: --place-orders requires --confirm')
            return
        # Load Alpaca keys from env (must be present)
        import os
        alpaca_key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
        alpaca_secret = os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_API_SECRET')
        if not alpaca_key or not alpaca_secret:
            logger.error('Alpaca API keys not found in environment; cannot place orders')
            return
        logger.warning('Placing live Alpaca orders (this is IRREVERSIBLE)')
        res = place_alpaca_orders(orders, alpaca_key, alpaca_secret)
        logger.info(f"Placed orders: {res}")
    else:
        logger.info('Dry-run mode: no orders placed. To enable live trading use --place-orders --confirm')
        # Write summary CSV
        import csv
        outp = Path('weekly_run_summary.csv')
        with outp.open('w', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=['ticker','last_price','prev_close','pct_change','source','dollars_to_invest'])
            writer.writeheader()
            for r in to_buy:
                writer.writerow({'ticker': r['ticker'], 'last_price': r['last_price'], 'prev_close': r['prev_close'], 'pct_change': r['pct_change'], 'source': r['source'], 'dollars_to_invest': args.dollars_per_ticker})
        logger.info(f"Wrote summary to {outp.resolve()}")


if __name__ == '__main__':
    main()

