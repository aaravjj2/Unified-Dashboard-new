"""
Verify Volatility Lab HTML Content
"""
import asyncio
from playwright.async_api import async_playwright

async def verify_content():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to dashboard...")
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            print("Navigating to Volatility Lab...")
            await page.click('text=Volatility Lab', timeout=10000)
            await page.wait_for_timeout(5000)
            
            # Dump HTML
            content = await page.content()
            
            # Check for new elements
            if "Glass Cards" in content or "Market Regime" in content or "High Volatility" in content:
                print("✓ SUCCESS: New Volatility Lab content detected!")
            else:
                print("❌ FAILURE: Old content detected or new content missing.")
                # Print snippet
                print("Snippet of content:")
                print(content[:1000])
                
            # Check for TradingView
            if "tradingview-widget-container" in content:
                 print("✓ SUCCESS: TradingView widget container detected!")
            else:
                 print("❌ FAILURE: TradingView widget missing.")

            await page.screenshot(path='/home/aarav/unified-dashboard/DEBUG_VolLab_Content.png', full_page=True)
            print("Saved DEBUG_VolLab_Content.png")
            
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(verify_content())
