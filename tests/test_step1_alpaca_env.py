#!/usr/bin/env python3
"""
Step 1: Alpaca Credentials & Environment Validation
Verifies keys.env loading and Alpaca API connectivity.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, '.')

def test_environment_setup():
    """Test environment variable loading and credential availability."""
    print("=" * 70)
    print("STEP 1: ALPACA CREDENTIALS & ENVIRONMENT VALIDATION")
    print("=" * 70)
    
    results = {
        'env_file_exists': False,
        'apca_key_id_loaded': False,
        'apca_secret_loaded': False,
        'credentials_valid': False,
        'alpaca_sdk_available': False,
    }
    
    # Check 1: keys.env file exists
    print("\n1️⃣ Checking keys.env file...")
    keys_env_path = Path('keys.env')
    results['env_file_exists'] = keys_env_path.exists()
    
    if results['env_file_exists']:
        print(f"   ✅ keys.env found at {keys_env_path.absolute()}")
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv('keys.env')
        print(f"   ✅ Loaded environment from keys.env")
    else:
        print(f"   ⚠️  keys.env not found")
    
    # Check 2: Alpaca credentials in environment
    print("\n2️⃣ Checking Alpaca credentials...")
    apca_key_id = os.getenv('APCA_API_KEY_ID')
    apca_secret = os.getenv('APCA_API_SECRET_KEY')
    
    results['apca_key_id_loaded'] = apca_key_id is not None
    results['apca_secret_loaded'] = apca_secret is not None
    
    if results['apca_key_id_loaded']:
        print(f"   ✅ APCA_API_KEY_ID loaded (length: {len(apca_key_id)})")
    else:
        print(f"   ❌ APCA_API_KEY_ID not found in environment")
    
    if results['apca_secret_loaded']:
        print(f"   ✅ APCA_API_SECRET_KEY loaded (length: {len(apca_secret)})")
    else:
        print(f"   ❌ APCA_API_SECRET_KEY not found in environment")
    
    results['credentials_valid'] = results['apca_key_id_loaded'] and results['apca_secret_loaded']
    
    # Check 3: Alpaca SDK availability
    print("\n3️⃣ Checking Alpaca SDK...")
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import OptionChainRequest
        print(f"   ✅ Alpaca SDK imported successfully")
        print(f"   ✅ StockHistoricalDataClient available")
        print(f"   ✅ OptionChainRequest available")
        results['alpaca_sdk_available'] = True
    except ImportError as e:
        print(f"   ❌ Alpaca SDK not available: {e}")
        results['alpaca_sdk_available'] = False
    
    # Check 4: Test Alpaca connection (if credentials available)
    print("\n4️⃣ Testing Alpaca API connection...")
    if results['credentials_valid'] and results['alpaca_sdk_available']:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            
            client = StockHistoricalDataClient(
                api_key=apca_key_id,
                secret_key=apca_secret
            )
            
            # Try to fetch a simple quote to test connectivity
            from alpaca.data.requests import StockLatestQuoteRequest
            request = StockLatestQuoteRequest(symbol_or_symbols=['SPY'])
            
            quote = client.get_stock_latest_quote(request)
            
            if quote and 'SPY' in quote:
                spy_quote = quote['SPY']
                print(f"   ✅ Successfully connected to Alpaca API")
                print(f"   ✅ Test quote for SPY:")
                print(f"      Bid: ${spy_quote.bid_price:.2f}")
                print(f"      Ask: ${spy_quote.ask_price:.2f}")
                results['alpaca_connection_test'] = True
            else:
                print(f"   ⚠️  Unexpected response from Alpaca API")
                results['alpaca_connection_test'] = False
                
        except Exception as e:
            print(f"   ❌ Alpaca API connection failed: {e}")
            print(f"   💡 Tip: Verify credentials are correct and account has API access")
            results['alpaca_connection_test'] = False
    else:
        print(f"   ⏭️  Skipping (credentials or SDK not available)")
        results['alpaca_connection_test'] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    for key, value in results.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {value}")
    
    all_passed = all([
        results['env_file_exists'],
        results['apca_key_id_loaded'],
        results['apca_secret_loaded'],
        results['alpaca_sdk_available'],
    ])
    
    print("\n" + "=" * 70)
    if all_passed:
        if results.get('alpaca_connection_test'):
            print("✅ ALPACA ENVIRONMENT: FULLY OPERATIONAL (Live API)")
        else:
            print("🟡 ALPACA ENVIRONMENT: CONFIGURED (Credentials present, API test failed)")
    else:
        print("⚠️  ALPACA ENVIRONMENT: INCOMPLETE (Will use fallback)")
    print("=" * 70)
    
    return results

if __name__ == '__main__':
    results = test_environment_setup()
    
    # Exit code for CI/CD
    if results.get('credentials_valid') and results.get('alpaca_sdk_available'):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Fallback mode
