"""
Deep debugging script for Market Trends first 3 rows size issue.
Checks: computed styles, cell content length, virtualization, data-specific issues.
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def deep_debug_market_trends():
    async with async_playwright() as p:
        # Launch browser with no cache to force fresh load
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            bypass_csp=True
        )
        page = await context.new_page()
        
        # Clear all cache and reload
        await context.clear_cookies()
        print("✓ Browser cache cleared")
        
        print("=" * 80)
        print("MARKET TRENDS ROW HEIGHT DEEP DEBUGGING")
        print("=" * 80)
        
        # Test both direct access and through unified dashboard
        test_scenarios = [
            ("Direct Access", "http://127.0.0.1:8050", None),
            ("Unified Dashboard", "http://127.0.0.1:8000", "trends")
        ]
        
        for scenario_name, url, tab_id in test_scenarios:
            print(f"\n{'=' * 80}")
            print(f"SCENARIO: {scenario_name}")
            print(f"{'=' * 80}\n")
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # Wait for React to finish loading
            try:
                await page.wait_for_selector('#react-entry-point', timeout=5000)
                print("✓ React entry point loaded")
                # Wait for Dash to initialize
                await asyncio.sleep(2)
            except:
                print("WARNING: React entry point not found")
            
            # If unified dashboard, click the tab
            if tab_id:
                print(f"Clicking {tab_id} tab...")
                await page.click(f'button[data-tab="{tab_id}"]')
                await asyncio.sleep(2)
                print("Waiting for iframe to load content...")
                await asyncio.sleep(5)
                
                # Get iframe
                iframe_elem = await page.query_selector(f'#{tab_id}-pane iframe')
                if not iframe_elem:
                    print("ERROR: Iframe not found!")
                    continue
                    
                frame = await iframe_elem.content_frame()
                if not frame:
                    print("ERROR: Iframe content not accessible!")
                    continue
                print("✓ Iframe loaded successfully")
            else:
                frame = page
            
            # Check if we need to click "Run Full Analysis" or "Refresh cached display"
            try:
                # First check if there's already cached results
                results_area = frame.locator('#results-area')
                if await results_area.count() > 0:
                    print("✓ Results area found")
                    results_text = await results_area.inner_text()
                    if 'Loaded cached results' in results_text or 'rows' in results_text.lower():
                        print("✓ Cached results already displayed")
                    else:
                        print("  Results area empty, need to trigger analysis...")
                        # Try clicking "Refresh cached display" button
                        refresh_btn = frame.locator('#refresh-cached')
                        if await refresh_btn.count() > 0:
                            print("  Clicking 'Refresh cached display'...")
                            await refresh_btn.click()
                            await asyncio.sleep(5)
                        else:
                            # Try "Run Full Analysis" button
                            run_btn = frame.locator('#run-btn')
                            if await run_btn.count() > 0:
                                print("  Clicking 'Run Full Analysis'...")
                                await run_btn.click()
                                await asyncio.sleep(10)
                
                # Wait for Dash loading to complete
                try:
                    loading = frame.locator('._dash-loading')
                    if await loading.count() > 0:
                        print("  Waiting for Dash to finish loading...")
                        await loading.wait_for(state='hidden', timeout=30000)
                        print("  ✓ Dash loading complete")
                except:
                    print("  No loading indicator or already loaded")
                
                # Then check for table
                await frame.wait_for_selector('#results-table-client', timeout=15000)
                print("✓ Table found in DOM")
            except Exception as e:
                print(f"ERROR: Table not found - {e}")
                # Try alternative selectors
                print("  Checking for alternative table selectors...")
                alt_tables = await frame.locator('table').count()
                print(f"  Found {alt_tables} table elements")
                
                datatable_count = await frame.locator('[class*="dash-table"]').count()
                print(f"  Found {datatable_count} dash-table elements")
                
                # Check results area content
                results_area = frame.locator('#results-area')
                if await results_area.count() > 0:
                    results_html = await results_area.inner_html()
                    print(f"  Results area HTML (first 500 chars): {results_html[:500]}")
                continue
            
            # Check if table is visible
            table_visible = await frame.locator('#results-table-client').is_visible()
            print(f"Table visible: {table_visible}")
            
            # Get table bounding box
            table = frame.locator('#results-table-client')
            table_box = await table.bounding_box()
            if table_box:
                print(f"Table dimensions: {table_box['width']:.0f}w × {table_box['height']:.0f}h")
            
            # Check all rows
            tbody = frame.locator('#results-table-client tbody')
            row_count = await tbody.locator('tr').count()
            print(f"\nTotal rows found: {row_count}")
            
            if row_count == 0:
                print("WARNING: No rows in table!")
                continue
            
            print("\n" + "-" * 80)
            print("ROW-BY-ROW ANALYSIS")
            print("-" * 80)
            
            for i in range(min(row_count, 10)):  # Check first 10 rows
                row = tbody.locator('tr').nth(i)
                
                # Check if row exists
                row_exists = await row.count() > 0
                if not row_exists:
                    print(f"\nRow {i}: NOT FOUND")
                    continue
                
                print(f"\n--- ROW {i} ---")
                
                # Get bounding box
                box = await row.bounding_box()
                if box:
                    print(f"  Height: {box['height']:.1f}px")
                    print(f"  Width: {box['width']:.1f}px")
                    print(f"  Y-position: {box['y']:.1f}px")
                    
                    # Flag abnormal heights
                    if box['height'] > 80:
                        print(f"  ⚠️  ABNORMAL HEIGHT DETECTED!")
                else:
                    print(f"  No bounding box (row may be virtual/offscreen)")
                
                # Get computed styles
                try:
                    height_style = await row.evaluate('el => window.getComputedStyle(el).height')
                    min_height_style = await row.evaluate('el => window.getComputedStyle(el).minHeight')
                    max_height_style = await row.evaluate('el => window.getComputedStyle(el).maxHeight')
                    display_style = await row.evaluate('el => window.getComputedStyle(el).display')
                    
                    print(f"  Computed Styles:")
                    print(f"    height: {height_style}")
                    print(f"    min-height: {min_height_style}")
                    print(f"    max-height: {max_height_style}")
                    print(f"    display: {display_style}")
                except Exception as e:
                    print(f"  Could not get computed styles: {e}")
                
                # Get cell count and content
                cells = row.locator('td')
                cell_count = await cells.count()
                print(f"  Cells: {cell_count}")
                
                # Check each cell's content
                for j in range(cell_count):
                    cell = cells.nth(j)
                    try:
                        text = await cell.inner_text()
                        text_preview = text[:50] + "..." if len(text) > 50 else text
                        print(f"    Cell {j}: '{text_preview}' (len={len(text)})")
                        
                        # Check if text is wrapping
                        cell_box = await cell.bounding_box()
                        if cell_box and cell_box['height'] > 60:
                            print(f"      ⚠️  Cell height {cell_box['height']:.1f}px - possible text wrapping!")
                            
                            # Get cell computed styles
                            white_space = await cell.evaluate('el => window.getComputedStyle(el).whiteSpace')
                            overflow = await cell.evaluate('el => window.getComputedStyle(el).overflow')
                            text_overflow = await cell.evaluate('el => window.getComputedStyle(el).textOverflow')
                            
                            print(f"      white-space: {white_space}")
                            print(f"      overflow: {overflow}")
                            print(f"      text-overflow: {text_overflow}")
                    except Exception as e:
                        print(f"    Cell {j}: Error reading - {e}")
                
                # Check for nested elements causing expansion
                try:
                    nested_divs = await row.locator('div').count()
                    if nested_divs > 0:
                        print(f"  ⚠️  Contains {nested_divs} nested div elements")
                        for k in range(min(nested_divs, 3)):
                            div = row.locator('div').nth(k)
                            div_box = await div.bounding_box()
                            if div_box:
                                print(f"    Div {k}: height={div_box['height']:.1f}px")
                except:
                    pass
            
            # Check CSS files loaded
            print("\n" + "-" * 80)
            print("CSS FILES LOADED")
            print("-" * 80)
            
            stylesheets = await frame.evaluate('''() => {
                return Array.from(document.styleSheets).map(sheet => {
                    try {
                        return sheet.href || 'inline';
                    } catch(e) {
                        return 'blocked';
                    }
                });
            }''')
            
            for css in stylesheets:
                if css and 'zz_ultimate_fix' in css:
                    print(f"  ✓ {css}")
                elif css and 'assets' in css:
                    print(f"  • {css}")
            
            # Check for conflicting CSS rules
            print("\n" + "-" * 80)
            print("CHECKING FOR CONFLICTING CSS RULES")
            print("-" * 80)
            
            first_row = tbody.locator('tr').nth(0)
            if await first_row.count() > 0:
                css_rules = await first_row.evaluate('''el => {
                    const styles = window.getComputedStyle(el);
                    return {
                        height: styles.height,
                        minHeight: styles.minHeight,
                        maxHeight: styles.maxHeight,
                        display: styles.display,
                        flexGrow: styles.flexGrow,
                        flexShrink: styles.flexShrink,
                        alignItems: styles.alignItems,
                        padding: styles.padding,
                        margin: styles.margin
                    };
                }''')
                
                print("  First row computed styles:")
                for key, value in css_rules.items():
                    if value and value != 'none' and value != 'normal' and value != '0px':
                        print(f"    {key}: {value}")
            
            # Take screenshot
            screenshot_name = f'debug_{scenario_name.lower().replace(" ", "_")}.png'
            await page.screenshot(path=screenshot_name, full_page=True)
            print(f"\n✓ Screenshot saved: {screenshot_name}")
            
            # Wait to observe
            print("\nWaiting 3 seconds for observation...")
            await asyncio.sleep(3)
        
        print("\n" + "=" * 80)
        print("DEBUG COMPLETE")
        print("=" * 80)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(deep_debug_market_trends())
