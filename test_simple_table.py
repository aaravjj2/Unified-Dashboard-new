from playwright.sync_api import sync_playwright
import time

print("Simple test: Does Positions tab show a table?")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto('http://localhost:8051/', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(5)
    
    # Click Portfolio  
    page.evaluate('Array.from(document.querySelectorAll(\'a[role="tab"]\')).find(el => el.textContent.includes("Portfolio"))?.click()')
    time.sleep(3)
    
    # Click Positions
    page.evaluate('Array.from(document.querySelectorAll(\'a[role="tab"]\')).find(el => el.textContent.trim() === "Positions")?.click()')
    time.sleep(5)
    
    # Check table
    has_table = page.evaluate('() => !!document.querySelector("table#positions-datatable")')
    rows = page.evaluate('() => document.querySelectorAll("table#positions-datatable tbody tr").length')
    
    print(f"Table exists: {has_table}")
    print(f"Rows: {rows}")
    
    if has_table and rows > 0:
        print(f"✅ SUCCESS - Table rendered with {rows} positions")
    else:
        print("❌ FAIL - Table not rendered or empty")
        
        # Check what IS there
        content = page.evaluate('() => document.querySelector("#portfolio-tracker-tab-positions-content")?.innerHTML.substring(0, 500) || "CONTENT DIV NOT FOUND"')
        print(f"\nActual content:\n{content}")
    
    browser.close()
