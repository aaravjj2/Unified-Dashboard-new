"""
Fetch data for a weekly picks universe (target ~1555 tickers) using dual Finnhub
API keys (rotate to respect per-key rate limits), supplement with yfinance, rank
tickers, and place buy orders on Alpaca for $500 per ticker.

Defaults: dry-run (no orders placed). To execute, pass --execute and ensure
ALPACA_API_KEY and ALPACA_SECRET_KEY are set in environment.

Environment variables expected:
- FINNHUB_API_KEY_1
- FINNHUB_API_KEY_2 (optional)
- ALPACA_API_KEY
- ALPACA_SECRET_KEY
- ALPACA_BASE_URL (optional, default paper API)

Usage examples:
    python financial_dashboard\scripts\fetch_and_trade_weekly.py --target-count 1555 --dry-run
    python financial_dashboard\scripts\fetch_and_trade_weekly.py --tickers-file my_universe.csv --execute

Notes on throttling:
- Finnhub: 60 req/min per key -> with 2 keys ~120 req/min (we sleep 0.6s between requests)
- Alpaca: 200 req/min -> we sleep 0.35s between order requests

This script focuses on robustness and conservative throttling. It logs actions and
writes outputs to `outputs/fetch_and_trade_<timestamp>.json`.
"""

import os
import sys
import time
import math
import json
import glob
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import requests
import pandas as pd

# yfinance is optional but useful for batch historicals
try:
    import yfinance as yf
except Exception:
    yf = None

import shutil
import subprocess

# Import our canonical key helpers
from financial_dashboard import key_names as KN

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger('fetch_and_trade_weekly')

# ---------------------------------------------------------------------------
# Secret helper: try environment first, then Doppler CLI if available
# ---------------------------------------------------------------------------

# NOTE: Secret lookup is centralized in `financial_dashboard.key_names.get_secret`
# which checks environment variables and falls back to the Doppler CLI if
# available. Use `KN.get_secret(name)` instead of local implementations.

# ---------------------------------------------------------------------------
# Utilities: picks file discovery, tickers expansion
# ---------------------------------------------------------------------------

