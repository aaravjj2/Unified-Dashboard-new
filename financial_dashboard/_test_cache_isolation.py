#!/usr/bin/env python
"""Test script to diagnose cache isolation issue in Dash callbacks."""
import sys
import os

# Simulate the import path Gunicorn uses
sys.path.insert(0, os.path.dirname(__file__))

import _shared as SH

print(f"[TEST] RESULTS_CACHE keys: {list(SH.RESULTS_CACHE.keys())}")
print(f"[TEST] RESULTS_CACHE['results'] type: {type(SH.RESULTS_CACHE.get('results'))}")

if SH.RESULTS_CACHE.get('results'):
    print(f"[TEST] RESULTS_CACHE['results'] keys: {list(SH.RESULTS_CACHE['results'].keys())}")
    if 'prices' in SH.RESULTS_CACHE['results']:
        prices = SH.RESULTS_CACHE['results']['prices']
        print(f"[TEST] Number of tickers in prices: {len(prices)}")
        # Print first 3 tickers
        for i, (ticker, data) in enumerate(list(prices.items())[:3]):
            print(f"[TEST]   {ticker}: current_price={data.get('current_price')}, source={data.get('source')}")
    else:
        print("[TEST] ❌ 'prices' key missing from RESULTS_CACHE['results']!")
else:
    print("[TEST] ❌ RESULTS_CACHE['results'] is None or missing!")

# Now simulate what the weekly_picks callback does
cached_results = SH.RESULTS_CACHE.get('results')
cached_prices = cached_results.get('prices') if cached_results else {}

print(f"\n[CALLBACK SIMULATION]")
print(f"cached_results type: {type(cached_results)}")
print(f"cached_prices type: {type(cached_prices)}")
print(f"Number of cached prices: {len(cached_prices)}")

# Check specific tickers from the CSV
test_tickers = ['ASTS', 'SNDK', 'RGTI']
for t in test_tickers:
    entry = cached_prices.get(t) or {}
    current_price = entry.get('current_price')
    print(f"  {t}: current_price={current_price}, entry={bool(entry)}")
