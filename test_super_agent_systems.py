#!/usr/bin/env python3
"""
SUPER-AGENT Test Script

Tests the centralized key management, cache persistence, and price fetching systems.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard')

print("="*80)
print("SUPER-AGENT SYSTEMS TEST")
print("="*80)

# Test 1: Keys Manager
print("\n[TEST 1] Keys Manager")
print("-"*80)
try:
    from financial_dashboard.utils.keys_manager import (
        get_market_trends_tickers,
        validate_cache,
        log_cache_status,
        MARKET_TRENDS_TICKERS
    )
    
    tickers = get_market_trends_tickers()
    print(f"✅ Keys Manager loaded successfully")
    print(f"   Market Trends tickers: {tickers}")
    print(f"   Constant MARKET_TRENDS_TICKERS: {MARKET_TRENDS_TICKERS}")
    
except Exception as e:
    print(f"❌ Keys Manager failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Cache Persistence
print("\n[TEST 2] Cache Persistence")
print("-"*80)
try:
    from financial_dashboard.utils.cache_persistence import (
        get_cache_persistence,
        read_cache
    )
    
    persistence = get_cache_persistence()
    print(f"✅ Cache Persistence loaded successfully")
    print(f"   Base dir: {persistence.base_dir}")
    
    # Try to read existing cache
    weekly_cache = read_cache('prices_weekly.json')
    if weekly_cache:
        price_count = len(weekly_cache.get('prices', {}))
        print(f"   Read prices_weekly.json: {price_count} tickers")
    else:
        print(f"   prices_weekly.json not found or empty")
    
except Exception as e:
    print(f"❌ Cache Persistence failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Price Fetcher
print("\n[TEST 3] Price Fetcher")
print("-"*80)
try:
    from financial_dashboard.utils.price_fetcher import (
        get_price_fetcher,
        fetch_ticker_prices
    )
    
    fetcher = get_price_fetcher()
    print(f"✅ Price Fetcher loaded successfully")
    
    # Test fetching a single ticker
    print(f"   Testing fetch for AAPL...")
    aapl_data = fetch_ticker_prices('AAPL')
    if aapl_data:
        print(f"   ✅ AAPL: ${aapl_data['current_price']:.2f} (P/L: {aapl_data['profit_loss']:+.2f})")
    else:
        print(f"   ❌ Failed to fetch AAPL")
    
except Exception as e:
    print(f"❌ Price Fetcher failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Integrated Test - Check Current Cache Status
print("\n[TEST 4] Current Cache Status")
print("-"*80)
try:
    import financial_dashboard._shared as SH
    
    cache_prices = SH.RESULTS_CACHE.get('results', {}).get('prices', {})
    print(f"Current cache has {len(cache_prices)} tickers")
    
    # Check Market Trends tickers specifically
    from financial_dashboard.utils.keys_manager import validate_cache, log_cache_status
    
    validation = validate_cache(SH.RESULTS_CACHE.get('results', {}))
    
    print(f"\nValidation Results:")
    print(f"  Complete: {validation['complete']}")
    print(f"  Total tickers: {validation['total_tickers']}")
    print(f"  Valid Market Trends: {len(validation['valid_tickers'])}/{len(MARKET_TRENDS_TICKERS)}")
    print(f"  ✅ Complete: {', '.join(validation['valid_tickers'])}")
    
    if validation['invalid_tickers']:
        print(f"  ⚠️  Incomplete: {', '.join(validation['invalid_tickers'])}")
        for ticker in validation['invalid_tickers']:
            missing = validation['validation_details'].get(ticker, [])
            print(f"     {ticker}: missing {', '.join(missing)}")
    
    if validation['missing_tickers']:
        print(f"  ❌ Missing: {', '.join(validation['missing_tickers'])}")
    
except Exception as e:
    print(f"❌ Cache status check failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test Manual Cache Refresh
print("\n[TEST 5] Manual Cache Refresh")
print("-"*80)
try:
    import financial_dashboard._shared as SH
    
    print("Calling refresh_prices_cache()...")
    result = SH.refresh_prices_cache(force_fetch_missing=True)
    
    print(f"Refresh result:")
    print(f"  Success: {result['success']}")
    print(f"  Tickers before: {result['tickers_before']}")
    print(f"  Tickers after: {result['tickers_after']}")
    print(f"  Fetched: {', '.join(result['fetched']) if result['fetched'] else 'none'}")
    
    if result.get('validation'):
        val = result['validation']
        print(f"  Final validation: {val['complete']}")
        if not val['complete']:
            print(f"    Still missing: {', '.join(val['missing_tickers'])}")
            print(f"    Still incomplete: {', '.join(val['invalid_tickers'])}")
    
except Exception as e:
    print(f"❌ Manual refresh failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
