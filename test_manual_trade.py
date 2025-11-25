"""Test Manual Trade P&L and Order Submission"""
import asyncio
from playwright.async_api import async_playwright

async def test_manual_trade():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        print("Loading dashboard...")
        await page.goto("http://localhost:8050/", wait_until="networkidle")
        await asyncio.sleep(10)
        
        # Navigate to Options Lab
        print("\nNavigating to Options Lab...")
        await page.click('a:has-text("Options Lab")')
        await asyncio.sleep(5)
        
        # Load options chain
        print("\nLoading SPY options chain...")
        ticker_input = page.locator('#options-ticker-input')
        await ticker_input.fill('SPY')
        await page.click('#options-load-btn')
        await asyncio.sleep(10)  # Wait for chain to load
        
        # Check status message
        status = await page.locator('#options-status-message').text_content()
        print(f"Chain load status: {status}")
        
        # Navigate to Manual Trade subtab
        print("\nClicking Manual Trade subtab...")
        try:
            # Try different selectors for the Manual Trade tab
            await page.click('button:has-text("Manual Trade")', timeout=5000)
        except:
            try:
                await page.click('a:has-text("Manual Trade")', timeout=5000)
            except:
                print("⚠️ Could not find Manual Trade tab button")
                tabs = await page.locator('button, a').all_text_contents()
                print(f"Available tabs: {[t for t in tabs[:30] if t.strip()]}")
                await browser.close()
                return
        
        await asyncio.sleep(3)
        print("✓ Opened Manual Trade")
        
        # TEST 1: Check if dropdowns are populated
        print("\n" + "="*60)
        print("TEST 1: Dropdown Population")
        print("="*60)
        
        exp_dropdown = page.locator('#sim-expiration-dropdown')
        strike_dropdown = page.locator('#sim-strike-dropdown')
        
        # Click expiration dropdown to see options
        if await exp_dropdown.count() > 0:
            await exp_dropdown.click()
            await asyncio.sleep(1)
            
            # Get the dropdown options
            exp_text = await exp_dropdown.text_content()
            print(f"Expiration dropdown content: {exp_text[:100]}")
            
            # Try to select first option
            try:
                await page.click('div[role="option"]', timeout=2000)
                print("✓ Selected an expiration")
                await asyncio.sleep(2)
            except:
                print("⚠️ No expiration options available")
        else:
            print("❌ Expiration dropdown not found")
        
        # Check strike dropdown
        if await strike_dropdown.count() > 0:
            strike_text = await strike_dropdown.text_content()
            print(f"Strike dropdown content: {strike_text[:100]}")
        else:
            print("❌ Strike dropdown not found")
        
        # TEST 2: Calculate P&L
        print("\n" + "="*60)
        print("TEST 2: P&L Calculation")
        print("="*60)
        
        calc_btn = page.locator('#sim-calculate-btn')
        if await calc_btn.count() > 0:
            print("Clicking Calculate P&L button...")
            
            # Get initial values
            max_profit_initial = await page.locator('#sim-max-profit').text_content()
            max_loss_initial = await page.locator('#sim-max-loss').text_content()
            breakeven_initial = await page.locator('#sim-breakeven').text_content()
            
            print(f"Before click: Profit={max_profit_initial}, Loss={max_loss_initial}, BE={breakeven_initial}")
            
            await calc_btn.click()
            await asyncio.sleep(5)
            
            # Get final values
            max_profit_final = await page.locator('#sim-max-profit').text_content()
            max_loss_final = await page.locator('#sim-max-loss').text_content()
            breakeven_final = await page.locator('#sim-breakeven').text_content()
            
            print(f"After click: Profit={max_profit_final}, Loss={max_loss_final}, BE={breakeven_final}")
            
            if max_profit_initial != max_profit_final or max_loss_initial != max_loss_final:
                print("✅ P&L values updated")
            else:
                print("⚠️ P&L values unchanged (likely no contract selected)")
        else:
            print("❌ Calculate button not found")
        
        # TEST 3: Submit Paper Order
        print("\n" + "="*60)
        print("TEST 3: Paper Order Submission")
        print("="*60)
        
        order_btn = page.locator('#sim-order-submit-btn')
        if await order_btn.count() > 0:
            print("Clicking Submit Paper Order button...")
            
            await order_btn.click()
            await asyncio.sleep(3)
            
            # Check confirmation
            confirmation = page.locator('#sim-order-confirmation')
            if await confirmation.count() > 0:
                conf_text = await confirmation.text_content()
                print(f"Order confirmation: {conf_text[:200]}")
                
                if "MOCK" in conf_text.upper():
                    print("⚠️ Order is MOCK only (not sent to Alpaca)")
                if "Order ID" in conf_text:
                    print("✓ Order confirmation displayed")
            else:
                print("❌ No order confirmation")
        else:
            print("❌ Submit order button not found")
        
        # Take screenshot
        await page.screenshot(path="manual_trade_test.png", full_page=True)
        print("\n📸 Screenshot saved: manual_trade_test.png")
        
        # Check console for errors
        page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}"))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_manual_trade())
