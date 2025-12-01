#!/usr/bin/env python3
"""
Debug: Volatility Lab Callback Registration Test
=================================================
Check if callbacks are being registered properly.
"""

import sys
sys.path.insert(0, '/home/aarav/unified-dashboard')

from financial_dashboard.app import create_app

app_instance = create_app()
dash_app = app_instance.app

# Check registered callbacks
print("\n=== DASH CALLBACK REGISTRY ===")
print(f"Total callbacks registered: {len(dash_app.callback_map)}")

# Search for volatility lab callbacks
vol_lab_callbacks = []
for cb_id, cb_spec in dash_app.callback_map.items():
    # Check if any output IDs start with 'vl-'
    if any('vl-' in str(output) for output in cb_spec.get('outputs', [])):
        vol_lab_callbacks.append(cb_id)
        print(f"\n✅ Volatility Lab Callback: {cb_id}")
        print(f"   Outputs: {cb_spec.get('outputs', [])[:2]}...")  # First 2 outputs
        print(f"   Inputs: {cb_spec.get('inputs', [])[:2]}...")    # First 2 inputs

print(f"\n=== SUMMARY ===")
print(f"Volatility Lab callbacks found: {len(vol_lab_callbacks)}")
print(f"Expected: 6")

if len(vol_lab_callbacks) < 6:
    print("\n❌ PROBLEM DETECTED: Missing callbacks!")
else:
    print("\n✅ All callbacks registered correctly")
