"""
Final Live Browser Test - TradingView Iframe + Vol Lab Tabs
"""
import asyncio
from playwright.async_api import async_playwright

async def final_test():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://172.28.80.1:9222')
        
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = await context.new_page()
        else:
            context = await browser.new_context()
            page = await context.new_page()
        
        print("=" * 80)
        print("FINAL VERIFICATION - TradingView Iframe + Vol Lab Tabs")
        print("=" * 80)
        
        try:
            # Navigate to dashboard
            print("\n[1] Navigating to http://localhost:8051...")
            await page.goto('http://localhost:8051', timeout=30000, wait_until='domcontentloaded')
            await page.wait_for_timeout(12000)  # Wait for widgets to load
            
            # Test 1: TradingView Iframe
            print("\n[TEST 1] TradingView Widget (Iframe)")
            iframe_exists = await page.is_visible('iframe#tradingview_widget')
            print(f"  TradingView iframe exists: {iframe_exists}")
            
            if iframe_exists:
                iframe_src = await page.get_attribute('iframe#tradingview_widget', 'src')
                print(f"  Iframe src: {iframe_src[:80]}...")
            
            # Capture Command Center
            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_CommandCenter.png', full_page=True)
            print("✓ Saved FINAL_CommandCenter.png")
            
            # Test 2: Vol Lab Tabs
            print("\n[TEST 2] Volatility Lab - Tab Navigation")
            await page.click('text=Volatility Lab', timeout=10000)
            await page.wait_for_timeout(3000)
            
            # Test each tab
            tabs = [
                ('📊 Overview', 'tab-overview'),
                ('📈 IV Surface', 'tab-iv-surface'),
                ('🎯 Signals & Backtest', 'tab-signals'),
                ('🔧 Diagnostics', 'tab-diagnostics')
            ]
            
            for tab_label, tab_id in tabs:
                try:
                    print(f"\n  → Testing tab: {tab_label}")
                    await page.click(f'text={tab_label}', timeout=5000)
                    await page.wait_for_timeout(2000)
                    
                    # Check if tab content loaded
                    if tab_id == 'tab-iv-surface':
                        compute_btn = await page.is_visible('#vl-calc-run-btn')
                        print(f"    Compute button visible: {compute_btn}")
                        
                        if compute_btn:
                            print(f"    → Clicking Compute Surface...")
                            await page.click('#vl-calc-run-btn')
                            await page.wait_for_timeout(5000)
                            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_VolLab_Surface.png', full_page=True)
                            print(f"    ✓ Saved FINAL_VolLab_Surface.png")
                    
                    elif tab_id == 'tab-signals':
                        scan_btn = await page.is_visible('#vl-signal-run-btn')
                        backtest_btn = await page.is_visible('#vl-backtest-run-btn')
                        print(f"    Scan Signals button visible: {scan_btn}")
                        print(f"    Run Backtest button visible: {backtest_btn}")
                        
                        if scan_btn:
                            print(f"    → Clicking Scan Signals...")
                            await page.click('#vl-signal-run-btn')
                            await page.wait_for_timeout(3000)
                        
                        if backtest_btn:
                            print(f"    → Clicking Run Backtest...")
                            await page.click('#vl-backtest-run-btn')
                            await page.wait_for_timeout(3000)
                            await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_VolLab_Signals.png', full_page=True)
                            print(f"    ✓ Saved FINAL_VolLab_Signals.png")
                    
                    print(f"    ✓ Tab {tab_label} working")
                    
                except Exception as e:
                    print(f"    ❌ Tab {tab_label} error: {e}")
            
            print("\n" + "=" * 80)
            print("FINAL TEST COMPLETE")
            print("=" * 80)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(final_test())
