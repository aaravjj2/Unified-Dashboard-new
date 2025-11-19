"""Test by running fresh analysis instead of cached"""
import asyncio
from playwright.async_api import async_playwright

async def test_fresh_run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Loading Market Trends...")
        await page.goto('http://127.0.0.1:8050', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(4)
        
        # Click "Run Full Analysis" to generate fresh table
        try:
            await page.click('#run-btn', timeout=5000)
            print("Clicked 'Run Full Analysis' button")
            await asyncio.sleep(15)  # Wait for analysis to complete
        except Exception as e:
            print(f"Could not click run button: {e}")
        
        # Check if table exists
        table = page.locator('#results-table-client')
        if await table.count() > 0:
            print("✓ Table found")
            
            tbody = page.locator('#results-table-client tbody tr')
            row_count = await tbody.count()
            print(f"Total rows: {row_count}")
            
            if row_count >= 3:
                row2 = tbody.nth(2)
                box = await row2.bounding_box()
                if box:
                    height = box['height']
                    print(f"Row 2 height: {height}px")
                    
                    if height > 80:
                        print("❌ FAIL: Row still too tall after fresh run")
                        cell = row2.locator('td').first
                        if await cell.count() > 0:
                            ws = await cell.evaluate('el => window.getComputedStyle(el).whiteSpace')
                            of = await cell.evaluate('el => window.getComputedStyle(el).overflow')
                            to = await cell.evaluate('el => window.getComputedStyle(el).textOverflow')
                            print(f"  Cell whiteSpace: {ws}")
                            print(f"  Cell overflow: {of}")
                            print(f"  Cell textOverflow: {to}")
                    else:
                        print("✅ PASS: Row height is normal after fresh run")
        else:
            print("❌ Table not found after analysis")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_fresh_run())
