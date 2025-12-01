"""Direct test - navigate to Volatility Lab by clicking the nav tab"""
import asyncio
from playwright.async_api import async_playwright

async def test_quick_compute_direct():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        # Load dashboard
        print("Loading dashboard...")
        await page.goto("http://localhost:8050/", wait_until="networkidle")
        await asyncio.sleep(10)
        
        # Try clicking by nav link
        print("Looking for Volatility Lab nav link...")
        try:
            # Try different selectors
            nav_link = page.locator('a:has-text("⚡ Volatility Lab")').first
            if await nav_link.count() > 0:
                print("Found nav link with emoji...")
                await nav_link.click()
            else:
                nav_link = page.locator('a:has-text("Volatility Lab")').first
                print("Found nav link without emoji...")
                await nav_link.click()
                
            await asyncio.sleep(5)
            print("Clicked Volatility Lab tab")
        except Exception as e:
            print(f"Error clicking tab: {e}")
            await browser.close()
            return
        
        # Look for Quick Compute button by ID
        print("\nLooking for Quick Compute button...")
        quick_btn = page.locator('#vl-compute-quick-btn')
        if await quick_btn.count() == 0:
            print("❌ Quick Compute button not found!")
            await page.screenshot(path="no_quick_btn.png")
            await browser.close()
            return
        
        # Get initial ATM IV
        print("Reading initial ATM IV...")
        atm_iv_elem = page.locator('#vl-overview-atm-iv')
        initial_val = await atm_iv_elem.text_content()
        print(f"  Initial: '{initial_val}'")
        
        # Click Quick Compute
        print("\nClicking Quick Compute...")
        await quick_btn.click()
        await asyncio.sleep(10)  # Wait for callback to complete
        
        # Check for change
        final_val = await atm_iv_elem.text_content()
        print(f"  After click: '{final_val}'")
        
        if initial_val != final_val:
            print(f"\n✅ SUCCESS! ATM IV changed from '{initial_val}' to '{final_val}'")
        else:
            print(f"\n⚠️ NO CHANGE - ATM IV still '{initial_val}'")
            print("Checking console for errors...")
            
        await page.screenshot(path="quick_compute_final.png", full_page=True)
        print("\nScreenshot saved: quick_compute_final.png")
        
        # Check network activity
        print("\nWaiting to see network activity...")
        await asyncio.sleep(5)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_quick_compute_direct())
