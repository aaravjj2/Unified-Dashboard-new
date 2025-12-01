"""
Test script to determine actual rate limits for Finnhub and Alpaca APIs.
Tests various endpoints to find what's allowed on free tier.
"""
import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/mnt/c/Aarav/fin_env/unified-dashboard/keys.env')

FINNHUB_KEY1 = os.getenv('FINNHUB_API_KEY')
FINNHUB_KEY2 = os.getenv('FINNHUB2_API_KEY')
ALPACA_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET = os.getenv('ALPACA_API_SECRET')

print("=" * 80)
print("API RATE LIMIT TESTING - FINNHUB & ALPACA")
print("=" * 80)
print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# =============================================================================
# FINNHUB API TESTS
# =============================================================================

def test_finnhub_basic_access(api_key, key_name):
    """Test basic Finnhub API access and common endpoints."""
    print(f"\n{'=' * 80}")
    print(f"TESTING FINNHUB API - {key_name}")
    print(f"{'=' * 80}")
    
    base_url = "https://finnhub.io/api/v1"
    test_symbol = "AAPL"
    
    # Calculate timestamps for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    end_ts = int(end_date.timestamp())
    start_ts = int(start_date.timestamp())
    
    endpoints_to_test = [
        {
            'name': 'Company Profile',
            'url': f'{base_url}/stock/profile2',
            'params': {'symbol': test_symbol, 'token': api_key}
        },
        {
            'name': 'Quote (Real-time Price)',
            'url': f'{base_url}/quote',
            'params': {'symbol': test_symbol, 'token': api_key}
        },
        {
            'name': 'Candles (Historical OHLC)',
            'url': f'{base_url}/stock/candle',
            'params': {
                'symbol': test_symbol,
                'resolution': 'D',
                'from': start_ts,
                'to': end_ts,
                'token': api_key
            }
        },
        {
            'name': 'Company News',
            'url': f'{base_url}/company-news',
            'params': {
                'symbol': test_symbol,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'token': api_key
            }
        },
        {
            'name': 'Market News',
            'url': f'{base_url}/news',
            'params': {'category': 'general', 'token': api_key}
        }
    ]
    
    results = {}
    
    for endpoint in endpoints_to_test:
        print(f"\n📍 Testing: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            response = requests.get(endpoint['url'], params=endpoint['params'], timeout=10)
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Headers: X-RateLimit-Limit={response.headers.get('X-RateLimit-Limit', 'N/A')}")
            print(f"           X-RateLimit-Remaining={response.headers.get('X-RateLimit-Remaining', 'N/A')}")
            print(f"           X-RateLimit-Reset={response.headers.get('X-RateLimit-Reset', 'N/A')}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS - Data returned: {type(data).__name__}")
                if isinstance(data, list):
                    print(f"      Items: {len(data)}")
                elif isinstance(data, dict):
                    print(f"      Keys: {list(data.keys())[:5]}")
                results[endpoint['name']] = {'status': 'SUCCESS', 'code': 200}
            elif response.status_code == 403:
                print(f"   ❌ FORBIDDEN (403) - Access denied")
                print(f"   Response: {response.text[:200]}")
                results[endpoint['name']] = {'status': 'FORBIDDEN', 'code': 403}
            elif response.status_code == 429:
                print(f"   ⚠️  RATE LIMITED (429)")
                print(f"   Response: {response.text[:200]}")
                results[endpoint['name']] = {'status': 'RATE_LIMITED', 'code': 429}
            else:
                print(f"   ⚠️  OTHER ERROR - {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results[endpoint['name']] = {'status': 'ERROR', 'code': response.status_code}
        
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            results[endpoint['name']] = {'status': 'EXCEPTION', 'error': str(e)}
        
        time.sleep(1)  # Be polite between requests
    
    return results


def test_finnhub_rate_limits(api_key, key_name):
    """Test Finnhub rate limits by making rapid requests."""
    print(f"\n{'=' * 80}")
    print(f"TESTING FINNHUB RATE LIMITS - {key_name}")
    print(f"{'=' * 80}")
    
    url = "https://finnhub.io/api/v1/quote"
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    print(f"\nMaking rapid requests (5 symbols)...")
    start_time = time.time()
    
    for i, symbol in enumerate(symbols):
        response = requests.get(url, params={'symbol': symbol, 'token': api_key}, timeout=10)
        print(f"   Request {i+1}: {symbol} - Status {response.status_code} - "
              f"Remaining: {response.headers.get('X-RateLimit-Remaining', 'N/A')}")
        
        if response.status_code == 429:
            print(f"   ⚠️  RATE LIMIT HIT at request {i+1}")
            break
    
    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.2f}s")


# =============================================================================
# ALPACA API TESTS
# =============================================================================

def test_alpaca_basic_access():
    """Test basic Alpaca API access and common endpoints."""
    print(f"\n{'=' * 80}")
    print(f"TESTING ALPACA API")
    print(f"{'=' * 80}")
    
    if not ALPACA_KEY or not ALPACA_SECRET:
        print("❌ Alpaca credentials not found in environment")
        return {}
    
    headers = {
        'APCA-API-KEY-ID': ALPACA_KEY,
        'APCA-API-SECRET-KEY': ALPACA_SECRET
    }
    
    # Alpaca endpoints
    base_url_trading = "https://paper-api.alpaca.markets/v2"
    base_url_data = "https://data.alpaca.markets/v2"
    
    test_symbol = "AAPL"
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    endpoints_to_test = [
        {
            'name': 'Account Info',
            'url': f'{base_url_trading}/account',
            'headers': headers,
            'params': {}
        },
        {
            'name': 'Stock Latest Quote',
            'url': f'{base_url_data}/stocks/{test_symbol}/quotes/latest',
            'headers': headers,
            'params': {'feed': 'iex'}  # Free tier uses IEX
        },
        {
            'name': 'Stock Latest Trade',
            'url': f'{base_url_data}/stocks/{test_symbol}/trades/latest',
            'headers': headers,
            'params': {'feed': 'iex'}
        },
        {
            'name': 'Stock Bars (Historical)',
            'url': f'{base_url_data}/stocks/{test_symbol}/bars',
            'headers': headers,
            'params': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'timeframe': '1Day',
                'feed': 'iex'
            }
        },
        {
            'name': 'Stock Snapshot',
            'url': f'{base_url_data}/stocks/{test_symbol}/snapshot',
            'headers': headers,
            'params': {'feed': 'iex'}
        }
    ]
    
    results = {}
    
    for endpoint in endpoints_to_test:
        print(f"\n📍 Testing: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            response = requests.get(
                endpoint['url'],
                headers=endpoint['headers'],
                params=endpoint['params'],
                timeout=10
            )
            
            print(f"   Status Code: {response.status_code}")
            
            # Check rate limit headers
            for header_name in ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset']:
                value = response.headers.get(header_name, 'N/A')
                print(f"   {header_name}: {value}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS - Data returned")
                if isinstance(data, dict):
                    print(f"      Keys: {list(data.keys())[:5]}")
                results[endpoint['name']] = {'status': 'SUCCESS', 'code': 200}
            elif response.status_code == 403:
                print(f"   ❌ FORBIDDEN (403)")
                print(f"   Response: {response.text[:200]}")
                results[endpoint['name']] = {'status': 'FORBIDDEN', 'code': 403}
            elif response.status_code == 404:
                print(f"   ❌ NOT FOUND (404)")
                print(f"   Response: {response.text[:200]}")
                results[endpoint['name']] = {'status': 'NOT_FOUND', 'code': 404}
            elif response.status_code == 429:
                print(f"   ⚠️  RATE LIMITED (429)")
                print(f"   Response: {response.text[:200]}")
                results[endpoint['name']] = {'status': 'RATE_LIMITED', 'code': 429}
            else:
                print(f"   ⚠️  OTHER ERROR - {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results[endpoint['name']] = {'status': 'ERROR', 'code': response.status_code}
        
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            results[endpoint['name']] = {'status': 'EXCEPTION', 'error': str(e)}
        
        time.sleep(1)  # Be polite between requests
    
    return results


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    # Test Finnhub Key 1
    if FINNHUB_KEY1:
        finnhub1_results = test_finnhub_basic_access(FINNHUB_KEY1, "Key 1")
        test_finnhub_rate_limits(FINNHUB_KEY1, "Key 1")
    else:
        print("\n⚠️  Finnhub Key 1 not found")
        finnhub1_results = {}
    
    # Test Finnhub Key 2
    if FINNHUB_KEY2:
        finnhub2_results = test_finnhub_basic_access(FINNHUB_KEY2, "Key 2")
        test_finnhub_rate_limits(FINNHUB_KEY2, "Key 2")
    else:
        print("\n⚠️  Finnhub Key 2 not found")
        finnhub2_results = {}
    
    # Test Alpaca
    alpaca_results = test_alpaca_basic_access()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print("\n📊 FINNHUB KEY 1 RESULTS:")
    for endpoint, result in finnhub1_results.items():
        status = result.get('status', 'UNKNOWN')
        emoji = '✅' if status == 'SUCCESS' else '❌'
        print(f"   {emoji} {endpoint}: {status}")
    
    print("\n📊 FINNHUB KEY 2 RESULTS:")
    for endpoint, result in finnhub2_results.items():
        status = result.get('status', 'UNKNOWN')
        emoji = '✅' if status == 'SUCCESS' else '❌'
        print(f"   {emoji} {endpoint}: {status}")
    
    print("\n📊 ALPACA RESULTS:")
    for endpoint, result in alpaca_results.items():
        status = result.get('status', 'UNKNOWN')
        emoji = '✅' if status == 'SUCCESS' else '❌'
        print(f"   {emoji} {endpoint}: {status}")
    
    print("\n" + "=" * 80)
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
