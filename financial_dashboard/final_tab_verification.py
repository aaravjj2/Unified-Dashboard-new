#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

print("="*70)
print("COMPREHENSIVE TAB VERIFICATION TEST")
print("="*70)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    page.goto('http://localhost:8000', wait_until='networkidle', timeout=60000)
    page.wait_for_selector('a[role="tab"]', timeout=10000)
    time.sleep(2)
    
    tabs = page.locator('a[id^="react-aria"][id*="-1-tab-"][role="tab"]').all()
    
    tab_names = [
        ("Market Trends", 0),
        ("Market Forecast", 1),
        ("Monthly Picks", 2),
        ("Weekly Picks", 3),
        ("Analysis Hub", 4),
        ("Portfolio Dashboard", 5),
        ("Research Lab", 6)
    ]
    
    for name, idx in tab_names:
        tabs[idx].click()
        time.sleep(2)
        
        error_count = page.locator('text=/Internal Server Error/i').count()
        visible_text = page.locator('body').text_content()[:500]
        
        print(f"\n{name} (index {idx}):")
        print(f"  Status: {'✗ ERROR' if error_count > 0 else '✓ OK'}")
        if error_count > 0:
            print(f"  Error count: {error_count}")
            errors = page.locator('text=/Internal Server Error/i').all()
            for i, err in enumerate(errors[:2]):
                print(f"  Error {i+1}: {err.text_content()[:100]}")
    
    # Special check for Portfolio subtabs
    print("\n" + "-"*70)
    print("PORTFOLIO SUBTABS:")
    print("-"*70)
    
    tabs[5].click()
    time.sleep(2)
    
    # Get Portfolio subtabs
    subtabs = page.locator('a[id^="react-aria"][id*="-3-tab-"][role="tab"]').all()
    subtab_names = ["Holdings", "Orders", "Analytics"]
    
    for name, idx in zip(subtab_names, range(len(subtabs))):
        if idx < len(subtabs):
            subtabs[idx].click()
            time.sleep(1)
            
            error_count = page.locator('text=/Error:/').count()
            print(f"\n  {name} subtab (index {idx}):")
            print(f"    Status: {'✗ ERROR' if error_count > 0 else '✓ OK'}")
            if error_count > 0:
                errors = page.locator('text=/Error:/').all()
                for i, err in enumerate(errors[:2]):
                    print(f"    Error: {err.text_content()[:150]}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    browser.close()
