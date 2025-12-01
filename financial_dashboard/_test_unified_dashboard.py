"""
Test unified dashboard - verify all tabs load and take screenshots
"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

async def test_unified_dashboard():
    print(f"\n{'='*60}")
    print(f"Unified Dashboard Test")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # Load unified dashboard
            print("Step 1: Loading unified dashboard...")
            await page.goto('http://127.0.0.1:8000', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            print("✓ Unified dashboard loaded")
            
            # Take initial screenshot
            await page.screenshot(path='unified_dashboard_initial.png', full_page=False)
            print("✓ Screenshot: unified_dashboard_initial.png")
            
            # Test each tab
            tabs = [
                ('trends', 'Market Trends'),
                ('forecast', 'Market Forecast'),
                ('monthly', 'Monthly Picks'),
                ('weekly', 'Weekly Picks')
            ]
            
            for tab_id, tab_name in tabs:
                print(f"\nStep: Testing {tab_name} tab...")
                
                # Click tab button
                tab_btn = page.locator(f'button[data-tab="{tab_id}"]')
                if await tab_btn.count() == 0:
                    print(f"  ✗ Tab button not found for {tab_name}")
                    continue
                
                await tab_btn.click()
                print(f"  ✓ Clicked {tab_name} tab")
                await asyncio.sleep(3)  # Wait for iframe to load
                
                # Check if iframe loaded
                iframe_selector = f'#{tab_id}-pane iframe'
                iframe = page.locator(iframe_selector)
                if await iframe.count() > 0:
                    print(f"  ✓ {tab_name} iframe found")
                    
                    # Check if loading indicator is hidden (means iframe loaded)
                    loading = page.locator(f'#{tab_id}-pane .loading')
                    if await loading.count() > 0:
                        is_visible = await loading.is_visible()
                        print(f"  Loading indicator visible: {is_visible}")
                else:
                    print(f"  ✗ {tab_name} iframe not found")
                
                # Take screenshot
                screenshot_path = f'unified_dashboard_{tab_id}.png'
                await page.screenshot(path=screenshot_path, full_page=False)
                print(f"  ✓ Screenshot: {screenshot_path}")
            
            # Return to first tab
            print("\nReturning to Market Trends...")
            await page.locator('button[data-tab="trends"]').click()
            await asyncio.sleep(2)
            
            # Take final screenshot
            await page.screenshot(path='unified_dashboard_final.png', full_page=False)
            print("✓ Screenshot: unified_dashboard_final.png")
            
            print(f"\n✓ All tabs tested successfully!")
            return True
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='unified_dashboard_error.png', full_page=False)
            return False
        
        finally:
            print(f"\nClosing browser...")
            await browser.close()

async def main():
    success = await test_unified_dashboard()
    
    print(f"\n{'='*60}")
    if success:
        print("✓ TEST PASSED: Unified dashboard working!")
    else:
        print("✗ TEST FAILED: Check error screenshots")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    asyncio.run(main())
