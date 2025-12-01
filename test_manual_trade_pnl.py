#!/usr/bin/env python
"""Test Manual Trade P&L with actual contract selection."""
from playwright.sync_api import sync_playwright
import time

def test_manual_trade_pnl():
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
        
        # Load SPY chain
        print("2. Loading SPY chain...")
        page.fill('#options-ticker-input', 'SPY')
        page.click('#options-load-btn')
        time.sleep(3)
        
        # Navigate to Manual Trade
        print("\n3. Clicking Manual Trade tab...")
        page.click('#options-manual-tab')
        time.sleep(2)
        
        # Select expiration (first one)
        print("4. Selecting expiration...")
        page.click('#sim-expiration-dropdown')
        time.sleep(0.5)
        page.keyboard.press('ArrowDown')
        page.keyboard.press('Enter')
        time.sleep(1)
        
        # Select strike (ATM or close)
        print("5. Selecting strike...")
        page.click('#sim-strike-dropdown')
        time.sleep(0.5)
        page.keyboard.press('ArrowDown')
        page.keyboard.press('ArrowDown')
        page.keyboard.press('Enter')
        time.sleep(1)
        
        # Click Calculate P&L
        print("\n6. Clicking Calculate P&L...")
        page.click('#sim-calculate-btn')
        time.sleep(2)
        
        # Check results
        print("\n7. Checking P&L results...")
        max_profit = page.locator('#sim-max-profit').inner_text()
        max_loss = page.locator('#sim-max-loss').inner_text()
        breakeven = page.locator('#sim-breakeven').inner_text()
        
        print(f"   Max Profit: {max_profit}")
        print(f"   Max Loss: {max_loss}")
        print(f"   Breakeven: {breakeven}")
        
        # Check if chart has data
        chart = page.locator('#sim-pnl-chart')
        has_chart = chart.is_visible()
        print(f"\n8. P&L Chart visible: {has_chart}")
        
        # Screenshot
        page.screenshot(path='/home/aarav/unified-dashboard/manual_trade_pnl_working.png')
        print("\n📸 Screenshot saved: manual_trade_pnl_working.png")
        
        print("\n✅ Manual Trade P&L test complete!")
        time.sleep(5)
        
        browser.close()

if __name__ == '__main__':
    test_manual_trade_pnl()
