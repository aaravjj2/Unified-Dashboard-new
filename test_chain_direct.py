#!/usr/bin/env python3
"""
Test Options Lab chain loading via direct Python import
"""
import sys
sys.path.insert(0, '/home/aarav/unified-dashboard')

from financial_dashboard.tabs.options_lab.data_loader import fetch_options_chain

print("Testing direct chain fetch...")
result = fetch_options_chain('SPY', use_mock=False, use_alpaca=False)

print(f"Result keys: {result.keys()}")
if 'error' not in result or not result['error']:
    print(f"✓ SUCCESS")
    print(f"  Source: {result.get('source', 'unknown')}")
    print(f"  Spot price: ${result.get('spot_price', 0):.2f}")
    print(f"  Calls: {len(result.get('calls', []))}")
    print(f"  Puts: {len(result.get('puts', []))}")
else:
    print(f"✗ FAILED: {result.get('error', 'Unknown error')}")
