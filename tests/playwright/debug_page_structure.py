#!/usr/bin/env python3
"""Debug: Inspect page structure"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8050"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
    time.sleep(5)
    
    # Save full page screenshot
    page.screenshot(path='test-artifacts/debug_full_page.png', full_page=True)
    
    # Get all links
    links = page.locator('a').all()
    print(f"Found {len(links)} links:")
    for i, link in enumerate(links[:20]):
        href = link.get_attribute('href')
        text = link.inner_text()[:50] if link.inner_text() else ''
        print(f"  {i+1}. href='{href}' text='{text}'")
    
    # Get all buttons
    buttons = page.locator('button').all()
    print(f"\nFound {len(buttons)} buttons:")
    for i, btn in enumerate(buttons[:20]):
        text = btn.inner_text()[:50] if btn.inner_text() else ''
        btn_id = btn.get_attribute('id')
        print(f"  {i+1}. id='{btn_id}' text='{text}'")
    
    # Save HTML
    html = page.content()
    with open('test-artifacts/debug_page.html', 'w') as f:
        f.write(html)
    
    print("\n✅ Debug artifacts saved")
    print("  - test-artifacts/debug_full_page.png")
    print("  - test-artifacts/debug_page.html")
    
    input("\nPress Enter to close browser...")
    browser.close()
