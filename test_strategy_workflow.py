"""Test Strategy Lab validation and backtest workflow"""
import asyncio
from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8050"

async def test_strategy_workflow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"🌐 Navigating to {DASHBOARD_URL}...")
        await page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(10000)
        
        # Navigate to Strategy Lab
        print("📊 Navigating to Strategy Lab...")
        await page.click('text=⚡ Strategy Lab', timeout=10000)
        await page.wait_for_timeout(5000)
        
        # Should be on Setup tab by default
        print("📋 On Setup tab - checking form elements...")
        
        # Check if strategy type dropdown exists
        strategy_dropdown = page.locator('#sl-strategy-type')
        if await strategy_dropdown.count() > 0:
            print(f"  ✅ Strategy type dropdown found")
        else:
            print(f"  ❌ Strategy type dropdown NOT found")
        
        # Check if tickers input exists
        tickers_input = page.locator('#sl-tickers-input')
        if await tickers_input.count() > 0:
            print(f"  ✅ Tickers input found")
            # Fill it
            await tickers_input.fill("AAPL,MSFT,GOOGL")
            print(f"  ✅ Filled tickers: AAPL,MSFT,GOOGL")
        else:
            print(f"  ❌ Tickers input NOT found")
        
        # Check if entry condition input exists
        entry_input = page.locator('#sl-entry-condition')
        if await entry_input.count() > 0:
            print(f"  ✅ Entry condition input found")
            await entry_input.fill("Close > SMA(20)")
            print(f"  ✅ Filled entry: Close > SMA(20)")
        else:
            print(f"  ❌ Entry condition input NOT found")
        
        # Check if exit condition input exists
        exit_input = page.locator('#sl-exit-condition')
        if await exit_input.count() > 0:
            print(f"  ✅ Exit condition input found")
            await exit_input.fill("Close < SMA(20)")
            print(f"  ✅ Filled exit: Close < SMA(20)")
        else:
            print(f"  ❌ Exit condition input NOT found")
        
        # Check for Validate button
        validate_btn = page.locator('#sl-validate-btn')
        if await validate_btn.count() > 0:
            is_visible = await validate_btn.is_visible()
            is_enabled = await validate_btn.is_enabled()
            print(f"  ✅ Validate button found (visible: {is_visible}, enabled: {is_enabled})")
            
            if is_visible and is_enabled:
                print("🖱️ Clicking Validate Strategy...")
                await validate_btn.click()
                await page.wait_for_timeout(3000)
                
                # Check for validation result
                result_div = page.locator('#sl-validation-result')
                if await result_div.count() > 0:
                    text = await result_div.inner_text()
                    print(f"  📝 Validation result: {text[:200]}")
                else:
                    print(f"  ⚠️ No validation result appeared")
        else:
            print(f"  ❌ Validate button NOT found")
        
        # Now try Execute tab
        print("\n▶️ Navigating to Execute tab...")
        execute_tab = page.locator('text=▶️ Execute')
        if await execute_tab.count() > 0:
            await execute_tab.click()
            await page.wait_for_timeout(3000)
            
            # Check Run Backtest button
            run_btn = page.locator('#sl-run-backtest-btn')
            if await run_btn.count() > 0:
                is_visible = await run_btn.is_visible()
                is_enabled = await run_btn.is_enabled()
                print(f"  ✅ Run Backtest button found (visible: {is_visible}, enabled: {is_enabled})")
                
                if is_visible and is_enabled:
                    print("🖱️ Clicking Run Backtest...")
                    await run_btn.click()
                    await page.wait_for_timeout(5000)
                    
                    # Check for results
                    status_div = page.locator('#sl-execution-status')
                    if await status_div.count() > 0:
                        text = await status_div.inner_text()
                        print(f"  📝 Execution status: {text[:200]}")
            else:
                print(f"  ❌ Run Backtest button NOT found")
        else:
            print(f"  ❌ Execute tab NOT found")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_strategy_workflow())
