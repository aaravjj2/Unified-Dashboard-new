"""
Capture Proof: Volatility Lab Functionality
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_vollab_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("VOL LAB FUNCTIONALITY PROOF")
        print("=" * 80)
        
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Navigate to Vol Lab
            print("\n[1] Navigating to Volatility Lab...")
            await page.click('text=Volatility Lab', timeout=10000)
            await page.wait_for_timeout(5000)
            
            # Go to IV Surface tab
            print("\n[2] Clicking IV Surface tab...")
            await page.click('#volatility-lab-tabs >> text=IV Surface', timeout=5000)
            await page.wait_for_timeout(3000)
            
            # Click Compute button
            print("\n[3] Clicking Compute Surface button...")
            if await page.is_visible('#vl-calc-run-btn'):
                await page.click('#vl-calc-run-btn')
                await page.wait_for_timeout(5000)
                await page.screenshot(path='/home/aarav/unified-dashboard/PROOF_VolLab_Compute.png', full_page=True)
                print("✓ Saved PROOF_VolLab_Compute.png")
            else:
                print("❌ Compute button not found!")
            
            # Go to Signals tab
            print("\n[4] Clicking Signals & Backtest tab...")
            await page.click('#volatility-lab-tabs >> text=Signals & Backtest', timeout=5000)
            await page.wait_for_timeout(3000)
            
            # Click Scan Signals button
            print("\n[5] Clicking Scan Signals button...")
            if await page.is_visible('#vl-signal-run-btn'):
                await page.click('#vl-signal-run-btn')
                await page.wait_for_timeout(3000)
                await page.screenshot(path='/home/aarav/unified-dashboard/PROOF_VolLab_Signals.png', full_page=True)
                print("✓ Saved PROOF_VolLab_Signals.png")
            else:
                print("❌ Scan Signals button not found!")
            
            # Click Run Backtest button
            print("\n[6] Clicking Run Backtest button...")
            if await page.is_visible('#vl-backtest-run-btn'):
                await page.click('#vl-backtest-run-btn')
                await page.wait_for_timeout(3000)
                await page.screenshot(path='/home/aarav/unified-dashboard/PROOF_VolLab_Backtest.png', full_page=True)
                print("✓ Saved PROOF_VolLab_Backtest.png")
            else:
                print("❌ Run Backtest button not found!")
                
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()
        print("\nDone!")

if __name__ == '__main__':
    asyncio.run(capture_vollab_proof())
