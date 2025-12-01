"""
Capture current Command Center state for analysis
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_current_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("=" * 80)
        print("CAPTURING CURRENT COMMAND CENTER STATE")
        print("=" * 80)
        
        # Load dashboard
        print("\n[1/3] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000, wait_until='domcontentloaded')
        await page.wait_for_timeout(8000)
        
        # Capture full page
        print("\n[2/3] Capturing screenshots...")
        await page.screenshot(path='/home/aarav/unified-dashboard/CURRENT_command_center_state.png', full_page=True)
        
        # Get page text for analysis
        page_text = await page.evaluate("() => document.body.innerText")
        
        # Analyze content
        print("\n[3/3] Analyzing current state...")
        print(f"\nPage content preview (first 2000 chars):")
        print(page_text[:2000])
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("SCREENSHOT SAVED: CURRENT_command_center_state.png")
        print("=" * 80)

if __name__ == '__main__':
    asyncio.run(capture_current_state())
