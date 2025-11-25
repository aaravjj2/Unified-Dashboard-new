"""
Test Market Forecast with fixed tab labels
"""
import asyncio
from playwright.async_api import async_playwright

async def test_market_forecast_v2():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8051')
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        print("✅ Dashboard loaded")
        
        # Wait for JavaScript to fix tab labels
        await page.wait_for_timeout(3000)
        
        # List all tabs
        print("\n📋 Available tabs:")
        tabs = await page.locator('[role="tab"]').all()
        for i, tab in enumerate(tabs):
            text = await tab.inner_text()
            print(f"  {i+1}. {text}")
        
        # Click Market Forecast tab by text
        print("\n📊 Clicking 'Market Forecast' tab...")
        await page.click('text=Market Forecast')
        await page.wait_for_timeout(2000)
        print("✅ Clicked Market Forecast tab")
        
        # Wait for inputs to be visible
        print("\n⏳ Waiting for Market Forecast inputs to appear...")
        await page.wait_for_selector('#mf-run-btn', state='visible', timeout=10000)
        print("✅ Market Forecast inputs are visible!")
        
        # Click Run Forecast button
        print("\n▶️  Clicking Run Forecast button...")
        await page.click('#mf-run-btn')
        
        # Wait for forecast to complete
        print("⏳ Waiting for forecast (15 seconds)...")
        await page.wait_for_timeout(15000)
        
        # Check if forecast chart updated
        forecast_chart = page.locator('#mf-forecast-chart')
        chart_html = await forecast_chart.inner_html()
        
        if 'Run forecast to see predictions' in chart_html:
            print("❌ Forecast still showing placeholder")
        elif 'plotly' in chart_html.lower() or 'data' in chart_html:
            print("✅ Forecast chart updated with data!")
        else:
            print(f"⚠️  Chart HTML (first 200 chars): {chart_html[:200]}")
        
        # Check status banner
        status_banner = page.locator('#mf-status-banner')
        if await status_banner.count() > 0:
            status_html = await status_banner.inner_html()
            print(f"\n📋 Status banner: {status_html[:200]}")
        
        # Take screenshot
        await page.screenshot(path='/tmp/market_forecast_v2.png', full_page=True)
        print("\n📸 Screenshot saved to /tmp/market_forecast_v2.png")
        
        await page.wait_for_timeout(2000)
        await browser.close()
        print("\n✅ Test complete!")

if __name__ == '__main__':
    asyncio.run(test_market_forecast_v2())
