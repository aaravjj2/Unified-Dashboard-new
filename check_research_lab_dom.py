#!/usr/bin/env python3
"""
Check Research Lab content after clicking.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    # Enable console monitoring
    def log_console(msg):
        if 'research' in msg.text.lower() or 'callback' in msg.text.lower():
            print(f"CONSOLE [{msg.type}]: {msg.text}")
    
    page.on("console", log_console)
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    print("Clicking Research Lab tab...")
    page.click('a[role="tab"]:has-text("Research Lab")')
    time.sleep(3)
    
    # Get the entire Research Lab tab content
    tab_content = page.query_selector('[id*="research-lab"]')
    if tab_content:
        html = tab_content.inner_html()
        print(f"\nResearch Lab content length: {len(html)} chars")
        print("\nFirst 500 chars:")
        print(html[:500])
        print("\n" + "="*80)
    
    # Look specifically for research-lab-content div
    content_div = page.query_selector('#research-lab-content')
    if content_div:
        inner = content_div.inner_html()
        print(f"\n#research-lab-content innerHTML length: {len(inner)} chars")
        print(f"Content: {inner[:500]}")
    else:
        print("\n❌ #research-lab-content div not found!")
    
    # Look for research-lab-tabs
    tabs_div = page.query_selector('#research-lab-tabs')
    if tabs_div:
        print(f"\n✅ #research-lab-tabs found")
        # Get active tab
        active = tabs_div.query_selector('.active')
        if active:
            print(f"Active subtab: {active.inner_text()}")
    else:
        print("\n❌ #research-lab-tabs not found!")
    
    time.sleep(5)
    browser.close()
