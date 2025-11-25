#!/usr/bin/env python3
"""
Diagnostic test for IV Surface generation in Volatility Lab.
Tests the full data flow from options_connector → iv_surface → plotly Surface.
"""

import sys
sys.path.insert(0, '/app/financial_dashboard')

import logging
import pandas as pd
import yfinance as yf

# Configure logging to see all diagnostic messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("IV SURFACE DIAGNOSTIC TEST")
print("=" * 80)

# Import required modules
from services.options_connector import get_options_chain, OptionsConnector
from volatility.iv_surface import calculate_iv_surface, interpolate_iv_surface

# Test 1: Get available expirations
print("\n[TEST 1] Fetching available expirations for SPY...")
connector = OptionsConnector()
expirations = connector.get_available_expirations('SPY')
print(f"✅ Found {len(expirations)} expirations")
print(f"   First 5: {expirations[:5]}")

# Test 2: Fetch options chain
print("\n[TEST 2] Fetching options chain for first expiration...")
exp = expirations[0]
print(f"   Using expiration: {exp}")

calls, puts, source = get_options_chain('SPY', exp)
print(f"✅ Retrieved {len(calls)} calls, {len(puts)} puts from {source}")

# Inspect columns
print(f"\n[TEST 2a] Calls DataFrame columns:")
print(f"   {list(calls.columns)}")

print(f"\n[TEST 2b] Sample call contract:")
if not calls.empty:
    sample = calls.iloc[0]
    print(f"   Strike: {sample.get('strike', 'MISSING')}")
    print(f"   Bid: {sample.get('bid', 'MISSING')}")
    print(f"   Ask: {sample.get('ask', 'MISSING')}")
    print(f"   Expiration: {sample.get('expiration_date', 'MISSING')}")
    print(f"   Option Type: {sample.get('option_type', 'MISSING')}")

# Test 3: Get current stock price
print("\n[TEST 3] Fetching current SPY price...")
ticker = yf.Ticker('SPY')
price = ticker.history(period='1d')['Close'].iloc[-1]
print(f"✅ Current SPY price: ${price:.2f}")

# Test 4: Calculate IV surface
print("\n[TEST 4] Calculating IV surface...")
all_opts = pd.concat([calls, puts], ignore_index=True)
print(f"   Total contracts: {len(all_opts)}")

iv_df = calculate_iv_surface(all_opts, price)
print(f"✅ IV calculation complete")

# Check results
valid_iv = iv_df[iv_df['implied_vol'].notna()]
print(f"   Valid IV contracts: {len(valid_iv)}/{len(iv_df)}")

if len(valid_iv) > 0:
    print(f"   IV range: {valid_iv['implied_vol'].min():.2%} to {valid_iv['implied_vol'].max():.2%}")
    print(f"   Mean IV: {valid_iv['implied_vol'].mean():.2%}")
    
    # Check for time_to_expiry column
    if 'time_to_expiry' in valid_iv.columns:
        print(f"   Time to expiry range: {valid_iv['time_to_expiry'].min():.4f} to {valid_iv['time_to_expiry'].max():.4f} years")
    else:
        print(f"   ❌ MISSING 'time_to_expiry' column!")
        print(f"   Available columns: {list(valid_iv.columns)}")
else:
    print("   ❌ No valid IV values calculated!")

# Test 5: Interpolate surface
if len(valid_iv) >= 4:
    print("\n[TEST 5] Interpolating IV surface...")
    print(f"   Using {len(valid_iv)} valid points")
    
    strike_mesh, tte_mesh, iv_mesh = interpolate_iv_surface(valid_iv, grid_size=30)
    
    if strike_mesh is not None and tte_mesh is not None and iv_mesh is not None:
        print(f"✅ Interpolation successful!")
        print(f"   Strike mesh shape: {strike_mesh.shape}")
        print(f"   TTE mesh shape: {tte_mesh.shape}")
        print(f"   IV mesh shape: {iv_mesh.shape}")
        print(f"   IV mesh range: {iv_mesh.min()*100:.1f}% to {iv_mesh.max()*100:.1f}%")
        print(f"   IV mesh mean: {iv_mesh.mean()*100:.1f}%")
        
        # Check for NaN or invalid values
        nan_count = pd.isna(iv_mesh).sum()
        if nan_count > 0:
            print(f"   ⚠️ Warning: {nan_count} NaN values in mesh")
        
        # Check for reasonable values
        if iv_mesh.min() < 0 or iv_mesh.max() > 5:
            print(f"   ⚠️ Warning: IV values outside reasonable range (0-500%)")
    else:
        print(f"❌ Interpolation failed - returned None meshes")
        print(f"   strike_mesh: {strike_mesh}")
        print(f"   tte_mesh: {tte_mesh}")
        print(f"   iv_mesh: {iv_mesh}")
else:
    print(f"\n[TEST 5] ⏭️ Skipped - insufficient data ({len(valid_iv)} points, need >=4)")

print("\n" + "=" * 80)
print("DIAGNOSTIC TEST COMPLETE")
print("=" * 80)
