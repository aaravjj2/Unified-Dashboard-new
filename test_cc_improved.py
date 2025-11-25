"""
Test improved Command Center with real market chart
"""
import asyncio
from playwright.async_api import async_playwright

async def test_improved_cc():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("=" * 80)
        print("TESTING IMPROVED COMMAND CENTER")
        print("=" * 80)
        
        print("\n[1/3] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=20000, wait_until='domcontentloaded')
        await page.wait_for_timeout(10000)  # Wait for chart to load
        
        print("\n[2/3] Capturing screenshots...")
        await page.screenshot(path='/home/aarav/unified-dashboard/CC_IMPROVED_full.png', full_page=True)
        await page.screenshot(path='/home/aarav/unified-dashboard/CC_IMPROVED_top.png', clip={' x': 0, 'y': 0, 'width': 1920, 'height': 800})
        
        print("\n[3/3] Analyzing improvements...")
        text = await page.evaluate("() => document.body.innerText")
        
        # Check for glassmorphism loading
        has_market_data = "S&P 500" in text or "$" in text[:500]
        print(f"  ✓ Market data present: {has_market_data}")
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("SCREENSHOTS SAVED")
        print("=" * 80)
        print("  - CC_IMPROVED_full.png")
        print("  - CC_IMPROVED_top.png")

if __name__ == '__main__':
    asyncio.run(test_improved_cc())
