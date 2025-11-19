"""
Comprehensive browser-based E2E test for Market Trends tab.
Tests: Tab clicking, full analysis workflow, cache verification.
Uses sync Playwright for stability.
"""
from playwright.sync_api import sync_playwright
import time
import json
import os
from datetime import datetime

def main():
    print("=" * 80)
    print("MARKET TRENDS E2E TEST - CHROMIUM BROWSER")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    with sync_playwright() as p:
        # Launch visible browser for debugging
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context()
        page = context.new_page()
        
        # Capture console and network
        console_messages = []
        page.on('console', lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
        
        api_calls = {'finnhub': [], 'alpaca': [], 'yfinance': []}
        def log_request(request):
            url = request.url
            if 'finnhub' in url.lower():
                api_calls['finnhub'].append(url)
            elif 'alpaca' in url.lower():
                api_calls['alpaca'].append(url)
        page.on('request', log_request)
        
        try:
            # Step 1: Load dashboard
            print("📍 Step 1: Loading dashboard...")
            page.goto('http://localhost:8050', wait_until='domcontentloaded')
            time.sleep(3)
            print("   ✅ Dashboard loaded")
            
            # Step 2: Click Market Trends tab with retry
            print("\n📍 Step 2: Clicking Market Trends tab...")
            selectors = [
                '#tab-market_trends',
                '[id*="tab-market_trends"]',
                'div[id*="market_trends"] a',
                '.nav-item:has-text("Market Trends")',
                'a:has-text("Market Trends")'
            ]
            
            clicked = False
            for attempt in range(5):
                for selector in selectors:
                    try:
                        tab = page.locator(selector)
                        count = tab.count()
                        if count > 0:
                            print(f"   Found tab with selector: {selector} (count: {count}, attempt: {attempt+1})")
                            tab.first.click(timeout=3000)
                            clicked = True
                            print(f"   ✅ Tab clicked successfully")
                            break
                    except Exception as e:
                        print(f"   Selector {selector} failed: {str(e)[:100]}")
                
                if clicked:
                    break
                time.sleep(1)
            
            if not clicked:
                print("   ❌ FAILED: Could not click Market Trends tab")
                page.screenshot(path='test-artifacts/e2e_failed_no_tab.png', full_page=True)
                return
            
            # Wait for tab content to load
            time.sleep(4)
            
            # Step 3: Verify table rendered
            print("\n📍 Step 3: Verifying table rendered...")
            table = page.locator('table, [data-testid*="market-trends-table"]').first
            if table.count() > 0:
                is_visible = table.is_visible()
                rows = page.locator('table tbody tr').all()
                print(f"   ✅ Table found (visible: {is_visible})")
                print(f"   📊 Rows: {len(rows)}")
            else:
                print("   ⚠️  Table not found")
            
            page.screenshot(path='test-artifacts/e2e_after_tab_click.png', full_page=True)
            print("   📸 Screenshot saved: e2e_after_tab_click.png")
            
            # Step 4: Click Run Full Analysis button
            print("\n📍 Step 4: Clicking Run Full Analysis button...")
            run_selectors = [
                '#run-btn',
                'button:has-text("Run Full Analysis")',
                '[id*="run-btn"]',
                'button:has-text("Run Analysis")'
            ]
            
            run_clicked = False
            for selector in run_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0:
                        is_visible = btn.first.is_visible()
                        print(f"   Found button with selector: {selector} (visible: {is_visible})")
                        if is_visible:
                            btn.first.click(timeout=5000)
                            run_clicked = True
                            print(f"   ✅ Button clicked")
                            break
                        else:
                            print(f"   Button not visible yet")
                except Exception as e:
                    print(f"   Selector {selector} error: {str(e)[:80]}")
            
            if not run_clicked:
                print("   ⚠️  Could not click Run Full Analysis button")
                page.screenshot(path='test-artifacts/e2e_no_run_button.png', full_page=True)
            else:
                # Wait for analysis to complete
                print("\n📍 Step 5: Waiting for analysis to complete...")
                for i in range(60):
                    time.sleep(1)
                    
                    # Check for completion indicators
                    status = page.locator('#status, [id*="status"]').first
                    if status.count() > 0:
                        status_text = status.inner_text()
                        if 'complete' in status_text.lower() or 'success' in status_text.lower():
                            print(f"   ✅ Analysis completed at {i+1}s")
                            print(f"   Status: {status_text[:100]}")
                            break
                        elif i % 10 == 0 and i > 0:
                            print(f"   ⏱️  {i}s elapsed... Status: {status_text[:50]}")
                    
                    # Check if table updated
                    rows = page.locator('table tbody tr').all()
                    if len(rows) > 50:
                        print(f"   ✅ Table updated at {i+1}s (rows: {len(rows)})")
                        break
                
                time.sleep(2)
                
                # Step 6: Verify final state
                print("\n📍 Step 6: Verifying final state...")
                rows = page.locator('table tbody tr').all()
                print(f"   📊 Final row count: {len(rows)}")
                
                # Get top 5 tickers
                if len(rows) > 0:
                    print("   🎯 Top 5 tickers:")
                    for i in range(min(5, len(rows))):
                        try:
                            text = rows[i].inner_text()
                            ticker = text.split()[0] if text else "Unknown"
                            print(f"      {i+1}. {ticker}")
                        except:
                            pass
                
                page.screenshot(path='test-artifacts/e2e_after_analysis.png', full_page=True)
                print("   📸 Screenshot saved: e2e_after_analysis.png")
            
            # Step 7: Check cache file
            print("\n📍 Step 7: Checking cache file...")
            cache_paths = [
                'outputs/market_brief.json',
                '/app/outputs/market_brief.json',
                'financial_dashboard/outputs/market_brief.json'
            ]
            
            cache_found = False
            for cache_path in cache_paths:
                if os.path.exists(cache_path):
                    cache_found = True
                    print(f"   ✅ Cache file found: {cache_path}")
                    try:
                        with open(cache_path, 'r') as f:
                            cache_data = json.load(f)
                            print(f"   📦 Cache keys: {list(cache_data.keys())[:5]}")
                            if 'tickers' in cache_data:
                                print(f"   🎯 Cached tickers: {len(cache_data.get('tickers', []))}")
                    except Exception as e:
                        print(f"   ⚠️  Could not read cache: {e}")
                    break
            
            if not cache_found:
                print("   ⚠️  Cache file not found in any expected location")
            
            # Step 8: Summary
            print("\n📍 Step 8: API Call Summary...")
            print(f"   📞 Finnhub calls: {len(api_calls['finnhub'])}")
            print(f"   📞 Alpaca calls: {len(api_calls['alpaca'])}")
            
            if console_messages:
                print("\n   Console messages (last 10):")
                for msg in console_messages[-10:]:
                    print(f"      {msg[:120]}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='test-artifacts/e2e_error.png', full_page=True)
        
        finally:
            print("\n" + "=" * 80)
            print("TEST COMPLETE - Browser will close in 15 seconds")
            print("=" * 80)
            time.sleep(15)
            browser.close()

if __name__ == '__main__':
    main()
