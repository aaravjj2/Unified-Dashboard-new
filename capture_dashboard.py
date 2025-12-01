"""
Take a screenshot of the dashboard to verify tabs are visible.
"""
from playwright.sync_api import sync_playwright
import time

def capture_dashboard_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        
        # Set viewport size
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        print("📸 Loading dashboard and taking screenshot...")
        page.goto('http://localhost:8050/', timeout=30000, wait_until='networkidle')
        
        # Wait for tabs to be visible
        page.wait_for_selector('.nav-item', timeout=10000)
        
        # Take screenshot
        page.screenshot(path='/tmp/dashboard_screenshot.png', full_page=True)
        
        # Count tabs
        tabs = page.locator('.nav-item').all_text_contents()
        
        print(f"✅ Screenshot saved to /tmp/dashboard_screenshot.png")
        print(f"📊 Found {len(tabs)} tabs:")
        for i, tab in enumerate(tabs, 1):
            print(f"  {i}. {tab}")
        
        browser.close()

if __name__ == '__main__':
    capture_dashboard_screenshot()
