#!/usr/bin/env python3
"""Direct test of the fixed callback"""
import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard')

from financial_dashboard.tabs.options_lab.data_loader import fetch_options_chain

print("Testing data loader with SPY...")
result = fetch_options_chain("SPY", use_mock=False, use_alpaca=True)

if result:
    print(f"✅ Got data!")
    print(f"   Ticker: {result.get('ticker')}")
    print(f"   Spot price: ${result.get('spot_price')}")
    print(f"   Source: {result.get('source')}")
    print(f"   Expirations: {len(result.get('expirations', []))}")
    print(f"   First 3 exps: {result.get('expirations', [])[:3]}")
    print(f"   Calls: {len(result.get('calls', []))} rows")
    print(f"   Puts: {len(result.get('puts', []))} rows")
    print(f"   Error: {result.get('error')}")
else:
    print("❌ No data returned")
