#!/usr/bin/env python3
"""Quick test to check Analysis Hub content"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Loading analysis hub page...")
    page.goto('http://localhost:8050', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(5000)
    
    print("\nChecking for welcome panel...")
    welcome = page.locator('#attr-initial-instructions')
    if welcome.count() > 0:
        visible = welcome.is_visible()
        text = welcome.text_content()
        print(f"Welcome panel exists: {welcome.count()} elements")
        print(f"Visible: {visible}")
        print(f"Text: {text[:200]}")
        if visible and len(text) > 50:
            print("\n✅ SUCCESS: Welcome panel is visible!")
        else:
            print("\n❌ FAIL: Welcome panel exists but not visible or empty")
    else:
        print("❌ FAIL: Welcome panel not found")
    
    print("\nChecking page content...")
    body_text = page.locator('body').text_content()
    if 'Welcome to Attribution Analysis' in body_text:
        print("✅ Welcome text found in page")
    elif len(body_text) < 100:
        print(f"❌ Page appears empty ({len(body_text)} chars)")
    else:
        print(f"⚠️  Page has content ({len(body_text)} chars) but no welcome message")
        print(f"Sample: {body_text[:300]}")
    
    browser.close()
