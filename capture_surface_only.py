"""
Capture IV Surface Only (Retry)
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("CAPTURING IV SURFACE (RETRY)")
        print("=" * 80)
        
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Navigate to Vol Lab
            print("Navigating to Vol Lab...")
            await page.click('text=Volatility Lab', timeout=10000)
            await page.wait_for_timeout(5000)
            
            # Click IV Surface Tab
            print("Clicking IV Surface Tab...")
            # Try finding the tab link specifically
            # dbc.Tabs renders as <ul> with <li><a>...</a></li>
            # The text "IV Surface" is inside the <a>
            await page.click('#volatility-lab-tabs a:has-text("IV Surface")', timeout=5000)
            await page.wait_for_timeout(3000)
            
            # Check if button is visible
            print("Checking for Compute button...")
            if await page.is_visible('#calc-run-btn'):
                print("Button found! Clicking...")
                await page.click('#calc-run-btn')
                await page.wait_for_timeout(5000)
                await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_VolLab_Surface.png', full_page=True)
                print("✓ Saved FINAL_VolLab_Surface.png")
            else:
                print("❌ Button NOT found. Dumping page content...")
                # await page.screenshot(path='/home/aarav/unified-dashboard/DEBUG_Surface_Fail.png', full_page=True)
                
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_proof())
