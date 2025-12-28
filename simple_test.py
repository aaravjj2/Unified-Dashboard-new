#!/usr/bin/env python3
"""Test the load button by simulating the callback"""
from playwright.sync_api import sync_playwright
import time
import json

print("Starting browser test...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    # Enable console logging
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    
    print("\n1. Loading page...")
    page.goto("http://localhost:8053")
    time.sleep(5)
    
    print("\n2. Filling ticker...")
    page.fill("#alpaca-ticker-input", "SPY")
    time.sleep(1)
    
    print("\n3. Clicking load button...")
    page.click("#alpaca-load-button")
    time.sleep(8)
    
    print("\n4. Checking status...")
    status = page.locator("#alpaca-status-message").inner_text()
    print(f"   Status: '{status}'")
    
    print("\n5. Checking table...")
    table_visible = page.locator("#alpaca-table-container").is_visible()
    print(f"   Table visible: {table_visible}")
    
    if table_visible:
        table_html = page.locator("#alpaca-table-container").inner_html()
        print(f"   Table HTML length: {len(table_html)}")
        if "DataTable" in table_html or "table" in table_html.lower():
            print("   ✅ Table has content!")
        else:
            print("   ⚠️ Table container visible but no table inside")
            print(f"   Content preview: {table_html[:300]}")
    
    print("\n6. Taking screenshot...")
    page.screenshot(path="test_result.png", full_page=True)
    
    print("\n7. Waiting 5 seconds...")
    time.sleep(5)
    
    browser.close()
    print("\n✅ Test complete!")
