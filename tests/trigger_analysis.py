#!/usr/bin/env python3
"""
Trigger Run Full Analysis and wait for completion
"""
import time
from playwright.sync_api import sync_playwright

def trigger_analysis():
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
        time.sleep(3)
        
        # Click Run Full Analysis
        print("3. Clicking 'Run Full Analysis' button...")
        page.locator('button:has-text("Run Full Analysis")').click()
        print("   ✅ Button clicked - job started")
        time.sleep(2)
        
        # Wait for job to complete (max 180 seconds, check every 2 seconds)
        print("Waiting for analysis to complete...")
        for i in range(90):  # 90 * 2 = 180 seconds
            time.sleep(2)
            
            # Check if status changed
            status_elem = page.query_selector('#market-trends-job-status')
            if status_elem:
                status_text = status_elem.inner_text()
                print(f"[{i*2}s] Status: {status_text}")
                if 'completed' in status_text.lower() or 'success' in status_text.lower():
                    print(f"✅ Job completed after {i*2} seconds")
                    time.sleep(5)  # Extra wait for cache save
                    break
            
            if i % 5 == 0:  # Print progress every 10 seconds
                print(f"Still waiting... ({i*2}s elapsed)")
        else:
            print("⚠️  Timed out after 180 seconds")
        
        # Give it a moment to render
        time.sleep(3)
        
        # Check the table
        print("5. Checking table...")
        rows = page.locator('tr[data-ticker]').all()
        print(f"   Found {len(rows)} rows")
        
        for i, row in enumerate(rows[:5]):
            ticker_cell = row.locator('td[data-col="ticker"]').first
            week_cell = row.locator('td[data-col="week_start_price"]').first
            
            ticker = ticker_cell.inner_text() if ticker_cell.count() else 'N/A'
            week_val = week_cell.get_attribute('data-value') if week_cell.count() else 'N/A'
            week_text = week_cell.inner_text() if week_cell.count() else 'N/A'
            
            status = "✅" if week_val and week_val != '' and week_val != ticker else "❌"
            print(f"   {status} {ticker}: week_start_price='{week_val}' (display: '{week_text}')")
        
        print("\n✅ Analysis complete - keeping browser open for 10 seconds...")
        time.sleep(10)
        browser.close()

if __name__ == '__main__':
    trigger_analysis()
