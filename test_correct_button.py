#!/usr/bin/env python3
"""
Test Portfolio with correct button ID.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    print("Clicking Portfolio tab...")
    page.click('a[role="tab"]:has-text("Portfolio")')
    time.sleep(2)
    
    # Click Positions subtab
    print("Clicking Positions subtab...")
    page.click('a[role="tab"]:has-text("Positions")')
    time.sleep(2)
    
    # Try the correct button ID
    print("\nTrying portfolio-positions-refresh-btn...")
    try:
        btn = page.locator('#portfolio-positions-refresh-btn')
        if btn.is_visible():
            print("✅ Found portfolio-positions-refresh-btn")
            btn.click()
            time.sleep(4)
            
            # Check results
            text = page.locator('body').inner_text()
            tickers = ['INTC', 'AAPL', 'MSFT', 'NVDA', 'TSLA']
            found = [t for t in tickers if t in text]
            print(f"\nFound tickers: {found}")
            print(f"Count: {len(found)}")
            
            if len(found) >= 3:
                print("\n✅ SUCCESS: Buttons work!")
            else:
                print("\n❌ STILL BROKEN")
        else:
            print("❌ Button not visible")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(3)
    browser.close()
