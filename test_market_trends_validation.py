#!/usr/bin/env python3
"""
Market Trends Tab Validation Script
Mission: Verify Market Trends table has NO "Data Unavailable" or "N/A" values
"""
import requests
import time
import subprocess
import sys
import json

BASE_URL = "http://localhost:8050"

def check_server_running():
    """Check if Dash server is running on port 8050"""
    try:
        response = requests.get(BASE_URL, timeout=5)
        return response.status_code == 200
    except:
        return False

def trigger_market_trends_analysis():
    """
    Trigger Market Trends analysis via the API.
    The Dash app doesn't expose REST API for this, so we'll use Playwright
    to click the "Run Full Analysis" button.
    """
    print("\n📋 Market Trends tab needs to be triggered manually or via Playwright")
    print("   Please ensure the analysis has been run recently and data is cached")
    return True

def check_cached_results():
    """Check if there are cached results in the outputs directory"""
    import os
    import pickle
    
    outputs_dir = "/mnt/c/Aarav/fin_env/unified-dashboard/outputs"
    cache_files = []
    
    if os.path.exists(outputs_dir):
        for file in os.listdir(outputs_dir):
            if file.endswith('.pkl') and 'market_trends' in file.lower():
                cache_files.append(os.path.join(outputs_dir, file))
    
    if not cache_files:
        print("\n❌ No cached Market Trends files found in outputs/")
        return None
    
    # Load most recent cache file
    latest_cache = max(cache_files, key=os.path.getmtime)
    print(f"\n✅ Found cached results: {os.path.basename(latest_cache)}")
    
    try:
        with open(latest_cache, 'rb') as f:
            data = pickle.load(f)
        
        # Check structure
        if isinstance(data, dict):
            detailed = data.get('detailed', [])
            tidy = data.get('tidy', [])
            prices = data.get('prices', {})
            
            print(f"\n📊 Cache Contents:")
            print(f"   - Detailed records: {len(detailed)}")
            print(f"   - Tidy records: {len(tidy)}")
            print(f"   - Price entries: {len(prices)}")
            
            # Check for "Data Unavailable" or N/A in the data
            issues = []
            
            # Check detailed records
            for record in detailed:
                for key, value in record.items():
                    if value == "Data Unavailable" or value == "N/A" or value is None:
                        issues.append(f"Field '{key}' in detailed: {value}")
            
            # Check prices
            for ticker, price_data in prices.items():
                if isinstance(price_data, dict):
                    for key, value in price_data.items():
                        if value is None or value == "N/A":
                            issues.append(f"Price field '{key}' for {ticker}: {value}")
            
            if issues:
                print(f"\n⚠️  Found {len(issues)} missing/N/A values:")
                for issue in issues[:10]:  # Show first 10
                    print(f"   - {issue}")
                return False
            else:
                print(f"\n✅ NO 'Data Unavailable' or 'N/A' values found in cache!")
                return True
        
    except Exception as e:
        print(f"\n❌ Failed to load cache file: {e}")
        return None

