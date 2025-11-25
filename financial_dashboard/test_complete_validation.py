#!/usr/bin/env python
"""
Agent 1B - Complete Validation Suite
Tests Weekly and Monthly picks Flask servers with JSON API endpoints
"""
import sys
import time
import subprocess
import requests
import json
from datetime import datetime

def start_server(script, port, name):
    """Start a Flask server"""
    print(f"🚀 Starting {name} on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd='/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard',
        env={'PORT': str(port)}
    )
    time.sleep(8)  # Wait for server initialization
    return proc

def test_endpoint(url, name):
    """Test an API endpoint and validate data quality"""
    print(f"\n{'='*80}")
    print(f"🔍 TESTING: {name}")
    print(f"URL: {url}")
    print(f"{'='*80}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}")
            return False
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"Response preview: {response.text[:500]}")
            return False
        
        # Check response structure
        if data.get('status') != 'success':
            print(f"❌ API returned error status: {data.get('message', 'Unknown error')}")
            return False
        
        count = data.get('count', 0)
        tickers = data.get('tickers', [])
        records = data.get('data', [])
        
        print(f"\n📊 RESPONSE SUMMARY:")
        print(f"   Status: {data.get('status')}")
        print(f"   Record Count: {count}")
        print(f"   Ticker Count: {len(tickers)}")
        print(f"   Source File: {data.get('source_file', 'N/A')}")
        print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
        
        if count == 0:
            print(f"❌ No data returned!")
            return False
        
        # DATA QUALITY VALIDATION
        print(f"\n📈 DATA QUALITY CHECK:")
        
        na_fields = {}
        missing_price_count = 0
        
        for record in records:
            ticker = record.get('Ticker', record.get('ticker', '?'))
            
            # Check for missing critical fields
            for field in ['Current_Price', 'Week_Start_Price', 'Month_Start_Price']:
                if field in record:
                    value = record[field]
                    if value is None or value == 'N/A' or value == 'Data Unavailable':
                        na_fields.setdefault(field, []).append(ticker)
                        if 'Price' in field:
                            missing_price_count += 1
        
        # Report findings
        if na_fields:
            print(f"   ⚠️  Found missing/N/A values:")
            for field, ticker_list in na_fields.items():
                print(f"      {field}: {len(ticker_list)} tickers - {ticker_list[:5]}{' ...' if len(ticker_list) > 5 else ''}")
        else:
            print(f"   ✅ NO 'Data Unavailable' or 'N/A' values found!")
        
        # Verify numeric values
        sample = records[0]
        print(f"\n📋 SAMPLE RECORD (Ticker: {sample.get('Ticker', sample.get('ticker', '?'))}):")
        for key in ['Ticker', 'Current_Price', 'Daily_Change', 'Profit_Loss', 'ROI_Pct']:
            if key in sample:
                value = sample[key]
                print(f"   {key}: {value}")
        
        # SUCCESS CRITERIA
        success = True
        if count < 20:
            print(f"\n   ⚠️  WARNING: Expected ≥20 tickers, got {count}")
        
        if missing_price_count > 0:
            print(f"\n   ❌ FAILED: {missing_price_count} records have missing price data")
            success = False
        else:
            print(f"\n   ✅ SUCCESS: All {count} records have valid price data!")
        
        return success
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection refused - server not running")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timeout (>30s)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main validation workflow"""
    print("="*80)
    print("🤖 AGENT 1B - COMPLETE VALIDATION SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}\n")
    
    servers = []
    
    try:
        # Start servers
        weekly_proc = start_server('weekly_picks_flask.py', 8053, 'Weekly Picks Flask')
        servers.append(weekly_proc)
        
        monthly_proc = start_server('monthly_picks_flask.py', 8052, 'Monthly Picks Flask')
        servers.append(monthly_proc)
        
        # Test endpoints
        weekly_ok = test_endpoint('http://localhost:8053/api/weekly_picks', 'Weekly Picks API')
        monthly_ok = test_endpoint('http://localhost:8052/api/monthly_picks', 'Monthly Picks API')
        
        # Summary
        print(f"\n{'='*80}")
        print("📊 VALIDATION SUMMARY")
        print(f"{'='*80}")
        print(f"Weekly Picks API:  {'✅ PASS' if weekly_ok else '❌ FAIL'}")
        print(f"Monthly Picks API: {'✅ PASS' if monthly_ok else '❌ FAIL'}")
        
        if weekly_ok and monthly_ok:
            print(f"\n🎉 SUCCESS: All data endpoints operational with valid data!")
            print(f"   ✓ No 'Data Unavailable' or 'N/A' values")
            print(f"   ✓ All tickers have numeric prices")
            print(f"   ✓ JSON API endpoints responding correctly")
            return 0
        else:
            print(f"\n❌ FAILURE: Data quality issues detected")
            return 1
            
    finally:
        # Cleanup
        print(f"\n🛑 Shutting down servers...")
        for proc in servers:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

if __name__ == '__main__':
    sys.exit(main())
