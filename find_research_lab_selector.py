#!/usr/bin/env python3
"""
Find Research Lab tab selector.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=300)
    page = browser.new_page()
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    # Find all tabs
    tabs = page.query_selector_all('a[role="tab"]')
    print(f"Found {len(tabs)} tabs:")
    for i, tab in enumerate(tabs):
        tab_text = tab.inner_text()
        tab_id = tab.get_attribute('id') or 'no-id'
        data_rb = tab.get_attribute('data-rb-event-key') or 'no-data-rb'
        print(f"{i+1}. Text: {tab_text[:30]:30} | ID: {tab_id:30} | data-rb-event-key: {data_rb}")
    
    print("\n" + "="*80)
    print("Clicking Research Lab tab by text...")
    research_tab = page.locator('a[role="tab"]:has-text("Research Lab")')
    if research_tab.count() > 0:
        research_tab.click()
        time.sleep(2)
        print("✅ Clicked Research Lab tab")
        
        # Find subtabs
        subtabs = page.query_selector_all('a[data-rb-event-key]')
        print(f"\nFound {len(subtabs)} subtabs:")
        for i, subtab in enumerate(subtabs):
            text = subtab.inner_text()
            key = subtab.get_attribute('data-rb-event-key')
            print(f"{i+1}. {text:30} | {key}")
    
    time.sleep(5)
    browser.close()
