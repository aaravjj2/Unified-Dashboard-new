#!/usr/bin/env python3
"""Test if Market Trends callbacks register without hanging."""

import sys
import time
sys.path.insert(0, '/home/aarav/unified-dashboard')

print("Importing modules...")
from dash import Dash
from financial_dashboard.tabs import market_trends

print("✅ Imports successful")

print("Creating Dash app...")
app = Dash(__name__)

print("Registering callbacks...")
start = time.time()
try:
    market_trends.register_callbacks(app)
    duration = time.time() - start
    print(f"✅ Callbacks registered successfully in {duration:.2f}s")
    print(f"   App has {len(app.callback_map)} callbacks registered")
    
    # Check if our callbacks exist
    mt_callbacks = [k for k in app.callback_map.keys() if 'mt-' in str(k) or 'status' in str(k) or 'results-area' in str(k)]
    print(f"   Found {len(mt_callbacks)} Market Trends callbacks:")
    for cb in mt_callbacks[:5]:
        print(f"      - {cb}")
    
except Exception as e:
    duration = time.time() - start
    print(f"❌ Callback registration failed after {duration:.2f}s:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ ALL TESTS PASSED")
