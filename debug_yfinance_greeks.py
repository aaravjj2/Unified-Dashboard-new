#!/usr/bin/env python
"""
Debug script: Check what columns yfinance returns for options data
"""
import yfinance as yf
import pandas as pd

def test_yfinance_options(ticker="AAPL"):
    """Test what columns yfinance returns for options data."""
    print(f"Testing yfinance options data for {ticker}")
    print("="*70)
    
    try:
        stock = yf.Ticker(ticker)
        
        # Get expiration dates
        expirations = stock.options
        if not expirations:
            print("❌ No expiration dates found")
            return
        
        # Get options chain for first expiration
        exp_date = expirations[0]
        print(f"📅 Using expiration: {exp_date}")
        
        chain = stock.option_chain(exp_date)
        calls = chain.calls
        puts = chain.puts
        
        print(f"\n📊 Calls DataFrame shape: {calls.shape}")
        print(f"📊 Puts DataFrame shape: {puts.shape}")
        
        print(f"\n📋 Calls columns ({len(calls.columns)}):")
        for col in calls.columns:
            print(f"  - {col}")
        
        print(f"\n📋 Puts columns ({len(puts.columns)}):")
        for col in puts.columns:
            print(f"  - {col}")
        
        # Check for Greeks
        greeks_cols = ['delta', 'gamma', 'vega', 'theta', 'rho']
        print(f"\n🔍 Greeks columns present:")
        for greek in greeks_cols:
            in_calls = greek in calls.columns
            in_puts = greek in puts.columns
            symbol = "✅" if (in_calls or in_puts) else "❌"
            print(f"  {symbol} {greek}: calls={in_calls}, puts={in_puts}")
        
        # Show first row of data
        print(f"\n📖 First call option:")
        print(calls.iloc[0])
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_yfinance_options()
