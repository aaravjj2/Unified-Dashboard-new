#!/usr/bin/env python3
"""Test screener backend function"""

import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard/financial_dashboard')

from picker.screening_universe import SCREENING_UNIVERSE
from tabs.market_trends import _screen_stocks

print(f"Testing screener with {len(SCREENING_UNIVERSE)} stocks...")
print(f"First 10 tickers: {SCREENING_UNIVERSE[:10]}")

# Test with VERY loose filters
results = _screen_stocks(
    universe=SCREENING_UNIVERSE[:10],  # Just first 10 for speed
    min_price=0,
    max_price=10000,
    min_volume=0,
    min_rsi=0,
    max_rsi=100,
    trend=None
)

print(f"\n✅ Got {len(results)} results")
for r in results:
    print(f"  {r['ticker']}: ${r['price']:.2f}, Vol={r['volume']:,}, RSI={r['rsi']:.1f}, Score={r['score']}")

if len(results) == 0:
    print("\n❌ ERROR: No results even with loose filters!")
    print("This means the API calls are failing.")
