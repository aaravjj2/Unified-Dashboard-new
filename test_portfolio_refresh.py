#!/usr/bin/env python3
"""
Test Portfolio refresh button to verify button click functionality.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    # Monitor console for errors
    errors = []
    def handle_console(msg):
        if msg.type in ['error', 'warning']:
            errors.append(f"[{msg.type}] {msg.text}")
    page.on("console", handle_console)
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    print("Clicking Portfolio tab...")
    page.click('a[role="tab"]:has-text("Portfolio")')
    time.sleep(2)
    
    # Click Current Positions subtab
    print("Clicking Current Positions subtab...")
    try:
        page.click('a[role="tab"]:has-text("Positions")', timeout=5000)
        time.sleep(1)
    except:
        print("⚠️ Positions tab not found, trying alternative...")
        pass
    
    # Look for refresh button
    print("\nLooking for Refresh button...")
    refresh_selectors = [
        '#portfolio-refresh-btn',
        '#portfolio-positions-refresh-btn',
        'button:has-text("Refresh")',
        'button:has-text("🔄")'
    ]
    
    refresh_btn = None
    for selector in refresh_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=1000):
                refresh_btn = btn
                print(f"✅ Found refresh button: {selector}")
                break
        except:
            continue
    
    if refresh_btn:
        print("\nClicking Refresh button...")
        refresh_btn.click()
        time.sleep(3)
        
        # Check for position entries
        print("\nChecking for position entries...")
        rows = page.locator('tr').all()
        print(f"Found {len(rows)} table rows")
        
        # Look for ticker symbols
        text = page.locator('body').inner_text()
        tickers = ['INTC', 'AAPL', 'MSFT', 'NVDA']
        found_tickers = [t for t in tickers if t in text]
        print(f"Found tickers: {found_tickers}")
        
        if len(found_tickers) >= 3:
            print("\n✅ SUCCESS: Buttons work! Found 3+ positions")
        elif len(found_tickers) == 1 and 'INTC' in found_tickers:
            print("\n❌ BUTTONS BROKEN: Only INTC showing (cached data)")
        else:
            print(f"\n⚠️ UNCLEAR: Found {len(found_tickers)} tickers")
    else:
        print("\n❌ No refresh button found!")
    
    print(f"\nConsole errors: {len(errors)}")
    if errors:
        print("First 5 errors:")
        for err in errors[:5]:
            print(f"  {err[:100]}")
    
    time.sleep(3)
    browser.close()
