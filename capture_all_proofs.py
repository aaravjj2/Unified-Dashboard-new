"""
Capture Final Proofs: TradingView + Vol Lab + Research Lab
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_all_proofs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("FINAL PROOF CAPTURE")
        print("=" * 80)
        
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(12000)  # Wait longer for TradingView to load
            
            # 1. Capture Command Center with TradingView
            print("\n[1] Capturing Command Center with TradingView...")
            await page.screenshot(path='/home/aarav/unified-dashboard/PROOF_TradingView_Fixed.png', full_page=True)
            print("✓ Saved PROOF_TradingView_Fixed.png")
            
            # 2. Navigate to Research Lab
            print("\n[2] Navigating to Research Lab...")
            await page.click('text=Research Lab', timeout=10000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path='/home/aarav/unified-dashboard/PROOF_ResearchLab_Overview.png', full_page=True)
            print("✓ Saved PROOF_ResearchLab_Overview.png")
            
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()
        print("\nDone!")

if __name__ == '__main__':
    asyncio.run(capture_all_proofs())
