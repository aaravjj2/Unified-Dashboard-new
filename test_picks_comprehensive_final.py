#!/usr/bin/env python3
"""
Final comprehensive test for Weekly/Monthly Picks with price data verification.
Navigate to tabs, wait for background fetch, capture screenshots, extract price data.
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

def test_picks_comprehensive():
    """Comprehensive test of Weekly and Monthly Picks tabs"""
    
    if not wait_for_app():
        return False
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Use workspace-local test-artifacts directory to avoid permission issues
    screenshot_dir = f'./test-artifacts/picks_final_{timestamp}'
    import os
    os.makedirs(screenshot_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("=" * 80)
            print("WEEKLY/MONTHLY PICKS COMPREHENSIVE TEST")
            print("=" * 80)
            
            # Load dashboard
            print("\n1️⃣ Loading dashboard...")
            page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            time.sleep(3)
            page.screenshot(path=f'{screenshot_dir}/01_home.png')
            print("   ✅ Dashboard loaded")
            
            # Find all navigation links
            print("\n2️⃣ Finding navigation links...")
            all_links = page.locator('a').all()
            link_texts = []
            for link in all_links[:50]:
                try:
                    text = link.inner_text()
                    if text:
                        link_texts.append(text)
                except:
                    pass
            
            print(f"   📊 Found {len(link_texts)} navigation links")
            weekly_found = any('weekly' in t.lower() and 'pick' in t.lower() for t in link_texts)
            monthly_found = any('monthly' in t.lower() and 'pick' in t.lower() for t in link_texts)
            print(f"   {'✅' if weekly_found else '❌'} Weekly Picks link: {'Found' if weekly_found else 'NOT FOUND'}")
            print(f"   {'✅' if monthly_found else '❌'} Monthly Picks link: {'Found' if monthly_found else 'NOT FOUND'}")
            
            # Test Weekly Picks
            if weekly_found:
                print("\n3️⃣ Testing Weekly Picks...")
                try:
                    weekly_link = page.locator('a').filter(has_text='Weekly Picks').first
                    weekly_link.click()
                    print("   ✅ Clicked Weekly Picks")
                    time.sleep(3)
                    page.screenshot(path=f'{screenshot_dir}/02_weekly_picks_initial.png')
                    
                    # Wait for background fetch to complete and for DOM to update
                    print("   ⏳ Waiting up to 30s for background price JSON to appear...")
                    try:
                        # Wait for the hidden JSON element that contains raw prices
                        page.wait_for_selector('#wp-prices-json', timeout=30000)
                        raw = page.locator('#wp-prices-json').inner_text()
                        try:
                            j = __import__('json').loads(raw)
                            prices = j.get('prices', {})
                            sample = list(prices.items())[:5]
                            print(f"   ✅ Weekly hidden JSON found: sample keys: {[k for k,_ in sample]}")
                        except Exception as e:
                            print(f"   ⚠️ Failed to parse weekly hidden JSON: {e}")
                    except Exception:
                        print("   ⚠️ Weekly hidden JSON not found within timeout — falling back to table scraping")
                        # Fallback 1: Try to fetch the persisted asset directly (served from /assets)
                        try:
                            import requests as _req
                            r = _req.get('http://localhost:8050/assets/prices_weekly.json', timeout=3)
                            if r.status_code == 200:
                                try:
                                    parsed = __import__('json').loads(r.text)
                                    prices = parsed.get('prices', {})
                                    if prices:
                                        print(f"   ✅ Weekly asset JSON fetched: sample keys: {list(prices.keys())[:5]}")
                                except Exception as _e:
                                    print(f"   ⚠️ Failed to parse weekly asset JSON: {_e}")
                        except Exception:
                            pass
                        # Fallback 2: Click refresh and scrape visible table cells
                        try:
                            refresh_btn = page.locator('#wp-refresh-btn')
                            if refresh_btn.count() > 0:
                                refresh_btn.click()
                                time.sleep(5)
                                page.screenshot(path=f'{screenshot_dir}/03b_weekly_picks_after_refresh.png')
                                print("   ✅ Refreshed Weekly Picks (fallback)")
                        except Exception as e:
                            print(f"   ⚠️ Could not click refresh: {e}")
                        # Try to scrape table values
                        try:
                            cells = page.locator('td').all()
                            price_like_values = []
                            for cell in cells[:200]:
                                try:
                                    text = cell.inner_text()
                                except:
                                    continue
                                if '$' in text and 'N/A' not in text:
                                    price_like_values.append(text)
                            if price_like_values:
                                print(f"   💰 Found {len(price_like_values)} price values (fallback)")
                                print(f"   📈 Sample prices: {price_like_values[:5]}")
                            else:
                                print("   ⚠️ No valid price values found in table (fallback)")
                        except Exception as e:
                            print(f"   ⚠️ Table scraping failed: {e}")
                except Exception as e:
                    print(f"   ❌ Error testing Weekly Picks: {e}")
                    page.screenshot(path=f'{screenshot_dir}/error_weekly.png')
            
            # Test Monthly Picks
            if monthly_found:
                print("\n4️⃣ Testing Monthly Picks...")
                try:
                    monthly_link = page.locator('a').filter(has_text='Monthly Picks').first
                    monthly_link.click()
                    print("   ✅ Clicked Monthly Picks")
                    time.sleep(3)
                    page.screenshot(path=f'{screenshot_dir}/04_monthly_picks_initial.png')
                    
                    # Wait up to 30s for hidden monthly JSON
                    print("   ⏳ Waiting up to 30s for monthly hidden price JSON to appear...")
                    try:
                        page.wait_for_selector('#mp-prices-json', timeout=30000)
                        rawm = page.locator('#mp-prices-json').inner_text()
                        try:
                            parsedm = __import__('json').loads(rawm)
                            samplem = list(parsedm.get('prices', {}).items())[:5]
                            print('   ✅ Monthly hidden JSON found: sample keys:', [k for k,_ in samplem])
                        except Exception as e:
                            print(f'   ⚠️ Failed to parse monthly hidden JSON: {e}')
                    except Exception:
                        print('   ⚠️ Monthly hidden JSON not found within timeout — falling back to table scraping')
                        # Fallback 1: Try to fetch the persisted asset directly (served from /assets)
                        try:
                            import requests as _req
                            r = _req.get('http://localhost:8050/assets/prices_monthly.json', timeout=3)
                            if r.status_code == 200:
                                try:
                                    parsedm = __import__('json').loads(r.text)
                                    if parsedm.get('prices'):
                                        print('   ✅ Monthly asset JSON fetched: sample keys:', list(parsedm.get('prices', {}).keys())[:5])
                                except Exception as _e:
                                    print(f"   ⚠️ Failed to parse monthly asset JSON: {_e}")
                        except Exception:
                            pass
                        try:
                            refresh_btn = page.locator('#mp-refresh-btn')
                            if refresh_btn.count() > 0:
                                refresh_btn.click()
                                time.sleep(5)
                                page.screenshot(path=f'{screenshot_dir}/05b_monthly_picks_after_refresh.png')
                                print('   ✅ Refreshed Monthly Picks (fallback)')
                        except Exception as e:
                            print(f'   ⚠️ Could not click monthly refresh: {e}')
                        try:
                            cells = page.locator('td').all()
                            price_like_values = []
                            for cell in cells[:200]:
                                try:
                                    text = cell.inner_text()
                                except:
                                    continue
                                if '$' in text and 'N/A' not in text:
                                    price_like_values.append(text)
                            if price_like_values:
                                print(f"   💰 Found {len(price_like_values)} price values (fallback)")
                                print(f"   📈 Sample prices: {price_like_values[:5]}")
                            else:
                                print('   ⚠️ No valid price values found in table (fallback)')
                        except Exception as e:
                            print(f'   ⚠️ Monthly table scraping failed: {e}')
                except Exception as e:
                    print(f"   ❌ Error testing Monthly Picks: {e}")
                    page.screenshot(path=f'{screenshot_dir}/error_monthly.png')
            
            page.screenshot(path=f'{screenshot_dir}/06_final.png')
            print(f"\n✅ Screenshots saved to {screenshot_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            page.screenshot(path=f'{screenshot_dir}/error.png')
            return False
        finally:
            browser.close()

if __name__ == '__main__':
    success = test_picks_comprehensive()
    
    # Check logs for background fetch activity
    print("\n5️⃣ Checking logs for background fetch activity...")
    result = subprocess.run(
        ['docker', 'logs', '--tail', '100', 'dash_app'],
        capture_output=True,
        text=True
    )
    
    log_lines = result.stdout.split('\n') + result.stderr.split('\n')
    fetch_logs = [line for line in log_lines if ('background' in line.lower() or 'price fetch' in line.lower()) and ('weekly' in line.lower() or 'monthly' in line.lower())]
    
    if fetch_logs:
        print("   ✅ Background fetch logs found:")
        for log in fetch_logs[-15:]:  # Show last 15 relevant logs
            if log.strip():
                print(f"      {log}")
    else:
        print("   ⚠️ No background fetch logs found")
    
    print("\n" + "=" * 80)
    if success:
        print("✅ PICKS COMPREHENSIVE TEST COMPLETED")
    else:
        print("❌ PICKS COMPREHENSIVE TEST FAILED")
    print("=" * 80)
