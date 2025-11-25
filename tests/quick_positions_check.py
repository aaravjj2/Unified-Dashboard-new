#!/usr/bin/env python3
"""Quick validation of positions rendering with fresh Alpaca data."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from portfolio tracker module
from financial_dashboard.tabs.portfolio_tracker_refactored import get_alpaca_client

def main():
    print("=" * 80)
    print("QUICK POSITIONS CHECK")
    print("=" * 80)
    
    # Get fresh data from Alpaca
    client = get_alpaca_client()
    if not client:
        print("❌ Alpaca client not available")
        return
    
    positions = client.get_all_positions()
    print(f"\n📊 Alpaca API returned {len(positions)} positions:")
    
    for pos in positions:
        qty = float(pos.qty)
        symbol = pos.symbol
        print(f"  - {symbol}: qty={qty:.2f}, market_value=${float(pos.market_value):.2f}")
    
    # Filter for open positions (qty > 0)
    open_positions = [p for p in positions if float(p.qty) > 0]
    print(f"\n✅ After filtering qty > 0: {len(open_positions)} open positions")
    
    for pos in open_positions:
        print(f"  - {pos.symbol}: qty={float(pos.qty):.2f}")
    
    # Convert to dict format as used by portfolio_data_store
    positions_data = []
    for pos in open_positions:
        positions_data.append({
            'symbol': pos.symbol,
            'ticker': pos.symbol,
            'qty': float(pos.qty),
            'avg_entry_price': float(pos.avg_entry_price),
            'current_price': float(pos.current_price),
            'cost_basis': float(pos.cost_basis),
            'market_value': float(pos.market_value),
            'unrealized_pl': float(pos.unrealized_pl),
            'unrealized_plpc': float(pos.unrealized_plpc)
        })
    
    print(f"\n📋 Converted to {len(positions_data)} position dictionaries:")
    for p in positions_data:
        print(f"  - {p['symbol']}: qty={p['qty']:.2f}")
    
    # Save to cache
    cache_path = Path(__file__).parent.parent / 'financial_dashboard' / 'cache' / 'portfolio_data.json'
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    cache_data = {
        'positions': positions_data,
        'account': {
            'portfolio_value': float(client.get_account().portfolio_value),
            'buying_power': float(client.get_account().buying_power)
        },
        'timestamp': '2025-01-26T18:30:00'
    }
    
    with open(cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"\n💾 Saved {len(positions_data)} positions to cache: {cache_path}")
    print("\n✅ VALIDATION COMPLETE")

if __name__ == '__main__':
    main()
