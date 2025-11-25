"""
Capture final proof screenshots for Command Center and Volatility Lab (Retry)
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_final_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("CAPTURING FINAL PROOF SCREENSHOTS (RETRY)")
        print("=" * 80)
        
        # 1. Command Center
        print("\n[1/2] Capturing Command Center...")
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(10000) # Wait for charts and animations
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_Command_Center.png', full_page=True)
            print("✓ Saved FINAL_Command_Center.png")
        except Exception as e:
            print(f"Error capturing Command Center: {e}")
        
        # 2. Volatility Lab
        print("\n[2/2] Capturing Volatility Lab...")
        try:
            # Click sidebar link
            await page.click('a[href="/volatility-lab"]')
            await page.wait_for_timeout(10000) # Wait for data load
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_Volatility_Lab.png', full_page=True)
            print("✓ Saved FINAL_Volatility_Lab.png")
        except Exception as e:
            print(f"Error capturing Volatility Lab: {e}")
            
        await browser.close()
        print("\nDone!")

if __name__ == '__main__':
    asyncio.run(capture_final_proof())
