#!/usr/bin/env python3
"""
Quick test to verify Options Lab changes are loaded
"""

import sys
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard')

from financial_dashboard.tabs.options_lab.layout import layout

print("="*80)
print("TESTING OPTIONS LAB LAYOUT")
print("="*80)

l = layout()
layout_str = str(l)

# Test 1: Contract Selector components
tests = {
    "Contract Selector Card": "Contract Selector" in layout_str,
    "Option Type Radio (contract-option-type)": "contract-option-type" in layout_str,
    "Strike Input (contract-strike-input)": "contract-strike-input" in layout_str,
    "Expiration Selector (contract-expiration-selector)": "contract-expiration-selector" in layout_str,
    "Generate Forecast Button": "Generate Forecast" in layout_str,
    "Get TradingView Signals Button": "Get TradingView Signals" in layout_str,
    "TradingView Signals Container": "tradingview-signals-container" in layout_str,
}

print("\n✅ Component Checks:")
for name, result in tests.items():
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"  {status}: {name}")

# Test 2: Check if old TradingView tab is removed
print("\n🔍 Checking for removed components:")
removed_checks = {
    "TradingView subtab (should be REMOVED)": 'tab_id="tradingview-signals"' in layout_str,
    "TradingView refresh button (should be REMOVED)": "tradingview-refresh-btn" in layout_str,
    "TradingView total signals (should be REMOVED)": "tradingview-total-signals" in layout_str,
}

for name, still_exists in removed_checks.items():
    if still_exists:
        print(f"  ❌ FAIL: {name} - STILL EXISTS!")
    else:
        print(f"  ✅ PASS: {name} - Correctly removed")

# Test 3: Count subtabs
import re
subtabs = re.findall(r'tab_id="([^"]+)"', layout_str)
print(f"\n📊 Found {len(subtabs)} subtabs: {subtabs}")

print("\n" + "="*80)
if all(tests.values()) and not any(removed_checks.values()):
    print("✅ ALL TESTS PASSED - Layout has correct changes!")
    sys.exit(0)
else:
    print("❌ SOME TESTS FAILED - Layout may not have changes")
    sys.exit(1)
