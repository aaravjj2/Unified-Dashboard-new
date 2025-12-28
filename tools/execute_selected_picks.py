#!/usr/bin/env python3
"""
Execute selected picks for weekly and monthly runs:
- Find latest `reports/picks/runs/*/selected.json` for weekly and monthly
- Query Alpaca positions/orders to see what's already bought
- Execute market orders for unbought picks using `financial_dashboard.services.picks.execute_picks`
- Annotate `selected.json` supplemental entries with 'supplemental': True and 'annotated_at'

Requires environment:
- ALLOW_AUTO_BUY=1 to actually place orders
- Alpaca keys: APCA_API_KEY_ID and APCA_API_SECRET_KEY

This script uses the existing `execute_picks` function which persists live-run logs.
"""

import os
import json
from pathlib import Path
import time
import sys

# Ensure project root is on sys.path so we can import `financial_dashboard` when run as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

ROOT = Path.cwd()
RUNS_DIR = ROOT / 'reports' / 'picks' / 'runs'
LIVE_DIR = ROOT / 'reports' / 'picks' / 'live_runs'

# helper to find latest run for type

def latest_run(run_type: str):
    runs = []
    if not RUNS_DIR.exists():
        return None
    for d in RUNS_DIR.iterdir():
        m = d / 'manifest.json'
        if m.exists():
            try:
                man = json.load(open(m, 'r', encoding='utf-8'))
                if man.get('run_type') == run_type:
                    runs.append((d.stat().st_mtime, d))
            except Exception:
                pass
    if not runs:
        return None
    runs.sort(reverse=True)
    return runs[0][1]


def read_selected(run_dir: Path):
    sel = run_dir / 'selected.json'
    if not sel.exists():
        return []
    try:
        return json.load(open(sel, 'r', encoding='utf-8'))
    except Exception:
        return []


