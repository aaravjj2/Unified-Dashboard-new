#!/usr/bin/env python
"""Test Manual Trade tab to check P&L calculation."""
from playwright.sync_api import sync_playwright
import time

def test_manual_trade():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Navigate to Options Lab
        print("\n1. Clicking Options Lab...")
        page.click('#tab-options_lab')
        time.sleep(1)
        
        # Load chain data
        print("2. Loading SPY chain...")
        page.fill('#options-ticker-input', 'SPY')
        time.sleep(0.5)
        page.click('#options-load-btn')
        time.sleep(3)
        
        # Check status
        status = page.locator('#options-status-message').inner_text()
        print(f"   Status: {status}")
        
        # Navigate to Manual Trade tab
        print("\n3. Clicking Manual Trade tab...")
        page.click('#options-manual-tab')
        time.sleep(2)
        
        # Check what's visible on Manual Trade tab
        print("\n4. Checking Manual Trade UI...")
        
        # Look for contract selection dropdown
        try:
            contract_dropdown = page.locator('#manual-contract-dropdown')
            is_visible = contract_dropdown.is_visible()
            print(f"   Contract dropdown visible: {is_visible}")
            
            if is_visible:
                # Get available options
                options = page.locator('#manual-contract-dropdown option').all_inner_texts()
                print(f"   Available contracts: {len(options)}")
                if options:
                    print(f"   First contract: {options[0][:100]}...")
        except Exception as e:
            print(f"   ⚠️ Contract dropdown error: {e}")
        
        # Check for P&L display
        try:
            pnl_divs = page.locator('[id*="pnl"], [id*="profit"]').all()
            print(f"\n5. P&L related elements: {len(pnl_divs)}")
            for i, div in enumerate(pnl_divs[:5]):
                elem_id = div.get_attribute('id')
                print(f"   - {elem_id}")
        except Exception as e:
            print(f"   ⚠️ P&L check error: {e}")
        
        # Take screenshot
        page.screenshot(path='/home/aarav/unified-dashboard/manual_trade_screenshot.png')
        print("\n📸 Screenshot saved to manual_trade_screenshot.png")
        
        print("\n6. Keeping browser open for 10 seconds for inspection...")
        time.sleep(10)
        
        browser.close()

if __name__ == '__main__':
    test_manual_trade()
