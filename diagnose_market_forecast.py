"""
Simple diagnostic test for Market Forecast tab
"""
import asyncio
from playwright.async_api import async_playwright

async def diagnose_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8051')
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        print("✅ Dashboard loaded\n")
        
        # List all tabs
        print("📋 Available tabs:")
        tabs = await page.locator('[role="tab"]').all()
        for i, tab in enumerate(tabs):
            text = await tab.inner_text()
            print(f"  {i+1}. {text}")
        
        # Click Market Forecast tab
        print("\n📊 Clicking 'Market Forecast' tab...")
        mf_tab = page.locator('[role="tab"]:has-text("Market Forecast")')
        if await mf_tab.count() > 0:
            await mf_tab.click()
            await page.wait_for_timeout(2000)
            print("✅ Clicked Market Forecast tab")
        else:
            print("❌ Market Forecast tab not found!")
            await browser.close()
            return
        
        # Check active tab
        active_tab = await page.locator('[role="tab"][aria-selected="true"]').inner_text()
        print(f"✅ Active tab: {active_tab}")
        
        # Check for Market Forecast content
        print("\n🔍 Looking for Market Forecast elements...")
        
        # Try different selectors
        selectors_to_try = [
            '#mf-ticker-input',
            '#mf-run-btn',
            'text=Run Forecast',
            'text=Forecast Inputs',
            '[id*="mf-"]'
        ]
        
        for selector in selectors_to_try:
            count = await page.locator(selector).count()
            if count > 0:
                visible = await page.locator(selector).first.is_visible()
                print(f"  ✅ Found {count} element(s) for '{selector}' (visible: {visible})")
            else:
                print(f"  ❌ No elements found for '{selector}'")
        
        # Get page HTML and search for mf- IDs
        html = await page.content()
        if 'mf-ticker-input' in html:
            print("\n✅ Market Forecast HTML is present in page")
        else:
            print("\n❌ Market Forecast HTML NOT found in page")
        
        # Take screenshot
        await page.screenshot(path='/tmp/market_forecast_diagnostic.png', full_page=True)
        print("\n📸 Screenshot saved to /tmp/market_forecast_diagnostic.png")
        
        await page.wait_for_timeout(3000)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(diagnose_tabs())
