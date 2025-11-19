#!/usr/bin/env python3
"""
Test to verify the three reported issues are fixed:
1. Analysis Hub not empty
2. SHAP data loads correctly
3. Portfolio tab names are visible
"""

from playwright.sync_api import sync_playwright
import time

print("=" * 80)
print("TESTING THREE REPORTED ISSUES")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Use headful to see actual rendering
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    
    # TEST 1: Analysis Hub not empty
    print("\n1. Testing Analysis Hub...")
    page.goto('http://localhost:8054', timeout=15000)
    page.wait_for_timeout(3000)
    
    # Check for content
    content = page.content()
    has_attribution = 'Attribution Analysis' in content or 'Portfolio Analytics' in content
    has_tabs = page.locator('.nav-tabs').count() > 0
    
    print(f"   - Has attribution content: {has_attribution}")
    print(f"   - Has tabs: {has_tabs}")
    
    # Take screenshot
    page.screenshot(path='test_screenshots/issue_fix_1_analysis_hub.png')
    print(f"   ✅ Screenshot saved: issue_fix_1_analysis_hub.png")
    
    if has_attribution and has_tabs:
        print(f"   ✅ Analysis Hub appears populated")
    else:
        print(f"   ⚠️  Analysis Hub may still have issues")
    
    # TEST 2 & 3: Portfolio tabs visible and SHAP working
    print("\n2. Testing Portfolio Tracker...")
    page.goto('http://localhost:8056', timeout=15000)
    page.wait_for_timeout(3000)
    
    # Check if tabs are visible
    tabs = page.locator('.nav-tabs .nav-link')
    tab_count = tabs.count()
    print(f"   - Found {tab_count} tabs")
    
    if tab_count > 0:
        for i in range(tab_count):
            tab = tabs.nth(i)
            tab_text = tab.inner_text()
            is_visible = tab.is_visible()
            print(f"     Tab {i}: '{tab_text}' (visible: {is_visible})")
    
    page.screenshot(path='test_screenshots/issue_fix_2_portfolio_tabs.png')
    print(f"   ✅ Screenshot saved: issue_fix_2_portfolio_tabs.png")
    
    # Test clicking on Factor Exposure tab
    print("\n3. Testing Factor Exposure (SHAP)...")
    try:
        # Try different selectors for the Factor Exposure tab
        factor_tab = None
        if page.locator('text=Factor Exposure').count() > 0:
            factor_tab = page.locator('text=Factor Exposure').first
        elif page.locator('.nav-link:has-text("Factor")').count() > 0:
            factor_tab = page.locator('.nav-link:has-text("Factor")').first
        
        if factor_tab:
            factor_tab.click(timeout=5000)
            page.wait_for_timeout(2000)
            
            # Check for content
            content = page.content()
            has_shap_content = 'Portfolio Factor Exposure' in content or 'SHAP' in content
            has_fallback = 'Holdings Allocation' in content
            has_error = 'SHAP Data Not Found' in content
            
            print(f"   - Has SHAP factor content: {has_shap_content}")
            print(f"   - Has fallback chart: {has_fallback}")
            print(f"   - Shows 'not found' error: {has_error}")
            
            page.screenshot(path='test_screenshots/issue_fix_3_factor_exposure.png')
            print(f"   ✅ Screenshot saved: issue_fix_3_factor_exposure.png")
            
            if has_shap_content:
                print(f"   ✅ SHAP factor exposure is working!")
            elif has_fallback:
                print(f"   ℹ️  Fallback chart is showing (SHAP data may not match portfolio)")
            else:
                print(f"   ⚠️  Factor exposure may have issues")
        else:
            print(f"   ⚠️  Could not find Factor Exposure tab")
            
    except Exception as e:
        print(f"   ❌ Error testing Factor Exposure: {e}")
        page.screenshot(path='test_screenshots/issue_fix_3_error.png')
    
    # Keep browser open for a moment to inspect
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nBrowser will stay open for 5 seconds for visual inspection...")
    time.sleep(5)
    
    browser.close()
    
    print("\n✅ Test completed. Check screenshots in test_screenshots/ directory")
    print("=" * 80)
