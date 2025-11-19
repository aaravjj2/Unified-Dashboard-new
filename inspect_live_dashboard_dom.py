#!/usr/bin/env python3
"""Quick DOM inspector to see actual dashboard structure"""

from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Loading dashboard...")
    page.goto("http://localhost:8050", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)
    
    # Take screenshot
    page.screenshot(path="dashboard_dom_debug.png", full_page=False)
    print("Screenshot saved")
    
    # Get all nav elements
    nav_elements = page.locator("nav").all()
    print(f"\nFound {len(nav_elements)} <nav> elements")
    
    for i, nav in enumerate(nav_elements):
        print(f"\n--- NAV {i} ---")
        print(f"Class: {nav.get_attribute('class')}")
        print(f"ID: {nav.get_attribute('id')}")
        inner = nav.inner_html()[:500]
        print(f"Inner HTML (first 500 chars):\n{inner}\n")
    
    # Try different selectors
    selectors_to_test = [
        "nav a",
        "a.nav-link",
        "[role='tab']",
        "div[role='tablist'] a",
        "ul.nav a",
        ".tabs a",
    ]
    
    print("\n\n=== TESTING SELECTORS ===")
    for selector in selectors_to_test:
        try:
            elements = page.locator(selector).all()
            print(f"\n✅ '{selector}' → {len(elements)} elements")
            if elements:
                first = elements[0]
                print(f"   First element text: {first.inner_text()[:50]}")
                print(f"   First element class: {first.get_attribute('class')}")
        except Exception as e:
            print(f"❌ '{selector}' → ERROR: {str(e)[:80]}")
    
    browser.close()
