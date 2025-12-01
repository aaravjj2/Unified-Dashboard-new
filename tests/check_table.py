#!/usr/bin/env python3
"""
Check if Market Trends table shows enriched data
"""
import time
from playwright.sync_api import sync_playwright

def check_table():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate
        print("1. Navigating to dashboard...")
        page.goto('http://localhost:8050', timeout=15000)
        time.sleep(2)
        
        # Click Market Trends tab
        print("2. Clicking Market Trends tab...")
        page.locator('a:has-text("Market Trends")').click()
        time.sleep(5)  # Wait for table to load
        
        # Check the table
        print("3. Checking table...")
        rows = page.locator('tr[data-ticker]').all()
        print(f"   Found {len(rows)} rows")
        
        enriched_count = 0
        for i, row in enumerate(rows):
            ticker_cell = row.locator('td[data-col="ticker"]').first
            week_cell = row.locator('td[data-col="week_start_price"]').first
            
            ticker = ticker_cell.inner_text() if ticker_cell.count() else 'N/A'
            week_val = week_cell.get_attribute('data-value') if week_cell.count() else 'N/A'
            week_text = week_cell.inner_text() if week_cell.count() else 'N/A'
            
            has_data = week_val and week_val != '' and week_val != ticker and week_val != 'N/A'
            if has_data:
                enriched_count += 1
            
            status = "✅" if has_data else "❌"
            print(f"   {status} {ticker}: week_start='{week_val}' (display: '{week_text}')")
        
        print(f"\n📊 SUMMARY: {enriched_count}/{len(rows)} rows have enriched data")
        print("✅ TEST PASSED" if enriched_count == len(rows) else "❌ TEST FAILED")
        
        browser.close()

if __name__ == '__main__':
    check_table()
