"""
Capture Market Forecast Graph Proof
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_forecast():
    async with async_playwright() as p:
        # Launch headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8051')
        await page.wait_for_selector('text=Financial Dashboard', timeout=15000)
        
        # Wait for JS fixes
        await page.wait_for_timeout(3000)
        
        # Navigate to Market Forecast (Tab 2)
        print("📊 Navigating to Market Forecast...")
        # We need to find the tab button. The labels are fixed by JS, but IDs are likely 'tab-1', 'tab-2' etc.
        # Based on index.py, Market Forecast is likely the second tab if enabled.
        # Let's try clicking the tab with text "Market Forecast"
        await page.click('text=Market Forecast')
        await page.wait_for_timeout(1000)
        
        # Enter Ticker
        print("⌨️ Entering Ticker AAPL...")
        # Dash Dropdown interaction
        await page.click('#mf-ticker-input')
        await page.keyboard.type('AAPL')
        await page.keyboard.press('Enter')
        
        # Click Run
        print("▶️ Running Forecast...")
        await page.click('#mf-run-btn')
        
        # Wait for Chart
        print("⏳ Waiting for chart to render...")
        # Wait for the chart to have data. The 'js-plotly-plot' class is added by Dash.
        await page.wait_for_selector('#mf-forecast-chart .js-plotly-plot', timeout=30000)
        await page.wait_for_timeout(5000) # Wait for animation/rendering
        
        # Take screenshot
        print("📸 Taking screenshot...")
        await page.screenshot(path='/home/aarav/unified-dashboard/market_forecast_graph_proof.png')
        
        print("✅ Screenshot saved to: /home/aarav/unified-dashboard/market_forecast_graph_proof.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_forecast())
