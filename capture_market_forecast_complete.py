"""
Capture Market Forecast with Feature Importance proof
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_market_forecast_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("=" * 70)
        print("MARKET FORECAST PROOF CAPTURE")
        print("=" * 70)
        
        # Load dashboard
        print("\n[1/4] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000)
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        await page.wait_for_timeout(3000)
        print("✓ Dashboard loaded")
        
        # Navigate to Market Forecast
        print("\n[2/4] Navigating to Market Forecast...")
        await page.click('text=Market Forecast')
        await page.wait_for_timeout(1000)
        print("✓ Market Forecast tab opened")
        
        # Enter ticker and run forecast
        print("\n[3/4] Running forecast for AAPL...")
        await page.click('#mf-ticker-input')
        await page.keyboard.type('AAPL')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(500)
        
        await page.click('#mf-run-btn')
        print("✓ Forecast triggered")
        
        # Wait for forecast to complete
        await page.wait_for_timeout(15000)
        
        # Screenshot full page
        print("\n[4/4] Capturing screenshots...")
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_market_forecast_complete.png', full_page=True)
        print("✓ Screenshot saved: proof_market_forecast_complete.png")
        
        await browser.close()
        
        print("\n" + "=" * 70)
        print("PROOF CAPTURE COMPLETE")
        print("=" * 70)

if __name__ == '__main__':
    asyncio.run(capture_market_forecast_proof())
