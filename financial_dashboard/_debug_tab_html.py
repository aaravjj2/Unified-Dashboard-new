"""Debug script to find tab structure with full HTML"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:8000")
    page.wait_for_timeout(3000)
    
    # Get dashboard-tabs container
    tabs_html = page.locator("#dashboard-tabs").inner_html()
    
    # Save to file
    with open("/tmp/dashboard_tabs.html", "w") as f:
        f.write(tabs_html)
    
    print("Tab HTML saved to /tmp/dashboard_tabs.html")
    print()
    print("First 3000 chars:")
    print(tabs_html[:3000])
    
    browser.close()
