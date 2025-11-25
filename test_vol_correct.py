#!/usr/bin/env python
"""Test Volatility Lab with CORRECT IDs."""
from playwright.sync_api import sync_playwright
import time

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        page.click('#tab-volatility_lab')
        time.sleep(2)
        
        buttons = ['vl-compute-quick-btn', 'vl-calc-run-btn', 'vl-signal-run-btn', 'vl-backtest-run-btn']
        
        print("\nTesting buttons:")
        for btn_id in buttons:
            btn = page.locator(f'#{btn_id}')
            exists = btn.count() > 0
            print(f"   {btn_id}: {'✅' if exists else '❌'}")
            
            if exists and btn.is_visible():
                print(f"      Clicking...")
                btn.click()
                time.sleep(2)
                print(f"      ✅ Clicked successfully")
        
        time.sleep(10)
        browser.close()

if __name__ == '__main__':
    test()
