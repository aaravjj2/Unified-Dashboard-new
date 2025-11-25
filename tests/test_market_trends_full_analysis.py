"""
Comprehensive browser-based clicker test for Market Trends tab.
Tests full analysis workflow with Finnhub fallback verification.
"""
import asyncio
import time
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def main():
    print("=" * 80)
    print("MARKET TRENDS FULL ANALYSIS - BROWSER CLICKER TEST")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    async with async_playwright() as p:
        # Launch browser with visible UI for debugging
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture console messages
        console_messages = []
        page.on('console', lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
        
        # Capture network requests
        api_calls = {'finnhub': [], 'yfinance': [], 'alpaca': []}
        
        def log_request(request):
            url = request.url
            if 'finnhub' in url:
                api_calls['finnhub'].append({'url': url, 'time': datetime.now()})
            elif 'alpaca' in url:
                api_calls['alpaca'].append({'url': url, 'time': datetime.now()})
        
        page.on('request', log_request)
        
        try:
            # Step 1: Navigate to dashboard
            print("📍 Step 1: Loading dashboard...")
            await page.goto('http://localhost:8050', wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            print("   ✅ Dashboard loaded")
            
            # Step 2: Click Market Trends tab
            print("\n📍 Step 2: Clicking Market Trends tab...")
            # Try stable id first, then fallback selectors
            selectors = ['#tab-market_trends', '[id*="tab-market_trends"]', 'a:has-text("Market Trends")']
            clicked = False
            for selector in selectors:
                tab = page.locator(selector)
                if await tab.count() > 0:
                    await tab.first.click()
                    clicked = True
                    print(f"   ✅ Tab clicked using selector: {selector}")
                    break
            if not clicked:
                print("   ⚠️  Could not find Market Trends tab")
            await page.wait_for_timeout(3000)
            print("   ✅ Waiting for tab activation...")
            
            # Step 3: Verify cached table appears
            print("\n📍 Step 3: Verifying cached table...")
            table = page.locator('table.market-trends-html-table, [data-test="market-trends-table"]').first
            if await table.count() > 0:
                is_visible = await table.is_visible()
                print(f"   ✅ Table found (visible: {is_visible})")
                
                # Count rows
                rows = page.locator('table tbody tr')
                row_count = await rows.count()
                print(f"   📊 Cached rows: {row_count}")
            else:
                print("   ⚠️  Table not found")
            
            # Take screenshot of cached state
            await page.screenshot(path='test-artifacts/market_trends_cached.png', full_page=True)
            print("   📸 Screenshot saved: market_trends_cached.png")
            
            # Step 4: Run full analysis
            print("\n📍 Step 4: Running full analysis...")
            run_button = page.locator('button:has-text("Run Full Analysis"), #run-analysis-btn')
            
            if await run_button.count() > 0:
                print("   🔘 Clicking Run Full Analysis button...")
                await run_button.first.click()
                print("   ⏳ Waiting for analysis to complete (60s timeout)...")
                
                # Wait for status message to show completion
                status_shown = False
                for i in range(60):
                    await page.wait_for_timeout(1000)
                    
                    # Check for completion indicators
                    status_area = page.locator('#status-message, [data-testid="status-message"]')
                    if await status_area.count() > 0:
                        status_text = await status_area.first.inner_text()
                        if 'complete' in status_text.lower() or 'success' in status_text.lower():
                            print(f"   ✅ Analysis completed at {i+1}s")
                            print(f"   📋 Status: {status_text[:100]}")
                            status_shown = True
                            break
                        elif i % 10 == 0:
                            print(f"   ⏱️  {i}s elapsed... Status: {status_text[:50]}")
                    
                    # Check if table has updated
                    rows = page.locator('table tbody tr')
                    if await rows.count() > 0:
                        first_row = await rows.first.inner_text()
                        if 'TSLA' in first_row or 'AAPL' in first_row:
                            print(f"   ✅ Table updated at {i+1}s")
                            break
                
                if not status_shown:
                    print("   ⚠️  Analysis may still be running (timeout reached)")
            else:
                print("   ⚠️  Run button not found")
            
            # Step 5: Wait for table to update
            print("\n📍 Step 5: Verifying table updated...")
            await page.wait_for_timeout(3000)
            
            rows = page.locator('table tbody tr')
            final_row_count = await rows.count()
            print(f"   📊 Final row count: {final_row_count}")
            
            # Extract ticker symbols
            if final_row_count > 0:
                print("   🎯 Tickers found:")
                for i in range(min(5, final_row_count)):
                    row = rows.nth(i)
                    text = await row.inner_text()
                    ticker = text.split()[0] if text else "Unknown"
                    print(f"      {i+1}. {ticker}")
            
            # Take final screenshot
            await page.screenshot(path='test-artifacts/market_trends_final.png', full_page=True)
            print("   📸 Screenshot saved: market_trends_final.png")
            
            # Step 6: Verify data sources
            print("\n📍 Step 6: Checking data sources...")
            
            # Check status indicators for price sources
            results_area = page.locator('#results-area')
            if await results_area.count() > 0:
                html = await results_area.first.inner_html()
                
                if 'yfinance' in html.lower():
                    print("   ✅ yfinance fallback used")
                if 'alpaca' in html.lower():
                    print("   ✅ Alpaca used")
                if 'finnhub' in html.lower():
                    print("   ✅ Finnhub used")
            
            # Step 7: API call summary
            print("\n📍 Step 7: API Call Summary...")
            print(f"   📞 Finnhub calls: {len(api_calls['finnhub'])}")
            print(f"   📞 Alpaca calls: {len(api_calls['alpaca'])}")
            
            # Check for errors in console
            errors = [msg for msg in console_messages if 'error' in msg.lower()]
            if errors:
                print(f"\n   ⚠️  Console errors: {len(errors)}")
                for err in errors[:3]:
                    print(f"      {err[:100]}")
            
            # Step 8: Final verification
            print("\n📍 Step 8: Final Verification...")
            
            # Check table is visible
            table = page.locator('table.market-trends-html-table, [data-test="market-trends-table"]').first
            if await table.count() > 0 and await table.is_visible():
                print("   ✅ Table is visible")
            else:
                print("   ❌ Table is NOT visible")
            
            # Check for loading spinners stuck
            spinner = page.locator('.loading, [class*="spinner"]')
            if await spinner.count() > 0:
                print("   ⚠️  Loading spinner still present")
            else:
                print("   ✅ No stuck loading spinners")
            
            # Check for news panel
            news_panel = page.locator('[data-testid="news-panel"]')
            if await news_panel.count() > 0:
                news_items = page.locator('[data-testid="news-panel"] > div')
                news_count = await news_items.count()
                print(f"   ✅ News panel found ({news_count} items)")
            else:
                print("   ⚠️  News panel not found")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Keep browser open for manual inspection
            print("\n" + "=" * 80)
            print("TEST COMPLETE - Browser will close in 10 seconds")
            print("=" * 80)
            await page.wait_for_timeout(10000)
            
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
