"""Test Quick Compute button functionality after callback fix"""
import asyncio
from playwright.async_api import async_playwright

async def test_quick_compute():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Navigate to dashboard
        print("Loading dashboard...")
        await page.goto("http://localhost:8050/", wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Navigate to Volatility Lab
        print("Clicking Volatility Lab tab...")
        await page.click('button:has-text("Volatility Lab")')
        await asyncio.sleep(5)
        
        # Capture initial state
        print("Capturing initial state...")
        initial_atm_iv = await page.locator('#vl-overview-atm-iv').text_content()
        print(f"  Initial ATM IV: {initial_atm_iv}")
        
        # Click Quick Compute button
        print("Clicking Quick Compute button...")
        await page.click('#vl-compute-quick-btn')
        await asyncio.sleep(5)
        
        # Capture after state
        print("Capturing after-click state...")
        after_atm_iv = await page.locator('#vl-overview-atm-iv').text_content()
        print(f"  After-click ATM IV: {after_atm_iv}")
        
        # Check for change
        if initial_atm_iv != after_atm_iv:
            print(f"✅ SUCCESS: ATM IV changed from '{initial_atm_iv}' to '{after_atm_iv}'")
        else:
            print(f"⚠️ NO CHANGE: ATM IV still '{initial_atm_iv}'")
            
        # Check browser console for errors
        print("\nBrowser console logs:")
        page.on("console", lambda msg: print(f"  {msg.type}: {msg.text}"))
        
        # Take screenshot
        await page.screenshot(path="quick_compute_test.png")
        print("\nScreenshot saved: quick_compute_test.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_quick_compute())
