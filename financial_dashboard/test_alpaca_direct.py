#!/usr/bin/env python3
"""Direct test of Alpaca API for screening"""

import os
import sys
from datetime import datetime, timedelta
import numpy as np

# Set up path
sys.path.insert(0, '/home/aarav/Unified-Dashboard/financial_dashboard')

# Load API keys
from dotenv import load_dotenv
load_dotenv('keys.env')

# Try Alpaca import
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    print("✅ Alpaca imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Get API key
api_key = os.getenv('ALPACA_API_KEY') or os.getenv('ALPACA_KEY_ID')
api_secret = os.getenv('ALPACA_SECRET_KEY') or os.getenv('ALPACA_SECRET')

if not api_key or not api_secret:
    print("❌ No Alpaca keys found in keys.env")
    sys.exit(1)

print(f"✅ API Key found: {api_key[:10]}...")

# Create client
try:
    client = StockHistoricalDataClient(api_key, api_secret)
    print("✅ Client created")
except Exception as e:
    print(f"❌ Client creation failed: {e}")
    sys.exit(1)

# Test with a few stocks
test_tickers = ['AAPL', 'MSFT', 'GOOGL']
end_date = datetime.now()
start_date = end_date - timedelta(days=60)

print(f"\n🔍 Testing API calls for {test_tickers}...")
print(f"Date range: {start_date.date()} to {end_date.date()}")

for ticker in test_tickers:
    try:
        request = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        if ticker in bars:
            df = bars[ticker].df
            if not df.empty:
                price = float(df['close'].iloc[-1])
                volume = int(df['volume'].iloc[-1])
                
                # Calculate RSI
                closes = df['close'].values
                if len(closes) >= 14:
                    deltas = np.diff(closes)
                    gains = np.where(deltas > 0, deltas, 0)
                    losses = np.where(deltas < 0, -deltas, 0)
                    avg_gain = np.mean(gains[-14:])
                    avg_loss = np.mean(losses[-14:])
                    if avg_loss > 0:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                    else:
                        rsi = 100
                else:
                    rsi = 50
                
                print(f"✅ {ticker}: Price=${price:.2f}, Vol={volume:,}, RSI={rsi:.1f}, Bars={len(df)}")
            else:
                print(f"❌ {ticker}: Empty dataframe")
        else:
            print(f"❌ {ticker}: Not in response")
            
    except Exception as e:
        print(f"❌ {ticker}: Error - {str(e)[:100]}")

print("\n✅ API test complete!")
