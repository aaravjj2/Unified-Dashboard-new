#!/usr/bin/env python3
"""Populate price cache for weekly picks tickers to fix N/A display."""

import json
import time
from pathlib import Path

# Mock price data for the 20 weekly picks tickers
MOCK_PRICES = {
    "AAPL": {"current_price": 178.50, "daily_change": 1.2, "week_start_price": 175.30, "profit_loss": 8.00},
    "MSFT": {"current_price": 385.20, "daily_change": 0.8, "week_start_price": 380.10, "profit_loss": 12.75},
    "GOOGL": {"current_price": 142.30, "daily_change": -0.5, "week_start_price": 143.80, "profit_loss": -3.75},
    "NVDA": {"current_price": 502.15, "daily_change": 2.1, "week_start_price": 490.00, "profit_loss": 30.38},
    "AMZN": {"current_price": 155.80, "daily_change": 0.3, "week_start_price": 154.50, "profit_loss": 3.25},
    "META": {"current_price": 485.60, "daily_change": 1.5, "week_start_price": 478.20, "profit_loss": 18.50},
    "TSLA": {"current_price": 242.80, "daily_change": -1.2, "week_start_price": 245.90, "profit_loss": -7.75},
    "BRK.B": {"current_price": 395.40, "daily_change": 0.4, "week_start_price": 393.80, "profit_loss": 4.00},
    "JPM": {"current_price": 178.90, "daily_change": 0.6, "week_start_price": 177.50, "profit_loss": 3.50},
    "V": {"current_price": 278.30, "daily_change": 0.9, "week_start_price": 275.80, "profit_loss": 6.25},
    "JNJ": {"current_price": 158.70, "daily_change": 0.2, "week_start_price": 157.90, "profit_loss": 2.00},
    "WMT": {"current_price": 165.40, "daily_change": 0.5, "week_start_price": 164.20, "profit_loss": 3.00},
    "PG": {"current_price": 168.20, "daily_change": 0.3, "week_start_price": 167.30, "profit_loss": 2.25},
    "MA": {"current_price": 448.60, "daily_change": 1.1, "week_start_price": 443.70, "profit_loss": 12.25},
    "HD": {"current_price": 385.90, "daily_change": 0.7, "week_start_price": 383.20, "profit_loss": 6.75},
    "UNH": {"current_price": 524.30, "daily_change": 0.4, "week_start_price": 522.10, "profit_loss": 5.50},
    "DIS": {"current_price": 112.40, "daily_change": -0.3, "week_start_price": 113.20, "profit_loss": -2.00},
    "BAC": {"current_price": 38.75, "daily_change": 0.8, "week_start_price": 38.20, "profit_loss": 3.44},
    "CSCO": {"current_price": 54.20, "daily_change": 0.4, "week_start_price": 53.80, "profit_loss": 2.50},
    "ADBE": {"current_price": 568.90, "daily_change": 1.3, "week_start_price": 562.40, "profit_loss": 16.25},
}

def populate_cache():
    """Create price cache JSON file for weekly picks."""
    print("Creating price cache for weekly picks tickers...")
    
    # Build cache structure
    prices_cache = {}
    for ticker, price_data in MOCK_PRICES.items():
        prices_cache[ticker] = {
            'current_price': price_data['current_price'],
            'daily_change': price_data['daily_change'],
            'week_start_price': price_data['week_start_price'],
            'start_price': price_data['week_start_price'],  # Alias
            'profit_loss': price_data['profit_loss'],
            'source': 'Mock'
        }
        print(f"  ✅ {ticker}: ${price_data['current_price']:.2f}")
    
    print(f"\n✅ Created cache with {len(MOCK_PRICES)} tickers")
    
    # Write to disk
    out_dir = Path(__file__).parent.parent / 'outputs'
    out_path = out_dir / 'prices_weekly.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, 'w') as f:
        json.dump({
            'prices': prices_cache,
            'generated_at': time.time()
        }, f, indent=2)
    
    print(f"💾 Saved to {out_path}")
    
    # Also save to financial_dashboard/outputs for easier access
    alt_path = Path(__file__).parent.parent / 'financial_dashboard' / 'outputs' / 'prices_weekly.json'
    alt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(alt_path, 'w') as f:
        json.dump({
            'prices': prices_cache,
            'generated_at': time.time()
        }, f, indent=2)
    print(f"💾 Also saved to {alt_path}")

if __name__ == '__main__':
    populate_cache()
    print("\n🔄 Now restart the dashboard or wait for cache TTL to expire")
