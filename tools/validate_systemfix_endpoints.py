#!/usr/bin/env python3
"""
Quick API Endpoint Validation - No Dashboard Startup Required
Tests endpoints that can respond before full callback registration
"""

import requests
import json
import time
from pathlib import Path

DASHBOARD_URL = "http://localhost:8050"
REPORT_DIR = Path("/home/aarav/unified-dashboard/reports/systemfix/diagnostics")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def test_endpoint(name, url, timeout=5):
    """Test an endpoint and return status."""
    print(f"\n🔍 Testing {name}...")
    print(f"   URL: {url}")
    
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout)
        duration = time.time() - start
        
        print(f"   Status: {response.status_code}")
        print(f"   Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ SUCCESS - JSON response received")
                
                # Save response
                filename = name.lower().replace(" ", "_").replace("/", "_") + ".json"
                (REPORT_DIR / filename).write_text(json.dumps(data, indent=2))
                print(f"   Saved to: {filename}")
                
                return True, data
            except:
                print(f"   ✅ SUCCESS - Non-JSON response")
                return True, response.text
        else:
            print(f"   ❌ FAILED - Status {response.status_code}")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️  TIMEOUT after {timeout}s")
        return False, None
    except requests.exceptions.ConnectionError:
        print(f"   ❌ CONNECTION REFUSED - Dashboard not running?")
        return False, None
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False, None

def main():
    print("="*80)
    print("SYSTEMFIX ENDPOINT VALIDATION")
    print("="*80)
    
    results = {}
    
    # Test 1: Health Endpoint
    success, data = test_endpoint(
        "Health Endpoint",
        f"{DASHBOARD_URL}/health/systemfix"
    )
    results['health'] = success
    if data and isinstance(data, dict):
        print(f"   System Status: {data.get('status', 'unknown')}")
        print(f"   Callbacks: {data.get('dash_app', {}).get('callback_count', 0)}")
    
    # Test 2: Callback Map
    success, data = test_endpoint(
        "Callback Map",
        f"{DASHBOARD_URL}/admin/callback_map"
    )
    results['callback_map'] = success
    if data and isinstance(data, dict):
        print(f"   Total Callbacks: {data.get('total_callbacks', 0)}")
        print(f"   Duplicates: {data.get('duplicate_count', 0)}")
    
    # Test 3: Market Sentiment
    success, data = test_endpoint(
        "Market Sentiment",
        f"{DASHBOARD_URL}/api/cc/market_sentiment"
    )
    results['market_sentiment'] = success
    if data and isinstance(data, dict) and 'last_updated' in data:
        print(f"   Last Updated: {data.get('last_updated', 'N/A')}")
    
    # Test 4: Market Trends Health
    success, data = test_endpoint(
        "Market Trends Health",
        f"{DASHBOARD_URL}/api/market_trends/health"
    )
    results['market_trends_health'] = success
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print("="*80)
    return all(results.values())

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
