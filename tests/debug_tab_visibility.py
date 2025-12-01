"""
Debug script to see the actual HTML structure when Market Trends tab is clicked.
"""
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # Run in headless mode
    page = browser.new_page()
    
    # Navigate to dashboard
    page.goto(BASE_URL)
    time.sleep(3)
    
    # Click Market Trends tab
    print("Clicking Market Trends tab...")
    tab = page.locator('a:has-text("Market Trends")')
    if tab.count() > 0:
        tab.first.click()
        print(f"✅ Clicked tab ({tab.count()} found)")
    else:
        print("❌ Tab not found")
    
    time.sleep(5)
    
    # Check tab panes
    print("\n=== Checking tab panes ===")
    tab_panes = page.locator('.tab-pane').all()
    print(f"Found {len(tab_panes)} tab panes")
    
    for i, pane in enumerate(tab_panes):
        classes = pane.get_attribute('class') or ''
        print(f"  Pane {i}: classes='{classes}'")
        if 'active' in classes:
            print(f"    ✅ Active pane")
        else:
            print(f"    ⚠️  Inactive pane")
    
    # Check tables
    print("\n=== Checking tables ===")
    tables = page.locator('table').all()
    print(f"Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        visible = table.is_visible()
        print(f"  Table {i}: visible={visible}")
        if not visible:
            # Check computed styles
            display = page.evaluate('(el) => window.getComputedStyle(el).display', table.element_handle())
            visibility = page.evaluate('(el) => window.getComputedStyle(el).visibility', table.element_handle())
            print(f"    display={display}, visibility={visibility}")
            
            # Check parent visibility
            parent = table.locator('xpath=..').first
            parent_display = page.evaluate('(el) => window.getComputedStyle(el).display', parent.element_handle())
            parent_visibility = page.evaluate('(el) => window.getComputedStyle(el).visibility', parent.element_handle())
            print(f"    parent: display={parent_display}, visibility={parent_visibility}")
    
    # Save full page HTML
    html = page.content()
    with open('test-artifacts/market_trends_debug_full.html', 'w') as f:
        f.write(html)
    print(f"\n✅ Saved full HTML to test-artifacts/market_trends_debug_full.html")
    
    # Take screenshot
    page.screenshot(path="test-artifacts/market_trends_debug.png", full_page=True)
    print("✅ Saved screenshot to test-artifacts/market_trends_debug.png")
    
    # Keep browser open for manual inspection
    print("\n⏸️  Closing browser...")
    time.sleep(1)
    
    browser.close()
