"""Quick test to check if row height fix is applied"""
import asyncio
from playwright.async_api import async_playwright

async def quick_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Loading Market Trends...")
        await page.goto('http://127.0.0.1:8050', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(5)
        
        # Click refresh cached display
        try:
            await page.click('#refresh-cached', timeout=5000)
            print("Clicked refresh button")
            await asyncio.sleep(7)
        except:
            print("Refresh button not found or not clickable")
        
        # Check if table exists
        table = page.locator('#results-table-client')
        if await table.count() > 0:
            print("✓ Table found")
            
            # Get first data row (skip header rows)
            tbody = page.locator('#results-table-client tbody tr')
            row_count = await tbody.count()
            print(f"Total rows: {row_count}")
            
            if row_count >= 3:
                # Check row 2 (first data row often has issues)
                row2 = tbody.nth(2)
                box = await row2.bounding_box()
                if box:
                    height = box['height']
                    print(f"Row 2 height: {height}px")
                    
                    if height > 80:
                        print("❌ FAIL: Row still too tall")
                        # Check first cell style
                        cell = row2.locator('td').first
                        if await cell.count() > 0:
                            ws = await cell.evaluate('el => window.getComputedStyle(el).whiteSpace')
                            of = await cell.evaluate('el => window.getComputedStyle(el).overflow')
                            print(f"  Cell whiteSpace: {ws}")
                            print(f"  Cell overflow: {of}")
                    else:
                        print("✅ PASS: Row height is normal")
                else:
                    print("Could not get row bounding box")
        else:
            print("❌ Table not found")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(quick_test())
