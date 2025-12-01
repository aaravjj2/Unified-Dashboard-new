#!/usr/bin/env python3
"""
Browser test - Open dashboard and verify all tabs load without 500 errors
"""
from playwright.sync_api import sync_playwright
import time

print("\n" + "="*70)
print("BROWSER TEST - Checking for 500 Internal Server Errors")
print("="*70 + "\n")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    # Track HTTP responses for 500 errors
    errors_500 = []
    
    def check_response(response):
        if response.status == 500:
            errors_500.append({
                'url': response.url,
                'status': response.status
            })
    
    page.on('response', check_response)
    
    print("Loading dashboard...")
    page.goto('http://localhost:8000', wait_until='networkidle', timeout=60000)
    page.wait_for_selector('a[role="tab"]', timeout=10000)
    time.sleep(2)
    print("✓ Dashboard loaded\n")
    
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
    
    print("Testing all main tabs:\n")
    
    for name, idx in tab_names:
        errors_500.clear()  # Clear for each tab
        
        print(f"  {idx+1}. {name}...", end=" ")
        tabs[idx].click()
        time.sleep(2)
        
        if errors_500:
            print(f"✗ 500 ERROR")
            for err in errors_500:
                print(f"     URL: {err['url']}")
        else:
            print("✓ OK")
    
    # Test Portfolio subtabs
    print("\nTesting Portfolio subtabs:\n")
    tabs[5].click()
    time.sleep(2)
    
    subtabs = page.locator('a[id^="react-aria"][id*="-3-tab-"][role="tab"]').all()
    subtab_names = ["Holdings", "Orders", "Analytics"]
    
    for name, idx in zip(subtab_names, range(len(subtabs))):
        if idx < len(subtabs):
            errors_500.clear()
            
            print(f"    {name}...", end=" ")
            subtabs[idx].click()
            time.sleep(1)
            
            if errors_500:
                print(f"✗ 500 ERROR")
                for err in errors_500:
                    print(f"       URL: {err['url']}")
            else:
                print("✓ OK")
    
    browser.close()
    
    print("\n" + "="*70)
    if not errors_500:
        print("✅ SUCCESS - No 500 errors detected!")
    else:
        print("❌ FAILURE - 500 errors found")
    print("="*70 + "\n")
