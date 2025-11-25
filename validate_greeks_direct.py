#!/usr/bin/env python
"""
FIX A - Repair Attempt 2: Server-side validation via API test
Directly call the data loader and check if Greeks are added
"""
import sys
import os

# Add dashboard to path
sys.path.insert(0, '/home/aarav/unified-dashboard/financial_dashboard')

from tabs.options_lab.data_loader import fetch_options_chain
import json

print("="*70)
print("FIX A - Repair Attempt 2: Direct API Validation")
print("Testing if Greeks are added to options chain data")
print("="*70)

# Test with AAPL
ticker = "AAPL"
print(f"\n📊 Fetching options chain for {ticker}...")

# Force yfinance path (use_alpaca=False)
result_yfinance = fetch_options_chain(ticker, use_mock=False, use_alpaca=False)

print(f"\n✅ Retrieved data from {result_yfinance.get('source')}")
print(f"   Spot price: ${result_yfinance.get('spot_price'):.2f}")
print(f"   Expirations: {len(result_yfinance.get('expirations', []))}")
print(f"   Calls: {len(result_yfinance.get('calls', []))} rows")
print(f"   Puts: {len(result_yfinance.get('puts', []))} rows")

# Check for Greeks columns
calls = result_yfinance.get('calls')
puts = result_yfinance.get('puts')

if calls is not None and len(calls) > 0:
    print(f"\n📋 Calls DataFrame columns ({len(calls.columns)}):")
    for col in calls.columns:
        print(f"   - {col}")
    
    # Check Greeks
    greeks = ['delta', 'gamma', 'vega', 'theta']
    greeks_present = {g: g in calls.columns for g in greeks}
    
    print(f"\n🔍 Greeks columns in Calls:")
    all_present = True
    for greek, present in greeks_present.items():
        symbol = "✅" if present else "❌"
        print(f"   {symbol} {greek}: {present}")
        if not present:
            all_present = False
    
    if all_present:
        print(f"\n✅ SUCCESS: All Greeks columns present")
        print(f"\n📊 Sample Greeks values (first call option):")
        first_call = calls.iloc[0]
        for greek in greeks:
            print(f"   {greek}: {first_call[greek]:.4f}")
        
        exit(0)
    else:
        print(f"\n❌ FAILURE: Missing Greeks columns")
        exit(1)
else:
    print(f"\n❌ FAILURE: No calls data returned")
    exit(1)
