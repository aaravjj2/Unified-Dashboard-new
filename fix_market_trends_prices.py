#!/usr/bin/env python3
"""
Quick Fix: Fetch prices for Market Trends cached tickers
This ensures price cache matches the tickers in tech_report_detailed.csv
"""
import sys
import os
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard')

import pandas as pd
import json
from datetime import datetime, timedelta

# Read cached Market Trends tickers
csv_path = '/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/outputs/tech_report_detailed.csv'
df = pd.read_csv(csv_path)
tickers = df['ticker'].tolist()

print(f"📋 Found {len(tickers)} tickers in Market Trends cache: {tickers}")

# Fetch prices using yfinance
try:
    import yfinance as yf
    
    prices = {}
    for ticker in tickers:
        print(f"📊 Fetching {ticker}...", end=' ')
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1mo')
            
            if hist.empty or len(hist) < 2:
                print("❌ No data")
                continue
            
            current_price = hist['Close'].iloc[-1]
            start_price = hist['Close'].iloc[0]
            daily_change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2] if len(hist) >= 2 else 0
            profit_loss = current_price - start_price
            
            # Week start (7 days ago if available)
            week_start_price = hist['Close'].iloc[-7] if len(hist) >= 7 else start_price
            month_start_price = start_price
            
            prices[ticker] = {
                'current_price': float(current_price),
                'daily_change': float(daily_change),
                'start_price': float(start_price),
                'week_start_price': float(week_start_price),
                'month_start_price': float(month_start_price),
                'profit_loss': float(profit_loss),
                'source': 'yfinance'
            }
            
            print(f"✅ ${current_price:.2f}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Save to prices_weekly.json
    output_path = '/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/outputs/prices_weekly.json'
    output_data = {
        'prices': prices,
        'generated_at': datetime.now().timestamp()
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Saved {len(prices)} prices to {output_path}")
    
    # Verify
    print("\n📊 Price Summary:")
    for ticker, data in prices.items():
        print(f"   {ticker}: ${data['current_price']:.2f} (change: ${data['daily_change']:+.2f})")
    
    print("\n✅ SUCCESS: Price cache updated with matching tickers!")
    print("   Now restart the Dash server to reload the cache")

except ImportError:
    print("❌ yfinance not installed")
    print("   Install with: pip install yfinance")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
