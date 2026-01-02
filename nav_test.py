#!/usr/bin/env python3
"""Navigate to Chain & Greeks and test."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("Loading page...")
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    page.screenshot(path='1_initial.png')
    print("1. Initial state saved")
    
    # Click Strategy tab using text
    print("2. Looking for Strategy tab...")
    strategy = page.locator('text=Strategy')
    if strategy.count() > 0:
        print(f"   Found {strategy.count()} matches")
        strategy.first.click()
        time.sleep(2)
        page.screenshot(path='2_strategy.png')
        print("   Strategy clicked, screenshot saved")
    else:
        # Try partial match
        strategy = page.locator('[class*="tab"]', has_text='Strategy')
        if strategy.count() > 0:
            strategy.first.click()
            time.sleep(2)
    
    # Look for Chain & Greeks
    print("3. Looking for Chain & Greeks subtab...")
    chain_tab = page.locator('text=Chain')
    if chain_tab.count() > 0:
        print(f"   Found {chain_tab.count()} matches")
        chain_tab.first.click()
        time.sleep(2)
        page.screenshot(path='3_chain.png')
        print("   Chain clicked, screenshot saved")
    
    # Check for chain-viewer-table-container
    print("4. Checking for chain viewer...")
    cv = page.locator('#chain-viewer-table-container')
    if cv.count() > 0:
        print(f"   Found! Visible: {cv.is_visible()}")
        content = cv.text_content()
        print(f"   Content: {content[:100]}...")
    else:
        print("   NOT FOUND")
        # Check what divs exist
        divs = page.locator('div[id*="chain"]')
        print(f"   Divs with 'chain' in id: {divs.count()}")
        for i in range(divs.count()):
            d = divs.nth(i)
            print(f"      - {d.get_attribute('id')}")
    
    # Try loading data anyway
    print("5. Clicking Load Chain...")
    load_btn = page.locator('#alpaca-load-button')
    if load_btn.is_visible():
        load_btn.click()
        print("   Clicked!")
        time.sleep(6)
        page.screenshot(path='4_after_load.png')
        print("   Screenshot saved")
    
    # Check status
    status = page.locator('#alpaca-status-message')
    if status.is_visible():
        print(f"6. Status: {status.text_content()}")
    
    # Check chain viewer again
    cv = page.locator('#chain-viewer-table-container')
    if cv.count() > 0 and cv.is_visible():
        content = cv.text_content()
        print(f"7. Chain viewer content: {len(content)} chars")
        print(f"   First 200: {content[:200]}")
    
    browser.close()
    print("\nDone! Check screenshots 1-4")
