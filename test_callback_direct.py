#!/usr/bin/env python3
"""Direct callback invocation test"""
import os
os.environ['AZURE_ENABLED'] = 'false'
os.environ['OPTIONS_DETERMINISTIC'] = '1'

from financial_dashboard.app import create_app

print("Creating app...")
app = create_app()

print("\nCallback map keys:")
for i, key in enumerate(list(app.callback_map.keys())[:20]):
    print(f"  {i+1}. {key}")

# Look for mt-run-analysis-btn callback
mt_callback = None
for key, callback_info in app.callback_map.items():
    if 'mt-run-analysis-btn' in str(key):
        print(f"\n✅ FOUND MT CALLBACK: {key}")
        mt_callback = (key, callback_info)
        break

if not mt_callback:
    print("\n❌ NO MT CALLBACK FOUND!")
else:
    print("\nCallback details:")
    print(f"  Key: {mt_callback[0]}")
    print(f"  Info keys: {mt_callback[1].keys() if hasattr(mt_callback[1], 'keys') else 'N/A'}")
    
print("\nTotal callbacks registered:", len(app.callback_map))
