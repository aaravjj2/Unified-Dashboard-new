"""
Comprehensive Testing Script - Post Server Restart
Tests all fixes with detailed screenshots
"""
import asyncio
from playwright.async_api import async_playwright

async def comprehensive_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("=" * 80)
        print("COMPREHENSIVE POST-RESTART TESTING")
        print("=" * 80)
        
        try:
            # Wait for server to be fully ready
            print("\n[INIT] Waiting for server to initialize...")
            await page.goto('http://localhost:8051', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(15000)  # Give TradingView time to load
            
            # TEST 1: Command Center - Text Colors & Layout
            print("\n[TEST 1] Command Center - Text Colors & Watchlist")
            await page.screenshot(path='/home/aarav/unified-dashboard/TEST_CommandCenter.png', full_page=True)
            print("✓ Saved TEST_CommandCenter.png")
            
            # TEST 2: Vol Lab - Navigate and test
            print("\n[TEST 2] Volatility Lab - Button Functionality")
            try:
                await page.click('text=Volatility Lab', timeout=10000)
                await page.wait_for_timeout(3000)
                
                # 2a: Overview tab
                await page.click('#volatility-lab-tabs >> text=Overview', timeout=5000)
                await page.wait_for_timeout(2000)
                await page.screenshot(path='/home/aarav/unified-dashboard/TEST_VolLab_Overview.png', full_page=True)
                print("✓ Saved TEST_VolLab_Overview.png")
                
                # 2b: IV Surface  tab - Click Compute
                await page.click('#volatility-lab-tabs >> text=IV Surface', timeout=5000)
                await page.wait_for_timeout(2000)
                
                if await page.is_visible('#vl-calc-run-btn'):
                    print("  → Clicking Compute Surface button...")
                    await page.click('#vl-calc-run-btn')
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path='/home/aarav/unified-dashboard/TEST_VolLab_Compute.png', full_page=True)
                    print("✓ Saved TEST_VolLab_Compute.png (after clicking Compute)")
                else:
                    print("  ❌ Compute button not found!")
                
                # 2c: Signals tab - Click Scan
                await page.click('#volatility-lab-tabs >> text=Signals & Backtest', timeout=5000)
                await page.wait_for_timeout(2000)
                
                if await page.is_visible('#vl-signal-run-btn'):
                    print("  → Clicking Scan Signals button...")
                    await page.click('#vl-signal-run-btn')
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path='/home/aarav/unified-dashboard/TEST_VolLab_Signals.png', full_page=True)
                    print("✓ Saved TEST_VolLab_Signals.png (after clicking Scan)")
                else:
                    print("  ❌ Scan Signals button not found!")
                
                # 2d: Backtest - Click Run
                if await page.is_visible('#vl-backtest-run-btn'):
                    print("  → Clicking Run Backtest button...")
                    await page.click('#vl-backtest-run-btn')
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path='/home/aarav/unified-dashboard/TEST_VolLab_Backtest.png', full_page=True)
                    print("✓ Saved TEST_VolLab_Backtest.png (after clicking Run Backtest)")
                else:
                    print("  ❌ Run Backtest button not found!")
                    
            except Exception as e:
                print(f"  ❌ Vol Lab test error: {e}")
                
            # TEST 3: TradingView Widget Check
            print("\n[TEST 3] TradingView Widget Verification")
            await page.goto('http://localhost:8051', timeout=30000)
            await page.wait_for_timeout(15000)  # Extra time for TradingView
            
            # Check if TradingView container exists
            tv_exists = await page.is_visible('#tradingview_widget_container')
            print(f"  TradingView container exists: {tv_exists}")
            
            if tv_exists:
                # Check if iframe was created by TradingView script
                iframe_count = await page.locator('iframe').count()
                print(f"  Iframes on page: {iframe_count}")
            
            await page.screenshot(path='/home/aarav/unified-dashboard/TEST_TradingView_Detail.png', full_page=True)
            print("✓ Saved TEST_TradingView_Detail.png")
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            
        await browser.close()
        print("\n" + "=" * 80)
        print("TESTING COMPLETE")
        print("=" * 80)

if __name__ == '__main__':
    asyncio.run(comprehensive_test())
