#!/usr/bin/env python3
"""
AGENT 1A DIAGNOSTIC: UI VISIBILITY CHECK
Validates that Weekly and Monthly Picks tables are actually visible in the browser.
"""
import time
from playwright.sync_api import sync_playwright

def check_table_visibility():
    """Check if tables are visible in the UI."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Non-headless to see what user sees
        page = browser.new_page()
        
        print("\n" + "="*70)
        print("AGENT 1A - UI VISIBILITY DIAGNOSTIC")
        print("="*70)
        
        # Load dashboard
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        print("✓ Dashboard loaded")
        time.sleep(3)
        
        # Check Weekly Picks
        print("\n--- WEEKLY PICKS TAB ---")
        weekly_tab = page.get_by_text("Weekly Picks", exact=True).first
        weekly_tab.click()
        print("✓ Clicked Weekly Picks tab")
        time.sleep(5)  # Allow content to load
        
        # Check if wp-content div exists and is visible
        wp_content = page.locator('#wp-content')
        wp_visible = wp_content.is_visible()
        print(f"  #wp-content visible: {wp_visible}")
        
        # Check for table inside wp-content
        wp_tables = wp_content.locator('table').all()
        print(f"  Tables in #wp-content: {len(wp_tables)}")
        
        # Check for rows
        wp_rows = wp_content.locator('tr[data-ticker]').all()
        print(f"  Rows with data-ticker: {len(wp_rows)}")
        
        if wp_rows:
            first_ticker = wp_rows[0].get_attribute('data-ticker')
            print(f"  First ticker: {first_ticker}")
            cells = wp_rows[0].locator('td').all()
            if len(cells) > 4:
                col4 = cells[4].get_attribute('data-col')
                val4 = cells[4].get_attribute('data-value')
                print(f"  Cell 4: {col4}={val4}")
        
        # Take screenshot
        page.screenshot(path='test-artifacts/weekly_visibility_check.png', full_page=True)
        print("  Screenshot: test-artifacts/weekly_visibility_check.png")
        
        # Check Monthly Picks
        print("\n--- MONTHLY PICKS TAB ---")
        monthly_tab = page.get_by_text("Monthly Picks", exact=True).first
        monthly_tab.click()
        print("✓ Clicked Monthly Picks tab")
        time.sleep(5)  # Allow content to load
        
        # Check if mp-content div exists and is visible
        mp_content = page.locator('#mp-content')
        mp_visible = mp_content.is_visible()
        print(f"  #mp-content visible: {mp_visible}")
        
        # Check for table inside mp-content
        mp_tables = mp_content.locator('table').all()
        print(f"  Tables in #mp-content: {len(mp_tables)}")
        
        # Check for rows
        mp_rows = mp_content.locator('tr[data-ticker]').all()
        print(f"  Rows with data-ticker: {len(mp_rows)}")
        
        if mp_rows:
            first_ticker = mp_rows[0].get_attribute('data-ticker')
            print(f"  First ticker: {first_ticker}")
            cells = mp_rows[0].locator('td').all()
            if len(cells) > 4:
                col4 = cells[4].get_attribute('data-col')
                val4 = cells[4].get_attribute('data-value')
                print(f"  Cell 4: {col4}={val4}")
        
        # Take screenshot
        page.screenshot(path='test-artifacts/monthly_visibility_check.png', full_page=True)
        print("  Screenshot: test-artifacts/monthly_visibility_check.png")
        
        # VERDICT
        print("\n" + "="*70)
        print("VISIBILITY VERDICT:")
        print("="*70)
        
        weekly_ok = wp_visible and len(wp_rows) >= 15
        monthly_ok = mp_visible and len(mp_rows) >= 15
        
        print(f"  Weekly Picks: {'✅ VISIBLE' if weekly_ok else '❌ NOT VISIBLE'}")
        print(f"  Monthly Picks: {'✅ VISIBLE' if monthly_ok else '❌ NOT VISIBLE'}")
        
        if weekly_ok and monthly_ok:
            print("\n🎉 SUCCESS: Both tables are visible in the UI!")
        else:
            print("\n⚠️  FAILURE: Tables are not visible. Further investigation needed.")
        
        # Keep browser open for 10 seconds for manual inspection
        print("\n[Browser will remain open for 10 seconds for manual inspection...]")
        time.sleep(10)
        
        browser.close()
        
        return weekly_ok and monthly_ok

if __name__ == '__main__':
    success = check_table_visibility()
    exit(0 if success else 1)
