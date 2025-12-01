#!/usr/bin/env python3
"""
Test Research Lab with inline content.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    print("Clicking Research Lab tab...")
    page.click('a[role="tab"]:has-text("Research Lab")')
    time.sleep(2)
    
    # Check for visible content in each subtab
    subtabs = [
        ("Market Scan", "market-scan"),
        ("Factor Analysis", "factor-analysis"),
        ("Research Notes", "research-notes")
    ]
    
    for label, tab_id in subtabs:
        print(f"\nClicking {label} subtab...")
        page.click(f'a[role="tab"]:has-text("{label}")')
        time.sleep(1)
        
        # Check for content
        content = page.locator(f'#react-aria').inner_text()
        has_content = len(content) > 50
        print(f"  Content found: {'✅ YES' if has_content else '❌ NO'} ({len(content)} chars)")
        
        if has_content:
            print(f"  First 100 chars: {content[:100]}")
    
    time.sleep(3)
    browser.close()
    print("\n✅ Test completed!")
