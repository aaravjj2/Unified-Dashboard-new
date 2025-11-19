"""
Comprehensive Playwright test for Market Trends table visibility.
Tests that table rows are actually rendered and visible after job completion.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
import sys
import os
import json
from datetime import datetime

async def test_market_trends_table():
    print(f"\n{'='*60}")
    print(f"Market Trends Table Visibility Test")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        # Launch browser in headed mode so we can see what's happening
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"BROWSER CONSOLE [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: print(f"BROWSER ERROR: {err}"))
        
        try:
            # Step 1: Navigate to dashboard
            print("Step 1: Loading dashboard...")
            await page.goto('http://127.0.0.1:8050', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            print("✓ Dashboard loaded")
            
            # Step 2: Click Market Trends tab
            print("\nStep 2: Navigating to Market Trends tab...")
            try:
                # Try multiple selectors to find the tab
                tab_selectors = [
                    'a[href="#trends"]',
                    'text=Market Trends',
                    '#tabs >> text=Market Trends',
                    '.nav-link:has-text("Market Trends")'
                ]
                
                clicked = False
                for selector in tab_selectors:
                    try:
                        await page.click(selector, timeout=5000)
                        clicked = True
                        print(f"✓ Clicked Market Trends tab using selector: {selector}")
                        break
                    except:
                        continue
                
                if not clicked:
                    print("✗ Could not find Market Trends tab, taking screenshot...")
                    await page.screenshot(path='_error_no_tab.png', full_page=True)
                    return False
                
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"✗ Failed to click Market Trends tab: {e}")
                await page.screenshot(path='_error_tab_click.png', full_page=True)
                return False
            
            # Step 3: Check initial state
            print("\nStep 3: Checking initial state...")
            await page.screenshot(path='_step3_initial_state.png', full_page=True)
            
            # Look for results table or cached data
            has_cached = await page.locator('#results-area').count() > 0
            print(f"  Results area exists: {has_cached}")
            
            # Check if there's a "Use cache only" checkbox and if it's checked
            cache_checkbox = page.locator('input[type="checkbox"][value="cache"]')
            if await cache_checkbox.count() > 0:
                is_checked = await cache_checkbox.is_checked()
                print(f"  'Use cache only' checkbox checked: {is_checked}")
                
                if not is_checked:
                    print("  Checking 'Use cache only' to speed up test...")
                    await cache_checkbox.check()
                    await asyncio.sleep(0.5)
            
            # Step 4: Click "Run Full Analysis"
            print("\nStep 4: Clicking 'Run Full Analysis' button...")
            try:
                run_btn = page.locator('#run-btn')
                if await run_btn.count() == 0:
                    print("✗ Run button not found!")
                    await page.screenshot(path='_error_no_run_btn.png', full_page=True)
                    return False
                
                await run_btn.click()
                print("✓ Clicked Run Full Analysis")
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"✗ Failed to click Run button: {e}")
                await page.screenshot(path='_error_run_click.png', full_page=True)
                return False
            
            # Step 5: Wait for job completion (poll status)
            print("\nStep 5: Waiting for job completion...")
            max_wait_seconds = 60
            poll_interval = 2
            elapsed = 0
            
            while elapsed < max_wait_seconds:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                
                # Check status div
                status_div = page.locator('#status')
                if await status_div.count() > 0:
                    status_text = await status_div.inner_text()
                    status_style = await status_div.get_attribute('style') or ''
                    
                    print(f"  [{elapsed}s] Status: {status_text[:60]}")
                    
                    # Check if completed (green background or "completed" text)
                    if 'completed' in status_text.lower() or 'background-color: green' in status_style.lower() or 'backgroundcolor: green' in status_style.lower():
                        print(f"✓ Job completed after {elapsed}s!")
                        await asyncio.sleep(2)  # Give time for results to render
                        break
                    
                    # Check if failed
                    if 'failed' in status_text.lower() or 'error' in status_text.lower():
                        print(f"✗ Job failed: {status_text}")
                        await page.screenshot(path='_error_job_failed.png', full_page=True)
                        return False
                
                # Check if results appeared even without status change
                results_area = page.locator('#results-area')
                if await results_area.count() > 0:
                    content = await results_area.inner_text()
                    if len(content) > 100:  # Has substantial content
                        print(f"✓ Results area populated after {elapsed}s")
                        break
            
            if elapsed >= max_wait_seconds:
                print(f"✗ Timeout after {max_wait_seconds}s waiting for completion")
                await page.screenshot(path='_error_timeout.png', full_page=True)
                return False
            
            # Step 6: Take post-completion screenshot
            print("\nStep 6: Taking post-completion screenshot...")
            await page.screenshot(path='market_trends_completed.png', full_page=True)
            print("✓ Screenshot saved: market_trends_completed.png")
            
            # Step 7: Analyze table visibility
            print("\nStep 7: Analyzing table structure and visibility...")
            
            # Check for various table selectors
            table_checks = {
                'DataTable': '#results-table-client',
                'DataTable container': '#trends-results-table-container',
                'Server-rendered table': '.market-trends-server-preview',
                'Results area': '#results-area',
                'Composite results': '#trends-composite-results',
                'Analysis Results header': 'text=Analysis Results'
            }
            
            found_elements = {}
            for name, selector in table_checks.items():
                count = await page.locator(selector).count()
                found_elements[name] = count
                print(f"  {name}: {count} element(s)")
            
            # Get results area HTML
            results_area = page.locator('#results-area')
            if await results_area.count() > 0:
                html_content = await results_area.inner_html()
                print(f"\n  Results area HTML length: {len(html_content)} chars")
                
                # Save HTML for inspection
                with open('_results_area_content.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"  ✓ Saved results HTML to _results_area_content.html")
                
                # Check for table rows
                row_count = html_content.count('<tr>') - html_content.count('<thead>')
                print(f"  Table rows found in HTML: {row_count}")
                
                # Check if DataTable has data
                datatable = page.locator('#results-table-client')
                if await datatable.count() > 0:
                    # Try to count visible rows
                    try:
                        visible_rows = await page.locator('#results-table-client tbody tr').count()
                        print(f"  DataTable visible rows: {visible_rows}")
                    except:
                        print(f"  DataTable visible rows: Could not count")
                
                # Check server-rendered table
                server_table = page.locator('.market-trends-server-preview table')
                if await server_table.count() > 0:
                    try:
                        server_rows = await page.locator('.market-trends-server-preview table tbody tr').count()
                        print(f"  Server-rendered table rows: {server_rows}")
                        
                        if server_rows > 0:
                            print(f"\n✓ SUCCESS: Server-rendered table has {server_rows} visible rows!")
                            
                            # Get a sample of the data
                            first_row = page.locator('.market-trends-server-preview table tbody tr').first
                            if await first_row.count() > 0:
                                row_text = await first_row.inner_text()
                                print(f"  Sample row data: {row_text[:100]}")
                            
                            return True
                    except Exception as e:
                        print(f"  Server-rendered table row check failed: {e}")
                
                # Check computed styles on DataTable
                if await datatable.count() > 0:
                    try:
                        display = await datatable.evaluate('el => window.getComputedStyle(el).display')
                        height = await datatable.evaluate('el => window.getComputedStyle(el).height')
                        overflow = await datatable.evaluate('el => window.getComputedStyle(el).overflow')
                        print(f"\n  DataTable computed styles:")
                        print(f"    display: {display}")
                        print(f"    height: {height}")
                        print(f"    overflow: {overflow}")
                        
                        # Check if rows are actually visible by checking first row
                        first_row = page.locator('#results-table-client tbody tr').first
                        if await first_row.count() > 0:
                            is_visible = await first_row.is_visible()
                            row_text = await first_row.inner_text()
                            print(f"\n  First DataTable row:")
                            print(f"    Visible: {is_visible}")
                            print(f"    Content: {row_text[:100]}")
                            
                            if is_visible and len(row_text) > 5:
                                print(f"\n✓ SUCCESS: DataTable has {row_count} rows and they are visible!")
                                return True
                    except Exception as e:
                        print(f"  Could not get computed styles: {e}")
                
                # If we have HTML content but no visible rows, that's the problem
                if row_count > 0:
                    print(f"\n⚠ WARNING: HTML contains {row_count} table rows, but visibility check failed.")
                    return False
            else:
                print("\n✗ Results area not found or empty!")
                return False
            
            print("\n✗ No visible table rows found")
            return False
            
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='_error_unexpected.png', full_page=True)
            return False
        
        finally:
            print(f"\nClosing browser...")
            await browser.close()

async def main():
    success = await test_market_trends_table()
    
    print(f"\n{'='*60}")
    if success:
        print("✓ TEST PASSED: Table is visible and has data!")
    else:
        print("✗ TEST FAILED: Table not visible or has issues")
    print(f"{'='*60}\n")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    asyncio.run(main())
