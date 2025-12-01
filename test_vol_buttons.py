#!/usr/bin/env python
"""Test actual Volatility Lab buttons with correct IDs."""
from playwright.sync_api import sync_playwright
import time

def test_vol_lab_buttons():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Navigate to Volatility Lab
        print("\n1. Clicking Volatility Lab...")
        page.click('#tab-volatility_lab')
        time.sleep(2)
        
        # Test buttons by their actual IDs from the code
        buttons_to_test = [
            ('vol-lab-overview-refresh-btn', 'Overview Refresh'),
            ('vol-lab-calc-run-btn', 'Run Calculation'),
            ('vol-lab-iv-export-btn', 'Export IV'),
            ('vol-lab-signal-run-btn', 'Run Signals'),
            ('vol-lab-backtest-run-btn', 'Run Backtest'),
        ]
        
        print("\n2. Testing buttons...")
        for btn_id, btn_name in buttons_to_test:
            print(f"\n   Testing: {btn_name} (#{btn_id})")
            try:
                # Check if button exists
                btn = page.locator(f'#{btn_id}')
                if btn.count() > 0:
                    print(f"      ✅ Button found")
                    
                    # Try clicking (but don't wait for result, just check it's clickable)
                    if btn.is_visible():
                        print(f"      ✅ Button visible")
                        btn.click(timeout=5000)
                        time.sleep(1)
                        print(f"      ✅ Button clickable")
                    else:
                        print(f"      ⚠️ Button not visible")
                else:
                    print(f"      ❌ Button not found")
            except Exception as e:
                print(f"      ⚠️ Error: {str(e)[:100]}")
        
        # Check for any output/results areas
        print("\n3. Checking for output areas...")
        output_ids = [
            'vol-lab-overview-metrics',
            'vol-lab-calc-output',
            'vol-lab-signal-output',
            'vol-lab-backtest-output',
            'vol-lab-diag-log',
        ]
        
        for out_id in output_ids:
            try:
                elem = page.locator(f'#{out_id}')
                exists = elem.count() > 0
                print(f"   {out_id}: {'✅ exists' if exists else '❌ missing'}")
            except:
                pass
        
        page.screenshot(path='/home/aarav/unified-dashboard/vol_lab_buttons.png')
        print("\n📸 Screenshot: vol_lab_buttons.png")
        
        print("\n✅ Test complete. Browser staying open for 10s...")
        time.sleep(10)
        
        browser.close()

if __name__ == '__main__':
    test_vol_lab_buttons()
