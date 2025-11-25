"""
Enhanced clicker that specifically tests the NEW refactored portfolio features:
- Positions tab with Inspect modal
- Order History tab
- Analytics tab with Monte Carlo button
- Factor Exposure tab
- Optimization tab
"""
from playwright.sync_api import sync_playwright
import os

URL = 'http://127.0.0.1:8056/'
SCREEN_DIR = 'test_screenshots/clicker_detailed'
os.makedirs(SCREEN_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Non-headless to see what's happening
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    
    print("🧪 Testing Refactored Portfolio Dashboard")
    print("=" * 60)
    
    # Load main page
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(SCREEN_DIR, '01_main_page.png'))
    print("✓ Main page loaded")
    
    # Test Positions tab
    try:
        positions_tab = page.locator("a:has-text('Positions')").first
        if positions_tab.is_visible(timeout=3000):
            positions_tab.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(SCREEN_DIR, '02_positions_tab.png'))
            print("✓ Positions tab clicked")
    except Exception as e:
        print(f"⚠ Positions tab: {e}")
    
    # Test Order History tab
    try:
        orders_tab = page.locator("a:has-text('Order History')").first
        if orders_tab.is_visible(timeout=3000):
            orders_tab.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(SCREEN_DIR, '03_orders_tab.png'))
            print("✓ Order History tab clicked")
    except Exception as e:
        print(f"⚠ Order History tab: {e}")
    
    # Test Analytics tab
    try:
        analytics_tab = page.locator("a:has-text('Analytics')").first
        if analytics_tab.is_visible(timeout=3000):
            analytics_tab.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(SCREEN_DIR, '04_analytics_tab.png'))
            print("✓ Analytics tab clicked")
            
            # Try Monte Carlo button
            try:
                monte_btn = page.locator("button:has-text('Monte Carlo')").first
                if monte_btn.is_visible(timeout=2000):
                    monte_btn.click()
                    page.wait_for_timeout(3000)
                    page.screenshot(path=os.path.join(SCREEN_DIR, '05_monte_carlo_run.png'))
                    print("✓ Monte Carlo button clicked")
            except Exception:
                print("⚠ Monte Carlo button not found or not clickable")
    except Exception as e:
        print(f"⚠ Analytics tab: {e}")
    
    # Test Factor Exposure tab
    try:
        factors_tab = page.locator("a:has-text('Factor Exposure')").first
        if factors_tab.is_visible(timeout=3000):
            factors_tab.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(SCREEN_DIR, '06_factor_exposure_tab.png'))
            print("✓ Factor Exposure tab clicked")
    except Exception as e:
        print(f"⚠ Factor Exposure tab: {e}")
    
    # Test Optimization tab
    try:
        opt_tab = page.locator("a:has-text('Optimization')").first
        if opt_tab.is_visible(timeout=3000):
            opt_tab.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(SCREEN_DIR, '07_optimization_tab.png'))
            print("✓ Optimization tab clicked")
            
            # Try entering tickers and optimizing
            try:
                ticker_input = page.locator("#optimization-tickers").first
                if ticker_input.is_visible(timeout=2000):
                    ticker_input.fill("AAPL,MSFT,GOOGL")
                    page.wait_for_timeout(500)
                    
                    opt_btn = page.locator("button:has-text('Optimize')").first
                    if opt_btn.is_visible(timeout=2000):
                        opt_btn.click()
                        page.wait_for_timeout(5000)
                        page.screenshot(path=os.path.join(SCREEN_DIR, '08_optimization_result.png'))
                        print("✓ Optimization run completed")
            except Exception:
                print("⚠ Optimization inputs not found or not clickable")
    except Exception as e:
        print(f"⚠ Optimization tab: {e}")
    
    print("=" * 60)
    print("🎉 Clicker test complete!")
    browser.close()
