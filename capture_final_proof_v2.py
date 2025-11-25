"""
Capture final proof screenshots for Command Center and Volatility Lab
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_final_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("CAPTURING FINAL PROOF SCREENSHOTS")
        print("=" * 80)
        
        # 1. Command Center
        print("\n[1/2] Capturing Command Center...")
        await page.goto('http://localhost:8051', timeout=30000, wait_until='networkidle')
        await page.wait_for_timeout(5000) # Wait for animations
        await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_Command_Center.png', full_page=True)
        print("✓ Saved FINAL_Command_Center.png")
        
        # 2. Volatility Lab
        print("\n[2/2] Capturing Volatility Lab...")
        # Click sidebar link
        await page.click('a[href="/volatility-lab"]')
        await page.wait_for_timeout(5000) # Wait for data load
        await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_Volatility_Lab.png', full_page=True)
        print("✓ Saved FINAL_Volatility_Lab.png")
        
        await browser.close()
        print("\nDone!")

if __name__ == '__main__':
    asyncio.run(capture_final_proof())
