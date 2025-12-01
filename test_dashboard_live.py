"""
Test Dashboard with Live Browser Connection
Uses CDP to connect to existing Chrome instance
"""
import asyncio
from playwright.async_api import async_playwright

async def test_dashboard():
    async with async_playwright() as p:
        # Connect to existing Chrome instance
        browser = await p.chromium.connect_over_cdp('http://172.28.80.1:9222')
        
        # Get the default context and page
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = await context.new_page()
        else:
            print("No context found, creating new one")
            context = await browser.new_context()
            page = await context.new_page()
        
        print("=" * 80)
        print("LIVE BROWSER TEST - DASHBOARD")
        print("=" * 80)
        
        try:
            # Navigate to dashboard
            print("\n[1] Navigating to http://localhost:8051...")
            await page.goto('http://localhost:8051', timeout=30000, wait_until='domcontentloaded')
            await page.wait_for_timeout(10000)  # Wait for TradingView and other widgets
            
            # Capture Command Center
            print("\n[2] Capturing Command Center...")
            await page.screenshot(path='/home/aarav/unified-dashboard/LIVE_CommandCenter.png', full_page=True)
            print("✓ Saved LIVE_CommandCenter.png")
            
            # Check TradingView widget
            print("\n[3] Checking TradingView widget...")
            tv_exists = await page.is_visible('#tradingview_widget_container')
            print(f"  TradingView container exists: {tv_exists}")
            
            if tv_exists:
                iframe_count = await page.locator('iframe').count()
                print(f"  Iframes on page: {iframe_count}")
                
                # List all iframes
                iframes = await page.locator('iframe').all()
                for i, iframe in enumerate(iframes):
                    src = await iframe.get_attribute('src')
                    print(f"  Iframe {i+1}: {src}")
            
            # Navigate to Volatility Lab
            print("\n[4] Testing Volatility Lab...")
            try:
                await page.click('text=Volatility Lab', timeout=10000)
                await page.wait_for_timeout(3000)
                
                # Click Compute button
                if await page.is_visible('#vl-calc-run-btn'):
                    print("  → Clicking Compute Surface...")
                    await page.click('#vl-calc-run-btn')
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path='/home/aarav/unified-dashboard/LIVE_VolLab.png', full_page=True)
                    print("✓ Saved LIVE_VolLab.png")
                else:
                    print("  ❌ Compute button not found")
                    
            except Exception as e:
                print(f"  Vol Lab error: {e}")
            
            print("\n" + "=" * 80)
            print("TEST COMPLETE")
            print("=" * 80)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Don't close browser - leave it open for user
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_dashboard())
