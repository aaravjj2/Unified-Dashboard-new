#!/usr/bin/env python3
"""Simple updater for market trend + pulse.
Writes outputs/market_trend_latest.json and outputs/market_trend_{YYYYMMDD}.json

This script uses the compute_market_trend_and_pulse function and accepts
optional JSON input via --input-file to supply real numbers. Otherwise it
runs a synthetic sample for demonstration.
"""
import os
import json
import argparse
from datetime import datetime

# ensure package path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.market_trend import compute_market_trend_and_pulse


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input-file', help='JSON file with input values for signals')
    p.add_argument('--out-root', default=os.path.join(os.path.dirname(__file__), '..', 'outputs'))
    p.add_argument('--state-path', default=os.path.join(os.path.dirname(__file__), '..', 'cache', 'market_trend_state.json'))
    args = p.parse_args()

    # default sample inputs (safe demo values)
    sample = {
        'r1m': 0.03, 'r3m': 0.08, 'r6m': 0.12,
        'ma50_pct_slope': 0.015, 'ma50_vs_ma200': 0.04, 'pct_above_200d': 0.55,
        'vix': 18.0, 'vix_mean_252': 20.0, 'vix_std_252': 5.0,
        'r1d': -0.01, 'r2d': -0.008, 'adv_decl_today': -0.1, 'vix_delta': 0.05, 'notable_market_news': False
    }

    inputs = sample
    if args.input_file and os.path.exists(args.input_file):
        try:
            with open(args.input_file, 'r', encoding='utf-8') as fh:
                j = json.load(fh)
                inputs.update(j)
        except Exception as e:
            print('Could not load input file:', e)

    out = compute_market_trend_and_pulse(
        inputs['r1m'], inputs['r3m'], inputs['r6m'],
        inputs['ma50_pct_slope'], inputs['ma50_vs_ma200'], inputs['pct_above_200d'],
        inputs['vix'], inputs['vix_mean_252'], inputs['vix_std_252'],
        inputs['r1d'], inputs['r2d'], inputs['adv_decl_today'], inputs['vix_delta'], inputs.get('notable_market_news', False),
        ema_alpha=0.25, state_path=args.state_path, persist_state=True
    )

    os.makedirs(args.out_root, exist_ok=True)
    latest_fn = os.path.join(args.out_root, 'market_trend_latest.json')
    dated_fn = os.path.join(args.out_root, f"market_trend_{datetime.utcnow().strftime('%Y-%m-%d')}.json")

    try:
        with open(latest_fn, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, indent=2)
        with open(dated_fn, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, indent=2)
        print('Wrote:', latest_fn, dated_fn)
    except Exception as e:
        print('Failed to write outputs:', e)

    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
