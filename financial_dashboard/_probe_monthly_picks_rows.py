#!/usr/bin/env python3
"""Direct probe of Monthly Picks table to capture row 1, 15, 16 data."""
from playwright.sync_api import sync_playwright
import sys

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("="*70)
        print("MONTHLY PICKS CRITICAL ROWS PROBE")
        print("="*70)
        
        # Navigate to dashboard
        page.goto('http://localhost:8050', wait_until='networkidle')
        page.wait_for_selector('#dashboard-tabs', timeout=30000)
        
        # Click Monthly Picks tab
        page.locator('text=Monthly Picks').first.click()
        page.wait_for_timeout(5000)  # Wait for data to load
        
        # Save screenshot
        page.screenshot(path='test-artifacts/monthly_picks_probe.png', full_page=True)
        
        # Extract critical ticker rows
        critical_tickers = ['WDC', 'APH', 'GEV']
        
        for ticker in critical_tickers:
            ticker_row = page.locator(f'tr:has-text("{ticker}")').first
            
            if ticker_row.count() == 0:
                print(f"\n❌ {ticker}: ROW NOT FOUND")
                continue
            
            row_text = ticker_row.inner_text()
            print(f"\n📊 {ticker}:")
            print(f"  Raw text: {row_text}")
            print(f"  N/A count: {row_text.count('N/A')}")
            print(f"  Has $: {'✅' if '$' in row_text else '❌'}")
            
            # Count formatted prices
            import re
            prices = re.findall(r'\$\d+\.\d{2}', row_text)
            print(f"  Formatted prices found: {len(prices)} → {prices}")
        
        print("\n" + "="*70)
        browser.close()

if __name__ == "__main__":
    main()
