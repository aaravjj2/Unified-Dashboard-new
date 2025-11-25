#!/usr/bin/env python3
"""
Test to verify tabs and SHAP by actually browsing to the page and triggering callbacks
"""

from playwright.sync_api import sync_playwright
import time
import json

print("=" * 80)
print("FINAL VERIFICATION TEST")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context(viewport={'width': 1600, 'height': 1000})
    page = context.new_page()
    
    # Enable console logging
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    
    print("\n1. Loading Portfolio Tracker...")
    page.goto('http://localhost:8056', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(5000)  # Wait for Dash to initialize
    
    # Take initial screenshot
    page.screenshot(path='test_screenshots/final_verify_01_initial.png', full_page=True)
    print("   Screenshot saved: final_verify_01_initial.png")
    
    # Check for tabs
    print("\n2. Checking for tab elements...")
    tab_containers = page.locator('.nav-tabs').count()
    print(f"   Found {tab_containers} tab container(s)")
    
    if tab_containers > 0:
        # Try to find all nav-link elements
        nav_links = page.locator('.nav-link').all()
        print(f"   Found {len(nav_links)} nav-link elements")
        
        for i, link in enumerate(nav_links):
            try:
                text = link.inner_text(timeout=1000)
                is_visible = link.is_visible()
                print(f"     Link {i}: text='{text}', visible={is_visible}")
            except:
                print(f"     Link {i}: <error reading text>")
    
    # Wait for any dynamic content to load
    print("\n3. Waiting for data to load...")
    page.wait_for_timeout(5000)
    
    # Try to click on tab by index (since labels might be empty)
    print("\n4. Attempting to click tabs...")
    for i in range(5):  # Try first 5 tabs
        try:
            tab = page.locator('.nav-link').nth(i)
            if tab.is_visible():
                print(f"   Clicking tab {i}...")
                tab.click(timeout=2000)
                page.wait_for_timeout(2000)
                page.screenshot(path=f'test_screenshots/final_verify_tab_{i}.png', full_page=True)
                print(f"   Screenshot saved: final_verify_tab_{i}.png")
                
                # Check for specific content
                content = page.content()
                if i == 3:  # Factor Exposure should be 4th tab (index 3)
                    if 'Portfolio Factor Exposure' in content:
                        print(f"   ✅ Tab {i}: SHAP factor chart found!")
                    elif 'Holdings Allocation' in content:
                        print(f"   ℹ️  Tab {i}: Fallback chart found")
                    elif 'SHAP Data Not Found' in content:
                        print(f"   ⚠️  Tab {i}: SHAP data not found message")
                    else:
                        print(f"   Tab {i}: Content unclear")
        except Exception as e:
            print(f"   Tab {i}: Error - {str(e)[:100]}")
    
    # Check Analysis Hub
    print("\n5. Checking Analysis Hub...")
    page.goto('http://localhost:8054', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(5000)
    page.screenshot(path='test_screenshots/final_verify_analysis_hub.png', full_page=True)
    
    content = page.content()
    has_config = 'Analysis Configuration' in content or 'Attribution Analysis' in content
    has_tabs = page.locator('.nav-tabs').count() > 0
    
    print(f"   Has configuration section: {has_config}")
    print(f"   Has tabs: {has_tabs}")
    print("   Screenshot saved: final_verify_analysis_hub.png")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nCheck test_screenshots/ for visual verification")
    print("Browser will stay open for 10 seconds...")
    time.sleep(10)
    
    browser.close()
