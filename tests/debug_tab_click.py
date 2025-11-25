"""Debug script to test tab click behavior"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8050"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("1. Navigating to dashboard...")
    page.goto(BASE_URL)
    page.wait_for_timeout(3000)
    
    print("2. Taking screenshot of initial state...")
    page.screenshot(path="/tmp/debug_before_click.png", full_page=True)
    
    print("3. Looking for Market Trends tab...")
    tab = page.locator('a:has-text("Market Trends")').first
    if tab.count() > 0:
        print("   ✅ Found tab")
        print("4. Clicking Market Trends tab...")
        tab.click()
        page.wait_for_timeout(5000)  # Wait longer for callback
        
        print("5. Taking screenshot after click...")
        page.screenshot(path="/tmp/debug_after_click.png", full_page=True)
        
        print("6. Checking for table...")
        tables = page.locator('table').all()
        print(f"   Found {len(tables)} tables")
        
        results_area = page.locator('#results-area')
        if results_area.count() > 0:
            print("   ✅ results-area exists")
            print(f"   Content: {results_area.text_content()[:200]}")
        else:
            print("   ❌ results-area NOT found")
            
    else:
        print("   ❌ Market Trends tab not found")
    
    print("\nPress Enter to close browser...")
    input()
    browser.close()
