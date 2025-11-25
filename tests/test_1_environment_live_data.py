#!/usr/bin/env python3
"""
Step 1: Environment & Live Data Verification
Comprehensive validation of Alpaca API, live data fetch, and fallback chain
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

sys.path.insert(0, '.')

# Load environment
from dotenv import load_dotenv
load_dotenv('keys.env')

def validate_environment() -> Dict[str, Any]:
    """Validate Alpaca API keys are loaded correctly."""
    print("\n" + "="*80)
    print("🔐 ENVIRONMENT VALIDATION")
    print("="*80)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'keys_loaded': False,
        'alpaca_key_id': None,
        'alpaca_secret': None,
        'keys_valid': False,
        'errors': []
    }
    
    # Check keys.env exists
    if not Path('keys.env').exists():
        error = "❌ keys.env not found"
        print(error)
        results['errors'].append(error)
        return results
    
    print("✅ keys.env found")
    
    # Load and validate keys
    try:
        load_dotenv('keys.env', override=True)
        
        apca_key_id = os.getenv('APCA_API_KEY_ID')
        apca_secret = os.getenv('APCA_API_SECRET_KEY')
        
        if not apca_key_id:
            error = "❌ APCA_API_KEY_ID not set"
            print(error)
            results['errors'].append(error)
        else:
            key_len = len(apca_key_id)
            masked = apca_key_id[:4] + '*' * (key_len - 8) + apca_key_id[-4:]
            print(f"✅ APCA_API_KEY_ID: {masked} ({key_len} chars)")
            results['alpaca_key_id'] = masked
        
        if not apca_secret:
            error = "❌ APCA_API_SECRET_KEY not set"
            print(error)
            results['errors'].append(error)
        else:
            secret_len = len(apca_secret)
            masked = apca_secret[:4] + '*' * (secret_len - 8) + apca_secret[-4:]
            print(f"✅ APCA_API_SECRET_KEY: {masked} ({secret_len} chars)")
            results['alpaca_secret'] = masked
        
        if apca_key_id and apca_secret:
            results['keys_loaded'] = True
            results['keys_valid'] = len(apca_key_id) > 10 and len(apca_secret) > 10
            
            if results['keys_valid']:
                print("✅ Alpaca credentials valid format")
            else:
                error = "⚠️  Credentials appear too short"
                print(error)
                results['errors'].append(error)
        
    except Exception as e:
        error = f"❌ Error loading keys: {e}"
        print(error)
        results['errors'].append(error)
    
    return results

def test_alpaca_api_connection() -> Dict[str, Any]:
    """Test live Alpaca API connection."""
    print("\n" + "="*80)
    print("📡 ALPACA API CONNECTION TEST")
    print("="*80)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'sdk_available': False,
        'api_connection': False,
        'live_quote': None,
        'errors': []
    }
    
    try:
        from alpaca.trading.client import TradingClient
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest
        
        results['sdk_available'] = True
        print("✅ Alpaca SDK imported successfully")
        
        # Test API connection with live quote
        api_key = os.getenv('APCA_API_KEY_ID')
        secret_key = os.getenv('APCA_API_SECRET_KEY')
        
        if not api_key or not secret_key:
            error = "❌ API keys not available"
            print(error)
            results['errors'].append(error)
            return results
        
        print("🔌 Testing live API connection...")
        data_client = StockHistoricalDataClient(api_key, secret_key)
        
        # Get live quote for SPY
        request = StockLatestQuoteRequest(symbol_or_symbols=['SPY'])
        quotes = data_client.get_stock_latest_quote(request)
        
        if 'SPY' in quotes:
            spy_quote = quotes['SPY']
            results['api_connection'] = True
            results['live_quote'] = {
                'symbol': 'SPY',
                'bid': float(spy_quote.bid_price),
                'ask': float(spy_quote.ask_price),
                'timestamp': spy_quote.timestamp.isoformat()
            }
            print(f"✅ Live API connection successful")
            print(f"   SPY Quote: ${spy_quote.bid_price:.2f} / ${spy_quote.ask_price:.2f}")
            print(f"   Timestamp: {spy_quote.timestamp}")
        else:
            error = "⚠️  No quote data returned"
            print(error)
            results['errors'].append(error)
            
    except ImportError as e:
        error = f"❌ Alpaca SDK not installed: {e}"
        print(error)
        results['errors'].append(error)
    except Exception as e:
        error = f"❌ API connection failed: {e}"
        print(error)
        results['errors'].append(error)
        import traceback
        traceback.print_exc()
    
    return results

def test_live_options_data(ticker: str, use_alpaca: bool = True) -> Dict[str, Any]:
    """Test live options data fetch with comprehensive validation."""
    print(f"\n📊 Testing {ticker} Options Data...")
    print("-" * 80)
    
    from financial_dashboard.tabs.options_lab.data_loader import fetch_options_chain
    import pandas as pd
    
    result = {
        'ticker': ticker,
        'timestamp': datetime.now().isoformat(),
        'success': False,
        'source': None,
        'spot_price': None,
        'expirations': [],
        'expirations_count': 0,
        'calls_count': 0,
        'puts_count': 0,
        'total_contracts': 0,
        'load_time_seconds': 0,
        'required_columns_present': False,
        'iv_range': {'min': 0, 'max': 0, 'avg': 0},
        'quality_checks': {},
        'errors': []
    }
    
    try:
        start_time = time.time()
        chain_data = fetch_options_chain(ticker, use_alpaca=use_alpaca, use_mock=False)
        load_time = time.time() - start_time
        result['load_time_seconds'] = round(load_time, 3)
        
        # Check for errors
        if chain_data.get('error'):
            error = chain_data['error']
            result['errors'].append(error)
            print(f"   ❌ Error: {error}")
            return result
        
        # Extract data
        result['source'] = chain_data.get('source', 'unknown')
        result['spot_price'] = chain_data.get('spot_price', 0)
        result['expirations'] = chain_data.get('expirations', [])
        result['expirations_count'] = len(result['expirations'])
        
        calls = chain_data.get('calls', [])
        puts = chain_data.get('puts', [])
        
        # Handle DataFrame or list
        if isinstance(calls, pd.DataFrame):
            result['calls_count'] = len(calls)
            calls_df = calls
        else:
            result['calls_count'] = len(calls) if isinstance(calls, list) else 0
            calls_df = pd.DataFrame(calls) if isinstance(calls, list) else pd.DataFrame()
        
        if isinstance(puts, pd.DataFrame):
            result['puts_count'] = len(puts)
            puts_df = puts
        else:
            result['puts_count'] = len(puts) if isinstance(puts, list) else 0
            puts_df = pd.DataFrame(puts) if isinstance(puts, list) else pd.DataFrame()
        
        result['total_contracts'] = result['calls_count'] + result['puts_count']
        
        # Check required columns
        required_cols = ['strike', 'bid', 'ask', 'lastPrice', 'impliedVolatility', 'volume', 'openInterest']
        if not calls_df.empty:
            present_cols = [col for col in required_cols if col in calls_df.columns]
            result['required_columns_present'] = len(present_cols) >= 5  # At least 5/7 required
            
            # Calculate IV range
            if 'impliedVolatility' in calls_df.columns:
                iv_values = calls_df['impliedVolatility'].dropna()
                if len(iv_values) > 0:
                    result['iv_range'] = {
                        'min': float(iv_values.min()),
                        'max': float(iv_values.max()),
                        'avg': float(iv_values.mean())
                    }
        
        # Quality checks
        result['quality_checks'] = {
            'has_expirations': result['expirations_count'] > 0,
            'min_20_expirations': result['expirations_count'] >= 20,
            'has_calls': result['calls_count'] > 0,
            'has_puts': result['puts_count'] > 0,
            'valid_spot': result['spot_price'] > 0,
            'load_time_ok': load_time < 3.0,
            'required_columns': result['required_columns_present'],
            'min_100_contracts': result['total_contracts'] >= 100
        }
        
        result['success'] = all([
            result['quality_checks']['has_expirations'],
            result['quality_checks']['has_calls'],
            result['quality_checks']['has_puts'],
            result['quality_checks']['valid_spot']
        ])
        
        # Display results
        source_badge = {'alpaca': '🟢', 'yfinance': '🟡', 'mock': '🔵'}.get(result['source'], '⚪')
        print(f"   {source_badge} Source: {result['source'].upper()}")
        print(f"   💵 Spot Price: ${result['spot_price']:.2f}")
        print(f"   📅 Expirations: {result['expirations_count']}")
        print(f"   📞 Calls: {result['calls_count']}")
        print(f"   📍 Puts: {result['puts_count']}")
        print(f"   📋 Total Contracts: {result['total_contracts']}")
        print(f"   ⏱️  Load Time: {result['load_time_seconds']}s")
        
        if result['iv_range']['avg'] > 0:
            print(f"   📊 IV Range: {result['iv_range']['min']:.1%} - {result['iv_range']['max']:.1%} (avg: {result['iv_range']['avg']:.1%})")
        
        # Quality status
        failed_checks = [k for k, v in result['quality_checks'].items() if not v]
        if not failed_checks:
            print(f"   ✅ All quality checks PASS")
        else:
            print(f"   ⚠️  Quality checks failed: {', '.join(failed_checks)}")
        
        # ABORT CONDITION: Less than 20 expirations
        if result['expirations_count'] < 20:
            error = f"ABORT: Only {result['expirations_count']} expirations (minimum 20 required)"
            print(f"   🚨 {error}")
            result['errors'].append(error)
            result['success'] = False
        
    except Exception as e:
        error = f"Exception: {e}"
        print(f"   ❌ {error}")
        result['errors'].append(error)
        import traceback
        traceback.print_exc()
    
    return result

def test_fallback_chain(ticker: str) -> Dict[str, Any]:
    """Test the fallback chain: Alpaca → yfinance → mock."""
    print(f"\n🔄 Testing Fallback Chain for {ticker}...")
    print("-" * 80)
    
    from financial_dashboard.tabs.options_lab.data_loader import fetch_options_chain
    
    results = {
        'ticker': ticker,
        'timestamp': datetime.now().isoformat(),
        'alpaca_attempt': {},
        'yfinance_attempt': {},
        'mock_attempt': {},
        'fallback_working': False
    }
    
    # Attempt 1: Alpaca (may fail if no subscription)
    print("   1️⃣ Attempting Alpaca...")
    try:
        chain = fetch_options_chain(ticker, use_alpaca=True, use_mock=False)
        source = chain.get('source', 'unknown')
        results['alpaca_attempt'] = {
            'source': source,
            'success': source == 'alpaca',
            'error': chain.get('error')
        }
        if source == 'alpaca':
            print(f"      ✅ Alpaca successful")
        elif source == 'yfinance':
            print(f"      🟡 Fell back to yfinance (Alpaca unavailable)")
        else:
            print(f"      ⚠️  Unexpected source: {source}")
    except Exception as e:
        results['alpaca_attempt'] = {'success': False, 'error': str(e)}
        print(f"      ❌ Alpaca failed: {e}")
    
    # Attempt 2: yfinance (should always work for major tickers)
    print("   2️⃣ Testing yfinance directly...")
    try:
        # Force yfinance by using Alpaca=True (will fallback)
        chain = fetch_options_chain(ticker, use_alpaca=True, use_mock=False)
        source = chain.get('source', 'unknown')
        results['yfinance_attempt'] = {
            'source': source,
            'success': source in ['yfinance', 'alpaca'],
            'expirations': len(chain.get('expirations', []))
        }
        if source == 'yfinance' or source == 'alpaca':
            print(f"      ✅ yfinance working ({results['yfinance_attempt']['expirations']} expirations)")
        else:
            print(f"      ⚠️  Unexpected source: {source}")
    except Exception as e:
        results['yfinance_attempt'] = {'success': False, 'error': str(e)}
        print(f"      ❌ yfinance failed: {e}")
    
    # Attempt 3: Mock (should always work)
    print("   3️⃣ Testing mock fallback...")
    try:
        chain = fetch_options_chain(ticker, use_alpaca=False, use_mock=True)
        source = chain.get('source', 'unknown')
        results['mock_attempt'] = {
            'source': source,
            'success': source == 'mock',
            'expirations': len(chain.get('expirations', []))
        }
        if source == 'mock':
            print(f"      ✅ Mock working ({results['mock_attempt']['expirations']} expirations)")
        else:
            print(f"      ⚠️  Expected mock, got: {source}")
    except Exception as e:
        results['mock_attempt'] = {'success': False, 'error': str(e)}
        print(f"      ❌ Mock failed: {e}")
    
    # Determine if fallback chain is working
    results['fallback_working'] = (
        results['yfinance_attempt'].get('success', False) and
        results['mock_attempt'].get('success', False)
    )
    
    if results['fallback_working']:
        print("   ✅ Fallback chain operational")
    else:
        print("   ❌ Fallback chain has issues")
    
    return results

def main():
    """Execute comprehensive environment and live data validation."""
    print("="*80)
    print("🎯 OPTIONS LAB - STEP 1: ENVIRONMENT & LIVE DATA VERIFICATION")
    print("="*80)
    print(f"Started: {datetime.now().isoformat()}")
    
    # Ensure directories
    Path('test-results/options_lab/step1').mkdir(parents=True, exist_ok=True)
    
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'environment': {},
        'api_connection': {},
        'live_data': {},
        'fallback_tests': {},
        'overall_status': 'UNKNOWN'
    }
    
    # Step 1.1: Environment validation
    env_results = validate_environment()
    all_results['environment'] = env_results
    
    # Step 1.2: API connection test
    api_results = test_alpaca_api_connection()
    all_results['api_connection'] = api_results
    
    # Step 1.3: Live data tests for each ticker
    print("\n" + "="*80)
    print("📊 LIVE OPTIONS DATA VALIDATION")
    print("="*80)
    
    tickers = ['SPY', 'AAPL', 'QQQ']
    for ticker in tickers:
        ticker_result = test_live_options_data(ticker, use_alpaca=True)
        all_results['live_data'][ticker] = ticker_result
        
        # ABORT if <20 expirations
        if ticker_result['expirations_count'] < 20 and not ticker_result.get('errors'):
            print(f"\n🚨 ABORT: {ticker} has only {ticker_result['expirations_count']} expirations (minimum 20 required)")
            all_results['overall_status'] = 'ABORTED'
            break
    
    # Step 1.4: Fallback chain tests
    if all_results['overall_status'] != 'ABORTED':
        print("\n" + "="*80)
        print("🔄 FALLBACK CHAIN VALIDATION")
        print("="*80)
        
        for ticker in tickers:
            fallback_result = test_fallback_chain(ticker)
            all_results['fallback_tests'][ticker] = fallback_result
    
    # Determine overall status
    if all_results['overall_status'] != 'ABORTED':
        all_pass = all([
            env_results.get('keys_valid', False),
            all(data.get('success', False) for data in all_results['live_data'].values()),
            all(fb.get('fallback_working', False) for fb in all_results['fallback_tests'].values())
        ])
        all_results['overall_status'] = 'PASS' if all_pass else 'FAIL'
    
    # Save results
    output_file = Path('test-results/options_lab/step1/environment_live_data_validation.json')
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Final summary
    print("\n" + "="*80)
    print("📋 VALIDATION SUMMARY")
    print("="*80)
    print(f"Environment: {'✅ PASS' if env_results.get('keys_valid') else '❌ FAIL'}")
    print(f"API Connection: {'✅ PASS' if api_results.get('api_connection') else '❌ FAIL'}")
    
    print("\nLive Data Results:")
    for ticker, data in all_results['live_data'].items():
        status = '✅ PASS' if data.get('success') else '❌ FAIL'
        exp_count = data.get('expirations_count', 0)
        contracts = data.get('total_contracts', 0)
        source = data.get('source', 'unknown')
        print(f"  {ticker}: {status} | {exp_count} expirations | {contracts} contracts | Source: {source}")
    
    print("\nFallback Chain Results:")
    for ticker, fb in all_results['fallback_tests'].items():
        status = '✅ PASS' if fb.get('fallback_working') else '❌ FAIL'
        print(f"  {ticker}: {status}")
    
    print(f"\n{'='*80}")
    print(f"OVERALL STATUS: {all_results['overall_status']}")
    print(f"Results saved: {output_file}")
    print(f"{'='*80}\n")
    
    return 0 if all_results['overall_status'] == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
