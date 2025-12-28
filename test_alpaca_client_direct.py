#!/usr/bin/env python3
"""Test if Alpaca client actually works"""
import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard')

from financial_dashboard.tabs.options_lab.alpaca_options import get_alpaca_client

print("Testing Alpaca client...")
client = get_alpaca_client()
print(f"Client available: {getattr(client, 'available', True)}")

if getattr(client, 'available', True):
    print("\nTrying to fetch SPY options chain...")
    try:
        chain_data = client.get_option_chain("SPY")
        if chain_data:
            print(f"✅ Got chain data!")
            print(f"   Spot price: ${chain_data.get('spot_price', 'N/A')}")
            print(f"   Expirations: {len(chain_data.get('chains', {}))}")
            exps = list(chain_data.get('chains', {}).keys())[:3]
            print(f"   First 3: {exps}")
        else:
            print("❌ Chain data is None")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ Client not available")
