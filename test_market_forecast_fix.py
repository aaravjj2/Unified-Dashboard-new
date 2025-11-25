"""
Test Market Forecast Tab - Verify functionality and fix issues
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def test_market_forecast():
    """Test the Market Forecast tab functionality."""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("🌐 Navigating to dashboard...")
        await page.goto('http://localhost:8051')
        
        # Wait for page load
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        print("✅ Dashboard loaded")
        
        # Click Market Forecast tab
        print("📊 Clicking Market Forecast tab...")
        await page.click('text=Market Forecast')
        await page.wait_for_timeout(2000)
        
        # Wait for inputs panel
        await page.wait_for_selector('#mf-ticker-input', timeout=5000)
        print("✅ Market Forecast tab loaded")
        
        # Check ticker dropdown options
        ticker_dropdown = page.locator('#mf-ticker-input')
        await ticker_dropdown.click()
        await page.wait_for_timeout(1000)
        
        # Verify options are present
        aapl_option = page.locator('text=AAPL - Apple')
        if await aapl_option.count() > 0:
            print("✅ Ticker dropdown has options")
        else:
            print("❌ Ticker dropdown missing options")
        
        # Close dropdown
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(500)
        
        # Click Run Forecast button
        print("▶️  Clicking Run Forecast button...")
        run_button = page.locator('#mf-run-btn')
        await run_button.click()
        
        # Wait for forecast to complete
        print("⏳ Waiting for forecast to complete...")
        await page.wait_for_timeout(10000)
        
        # Check if forecast chart appeared
        forecast_chart = page.locator('#mf-forecast-chart')
        chart_html = await forecast_chart.inner_html()
        
        if 'Run forecast to see predictions' in chart_html:
            print("❌ Forecast still showing placeholder - callback may not be working")
        elif 'Forecasts' in chart_html or 'data' in chart_html:
            print("✅ Forecast chart updated with data!")
        else:
            print(f"⚠️  Chart HTML: {chart_html[:200]}")
        
        # Check status banner
        status_banner = page.locator('#mf-status-banner')
        if await status_banner.count() > 0:
            status_text = await status_banner.inner_text()
            print(f"📋 Status: {status_text}")
        
        # Take screenshot
        await page.screenshot(path='/tmp/market_forecast_test.png')
        print("📸 Screenshot saved to /tmp/market_forecast_test.png")
        
        # Check browser console for errors
        print("\n🔍 Checking for console errors...")
        page.on('console', lambda msg: print(f"  Console: {msg.text}"))
        
        await page.wait_for_timeout(2000)
        
        await browser.close()
        print("\n✅ Test complete!")

if __name__ == '__main__':
    asyncio.run(test_market_forecast())