def find_latest_picks_file() -> Optional[str]:
    # Search known locations for picks_*.csv and return the most recent
    patterns = [
        os.path.join('financial_dashboard', 'models', 'full_run', 'picks_*.csv'),
        os.path.join('financial_dashboard', 'models', 'weekly_run', 'picks_*.csv'),
        os.path.join('financial_dashboard', 'models', 'weekly_run_retrain', 'picks_*.csv'),
        os.path.join('financial_dashboard', 'models', 'weekly_run_multimodal', 'picks_*.csv'),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_tickers_from_csv(path: str) -> List[str]:
    df = pd.read_csv(path)
    # try common column names
    for c in ['ticker', 'symbol', 'Ticker', 'Symbol']:
        if c in df.columns:
            return [str(x).strip().upper() for x in df[c].dropna().unique().tolist()]
    # otherwise take first column
    first = df.columns[0]
    return [str(x).strip().upper() for x in df[first].dropna().unique().tolist()]


def expand_tickers_to_target(tickers: List[str], target: int) -> List[str]:
    if len(tickers) >= target:
        return tickers[:target]
    needed = target - len(tickers)
    logger.info('Need to expand tickers by %d to reach target %d', needed, target)
    # attempt to load S&P500 via wikipedia
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        pool = [s.strip().upper() for s in sp500['Symbol'].tolist() if s]
    except Exception:
        pool = []
    # fallback to some tech tickers if still not enough
    fallback = ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','BRK.B','JPM','JNJ','V','PG','UNH','MA','HD','DIS']
    pool.extend([x for x in fallback if x not in pool])
    # Add tickers from pool not already present
    for t in pool:
        if len(tickers) >= target:
            break
        if t not in tickers:
            tickers.append(t)
    return tickers[:target]


# ---------------------------------------------------------------------------
# Finnhub client with key rotation and throttling
# ---------------------------------------------------------------------------

class FinnhubRotator:
    def __init__(self, keys: List[str], per_key_limit_per_min: int = 60, safety_sleep: float = 0.6):
        self.keys = [k for k in keys if k]
        if not self.keys:
            raise ValueError('No Finnhub API keys provided')
        self.idx = 0
        self.n = len(self.keys)
        self.sleep = safety_sleep

    def _next_key(self) -> str:
        k = self.keys[self.idx % self.n]
        self.idx += 1
        return k

    def quote(self, symbol: str) -> Optional[dict]:
        key = self._next_key()
        url = f'https://finnhub.io/api/v1/quote'
        params = {'symbol': symbol, 'token': key}
        try:
            r = requests.get(url, params=params, timeout=20)
            time.sleep(self.sleep)
            if r.status_code == 200:
                return r.json()
            else:
                logger.debug('Finnhub quote failed %s %s: %s', symbol, r.status_code, r.text)
                return None
        except Exception as e:
            logger.warning('Finnhub quote exception for %s: %s', symbol, e)
            time.sleep(self.sleep)
            return None


# ---------------------------------------------------------------------------
# Alpaca order helper (uses REST endpoints via requests)
# ---------------------------------------------------------------------------

class AlpacaClient:
    def __init__(self, api_key: str, api_secret: str, base_url: Optional[str] = None, per_min_limit: int = 200, safety_sleep: float = 0.35):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or os.getenv('ALPACA_BASE_URL') or 'https://paper-api.alpaca.markets'
        self.headers = {'APCA-API-KEY-ID': self.api_key, 'APCA-API-SECRET-KEY': self.api_secret}
        self.sleep = safety_sleep

    def place_buy_order(self, symbol: str, qty: int, type: str = 'market', time_in_force: str = 'gtc') -> dict:
        url = f"{self.base_url}/v2/orders"
        payload = {'symbol': symbol, 'qty': qty, 'side': 'buy', 'type': type, 'time_in_force': time_in_force}
        try:
            r = requests.post(url, headers=self.headers, json=payload, timeout=30)
            time.sleep(self.sleep)
            if r.status_code in (200, 201):
                return r.json()
            else:
                logger.warning('Alpaca order failed %s: %s %s', symbol, r.status_code, r.text)
                return {'error': r.text, 'status_code': r.status_code}
        except Exception as e:
            logger.exception('Exception placing Alpaca order for %s: %s', symbol, e)
            time.sleep(self.sleep)
            return {'error': str(e)}


# ---------------------------------------------------------------------------
# Ranking logic using Finnhub quote and yfinance momentum
# ---------------------------------------------------------------------------


def compute_scores(tickers: List[str], fh: FinnhubRotator, batch_size_yf: int = 200) -> pd.DataFrame:
    """Return DataFrame with columns: ticker, price, prev_close, pct_1d, ret_1m, score"""
    rows = []
    # First, collect Finnhub quotes (fast single-value) to get current price and prev close
    for i, t in enumerate(tickers, 1):
        quote = fh.quote(t)
        price = None
        prev_close = None
        pct_1d = None
        if quote:
            price = quote.get('c')
            prev_close = quote.get('pc')
            try:
                if price is not None and prev_close is not None:
                    pct_1d = (price - prev_close) / max(abs(prev_close), 1e-9)
            except Exception:
                pct_1d = None
        rows.append({'ticker': t, 'price': price, 'prev_close': prev_close, 'pct_1d': pct_1d})
        if i % 100 == 0:
            logger.info('Fetched Finnhub quotes for %d/%d', i, len(tickers))
    df = pd.DataFrame(rows)

    # Next, use yfinance to compute 1-month return in batches to avoid hitting rate limits
    if yf is not None:
        all_ret = {}
        for i in range(0, len(tickers), batch_size_yf):
            batch = tickers[i:i+batch_size_yf]
            try:
                data = yf.download(batch, period='1mo', interval='1d', group_by='ticker', threads=True, progress=False)
                for t in batch:
                    try:
                        if len(batch) == 1 and isinstance(data, pd.DataFrame) and 'Close' in data.columns:
                            df_hist = data
                        else:
                            df_hist = data[t]['Close'] if t in data and 'Close' in data[t] else None
                        if df_hist is None or df_hist.empty:
                            all_ret[t] = None
                            continue
                        first = df_hist.dropna().iloc[0]
                        last = df_hist.dropna().iloc[-1]
                        all_ret[t] = (last / first - 1.0) if first and first != 0 else None
                    except Exception:
                        all_ret[t] = None
            except Exception as e:
                logger.warning('yfinance batch download failed for batch starting at %d: %s', i, e)
                for t in batch:
                    all_ret[t] = None
            time.sleep(1.0)  # pace the batches
        df['ret_1m'] = df['ticker'].map(all_ret)
    else:
        df['ret_1m'] = None

    # Compute score: weight ret_1m (70%) and 1d pct (30%) - handle missing safely
    def safe_val(v):
        try:
            return float(v) if v is not None else 0.0
        except Exception:
            return 0.0
    df['score'] = df.apply(lambda r: 0.7 * safe_val(r.get('ret_1m')) + 0.3 * safe_val(r.get('pct_1d')), axis=1)
    df = df.sort_values('score', ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--tickers-file', help='CSV with tickers (one column named ticker or first column)')
    p.add_argument('--target-count', type=int, default=1555, help='Target universe size')
    p.add_argument('--dry-run', action='store_true', default=True, help='Do not place live orders (default)')
    p.add_argument('--execute', action='store_true', help='Place live Alpaca orders (requires env keys). Overrides --dry-run')
    p.add_argument('--order-dollar', type=float, default=500.0, help='Dollar amount per ticker')
    p.add_argument('--output', default=None, help='Path to JSON output (defaults to outputs/...)')
    args = p.parse_args(argv)

    dry_run = not args.execute

    # Prepare tickers
    if args.tickers_file:
        if not os.path.exists(args.tickers_file):
            logger.error('Tickers file not found: %s', args.tickers_file)
            return
        tickers = load_tickers_from_csv(args.tickers_file)
    else:
        latest = find_latest_picks_file()
        if latest:
            logger.info('Found picks file: %s', latest)
            tickers = load_tickers_from_csv(latest)
        else:
            logger.warning('No picks file found; using fallback small universe')
            tickers = ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA']

    tickers = [t for t in tickers if isinstance(t, str) and t.strip()]
    tickers = [t.upper().strip() for t in tickers]

    if args.target_count:
        tickers = expand_tickers_to_target(tickers, args.target_count)

    logger.info('Prepared %d tickers for processing', len(tickers))

    # Finnhub rotator setup
    # Prefer env vars, then Doppler secrets
    fh_keys = [KN.get_secret('FINNHUB_API_KEY_1'), KN.get_secret('FINNHUB_API_KEY_2')]
    fh_keys = [k for k in fh_keys if k]
    if not fh_keys:
        logger.error('No FINNHUB_API_KEY_1/2 found in environment; aborting')
        return
    fh = FinnhubRotator(fh_keys, safety_sleep=0.6)

    # Compute scores
    logger.info('Fetching data and computing scores; this may take several minutes')
    scores_df = compute_scores(tickers, fh)

    # Persist scoring output
    out = {'generated_at': datetime.utcnow().isoformat(), 'n_tickers': len(scores_df), 'order_dollar': args.order_dollar}
    out['scores_preview'] = scores_df.head(50).to_dict('records')

    # Prepare Alpaca client if executing
    alpaca_api_key = KN.get_secret('ALPACA_API_KEY')
    alpaca_secret = KN.get_secret('ALPACA_SECRET_KEY')
    alpaca_base = os.getenv('ALPACA_BASE_URL')
    alp = None
    if not dry_run:
        if not (alpaca_api_key and alpaca_secret):
            logger.error('ALPACA_API_KEY or ALPACA_SECRET_KEY missing; cannot execute orders')
            return
        alp = AlpacaClient(alpaca_api_key, alpaca_secret, base_url=alpaca_base, safety_sleep=0.35)

    # Place orders for all tickers: $order_dollar each
    orders = []
    for idx, row in scores_df.iterrows():
        t = row['ticker']
        price = row.get('price')
        if price is None or price <= 0:
            logger.warning('Skipping %s: no valid price', t)
            continue
        qty = int(math.floor(args.order_dollar / price))
        if qty <= 0:
            logger.info('Skipping %s: price %s > order_dollar %s', t, price, args.order_dollar)
            continue

        if dry_run:
            logger.info('[dry-run] Would place order: BUY %d of %s at market (~$%s)', qty, t, args.order_dollar)
            orders.append({'ticker': t, 'qty': qty, 'status': 'dry-run', 'price': price, 'score': row.get('score')})
        else:
            res = alp.place_buy_order(t, qty)
            orders.append({'ticker': t, 'qty': qty, 'status': res})

    out['orders'] = orders

    # Write output file
    out_path = args.output or os.path.join('outputs', f'fetch_and_trade_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh_out:
        json.dump(out, fh_out, indent=2, default=str)

    logger.info('Completed. Results written to %s', out_path)


if __name__ == '__main__':
    main()
