#!/usr/bin/env python3
"""Test layout() function directly."""
import sys
sys.path.insert(0, '/home/aarav/unified-dashboard')

print("Importing market_trends...")
from financial_dashboard.tabs import market_trends

print("Calling layout()...")
try:
    result = market_trends.layout()
    print(f"✅ Layout returned: {type(result)}")
    print(f"   Has children: {hasattr(result, 'children')}")
    if hasattr(result, 'children'):
        print(f"   Number of children: {len(result.children) if result.children else 0}")
except Exception as e:
    print(f"❌ Layout failed: {e}")
    import traceback
    traceback.print_exc()
