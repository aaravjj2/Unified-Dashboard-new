#!/usr/bin/env python3
"""
Debug script to inspect tab structure and find Strategy Lab tab selector
"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8050"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # Navigate
    page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
    time.sleep(5)
    
    # Save page HTML
    html = page.content()
    with open('test-artifacts/dashboard_structure.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Saved HTML to test-artifacts/dashboard_structure.html")
    
    # Try to find all tabs
    print("\n🔍 Searching for tabs...")
    
    # Method 1: Look for all buttons with role="tab"
    tabs = page.locator('button[role="tab"]').all()
    print(f"\nFound {len(tabs)} buttons with role='tab':")
    for i, tab in enumerate(tabs):
        try:
            text = tab.inner_text()
            print(f"  {i+1}. {text}")
        except:
            print(f"  {i+1}. (could not get text)")
    
    # Method 2: Look for all <a> tags that might be tabs
    links = page.locator('a.nav-link').all()
    print(f"\nFound {len(links)} <a> tags with class='nav-link':")
    for i, link in enumerate(links):
        try:
            text = link.inner_text()
            print(f"  {i+1}. {text}")
        except:
            print(f"  {i+1}. (could not get text)")
    
    # Method 3: Look for Strategy Lab specifically
    print("\n🎯 Searching for 'Strategy Lab' text...")
    strategy_elements = page.locator('text=/Strategy Lab/i').all()
    print(f"Found {len(strategy_elements)} elements containing 'Strategy Lab':")
    for i, elem in enumerate(strategy_elements):
        try:
            tag = elem.evaluate('el => el.tagName')
            text = elem.inner_text()
            classes = elem.evaluate('el => el.className')
            elem_id = elem.evaluate('el => el.id')
            print(f"  {i+1}. <{tag}> id='{elem_id}' class='{classes}' text='{text}'")
        except Exception as e:
            print(f"  {i+1}. Error: {e}")
    
    # Method 4: Get all tab IDs from dbc.Tabs structure
    print("\n📋 Looking for dbc.Tabs container...")
    tabs_container = page.locator('[class*="nav-tabs"]').first
    if tabs_container.count() > 0:
        print("✅ Found nav-tabs container")
        all_children = tabs_container.locator('*').all()
        print(f"   Contains {len(all_children)} child elements")
    
    print("\n⏸️  Browser will stay open for 30 seconds for manual inspection...")
    time.sleep(30)
    
    browser.close()
