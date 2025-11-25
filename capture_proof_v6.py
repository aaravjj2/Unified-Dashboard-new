"""
Capture proof screenshots for Volatility Lab Overhaul and TradingView Fix (v6)
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("CAPTURING PROOF SCREENSHOTS (v6)")
        print("=" * 80)
        
        # 1. Command Center (TradingView Fixed)
        print("\n[1/5] Capturing Command Center (TradingView)...")
        try:
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(10000) # Wait for TradingView to load
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_TradingView_Fixed.png', full_page=True)
            print("✓ Saved FINAL_TradingView_Fixed.png")
        except Exception as e:
            print(f"Error capturing Command Center: {e}")
        
        # Navigate to Volatility Lab
        print("\nNavigating to Volatility Lab...")
        try:
            await page.click('text=Volatility Lab', timeout=10000)
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Error navigating to Vol Lab: {e}")
            
        # 2. Tab 1: Overview
        print("\n[2/5] Capturing Vol Lab - Overview...")
        try:
            # Scope click to the tabs container to avoid sidebar conflict
            await page.click('#volatility-lab-tabs >> text=Overview', timeout=5000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_VolLab_Overview.png', full_page=True)
            print("✓ Saved FINAL_VolLab_Overview.png")
        except Exception as e:
            print(f"Error capturing Overview: {e}")

        # 3. Tab 2: IV Surface (Compute)
        print("\n[3/5] Capturing Vol Lab - IV Surface...")
        try:
            await page.click('#volatility-lab-tabs >> text=IV Surface', timeout=5000)
            await page.wait_for_timeout(2000)
            
            # Click Compute
            print("Clicking Compute Surface...")
            await page.wait_for_selector('#calc-run-btn', state='visible', timeout=5000)
            await page.click('#calc-run-btn')
            await page.wait_for_timeout(5000) # Wait for demo data
            
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_VolLab_Surface.png', full_page=True)
            print("✓ Saved FINAL_VolLab_Surface.png")
        except Exception as e:
            print(f"Error capturing IV Surface: {e}")

        # 4. Tab 3: Signals
        print("\n[4/5] Capturing Vol Lab - Signals...")
        try:
            await page.click('#volatility-lab-tabs >> text=Signals & Backtest', timeout=5000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_VolLab_Signals.png', full_page=True)
            print("✓ Saved FINAL_VolLab_Signals.png")
        except Exception as e:
            print(f"Error capturing Signals: {e}")

        # 5. Tab 4: Diagnostics
        print("\n[5/5] Capturing Vol Lab - Diagnostics...")
        try:
            await page.click('#volatility-lab-tabs >> text=Diagnostics', timeout=5000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_VolLab_Diagnostics.png', full_page=True)
            print("✓ Saved FINAL_VolLab_Diagnostics.png")
        except Exception as e:
            print(f"Error capturing Diagnostics: {e}")
            
        await browser.close()
        print("\nDone!")

if __name__ == '__main__':
    asyncio.run(capture_proof())
