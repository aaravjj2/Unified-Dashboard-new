#!/usr/bin/env python3
"""
PHASE 6E: Module Identity Verification Script
Tests that _shared module is imported consistently and RESULTS_CACHE is populated.
"""
import sys
import os

# Add financial_dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'financial_dashboard'))

print("=" * 80)
print("PHASE 6E: MODULE IDENTITY VERIFICATION")
print("=" * 80)

# Test 1: Import _shared directly
print("\n[Test 1] Import _shared as SH")
import _shared as SH
print(f"  SH module: {SH.__file__}")
print(f"  id(SH): {id(SH)}")
print(f"  id(SH.RESULTS_CACHE): {id(SH.RESULTS_CACHE)}")
print(f"  RESULTS_CACHE keys: {SH.RESULTS_CACHE.keys()}")

# Check if prices are loaded
results = SH.RESULTS_CACHE.get('results', {})
prices = results.get('prices', {})
print(f"  Prices loaded: {len(prices)} tickers")
if prices:
    print(f"  Sample tickers: {list(prices.keys())[:5]}")
    sample_ticker = list(prices.keys())[0]
    print(f"  Sample price data ({sample_ticker}): {prices[sample_ticker]}")

# Test 2: Import from a simulated callback context
print("\n[Test 2] Simulate callback import")
def simulate_callback():
    """Simulates how a callback imports _shared"""
    import _shared as SH_callback
    print(f"  SH_callback module: {SH_callback.__file__}")
    print(f"  id(SH_callback): {id(SH_callback)}")
    print(f"  id(SH_callback.RESULTS_CACHE): {id(SH_callback.RESULTS_CACHE)}")
    
    # Check if same object
    print(f"  Same module object? {id(SH_callback) == id(SH)}")
    print(f"  Same RESULTS_CACHE object? {id(SH_callback.RESULTS_CACHE) == id(SH.RESULTS_CACHE)}")
    
    return SH_callback

SH_callback = simulate_callback()

# Test 3: Check if reload works
print("\n[Test 3] Test cache reload")
print(f"  Before reload: {len(SH.RESULTS_CACHE.get('results', {}).get('prices', {}))} prices")
try:
    SH._preload_persisted_prices()
    print(f"  After reload: {len(SH.RESULTS_CACHE.get('results', {}).get('prices', {}))} prices")
except Exception as e:
    print(f"  Reload failed: {e}")

# Test 4: Verify OUT_ROOT path
print("\n[Test 4] Verify output paths")
print(f"  SH.OUT_ROOT: {SH.OUT_ROOT}")
print(f"  OUT_ROOT exists: {os.path.exists(SH.OUT_ROOT)}")
weekly_prices = os.path.join(SH.OUT_ROOT, 'prices_weekly.json')
monthly_prices = os.path.join(SH.OUT_ROOT, 'prices_monthly.json')
print(f"  prices_weekly.json exists: {os.path.exists(weekly_prices)}")
print(f"  prices_monthly.json exists: {os.path.exists(monthly_prices)}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
