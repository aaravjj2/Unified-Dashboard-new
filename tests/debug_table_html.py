#!/usr/bin/env python3
"""
Debug script to inspect the actual Market Trends table HTML
"""
import time
from playwright.sync_api import sync_playwright

def debug_table():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to dashboard
        print("Navigating to localhost:8050...")
        page.goto('http://localhost:8050', timeout=10000)
        time.sleep(2)
        
        # Click Market Trends tab
        print("Clicking Market Trends tab...")
        page.click('a[data-value="market_trends"]')
        time.sleep(3)
        
        # Find the table
        table = page.locator('[data-testid="market-trends-table"]').first
        
        if not table.count():
            print("❌ Table not found!")
            browser.close()
            return
        
        print(f"✅ Found table")
        
        # Get all rows with data-ticker attribute
        rows = page.locator('tr[data-ticker]').all()
        print(f"Found {len(rows)} ticker rows\n")
        
        # Check first 3 rows in detail
        for i, row in enumerate(rows[:3]):
            ticker_cell = row.locator('td[data-col="ticker"]').first
            week_cell = row.locator('td[data-col="week_start_price"]').first
            month_cell = row.locator('td[data-col="month_start_price"]').first
            daily_cell = row.locator('td[data-col="daily_change"]').first
            
            ticker_val = ticker_cell.get_attribute('data-value') if ticker_cell.count() else 'N/A'
            ticker_text = ticker_cell.inner_text() if ticker_cell.count() else 'N/A'
            
            week_val = week_cell.get_attribute('data-value') if week_cell.count() else 'N/A'
            week_text = week_cell.inner_text() if week_cell.count() else 'N/A'
            
            month_val = month_cell.get_attribute('data-value') if month_cell.count() else 'N/A'
            month_text = month_cell.inner_text() if month_cell.count() else 'N/A'
            
            daily_val = daily_cell.get_attribute('data-value') if daily_cell.count() else 'N/A'
            daily_text = daily_cell.inner_text() if daily_cell.count() else 'N/A'
            
            print(f"Row {i+1}: {ticker_text}")
            print(f"  Ticker data-value: '{ticker_val}'")
            print(f"  Week Start Price: data-value='{week_val}', display='{week_text}'")
            print(f"  Month Start Price: data-value='{month_val}', display='{month_text}'")
            print(f"  Daily Change: data-value='{daily_val}', display='{daily_text}'")
            print()
        
        browser.close()

if __name__ == '__main__':
    debug_table()
