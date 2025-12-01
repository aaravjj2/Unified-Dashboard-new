#!/usr/bin/env python
"""Debug: Check if dropdown options are populated."""
from playwright.sync_api import sync_playwright
import time

def check_dropdowns():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Navigate to Options Lab
        page.click('#tab-options_lab')
        time.sleep(1)
        
        # Load SPY
        page.fill('#options-ticker-input', 'SPY')
        page.click('#options-load-btn')
        time.sleep(4)
        
        status = page.locator('#options-status-message').inner_text()
        print(f"\nStatus: {status}")
        
        # Click Manual Trade
        page.click('#options-manual-tab')
        time.sleep(2)
        
        # Check expiration dropdown
        print("\n📅 Expiration dropdown:")
        try:
            exp_options = page.locator('#sim-expiration-dropdown option').all_inner_texts()
            print(f"   Options count: {len(exp_options)}")
            for i, opt in enumerate(exp_options[:5]):
                print(f"   {i+1}. {opt}")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Select first expiration
        if len(exp_options) > 0:
            page.select_option('#sim-expiration-dropdown', index=0)
            time.sleep(1)
            
            # Check strike dropdown
            print("\n💰 Strike dropdown:")
            try:
                strike_options = page.locator('#sim-strike-dropdown option').all_inner_texts()
                print(f"   Options count: {len(strike_options)}")
                for i, opt in enumerate(strike_options[:5]):
                    print(f"   {i+1}. {opt}")
            except Exception as e:
                print(f"   ⚠️ Error: {e}")
        
        time.sleep(5)
        browser.close()

if __name__ == '__main__':
    check_dropdowns()
