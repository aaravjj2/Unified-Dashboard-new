"""
Market Forecast Browser Tests
End-to-end Playwright tests for UI interaction
"""

from playwright.sync_api import sync_playwright
import time
import json

def test_market_forecast_ui():
    """Test Market Forecast UI loads and displays data"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        
        try:
            # Navigate to dashboard
            print("📍 Loading dashboard...")
            page.goto("http://localhost:8051/", timeout=30000)
            time.sleep(2)
            
            # Click Market Forecast tab
            print("📍 Clicking Market Forecast tab...")
            page.click('a[role="tab"]:has-text("Market Forecast")')
            time.sleep(2)
            
            # Check for mf- component IDs
            print("📍 Checking for UI components...")
            
            # Check ticker dropdown
            ticker_input = page.locator('#mf-ticker-input')
            assert ticker_input.is_visible(), "❌ Ticker input not found"
            print("✅ Ticker input visible")
            
            # Check horizon dropdown
            horizon_select = page.locator('#mf-horizon-select')
            assert horizon_select.is_visible(), "❌ Horizon select not found"
            print("✅ Horizon select visible")
            
            # Check run button
            run_btn = page.locator('#mf-run-btn')
            assert run_btn.is_visible(), "❌ Run button not found"
            print("✅ Run button visible")
            
            # Check forecast chart
            forecast_chart = page.locator('#mf-forecast-chart')
            assert forecast_chart.is_visible(), "❌ Forecast chart not found"
            print("✅ Forecast chart visible")
            
            # Check explain chart
            explain_chart = page.locator('#mf-explain-chart')
            assert explain_chart.is_visible(), "❌ Explain chart not found"
            print("✅ Explain chart visible")
            
            # Check summary cards
            body_text = page.locator('body').inner_text()
            assert 'Expected Return' in body_text, "❌ Expected Return card not found"
            assert 'Volatility' in body_text, "❌ Volatility card not found"
            assert 'Sharpe Ratio' in body_text, "❌ Sharpe Ratio card not found"
            print("✅ Summary cards visible")
            
            # Take screenshot
            page.screenshot(path='reports/market_forecast_rebuild/diagnostics/playwright/market_forecast_ui.png')
            print("✅ Screenshot saved")
            
            print("\n" + "="*60)
            print("✅ ALL MARKET FORECAST UI TESTS PASSED")
            print("="*60)
            
            time.sleep(2)
            
        finally:
            browser.close()

if __name__ == '__main__':
    import os
    os.makedirs('reports/market_forecast_rebuild/diagnostics/playwright', exist_ok=True)
    test_market_forecast_ui()
