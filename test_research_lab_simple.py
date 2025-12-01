#!/usr/bin/env python3
"""
Test Research Lab with inline content - simple version.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=800)
    page = browser.new_page()
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    print("Clicking Research Lab tab...")
    page.click('a[role="tab"]:has-text("Research Lab")')
    time.sleep(2)
    
    print("\nClicking Market Scan subtab...")
    page.click('a[role="tab"]:has-text("Market Scan")')
    time.sleep(2)
    
    # Check if "Market Scan" heading is visible
    heading = page.locator('h4:has-text("Market Scan")')
    if heading.is_visible():
        print("✅ Market Scan content is visible!")
    else:
        print("❌ Market Scan content NOT visible")
    
    print("\nClicking Research Notes subtab...")
    page.click('a[role="tab"]:has-text("Research Notes")')
    time.sleep(2)
    
    # Check for Research Notes content
    refresh_btn = page.locator('button:has-text("Refresh")')
    if refresh_btn.is_visible():
        print("✅ Research Notes content is visible!")
    else:
        print("❌ Research Notes content NOT visible")
    
    time.sleep(3)
    browser.close()
    print("\n✅ Test completed!")
