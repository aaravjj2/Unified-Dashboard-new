"""
Dry-run script: fetch prices for a small ticker sample (default 20) using the project's
price_fetch pipeline (Finnhub -> Alpaca -> yfinance). Respects existing key rotation
and rate-limit handling in `price_fetch`.

Usage (from project root in WSL):
  source /mnt/c/Aarav/fin_env/.venv_local/bin/activate
  python3 financial_dashboard/scripts/dry_run_weekly.py --debug

This script intentionally does not place orders; it's a read-only dry-run for validation.
"""
import argparse
import logging
import time
import sys
from pathlib import Path

# Adjust import path to allow running from project root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_dashboard.utils.price_fetch import (fetch_prices_batch,
                                                   get_finnhub_key_status,
                                                   get_rate_limit_stats)


SAMPLE_20 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK.B', 'JPM', 'V',
    'UNH', 'HD', 'PG', 'MA', 'DIS', 'BAC', 'ADBE', 'CMCSA', 'NFLX', 'INTC'
]


def parse_args():
    p = argparse.ArgumentParser(description='Dry-run weekly price fetch (20 tickers)')
    p.add_argument('--tickers', type=str, help='Comma-separated tickers to fetch')
    p.add_argument('--tickers-file', type=str, help='File with one ticker per line')
    p.add_argument('--parallel', type=int, default=8, help='Parallel workers')
    p.add_argument('--debug', action='store_true', help='Enable debug logging')
    p.add_argument('--context', type=str, default='live', choices=['live','daily','weekly','monthly'], help='Data context/TTL to use')
    return p.parse_args()


def load_tickers(args):
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(',') if t.strip()]
    if args.tickers_file:
        p = Path(args.tickers_file)
        if p.exists():
            return [line.strip().upper() for line in p.read_text().splitlines() if line.strip()]
    return SAMPLE_20


def main():
    args = parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s: %(message)s')
    logger = logging.getLogger('dry_run_weekly')

    tickers = load_tickers(args)
    logger.info(f"Dry-run fetch for {len(tickers)} tickers (parallel={args.parallel}, context={args.context})")

    start = time.time()
    results = fetch_prices_batch(tickers, parallelism=args.parallel, context=args.context)
    took = time.time() - start

    success = 0
    sources = {}
    for t in tickers:
        r = results.get(t)
        if not r:
            logger.warning(f"{t}: no result returned")
            continue
        src = r.get('source')
        sources[src] = sources.get(src, 0) + 1
        price = r.get('last_price')
        if price:
            success += 1
            logger.info(f"{t}: ${price:.2f} (source={src})")
        else:
            logger.warning(f"{t}: FAILED (source={src}) error={r.get('error')}")

    logger.info(f"Summary: {success}/{len(tickers)} succeeded in {took:.2f}s")
    logger.info(f"Source breakdown: {sources}")

    # Rate limit + key status
    rl = get_rate_limit_stats()
    kh = get_finnhub_key_status()
    logger.info(f"Rate limits: {rl}")
    logger.info(f"Finnhub key status: {kh}")

    # Warn if any yfinance results were used (we want Finnhub/Alpaca primarily)
    if 'yfinance' in sources and sources['yfinance'] > 0:
        logger.warning('yfinance was used for some tickers — check Finnhub/Alpaca keys and availability')


if __name__ == '__main__':
    main()

