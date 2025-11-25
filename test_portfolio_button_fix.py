"""Test Portfolio button with CORRECT ID"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("Loading...")
    page.goto('http://localhost:8050/', timeout=60000)
    page.wait_for_load_state('networkidle')
    time.sleep(5)
    
    print("\nGoing to Portfolio...")
    page.get_by_role("tab", name="Portfolio").click()
    time.sleep(2)
    
    # Click Current Positions
    page.get_by_text("Current Positions").click()
    time.sleep(2)
    
    # Count BEFORE
    table = page.locator('table#positions-datatable tbody tr')
    count_before = table.count()
    print(f"Positions BEFORE: {count_before}")
    
    # Click CORRECT refresh button ID
    refresh_btn = page.locator('button#portfolio-positions-refresh-btn')
    if refresh_btn.is_visible():
        print("\\nClicking refresh button...")
        refresh_btn.click()
        time.sleep(7)  # Wait for API call
        
        count_after = table.count()
        print(f"Positions AFTER: {count_after}")
        
        if count_after >= 3:
            print("\\n✅✅✅ PORTFOLIO REFRESH BUTTON WORKS! ✅✅✅")
        else:
            print(f"\\n❌ Still only {count_after} positions")
        
        page.screenshot(path='reports/fix_verification/screenshots/portfolio_BUTTON_TEST.png')
    else:
        print("❌ Button not visible")
    
    browser.close()
