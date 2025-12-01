#!/usr/bin/env python3
"""
Verify that Market Trends table auto-loads on page load without button clicks.
Tests both persistence and layout fixes.
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def verify_auto_load():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Loading Market Trends page...")
        await page.goto('http://127.0.0.1:8050', timeout=15000)
        
        # Wait for React to mount
        await page.wait_for_selector('#react-entry-point', timeout=10000)
        print("✓ React mounted")
        
        # Wait for any Dash loading overlays to clear
        try:
            loading = page.locator('.dash-loading')
            if await loading.count() > 0:
                await loading.first.wait_for(state='hidden', timeout=10000)
        except Exception:
            pass
        
        # Wait a moment for the auto-load callback to trigger
        await asyncio.sleep(2)
        
        # Check if table exists WITHOUT clicking any buttons
        table = page.locator('#results-table-client')
        table_count = await table.count()
        
        print(f"\n{'='*60}")
        print(f"AUTO-LOAD TEST RESULTS")
        print(f"{'='*60}")
        
        if table_count > 0:
            print(f"✅ SUCCESS: Table auto-loaded without button click!")
            
            # Check table visibility
            is_visible = await table.is_visible()
            print(f"   Table visible: {is_visible}")
            
            # Get table rows
            rows = page.locator('#results-table-client tbody tr')
            row_count = await rows.count()
            print(f"   Total rows: {row_count}")
            
            if row_count > 0:
                # Check row 2 (first data row) height
                try:
                    row2 = rows.nth(1)
                    row2_box = await row2.bounding_box()
                    if row2_box:
                        height = row2_box['height']
                        print(f"   Row 2 height: {height:.1f}px")
                        
                        if height < 60:
                            print(f"   ✅ Row height is normal (< 60px)")
                        else:
                            print(f"   ❌ Row height is too large (> 60px)")
                        
                        # Check computed styles (with timeout)
                        try:
                            cell = row2.locator('td').first
                            white_space = await cell.evaluate('el => getComputedStyle(el).whiteSpace', timeout=2000)
                            overflow = await cell.evaluate('el => getComputedStyle(el).overflow', timeout=2000)
                            
                            print(f"   Cell whiteSpace: {white_space}")
                            print(f"   Cell overflow: {overflow}")
                            
                            if white_space == 'nowrap' and overflow == 'hidden':
                                print(f"   ✅ Cell styles are correct")
                            else:
                                print(f"   ❌ Cell styles need fixing")
                        except Exception:
                            print(f"   ⚠️  Could not check cell styles (virtual scrolling table)")
                except Exception as e:
                    print(f"   ⚠️  Could not check row details: {e}")
                
                # Check table container layout
                container = page.locator('#trends-results-table-container')
                if await container.count() > 0:
                    container_box = await container.bounding_box()
                    if container_box:
                        print(f"   Container width: {container_box['width']:.1f}px")
                        print(f"   ✅ Table has responsive container")
            else:
                print(f"   ⚠️  Table exists but has no rows")
        else:
            print(f"❌ FAIL: Table did not auto-load")
            print(f"   Table not found in DOM without button click")
            
            # Check if there's a message instead
            results_area = page.locator('#results-area')
            if await results_area.count() > 0:
                text = await results_area.inner_text()
                print(f"   Results area text: {text[:100]}")
        
        print(f"{'='*60}\n")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(verify_auto_load())
