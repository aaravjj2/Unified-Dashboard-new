#!/usr/bin/env python3
"""Fetch headlines for tickers that currently have zero headlines recorded.

Usage:
  python3 scripts/fetch_headlines_zero_coverage.py [--sample N] [--no-run] [--days D] [--use-scrape]

This script:
 - reads `Weekly ticker list.csv` (repo root) to get the universe
 - reads `data/weekly_headlines.parquet` (if present) to find tickers already fetched
 - writes a temporary CSV with tickers that have zero headlines
 - optionally calls scripts/fetch_headlines.py with that subset
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from pathlib import Path


def load_universe(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, newline='') as f:
        r = csv.reader(f)
        for row in r:
            if not row: continue
            t = row[0].strip().upper()
            if not t: continue
            if t in ('SYMBOL', 'TICKER', 'TICKERS'): continue
            if not re.match(r'^[A-Z0-9\.\-]+$', t):
                continue
            out.append(t)
    return out


def load_headline_tickers(parquet_path):
    try:
        import pandas as pd
    except Exception:
        return set()
    if not os.path.exists(parquet_path):
        return set()
    try:
        df = pd.read_parquet(parquet_path)
        if 'ticker' not in df.columns:
            return set()
        return set(df['ticker'].astype(str).str.strip().str.upper().unique().tolist())
    except Exception:
        return set()


def write_temp_tickers(tickers, out_path):
    with open(out_path, 'w') as f:
        for t in tickers:
            f.write(t + '\n')


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--universe', default='Weekly ticker list.csv')
    p.add_argument('--headlines', default='data/weekly_headlines.parquet')
    p.add_argument('--sample', type=int, default=0, help='Only include first N zero-headline tickers')
    p.add_argument('--out-temp', default='scripts/zero_tickers.csv', help='Temporary tickers CSV to write')
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--use-scrape', action='store_true')
    p.add_argument('--newsapi-daily-limit', type=int, default=0)
    p.add_argument('--finnhub-per-minute', type=int, default=60)
    p.add_argument('--parallel-workers', type=int, default=1)
    p.add_argument('--no-run', action='store_true', help='Only write the subset file, do not invoke fetch')
    args = p.parse_args(argv)

    universe = load_universe(args.universe)
    if not universe:
        print('No universe found at', args.universe)
        return 1
    got = load_headline_tickers(args.headlines)
    zero = [t for t in universe if t not in got]
    if args.sample and args.sample > 0:
        zero = zero[:args.sample]

    if not zero:
        print('No zero-headline tickers found; nothing to do')
        return 0

    write_temp_tickers(zero, args.out_temp)
    print(f'Wrote {len(zero)} tickers to {args.out_temp}')

    if args.no_run:
        print('No-run requested; exiting after writing temp file')
        return 0

    # Build fetch command
    cmd = [sys.executable, 'scripts/fetch_headlines.py', '--tickers-file', args.out_temp, '--out', 'data/weekly_headlines.parquet', '--days', str(args.days), '--finnhub-per-minute', str(args.finnhub_per_minute), '--parallel-workers', str(args.parallel_workers)]
    if args.use_scrape:
        cmd.append('--use-scrape')
    if args.newsapi_daily_limit and args.newsapi_daily_limit > 0:
        cmd += ['--newsapi-daily-limit', str(args.newsapi_daily_limit)]

    print('Running fetch for zero-coverage tickers with command:')
    print(' '.join(cmd))
    ret = subprocess.call(cmd)
    return ret


if __name__ == '__main__':
    sys.exit(main())
