#!/usr/bin/env python3
"""
Extract exact component IDs from rendered HTML.
"""

from playwright.sync_api import sync_playwright
import time
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=300)
    page = browser.new_page()
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    print("Clicking Research Lab tab...")
    page.click('a[role="tab"]:has-text("Research Lab")')
    time.sleep(2)
    
    # Get all HTML
    html = page.content()
    
    # Find research-lab IDs
    print("\n" + "="*80)
    print("Searching for 'research-lab' IDs in HTML:")
    print("="*80)
    
    # Pattern: id="research-lab-something"
    ids = re.findall(r'id="(research-lab[^"]*)"', html)
    if ids:
        print(f"Found {len(ids)} IDs containing 'research-lab':")
        for id_val in set(ids):
            print(f"  - {id_val}")
    else:
        print("❌ No IDs containing 'research-lab' found!")
    
    # Check if the tabs element exists with correct ID
    tabs_elem = page.query_selector('#research-lab-tabs')
    if tabs_elem:
        print(f"\n✅ Element with id='research-lab-tabs' found!")
        print(f"   Tag: {tabs_elem.evaluate('el => el.tagName')}")
        print(f"   Class: {tabs_elem.get_attribute('class')}")
    else:
        print(f"\n❌ No element with id='research-lab-tabs'!")
    
    # Check content div
    content_elem = page.query_selector('#research-lab-content')
    if content_elem:
        print(f"\n✅ Element with id='research-lab-content' found!")
        print(f"   Tag: {content_elem.evaluate('el => el.tagName')}")
        print(f"   innerHTML length: {len(content_elem.inner_html())}")
    else:
        print(f"\n❌ No element with id='research-lab-content'!")
    
    time.sleep(3)
    browser.close()
