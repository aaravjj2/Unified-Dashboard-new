"""Debug script to capture tab labels in Options Lab."""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Navigate to dashboard
    page.goto("http://localhost:8000", wait_until="domcontentloaded")
    time.sleep(3)
    
    # Click Options Lab
    page.click('text="💹 Options Lab"', timeout=10000)
    time.sleep(5)  # Give extra time for sub-tabs to render
    
    # Look for all clickable tab-like elements
    print("Looking for tabs and labels...")
    
    # Try different selectors
    selectors_to_try = [
        'a[role="tab"]',
        '[role="tab"]',
        '.nav-link',
        'button[role="tab"]',
        '[id*="tab"]',
        'text=/Manual Trade|P&L|Strategy/',
    ]
    
    for selector in selectors_to_try:
        try:
            elements = page.locator(selector).all()
            if elements:
                print(f"\n{selector}: Found {len(elements)} elements")
                for i, el in enumerate(elements[:10]):  # Limit to 10
                    try:
                        text = el.inner_text(timeout=1000)
                        if text.strip():
                            print(f"  [{i}] {text[:80]}")
                    except:
                        pass
        except Exception as e:
            pass
    
    # Get all text content to search
    print("\n--- Searching for sub-tab keywords in page text ---")
    try:
        body_text = page.locator('body').inner_text(timeout=5000)
        keywords = ['Manual Trade', 'Strategy Monitor', 'P&L Analyzer', 'Strategy Creator']
        for kw in keywords:
            if kw in body_text:
                print(f"✓ Found: {kw}")
            else:
                print(f"✗ Missing: {kw}")
    except:
        print("Could not get body text")
    
    browser.close()
