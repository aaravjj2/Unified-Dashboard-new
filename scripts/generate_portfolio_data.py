#!/usr/bin/env python3
"""
Generate portfolio_data.json from Alpaca API
"""

import json
import os
from pathlib import Path
from datetime import datetime

try:
    from alpaca.trading.client import TradingClient
    
    # Initialize Alpaca client
    api_key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")
    
    if not api_key or not api_secret:
        print("❌ ERROR: APCA_API_KEY_ID and APCA_API_SECRET_KEY must be set")
        exit(1)
    
    client = TradingClient(api_key, api_secret, paper=True)
    
    print("="*80)
    print("PORTFOLIO DATA GENERATOR")
    print("="*80)
    print(f"Fetching from Alpaca...")
    
    # Get positions
    positions = client.get_all_positions()
    
    if not positions:
        print("⚠️  No positions found in Alpaca account")
        exit(1)
    
    # Get account info
    account = client.get_account()
    
    # Format positions data
    positions_data = []
    total_value = 0.0
    
    for pos in positions:
        market_value = float(pos.market_value)
        total_value += market_value
        
        positions_data.append({
            "ticker": pos.symbol,
            "qty": float(pos.qty),
            "avg_entry_price": float(pos.avg_entry_price),
            "current_price": float(pos.current_price),
            "market_value": market_value,
            "unrealized_pl": float(pos.unrealized_pl),
            "unrealized_plpc": float(pos.unrealized_plpc) * 100,  # Convert to percentage
            "cost_basis": float(pos.cost_basis)
        })
    
    # Create output structure
    output = {
        "generated_at": datetime.now().isoformat(),
        "account": {
            "equity": float(account.equity),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power)
        },
        "positions": positions_data,
        "summary": {
            "num_positions": len(positions_data),
            "total_market_value": total_value
        }
    }
    
    # Save to cache directory
    cache_dir = Path("/app/cache")
    cache_dir.mkdir(exist_ok=True)
    output_path = cache_dir / "portfolio_data.json"
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ GENERATION COMPLETE")
    print("="*80)
    print(f"File: {output_path}")
    print(f"Size: {output_path.stat().st_size:,} bytes")
    print(f"\nSummary:")
    print(f"  Positions: {len(positions_data)}")
    print(f"  Total Value: ${total_value:,.2f}")
    print(f"  Account Equity: ${float(account.equity):,.2f}")
    print(f"\nSample tickers: {', '.join([p['ticker'] for p in positions_data[:5]])}")
    print("="*80)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
