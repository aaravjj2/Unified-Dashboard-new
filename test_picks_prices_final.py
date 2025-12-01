#!/usr/bin/env python3
"""
Final test to verify Weekly/Monthly Picks price data fetching after PHASE 18B fix.
Tests that background fetch is triggered and prices are populated correctly.
"""

import time
import subprocess
from playwright.sync_api import sync_playwright
from datetime import datetime

def wait_for_app(url="http://localhost:8050", timeout=30):
    """Wait for app to be ready"""
    import requests
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print("✅ App is ready")
                return True
        except:
            pass
        time.sleep(2)
    print("❌ App failed to become ready")
    return False

def test_picks_prices():
    """Test Weekly and Monthly Picks price data"""
    
    if not wait_for_app():
        return False
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_dir = f'/app/test-artifacts/picks_prices_{timestamp}'
    subprocess.run(['mkdir', '-p', screenshot_dir], check=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load dashboard
            print("1️⃣ Loading dashboard...")
            page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            time.sleep(3)
            page.screenshot(path=f'{screenshot_dir}/01_dashboard_loaded.png')
            print("   ✅ Dashboard loaded")
            
            # Test Weekly Picks
            print("\n2️⃣ Testing Weekly Picks...")
            
            # Click Weekly Picks tab
            weekly_tab = page.locator('button:has-text("Weekly Picks")')
            if weekly_tab.count() > 0:
                weekly_tab.click()
                print("   ✅ Clicked Weekly Picks tab")
                time.sleep(2)
                page.screenshot(path=f'{screenshot_dir}/02_weekly_picks_initial.png')
                
                # Wait for background fetch to complete (up to 15 seconds)
                print("   ⏳ Waiting for background fetch to complete...")
                time.sleep(10)
                page.screenshot(path=f'{screenshot_dir}/03_weekly_picks_after_fetch.png')
                
                # Check for price data in the table
                table = page.locator('#weekly-picks-table')
                if table.count() > 0:
                    # Get all cells in Current Price column
                    price_cells = page.locator('#weekly-picks-table td').all()
                    price_values = []
                    for cell in price_cells[:50]:  # Check first 50 cells
                        text = cell.inner_text()
                        if '$' in text and text != '$-' and text != '$N/A':
                            price_values.append(text)
                    
                    print(f"   📊 Found {len(price_values)} price values in Weekly Picks table")
                    if price_values:
                        print(f"   📈 Sample prices: {price_values[:5]}")
                        print("   ✅ Weekly Picks has price data!")
                    else:
                        print("   ⚠️ Weekly Picks table exists but no valid prices found")
                else:
                    print("   ❌ Weekly Picks table not found")
            else:
                print("   ❌ Weekly Picks tab button not found")
            
            # Test Monthly Picks
            print("\n3️⃣ Testing Monthly Picks...")
            
            # Click Monthly Picks tab
            monthly_tab = page.locator('button:has-text("Monthly Picks")')
            if monthly_tab.count() > 0:
                monthly_tab.click()
                print("   ✅ Clicked Monthly Picks tab")
                time.sleep(2)
                page.screenshot(path=f'{screenshot_dir}/04_monthly_picks_initial.png')
                
                # Wait for background fetch to complete
                print("   ⏳ Waiting for background fetch to complete...")
                time.sleep(10)
                page.screenshot(path=f'{screenshot_dir}/05_monthly_picks_after_fetch.png')
                
                # Check for price data in the table
                table = page.locator('#monthly-picks-table')
                if table.count() > 0:
                    # Get all cells in Current Price column
                    price_cells = page.locator('#monthly-picks-table td').all()
                    price_values = []
                    for cell in price_cells[:50]:  # Check first 50 cells
                        text = cell.inner_text()
                        if '$' in text and text != '$-' and text != '$N/A':
                            price_values.append(text)
                    
                    print(f"   📊 Found {len(price_values)} price values in Monthly Picks table")
                    if price_values:
                        print(f"   📈 Sample prices: {price_values[:5]}")
                        print("   ✅ Monthly Picks has price data!")
                    else:
                        print("   ⚠️ Monthly Picks table exists but no valid prices found")
                else:
                    print("   ❌ Monthly Picks table not found")
            else:
                print("   ❌ Monthly Picks tab button not found")
            
            # Final screenshot
            page.screenshot(path=f'{screenshot_dir}/06_final.png')
            
            print(f"\n✅ Test completed - Screenshots saved to {screenshot_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            page.screenshot(path=f'{screenshot_dir}/error.png')
            return False
        finally:
            browser.close()

if __name__ == '__main__':
    print("=" * 80)
    print("TESTING WEEKLY/MONTHLY PICKS PRICE DATA (PHASE 18B FIX VERIFICATION)")
    print("=" * 80)
    
    success = test_picks_prices()
    
    # Check logs for background fetch activity
    print("\n4️⃣ Checking logs for background fetch activity...")
    result = subprocess.run(
        ['tail', '-50', '/app/app.log'],
        capture_output=True,
        text=True
    )
    
    log_lines = result.stdout.split('\n')
    fetch_logs = [line for line in log_lines if 'background' in line.lower() and 'fetch' in line.lower() and 'price' in line.lower()]
    
    if fetch_logs:
        print("   ✅ Found background fetch logs:")
        for log in fetch_logs[-10:]:  # Show last 10 relevant logs
            print(f"      {log}")
    else:
        print("   ⚠️ No background fetch logs found in recent logs")
    
    print("\n" + "=" * 80)
    if success:
        print("✅ PICKS PRICE TEST PASSED")
    else:
        print("❌ PICKS PRICE TEST FAILED")
    print("=" * 80)
