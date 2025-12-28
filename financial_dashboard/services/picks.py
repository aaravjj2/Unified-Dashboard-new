"""
Stock Picks Generator & Execution

Generates trade ideas from a candidate universe using live price signals and news, and
optionally executes market orders via AlpacaExecutor (paper or live depending on config).

Safety:
- Orders will be DRY-RUN by default. To actually place orders, set environment variable
  `ALLOW_AUTO_BUY=1` and ensure Alpaca keys are configured. Prefer PAPER trading by default.
"""
from typing import List, Dict, Optional
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _default_universe() -> List[str]:
    # Practical small universe to sample from; could be extended to S&P100 etc.
    return [
        'AAPL','MSFT','NVDA','AMZN','GOOGL','TSLA','META','JPM','BAC','GS',
        'NFLX','ADBE','INTC','AMD','PYPL','SQ','UBER','NIO','CRM','ORCL'
    ]


def generate_stock_picks(n: int = 5, universe: Optional[List[str]] = None) -> List[Dict]:
    """Generate a list of stock picks (long/short) based on simple momentum heuristics.

    Strategy:
    - Fetch recent % change for symbols using `price_fetch.fetch_prices_batch`
    - Pick top gainers for LONGs and top losers for SHORTs, mix based on direction.

    Returns a list of picks with fields: ticker, direction, confidence, suggested_qty (None)
    """
    try:
        from financial_dashboard.utils.price_fetch import fetch_prices_batch
    except Exception:
        fetch_prices_batch = None

    universe = universe or _default_universe()

    prices = {}
    if fetch_prices_batch:
        try:
            res = fetch_prices_batch(universe, parallelism=8, context='daily')
            for t, v in res.items():
                prices[t] = v
        except Exception as e:
            logger.warning(f"fetch_prices_batch failed: {e}")
            prices = {}

    # Score tickers by change_pct if available
    scored = []
    for t in universe:
        info = prices.get(t) or {}
        change = info.get('change_pct') if info else None
        if change is None:
            # fallback: small random score so we still pick new stocks
            try:
                import random
                change = random.uniform(-1.5, 1.5)
            except Exception:
                change = 0.0
        scored.append((t, float(change)))

    # Sort by change descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Build separated lists: longs (top gainers) and shorts (top losers)
    half = max(1, n // 2)
    gainers = scored[:half]
    losers = scored[-half:]

    longs = []
    shorts = []

    for t, ch in gainers:
        longs.append({
            'ticker': t,
            'direction': 'LONG',
            'signal': 'momentum',
            'score': round(float(ch), 2),
            'generated_at': datetime.now().isoformat()
        })

    for t, ch in reversed(losers):
        shorts.append({
            'ticker': t,
            'direction': 'SHORT',
            'signal': 'momentum',
            'score': round(float(ch), 2),
            'generated_at': datetime.now().isoformat()
        })

    # Ensure strict separation: unique tickers across longs and shorts
    long_tickers = {p['ticker'] for p in longs}
    shorts = [s for s in shorts if s['ticker'] not in long_tickers]

    combined = longs + shorts

    # Trim to requested n preserving block separation (longs first, then shorts)
    return combined[:n]


def generate_stock_picks_separated(n: int = 5, universe: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """Return picks separated into `longs` and `shorts` lists.

    Keeps same scoring logic but returns structured output so callers (UI) can present
    longs and shorts strictly separately.
    """
    combined = generate_stock_picks(n=n, universe=universe)
    longs = [p for p in combined if p.get('direction') == 'LONG']
    shorts = [p for p in combined if p.get('direction') == 'SHORT']
    return {'longs': longs, 'shorts': shorts, 'combined': combined}


def execute_picks(picks: List[Dict], allocation_per_pick: float = 500.0, dry_run: Optional[bool] = None) -> List[Dict]:
    """Execute picks by placing market orders via AlpacaExecutor.

    Args:
        picks: list of picks (from generate_stock_picks)
        allocation_per_pick: USD allocation per pick (used to compute qty)
        dry_run: If None, default True unless ALLOW_AUTO_BUY=1. If True, will not place live orders.

    Returns:
        List of order result dicts.
    """
    allow = os.getenv('ALLOW_AUTO_BUY', '0') == '1'
    if dry_run is None:
        dry_run = not allow

    results = []

    try:
        from financial_dashboard.utils.execution import AlpacaExecutor
        executor = AlpacaExecutor(paper=True)
    except Exception as e:
        logger.error(f"AlpacaExecutor not available: {e}")
        executor = None

    # Support both: picks can be a dict with 'longs'/'shorts' or a flat list
    flat_picks = []
    if isinstance(picks, dict):
        longs = picks.get('longs', [])
        shorts = picks.get('shorts', [])
        # concat longs then shorts to preserve separation
        flat_picks = list(longs) + list(shorts)
    elif isinstance(picks, list):
        flat_picks = picks
    else:
        logger.warning('Unknown picks format; attempting to iterate')
        try:
            flat_picks = list(picks)
        except Exception:
            flat_picks = []

    for p in flat_picks:
        ticker = p['ticker']
        side = 'buy' if p.get('direction', 'LONG') == 'LONG' else 'sell'

        # Determine price (use price_fetch as fallback)
        price = None
        try:
            from financial_dashboard.utils.price_fetch import get_price_single
            pf = get_price_single(ticker)
            price = pf.get('last_price') if pf else None
        except Exception:
            price = None

        if price and price > 0:
            qty = max(1, round(allocation_per_pick / price, 2))
        else:
            qty = 1.0

        order_res = None
        if executor:
            try:
                order_res = executor.place_market_order(ticker=ticker, qty=qty, side=side, dry_run=dry_run)
            except Exception as e:
                logger.error(f"Order failed for {ticker}: {e}")
                order_res = {'ticker': ticker, 'error': str(e)}
        else:
            order_res = {'ticker': ticker, 'qty': qty, 'side': side, 'dry_run': True, 'note': 'executor unavailable'}

        results.append({'pick': p, 'order': order_res})

    # Persist live run logs for audit when actual orders were placed (not dry-run)
    try:
        if not dry_run and results:
            reports_dir = os.path.join(os.getcwd(), 'reports', 'picks', 'live_runs')
            os.makedirs(reports_dir, exist_ok=True)
            import uuid
            run_id = str(uuid.uuid4())
            out_path = os.path.join(reports_dir, f'live_run_{run_id}.json')
            payload = {
                'run_id': run_id,
                'timestamp': datetime.utcnow().isoformat(),
                'picks_count': len(flat_picks),
                'results': results
            }
            import json
            with open(out_path, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, indent=2, default=str)
            logger.info(f"Persisted live run log: {out_path}")
    except Exception as e:
        logger.warning(f"Failed to persist live run log: {e}")

    return results
