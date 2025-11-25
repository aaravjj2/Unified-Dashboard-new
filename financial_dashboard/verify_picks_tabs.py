"""Quick verification that monthly and weekly picks tabs load with price data"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from tabs import monthly_picks, weekly_picks

print("="*70)
print("TESTING MONTHLY PICKS TAB")
print("="*70)

try:
    # Test monthly picks
    csv_path = monthly_picks._find_latest_picks()
    print(f"✓ Found latest monthly CSV: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} rows from CSV")
    
    # Test price fetching
    display_df = monthly_picks._prepare_display_df(df.head(5))
    print(f"✓ Prepared display DataFrame with {len(display_df)} rows")
    
    # Check for required columns
    required_cols = ['price_live', 'profit_loss', 'month_start']
    for col in required_cols:
        if col in display_df.columns:
            non_null = display_df[col].notna().sum()
            print(f"✓ Column '{col}': {non_null}/{len(display_df)} non-null values")
        else:
            print(f"✗ Missing column: {col}")
    
    print("\nSample data:")
    print(display_df[['ticker', 'price_live', 'month_start', 'profit_loss']].head(3))
    
except Exception as e:
    print(f"✗ Error testing monthly picks: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TESTING WEEKLY PICKS TAB")
print("="*70)

try:
    # Test weekly picks
    csv_path = weekly_picks._find_latest_weekly_picks()
    print(f"✓ Found latest weekly CSV: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} rows from CSV")
    
    # Test price fetching
    display_df = weekly_picks._prepare_weekly_display_df(df.head(5))
    print(f"✓ Prepared display DataFrame with {len(display_df)} rows")
    
    # Check for required columns
    required_cols = ['price_live', 'profit_loss', 'week_start']
    for col in required_cols:
        if col in display_df.columns:
            non_null = display_df[col].notna().sum()
            print(f"✓ Column '{col}': {non_null}/{len(display_df)} non-null values")
        else:
            print(f"✗ Missing column: {col}")
    
    print("\nSample data:")
    print(display_df[['ticker', 'price_live', 'week_start', 'profit_loss']].head(3))
    
except Exception as e:
    print(f"✗ Error testing weekly picks: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("✓ ALL TESTS COMPLETE")
print("="*70)