def annotate_supplementals(run_dir: Path, canonical_set: set):
    sel_path = run_dir / 'selected.json'
    if not sel_path.exists():
        return
    try:
        selected = json.load(open(sel_path, 'r', encoding='utf-8'))
    except Exception:
        return
    changed = False
    for rec in selected:
        t = (rec.get('ticker') or '').upper()
        if t and t not in canonical_set:
            if not rec.get('supplemental'):
                rec['supplemental'] = True
                rec['annotated_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                changed = True
    if changed:
        json.dump(selected, open(sel_path, 'w', encoding='utf-8'), indent=2, default=str)


# Build canonical sets
import csv
CANONICAL_WEEKLY = ROOT / 'data' / 'picks_input' / 'weekly_source.csv'
CANONICAL_MONTHLY = ROOT / 'data' / 'picks_input' / 'monthly_source.csv'

def read_canonical(path: Path):
    if not path.exists():
        return set()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return { (r.get('ticker') or '').upper() for r in reader }
    except Exception:
        return set()

canon_week = read_canonical(CANONICAL_WEEKLY)
canon_month = read_canonical(CANONICAL_MONTHLY)

# Find latest runs
weekly_dir = latest_run('weekly')
monthly_dir = latest_run('monthly')

if not weekly_dir and not monthly_dir:
    print('No runs found under reports/picks/runs')
    exit(1)

print('Found runs: weekly=', weekly_dir, 'monthly=', monthly_dir)

# Read selected lists
weekly_sel = read_selected(weekly_dir) if weekly_dir else []
monthly_sel = read_selected(monthly_dir) if monthly_dir else []

weekly_tickers = [ (s.get('ticker') or '').upper() for s in weekly_sel ]
monthly_tickers = [ (s.get('ticker') or '').upper() for s in monthly_sel ]

print('Weekly selected tickers:', weekly_tickers)
print('Monthly selected tickers:', monthly_tickers)

# Determine already bought tickers from live run logs
bought = set()
if LIVE_DIR.exists():
    for p in sorted(LIVE_DIR.glob('*.json')):
        try:
            j = json.load(open(p, 'r', encoding='utf-8'))
            for r in j.get('results', []):
                ord = r.get('order') or {}
                t = (ord.get('ticker') or r.get('pick', {}).get('ticker') or '').upper()
                dry = ord.get('dry_run', True)
                if dry is False:
                    bought.add(t)
        except Exception:
            pass

# Also check Alpaca account positions and filled orders
alpaca_bought = set()
have_alpaca = False
try:
    from alpaca.trading.client import TradingClient
    key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA2_KEY')
    secret = os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA2_SECRET')
    if key and secret:
        client = TradingClient(key, secret, paper=True)
        have_alpaca = True
        # positions
        try:
            positions = client.get_all_positions()
            for p in positions:
                sym = getattr(p, 'symbol', None) or p.get('symbol') if isinstance(p, dict) else None
                if not sym:
                    continue
                qty = float(getattr(p, 'qty', 0) or p.get('qty', 0) or 0)
                if qty and qty > 0:
                    alpaca_bought.add(sym.upper())
        except Exception as e:
            print('Warning: could not fetch positions from Alpaca:', e)
        # recent orders (today)
        try:
            orders = client.get_orders(status='all', limit=100)
            for o in orders:
                # object may be dict or object
                symbol = getattr(o, 'symbol', None) or (o.get('symbol') if isinstance(o, dict) else None)
                status = getattr(o, 'status', None) or (o.get('status') if isinstance(o, dict) else None)
                filled = status == 'filled'
                if filled and symbol:
                    alpaca_bought.add(symbol.upper())
        except Exception as e:
            print('Warning: could not fetch orders from Alpaca:', e)
except Exception as e:
    print('Alpaca client not available or keys missing:', e)

print('Bought from logs:', sorted(list(bought)))
print('Bought from Alpaca positions/orders:', sorted(list(alpaca_bought)))

# Consolidate bought set
already_bought = set(list(bought) + list(alpaca_bought))

# Determine which tickers still need buying
to_buy_weekly = [t for t in weekly_tickers if t and t not in already_bought]
to_buy_monthly = [t for t in monthly_tickers if t and t not in already_bought]

print('To buy weekly:', to_buy_weekly)
print('To buy monthly:', to_buy_monthly)

# If ALLOW_AUTO_BUY not set, abort before placing orders
if os.getenv('ALLOW_AUTO_BUY') != '1':
    print('ALLOW_AUTO_BUY not set to 1; aborting execution. Set ALLOW_AUTO_BUY=1 to proceed.')
else:
    # Load execution function
    try:
        from financial_dashboard.services.picks import execute_picks
    except Exception as e:
        print('Could not import execute_picks:', e)
        execute_picks = None

    # Helper to build pick records from ticker list using latest selected entries or minimal dict
    def build_picks_from_tickers(tickers, selected_records):
        out = []
        lookup = { (r.get('ticker') or '').upper(): r for r in selected_records }
        for t in tickers:
            rec = lookup.get(t)
            if rec:
                out.append(rec)
            else:
                out.append({'ticker': t, 'direction': 'LONG'})
        return out

    # Execute weekly
    if to_buy_weekly and execute_picks:
        picks = build_picks_from_tickers(to_buy_weekly, weekly_sel)
        print('Executing weekly buys for:', [p.get('ticker') for p in picks])
        res = execute_picks(picks, allocation_per_pick=500, dry_run=False)
        print('Weekly execution results saved, count=', len(res))
    else:
        print('No weekly buys needed or execute_picks unavailable')

    # Execute monthly
    if to_buy_monthly and execute_picks:
        # Avoid buying duplicates that were purchased in weekly execution (re-evaluate live logs)
        # Recompute already_bought after possible weekly run artifacts
        new_bought = set()
        if LIVE_DIR.exists():
            for p in sorted(LIVE_DIR.glob('*.json')):
                try:
                    j = json.load(open(p, 'r', encoding='utf-8'))
                    for r in j.get('results', []):
                        ord = r.get('order') or {}
                        t = (ord.get('ticker') or r.get('pick', {}).get('ticker') or '').upper()
                        dry = ord.get('dry_run', True)
                        if dry is False:
                            new_bought.add(t)
                except Exception:
                    pass
        already_bought |= new_bought
        to_buy_monthly = [t for t in to_buy_monthly if t not in already_bought]

        if to_buy_monthly:
            picks = build_picks_from_tickers(to_buy_monthly, monthly_sel)
            print('Executing monthly buys for:', [p.get('ticker') for p in picks])
            res = execute_picks(picks, allocation_per_pick=500, dry_run=False)
            print('Monthly execution results saved, count=', len(res))
        else:
            print('No monthly buys needed after weekly execution')

# Finally, annotate supplemental entries in selected.json files
if weekly_dir:
    annotate_supplementals(weekly_dir, canon_week)
if monthly_dir:
    annotate_supplementals(monthly_dir, canon_month)

print('Done.')
