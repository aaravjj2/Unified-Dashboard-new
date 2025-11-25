#!/usr/bin/env python3
"""
Click Research Lab and watch for callback firing.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=1000)
    page = browser.new_page()
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    print("Clicking Research Lab tab...")
    page.click('a[role="tab"]:has-text("Research Lab")')
    
    print("Waiting for callback to fire...")
    time.sleep(3)
    
    # Click a subtab
    print("\nClicking Market Scan subtab...")
    page.click('a[role="tab"]:has-text("Market Scan")')
    
    print("Waiting...")
    time.sleep(3)
    
    # Click another subtab
    print("\nClicking Research Notes subtab...")
    page.click('a[role="tab"]:has-text("Research Notes")')
    
    print("Waiting...")
    time.sleep(3)
    
    # Check content
    content = page.query_selector('#research-lab-content')
    if content:
        html = content.inner_html()
        print(f"\nContent length: {len(html)} chars")
        if len(html) > 0:
            print(f"First 200 chars: {html[:200]}")
    
    time.sleep(5)
    browser.close()
