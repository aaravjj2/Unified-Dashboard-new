#!/usr/bin/env python3
"""Final proof that chain viewer is working."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("="*60)
    print("CHAIN VIEWER FIX VERIFICATION")
    print("="*60)
    
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    # Navigate to Strategy > Chain & Greeks
    page.locator('text=Strategy').first.click()
    time.sleep(1)
    page.locator('text=Chain').first.click()
    time.sleep(2)
    
    # Check initial state
    cv = page.locator('#chain-viewer-table-container')
    initial = cv.text_content() if cv.is_visible() else ""
    print(f"\n1. BEFORE Load Chain:")
    print(f"   Content length: {len(initial)} chars")
    print(f"   Shows placeholder: {'Click' in initial or len(initial) < 500}")
    
    # Click Load Chain
    page.locator('#alpaca-load-button').click()
    time.sleep(7)
    
    # Check final state
    final = cv.text_content() if cv.is_visible() else ""
    print(f"\n2. AFTER Load Chain:")
    print(f"   Content length: {len(final)} chars")
    print(f"   Has real data: {len(final) > 1000}")
    
    # Status check
    status = page.locator('#alpaca-status-message')
    status_text = status.text_content() if status.is_visible() else ""
    print(f"\n3. Status Message:")
    print(f"   {status_text}")
    
    # Take proof screenshot
    page.screenshot(path='CHAIN_VIEWER_FIXED_PROOF.png', full_page=True)
    
    print("\n" + "="*60)
    if len(final) > 1000 and "Successfully loaded" in status_text:
        print("✅ CHAIN VIEWER FIX VERIFIED - WORKING!")
    else:
        print("❌ CHAIN VIEWER STILL BROKEN")
    print("="*60)
    print("\n📸 Screenshot: CHAIN_VIEWER_FIXED_PROOF.png")
    
    browser.close()
