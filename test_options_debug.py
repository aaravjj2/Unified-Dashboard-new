"""Quick debug script to check Options Lab loading"""
import time
from playwright.sync_api import sync_playwright

DASHBOARD_URL = 'http://localhost:8050'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.set_default_timeout(60000)
    
    print("🔵 Navigating to dashboard...")
    page.goto(DASHBOARD_URL)
    
    # Wait for dashboard to load
    page.wait_for_selector('text=Financial Dashboard', timeout=60000)
    print("✅ Dashboard loaded")
    
    # Take screenshot of home page
    page.screenshot(path='screenshot_home.png')
    print("📸 Screenshot saved: screenshot_home.png")
    
    # Click Options Lab tab
    print("🔵 Clicking Options Lab tab...")
    options_tab = page.locator('text=💹 Options Lab').first
    options_tab.click()
    time.sleep(3)
    
    # Take screenshot after clicking
    page.screenshot(path='screenshot_options_lab.png')
    print("📸 Screenshot saved: screenshot_options_lab.png")
    
    # Check if ticker input exists
    ticker_input = page.locator('#options-ticker-input')
    if ticker_input.is_visible():
        print("✅ Ticker input is visible")
        
        # Try to load mock data
        ticker_input.fill('AAPL')
        print("✅ Filled ticker: AAPL")
        
        mock_btn = page.locator('#options-mock-btn')
        if mock_btn.is_visible():
            print("✅ Mock button is visible")
            mock_btn.click()
            print("🔵 Clicked mock button")
            
            time.sleep(3)
            page.screenshot(path='screenshot_after_mock.png')
            print("📸 Screenshot saved: screenshot_after_mock.png")
            
            # Check status message
            status = page.locator('#options-status-message').text_content()
            print(f"📋 Status message: {status}")
        else:
            print("❌ Mock button NOT visible")
    else:
        print("❌ Ticker input NOT visible")
        print("📋 Page content:")
        print(page.content()[:1000])
    
    browser.close()
    print("✅ Test complete")
