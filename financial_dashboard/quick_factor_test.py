#!/usr/bin/env python3
"""Quick test to check Factor Exposure content"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Loading portfolio page...")
    page.goto('http://localhost:8056', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(5000)  # Wait for Dash to initialize
    
    print("Looking for Factor Exposure tab...")
    tabs = page.locator('.nav-link').all()
    print(f"Found {len(tabs)} tabs")
    
    factor_tab = None
    for i, tab in enumerate(tabs):
        text = tab.text_content()
        print(f"  Tab {i}: {text}")
        if 'Factor' in text or 'factor' in text:
            factor_tab = tab
            print(f"  -> Found Factor tab at position {i}")
            break
    
    if factor_tab:
        print("\nClicking Factor Exposure tab...")
        factor_tab.click()
        page.wait_for_timeout(3000)
        
        print("\nChecking content...")
        content = page.locator('#portfolio-factor-exposure-content').text_content()
        if content:
            print(f"Content length: {len(content)} characters")
            print(f"First 500 chars: {content[:500]}")
            
            if 'No SHAP' in content or 'No positions' in content:
                print("\n❌ FAIL: Still showing error message")
            elif len(content) > 100:
                print("\n✅ SUCCESS: Factor Exposure has content!")
            else:
                print("\n⚠️  UNCLEAR: Content exists but very short")
        else:
            print("❌ No content found")
    else:
        print("❌ Could not find Factor Exposure tab")
    
    browser.close()
