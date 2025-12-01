from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    page.goto('http://localhost:8051/', timeout=60000)
    page.wait_for_load_state('networkidle')
    time.sleep(5)
    
    page.get_by_role("tab", name="Portfolio").click()
    time.sleep(2)
    
    page.get_by_text("Current Positions").click()
    time.sleep(2)
    
    table = page.locator('table#positions-datatable tbody tr')
    count_before = table.count()
    print(f"Positions BEFORE: {count_before}")
    
    refresh_btn = page.locator('button#portfolio-positions-refresh-btn')
    if refresh_btn.is_visible():
        print("Clicking refresh...")
        refresh_btn.click()
        time.sleep(8)
        
        count_after = table.count()
        print(f"Positions AFTER: {count_after}")
        
        if count_after >= 3:
            print("SUCCESS - BUTTONS WORK!")
        else:
            print(f"FAIL - only {count_after} positions")
        
        page.screenshot(path='reports/fix_verification/screenshots/BUTTON_TEST.png')
    
    browser.close()
