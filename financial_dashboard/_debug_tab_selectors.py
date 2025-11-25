"""Quick debug script to see what tab selectors exist"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("http://localhost:8000")
    page.wait_for_timeout(5000)
    
    # Get all tabs
    tabs = page.query_selector_all(".nav-link, [role='tab'], a[id^='tab-']")
    print(f"Found {len(tabs)} tab elements:")
    for i, tab in enumerate(tabs):
        print(f"  {i}: {tab.inner_text()[:50]}")
        print(f"     Classes: {tab.get_attribute('class')}")
        print(f"     ID: {tab.get_attribute('id')}")
        print(f"     Href: {tab.get_attribute('href')}")
        print()
    
    page.screenshot(path="/tmp/dashboard_tabs.png")
    print("Screenshot saved to /tmp/dashboard_tabs.png")
    
    browser.close()
