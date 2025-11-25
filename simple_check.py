"""
Simple test - just check which Command Center is loaded
"""
import asyncio
from playwright.async_api import async_playwright

async def simple_check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("Loading dashboard...")
        try:
            await page.goto('http://localhost:8051', timeout=30000, wait_until='domcontentloaded')
            await page.wait_for_timeout(10000)
            
            text = await page.evaluate("() => document.body.innerText")
            
            print("\nChecking indicators...")
            print(f"Portfolio Summary (home.py): {'Portfolio Summary' in text}")
            print(f"Quick Query (command_center_pkg): {'Quick Query' in text}")
            
            await page.screenshot(path='/home/aarav/unified-dashboard/SIMPLE_check.png', full_page=True)
            print("\nScreenshot saved: SIMPLE_check.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(simple_check())
