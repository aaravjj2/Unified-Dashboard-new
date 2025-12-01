#!/usr/bin/env python
"""
Agent 1B - API Endpoint Validation Script
Tests the /api/weekly_picks and /api/monthly_picks endpoints
"""
import sys
import time
import subprocess
import requests
import json

def start_server():
    """Start the dashboard server"""
    print("🚀 Starting dashboard server...")
    proc = subprocess.Popen(
        [sys.executable, 'index.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd='/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard'
    )
    # Wait for server to initialize
    time.sleep(10)
    return proc

def test_endpoint(url, name):
    """Test an API endpoint"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ SUCCESS - JSON Response Received")
                print(f"Status: {data.get('status', 'unknown')}")
                print(f"Count: {data.get('count', 0)}")
                print(f"Tickers: {len(data.get('tickers', []))}")
                
                # Check for data quality
                if data.get('count', 0) > 0:
                    sample = data.get('data', [])[0] if data.get('data') else {}
                    print(f"\nSample Record:")
                    for key, value in list(sample.items())[:5]:
                        print(f"  {key}: {value}")
                    
                    # Count N/A values
                    na_count = 0
                    for record in data.get('data', []):
                        for value in record.values():
                            if value in [None, 'N/A', 'Data Unavailable']:
                                na_count += 1
                    
                    print(f"\n📊 Data Quality Check:")
                    print(f"  Total fields: {data.get('count', 0) * len(sample)}")
                    print(f"  N/A values: {na_count}")
                    
                    if na_count == 0:
                        print(f"  ✅ NO 'Data Unavailable' or 'N/A' values found!")
                    else:
                        print(f"  ❌ Found {na_count} N/A values - DATA QUALITY ISSUE")
                else:
                    print("❌ No data returned")
                    return False
                    
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response: {e}")
                print(f"Response text: {response.text[:500]}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection refused - server not running")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timeout")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function"""
    print("="*70)
    print("AGENT 1B - API ENDPOINT VALIDATION")
    print("="*70)
    
    # Start server
    server_proc = start_server()
    
    try:
        # Test endpoints
        weekly_ok = test_endpoint('http://localhost:8050/api/weekly_picks', 'Weekly Picks API')
        monthly_ok = test_endpoint('http://localhost:8050/api/monthly_picks', 'Monthly Picks API')
        
        # Summary
        print(f"\n{'='*70}")
        print("VALIDATION SUMMARY")
        print(f"{'='*70}")
        print(f"Weekly Picks API:  {'✅ PASS' if weekly_ok else '❌ FAIL'}")
        print(f"Monthly Picks API: {'✅ PASS' if monthly_ok else '❌ FAIL'}")
        
        if weekly_ok and monthly_ok:
            print(f"\n🎉 SUCCESS: All API endpoints operational!")
            return 0
        else:
            print(f"\n❌ FAILURE: Some endpoints failed validation")
            return 1
            
    finally:
        # Cleanup
        print(f"\n🛑 Shutting down server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()

if __name__ == '__main__':
    sys.exit(main())
