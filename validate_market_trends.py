#!/usr/bin/env python3
"""
Quick validation script for SUPER-AGENT deployment.
Run this to verify Market Trends data is complete.
"""

import sys
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard')

print("="*80)
print("SUPER-AGENT QUICK VALIDATION")
print("="*80)

try:
    import financial_dashboard._shared as SH
    from financial_dashboard.utils.keys_manager import (
        get_market_trends_tickers,
        validate_cache,
        REQUIRED_PRICE_FIELDS
    )
    
    cache_prices = SH.RESULTS_CACHE.get('results', {}).get('prices', {})
    market_trends_tickers = get_market_trends_tickers()
    
    print(f"\n📊 Cache Status:")
    print(f"   Total tickers in cache: {len(cache_prices)}")
    
    print(f"\n🎯 Market Trends Validation:")
    all_complete = True
    
    for ticker in market_trends_tickers:
        if ticker not in cache_prices:
            print(f"   ❌ {ticker}: MISSING from cache")
            all_complete = False
        else:
            data = cache_prices[ticker]
            missing_fields = []
            for field in REQUIRED_PRICE_FIELDS:
                if field not in data or data[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ⚠️  {ticker}: Missing {', '.join(missing_fields)}")
                all_complete = False
            else:
                price = data.get('current_price', 'N/A')
                pl = data.get('profit_loss', 0)
                print(f"   ✅ {ticker}: ${price} (P/L: {pl:+.2f})")
    
    if all_complete:
        print(f"\n🎉 SUCCESS: All Market Trends tickers have complete data!")
        print(f"   No 'Data Unavailable' values expected in UI")
        sys.exit(0)
    else:
        print(f"\n⚠️  WARNING: Some tickers incomplete")
        print(f"   'Data Unavailable' may appear in UI")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(2)
