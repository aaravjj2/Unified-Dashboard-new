#!/usr/bin/env python3
"""Check what's actually in the DOM."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("Loading page...")
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    # Take screenshot of initial state
    page.screenshot(path='initial_state.png')
    print("Screenshot: initial_state.png")
    
    # Find all tabs
    print("\n=== TAB LINKS (role=tab) ===")
    tabs = page.locator('[role="tab"]')
    count = tabs.count()
    print(f"Found {count} tabs")
    for i in range(count):
        tab = tabs.nth(i)
        text = tab.text_content().strip()
        print(f"  {i}: {text}")
    
    # Find main tabs by class
    print("\n=== MAIN TABS (.nav-link) ===")
    nav_links = page.locator('.nav-link')
    count = nav_links.count()
    print(f"Found {count} nav links")
    for i in range(min(count, 20)):
        link = nav_links.nth(i)
        text = link.text_content().strip()
        if text:
            print(f"  {i}: {text}")
    
    # Check if chain viewer exists
    print("\n=== CHAIN VIEWER ===")
    chain_viewer = page.locator('#chain-viewer-table-container')
    print(f"Chain viewer exists: {chain_viewer.count() > 0}")
    
    # Check load button
    print("\n=== LOAD BUTTON ===")
    load_btn = page.locator('#alpaca-load-button')
    print(f"Load button visible: {load_btn.is_visible()}")
    
    browser.close()
