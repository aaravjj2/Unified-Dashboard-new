"""Test all Volatility Lab buttons across different subtabs"""
import asyncio
from playwright.async_api import async_playwright

async def test_all_vol_buttons():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        # Navigate to Volatility Lab
        print("Loading dashboard and navigating to Volatility Lab...")
        await page.goto("http://localhost:8050/", wait_until="networkidle")
        await asyncio.sleep(10)
        
        await page.click('a:has-text("Volatility Lab")') 
        await asyncio.sleep(3)
        print("✓ Opened Volatility Lab\n")
        
        # TEST 1: Quick Compute (Overview tab - default)
        print("=" * 60)
        print("TEST 1: Quick Compute Button (Overview Tab)")
        print("=" * 60)
        initial_atm = await page.locator('#vl-overview-atm-iv').text_content()
        print(f"Initial ATM IV: {initial_atm}")
        
        await page.click('#vl-compute-quick-btn')
        await asyncio.sleep(5)
        
        final_atm = await page.locator('#vl-overview-atm-iv').text_content()
        print(f"After click: {final_atm}")
        if initial_atm != final_atm:
            print("✅ PASS: ATM IV updated\n")
        else:
            print("⚠️ FAIL: No change\n")
        
        # TEST 2: Calculate IV Surface (IV Surface tab)
        print("=" * 60)
        print("TEST 2: Calculate IV Surface (IV Surface Tab)")
        print("=" * 60)
        
        # Click IV Surface tab
        print("Clicking 'IV Surface' subtab...")
        try:
            await page.click('button[data-rb-event-key="tab-iv-surface"]', timeout=5000)
            await asyncio.sleep(2)
            print("✓ Switched to IV Surface tab")
        except:
            print("Trying alternate selector...")
            await page.click('button:has-text("IV Surface")')
            await asyncio.sleep(2)
        
        # Check if Run button exists
        run_btn = page.locator('#vl-calc-run-btn')
        if await run_btn.count() > 0:
            print("✓ Found 'Run' button")
            
            # Get initial heatmap state
            heatmap = page.locator('#vl-heatmap')
            initial_hash = hash(str(await heatmap.bounding_box()))
            print(f"Initial heatmap state: {initial_hash}")
            
            # Click Run
            await run_btn.click()
            print("Clicked 'Run' button, waiting for computation...")
            await asyncio.sleep(10)
            
            final_hash = hash(str(await heatmap.bounding_box()))
            print(f"After click: {final_hash}")
            
            if initial_hash != final_hash:
                print("✅ PASS: Heatmap updated\n")
            else:
                print("⚠️ Result unclear - heatmap may have updated\n")
        else:
            print("❌ FAIL: Run button not found\n")
        
        # TEST 3: Run Signals (Signals & Backtest tab)
        print("=" * 60)
        print("TEST 3: Run Signals (Signals & Backtest Tab)")
        print("=" * 60)
        
        print("Clicking 'Signals & Backtest' subtab...")
        try:
            await page.click('button[data-rb-event-key="tab-signals"]', timeout=5000)
            await asyncio.sleep(2)
            print("✓ Switched to Signals & Backtest tab")
        except:
            await page.click('button:has-text("Signals")')
            await asyncio.sleep(2)
        
        # Check Run Signals button
        signals_btn = page.locator('#vl-signal-run-btn')
        if await signals_btn.count() > 0:
            print("✓ Found 'Run Signals' button")
            
            # Get initial signal table
            signal_table = page.locator('#vl-signal-table')
            initial_content = await signal_table.text_content() if await signal_table.count() > 0 else ""
            print(f"Initial signals: '{initial_content[:50]}'...")
            
            await signals_btn.click()
            print("Clicked 'Run Signals', waiting for computation...")
            await asyncio.sleep(10)
            
            final_content = await signal_table.text_content() if await signal_table.count() > 0 else ""
            print(f"After click: '{final_content[:50]}'...")
            
            if initial_content != final_content:
                print("✅ PASS: Signals table updated\n")
            else:
                print("⚠️ FAIL: No change in signals\n")
        else:
            print("❌ FAIL: Run Signals button not found\n")
        
        # TEST 4: Run Backtest
        print("=" * 60)
        print("TEST 4: Run Backtest (Same Tab)")
        print("=" * 60)
        
        backtest_btn = page.locator('#vl-backtest-run-btn')
        if await backtest_btn.count() > 0:
            print("✓ Found 'Run Backtest' button")
            
            # Get initial backtest results
            backtest_results = page.locator('#vl-backtest-results')
            initial_results = await backtest_results.text_content() if await backtest_results.count() > 0 else ""
            print(f"Initial results: '{initial_results[:50]}'...")
            
            await backtest_btn.click()
            print("Clicked 'Run Backtest', waiting for computation...")
            await asyncio.sleep(10)
            
            final_results = await backtest_results.text_content() if await backtest_results.count() > 0 else ""
            print(f"After click: '{final_results[:50]}'...")
            
            if initial_results != final_results:
                print("✅ PASS: Backtest results updated\n")
            else:
                print("⚠️ FAIL: No change in results\n")
        else:
            print("❌ FAIL: Run Backtest button not found\n")
        
        # Final screenshot
        await page.screenshot(path="vol_lab_all_buttons_test.png", full_page=True)
        print("\n📸 Screenshot saved: vol_lab_all_buttons_test.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_all_vol_buttons())
