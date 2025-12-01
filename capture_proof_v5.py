"""
Capture proof screenshots for TradingView, Recent Trades, and Volatility Lab Fix (v5)
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("CAPTURING PROOF SCREENSHOTS (v5)")
        print("=" * 80)
        
        # 1. Command Center (TradingView + Recent Trades)
        print("\n[1/2] Capturing Command Center (TradingView + Trades)...")
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(10000) # Wait for TradingView and Trades to load
            
            # Scroll down to see Recent Trades if needed
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_TradingView_Trades.png', full_page=True)
            print("✓ Saved FINAL_TradingView_Trades.png")
        except Exception as e:
            print(f"Error capturing Command Center: {e}")
        
        # 2. Volatility Lab (Demo Data)
        print("\n[2/2] Capturing Volatility Lab (Demo Data)...")
        try:
            # Click sidebar link
            await page.click('text=Volatility Lab', timeout=10000)
            await page.wait_for_timeout(5000)
            
            # Click Compute Button to trigger demo data
            print("Clicking 'Compute' button...")
            # Try to find button by text or ID. Based on callbacks, ID is likely 'calc-run-btn'
            # But let's try text "Compute Surface" or similar if ID fails
            try:
                await page.click('#calc-run-btn', timeout=5000)
            except:
                await page.click('button:has-text("Compute")', timeout=5000)
                
            await page.wait_for_timeout(5000) # Wait for demo data to render
            
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_Volatility_Lab_Demo.png', full_page=True)
            print("✓ Saved FINAL_Volatility_Lab_Demo.png")
        except Exception as e:
            print(f"Error capturing Volatility Lab: {e}")
            
        await browser.close()
        print("\nDone!")

if __name__ == '__main__':
    asyncio.run(capture_proof())
