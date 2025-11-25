"""
Capture ACTUAL Current State Screenshots  
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_current_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("CAPTURING ACTUAL CURRENT STATE")  
        print("=" * 80)
        
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(15000)  # Wait longer for TradingView
            
            # 1. Command Center  
            print("\n[1] Capturing Command Center CURRENT STATE...")
            await page.screenshot(path='/home/aarav/unified-dashboard/ACTUAL_CommandCenter.png', full_page=True)
            print("✓ Saved ACTUAL_CommandCenter.png")
            
            # 2. Navigate to Vol Lab
            try:
                await page.click('text=Volatility Lab', timeout=10000)
                await page.wait_for_timeout(5000)
                
                # Try IV Surface tab - click Compute
                await page.click('#volatility-lab-tabs >> text=IV Surface', timeout=5000)
                await page.wait_for_timeout(2000)
                
                # Check if compute button exists
                if await page.is_visible('#vl-calc-run-btn'):
                    print("\n[2] Clicking Compute button...")
                    await page.click('#vl-calc-run-btn')
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path='/home/aarav/unified-dashboard/ACTUAL_VolLab_Surface.png', full_page=True)
                    print("✓ Saved ACTUAL_VolLab_Surface.png")
                else:
                    print("❌ Compute button not found")
                    
            except Exception as e:
                print(f"Vol Lab navigation error: {e}")
                
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()
        print("\nDone!")

if __name__ == '__main__':
    asyncio.run(capture_current_state())
