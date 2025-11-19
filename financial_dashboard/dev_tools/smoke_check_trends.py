"""
Smoke-check script for Trends canonical JSON and server-rendered preview.

Usage:
  python dev_tools/smoke_check_trends.py --tickers UBER,AAPL [--check-layout]

Checks:
- `outputs/tech_report_detailed.json` exists and contains the listed tickers.
- Optionally requests http://localhost:8050/_dash-layout and ensures the server-rendered
  HTML contains a small table preview (a lightweight check for the 'Preview (server-rendered)') string.

This script is intentionally small and dependency-free (uses only stdlib).
"""

import os
import json
import argparse
import sys
import urllib.request

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_ROOT = os.path.join(PROJ_ROOT, '..', 'outputs')
# normalize path
OUT_ROOT = os.path.normpath(OUT_ROOT)


def check_json(tickers):
    jfn = os.path.join(OUT_ROOT, 'tech_report_detailed.json')
    if not os.path.exists(jfn):
        print(f"MISSING: {jfn}")
        return 2
    try:
        with open(jfn, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)
    except Exception as e:
        print(f"ERROR reading {jfn}: {e}")
        return 2
    recs = payload.get('records') if isinstance(payload, dict) else None
    if not recs:
        print(f"NO RECORDS in {jfn}")
        return 2
    found = set((r.get('ticker') or '').upper() for r in recs if isinstance(r, dict))
    missing = [t for t in tickers if t.upper() not in found]
    if missing:
        print(f"MISSING TICKERS: {missing}")
        return 3
    print(f"OK: found tickers {tickers}")
    return 0


def check_layout():
    url = 'http://127.0.0.1:8050/_dash-layout'
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = r.read().decode('utf-8', errors='ignore')
            if 'Preview (server-rendered)' in data or 'Loaded cached results' in data:
                print('OK: server-rendered preview appears in layout')
                return 0
            else:
                print('WARN: layout fetched but preview marker not found')
                return 4
    except Exception as e:
        print(f"ERROR fetching layout: {e}")
        return 5


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--tickers', required=True, help='Comma-separated tickers to assert present in canonical JSON')
    p.add_argument('--check-layout', action='store_true', help='Also fetch /_dash-layout and check for preview marker')
    args = p.parse_args(argv)
    tickers = [t.strip().upper() for t in args.tickers.split(',') if t.strip()]
    rc = check_json(tickers)
    if rc != 0:
        return rc
    if args.check_layout:
        return check_layout()
    return 0


if __name__ == '__main__':
    sys.exit(main())