def test_market_trends_via_playwright():
    """
    Use Playwright to:
    1. Navigate to Market Trends tab
    2. Trigger "Run Full Analysis"
    3. Wait for completion
    4. Inspect table for "Data Unavailable" text
    """
    print("\n🎭 Starting Playwright test...")
    
    test_script = '''
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("📍 Navigating to Market Trends tab...")
        await page.goto("http://localhost:8050/", wait_until="domcontentloaded")
        await page.wait_for_selector('a:has-text("Market Trends")', timeout=10000)
        
        # Click Market Trends tab
        await page.locator('a:has-text("Market Trends")').click()
        await page.wait_for_timeout(2000)
        
        print("🔍 Checking for existing table data...")
        # Check if table already has data
        table = page.locator('table.market-trends-html-table')
        if await table.count() > 0:
            # Check for "Data Unavailable" text
            page_content = await page.content()
            unavailable_count = page_content.count("Data Unavailable")
            na_count = page_content.count(">N/A<")
            
            print(f"\\n📊 Table Analysis:")
            print(f"   - 'Data Unavailable' occurrences: {unavailable_count}")
            print(f"   - 'N/A' occurrences: {na_count}")
            
            if unavailable_count == 0 and na_count == 0:
                print("\\n✅ SUCCESS: No 'Data Unavailable' or 'N/A' values found!")
                await browser.close()
                return True
            else:
                print(f"\\n❌ FAILURE: Found {unavailable_count + na_count} missing values")
                await page.screenshot(path="market_trends_failure.png")
                await browser.close()
                return False
        else:
            print("⚠️  No table found - triggering analysis...")
            
            # Click "Run Full Analysis" button
            run_btn = page.locator('#run-btn')
            if await run_btn.count() > 0:
                await run_btn.click()
                print("🚀 Clicked 'Run Full Analysis' - waiting for job completion...")
                
                # Wait up to 60 seconds for table to appear
                try:
                    await page.wait_for_selector('table.market-trends-html-table', timeout=60000)
                    print("✅ Table appeared!")
                    
                    # Re-check for "Data Unavailable"
                    page_content = await page.content()
                    unavailable_count = page_content.count("Data Unavailable")
                    na_count = page_content.count(">N/A<")
                    
                    print(f"\\n📊 Table Analysis After Run:")
                    print(f"   - 'Data Unavailable' occurrences: {unavailable_count}")
                    print(f"   - 'N/A' occurrences: {na_count}")
                    
                    await page.screenshot(path="market_trends_result.png")
                    await browser.close()
                    
                    return unavailable_count == 0 and na_count == 0
                    
                except Exception as e:
                    print(f"❌ Timeout waiting for table: {e}")
                    await page.screenshot(path="market_trends_timeout.png")
                    await browser.close()
                    return False
        
        await browser.close()
        return False

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)
'''
    
    # Write test script to temp file
    with open('/tmp/test_market_trends_pw.py', 'w') as f:
        f.write(test_script)
    
    # Run Playwright test
    try:
        result = subprocess.run(
            ['python3', '/tmp/test_market_trends_pw.py'],
            capture_output=True,
            text=True,
            timeout=90
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Playwright test timed out after 90 seconds")
        return False
    except Exception as e:
        print(f"❌ Playwright test failed: {e}")
        return False

def main():
    print("="*80)
    print("MARKET TRENDS TAB VALIDATION")
    print("="*80)
    
    # Step 1: Check server
    print("\nStep 1: Checking if Dash server is running...")
    if not check_server_running():
        print("❌ Dash server not running on http://localhost:8050")
        print("   Please start the server first: cd financial_dashboard && python index.py")
        return False
    print("✅ Server is running")
    
    # Step 2: Check cached results
    print("\nStep 2: Checking cached results...")
    cache_valid = check_cached_results()
    
    # Step 3: Run Playwright test
    print("\nStep 3: Testing Market Trends UI with Playwright...")
    try:
        ui_valid = test_market_trends_via_playwright()
    except Exception as e:
        print(f"❌ Playwright test crashed: {e}")
        ui_valid = False
    
    # Final verdict
    print("\n" + "="*80)
    print("FINAL VERDICT")
    print("="*80)
    
    if cache_valid and ui_valid:
        print("✅ SUCCESS: Market Trends tab is fully operational!")
        print("   - Cache data is clean (no N/A values)")
        print("   - UI renders correctly (no 'Data Unavailable' text)")
        return True
    elif cache_valid:
        print("⚠️  PARTIAL: Cache is good but UI has issues")
        return False
    elif ui_valid:
        print("⚠️  PARTIAL: UI is good but cache has issues")
        return False
    else:
        print("❌ FAILURE: Market Trends tab has data quality issues")
        print("   Next steps:")
        print("   1. Check price fetching logic in tabs/market_trends.py")
        print("   2. Verify SH.RESULTS_CACHE is being populated correctly")
        print("   3. Run 'Run Full Analysis' button manually to regenerate cache")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
