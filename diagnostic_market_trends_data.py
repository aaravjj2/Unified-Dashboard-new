#!/usr/bin/env python3
"""
Quick diagnostic: Check if Market Trends rendering logic works correctly
"""
import sys
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard')

import _shared as SH
import pandas as pd

print("="*80)
print("MARKET TRENDS DATA FLOW DIAGNOSTIC")
print("="*80)

# Step 1: Check if prices are preloaded
prices = SH.RESULTS_CACHE.get('results', {}).get('prices', {})
print(f"\n✅ Step 1: Price Cache Status")
print(f"   - Loaded prices: {len(prices)} tickers")
print(f"   - Sample tickers: {list(prices.keys())[:5]}")

if len(prices) > 0:
    # Show sample price structure
    sample_ticker = list(prices.keys())[0]
    sample_data = prices[sample_ticker]
    print(f"\n   Sample price data for {sample_ticker}:")
    for key, value in sample_data.items():
        print(f"     - {key}: {value}")

# Step 2: Load cached results (CSV data)
last = SH.load_last_cached_results()
print(f"\n✅ Step 2: Cached Results Status")
if last:
    detailed = last.get('detailed', [])
    print(f"   - Detailed records: {len(detailed)}")
    if len(detailed) > 0:
        print(f"   - Sample record keys: {list(detailed[0].keys())}")
        print(f"   - First ticker: {detailed[0].get('ticker')}")
else:
    print(f"   ❌ No cached results found")

# Step 3: Simulate rendering logic
if last and prices:
    detailed = last.get('detailed', [])
    df = pd.DataFrame(detailed)
    
    if 'ticker' in df.columns:
        ticker_list = df['ticker'].unique().tolist()
        print(f"\n✅ Step 3: Rendering Simulation")
        print(f"   - Tickers to render: {len(ticker_list)}")
        
        # Check how many tickers have price data
        tickers_with_prices = 0
        tickers_without_prices = []
        
        for ticker in ticker_list:
            entry = prices.get(ticker, {})
            if entry.get('current_price') is not None:
                tickers_with_prices += 1
            else:
                tickers_without_prices.append(ticker)
        
        print(f"   - Tickers WITH price data: {tickers_with_prices}")
        print(f"   - Tickers WITHOUT price data: {len(tickers_without_prices)}")
        
        if tickers_without_prices:
            print(f"   - Missing: {tickers_without_prices}")
        
        # Estimate "Data Unavailable" occurrences
        # Each ticker without prices has 5 price columns: current_price, week_start_price, month_start_price, daily_change, profit_loss
        missing_cells = len(tickers_without_prices) * 5
        
        print(f"\n📊 Estimated 'Data Unavailable' count: {missing_cells}")
        
        if missing_cells == 0:
            print("✅ SUCCESS: All tickers have complete price data!")
        else:
            print(f"⚠️  WARNING: {missing_cells} cells will show 'Data Unavailable'")
    else:
        print("\n❌ Step 3: FAILED - No 'ticker' column in detailed records")

print("\n" + "="*80)
print("RECOMMENDATION:")
print("="*80)

if len(prices) == 0:
    print("❌ Price cache is EMPTY - prices need to be fetched")
    print("   Action: Run weekly/monthly picks to populate price cache")
elif last is None:
    print("❌ No cached results - Market Trends analysis needs to be run")
    print("   Action: Click 'Run Full Analysis' button in Market Trends tab")
else:
    detailed = last.get('detailed', [])
    if not detailed:
        print("❌ Cached results exist but no detailed records")
        print("   Action: Re-run Market Trends analysis")
    else:
        df = pd.DataFrame(detailed)
        if 'ticker' not in df.columns:
            print("❌ Detailed records missing 'ticker' column")
            print("   Action: Check data pipeline - column name might be different")
        else:
            ticker_list = df['ticker'].unique().tolist()
            tickers_with_prices = sum(1 for t in ticker_list if prices.get(t, {}).get('current_price') is not None)
            
            if tickers_with_prices == len(ticker_list):
                print("✅ ALL SYSTEMS GO - Restart Dash server to pick up cache")
                print("   Action: Ctrl+C and restart: python index.py")
            else:
                print(f"⚠️  PARTIAL - Only {tickers_with_prices}/{len(ticker_list)} tickers have prices")
                print("   Action: Run price refresh job or restart server")
