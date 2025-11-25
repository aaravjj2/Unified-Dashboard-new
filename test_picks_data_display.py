#!/usr/bin/env python3
"""
Test picks tabs to verify data is actually displayed after callback execution.
"""
import time
from playwright.sync_api import sync_playwright, expect

def test_picks_tabs():
    """Test both weekly and monthly picks tabs load data correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Navigate to dashboard
            page.goto("http://localhost:8051", wait_until="networkidle", timeout=30000)
            print("✓ Dashboard loaded")
            
            # Test Weekly Picks
            print("\n=== Testing Weekly Picks ===")
            weekly_tab = page.locator('text="Weekly Picks"').first
            weekly_tab.click()
            print("✓ Clicked Weekly Picks tab")
            
            # Wait for loading to complete (spinner disappears)
            page.wait_for_timeout(3000)
            
            # Check for error messages
            error = page.locator('.alert-danger').first
            if error.is_visible():
                print(f"✗ ERROR ALERT: {error.text_content()}")
            else:
                print("✓ No error alerts")
            
            # Check if table has data
            table = page.locator('#wp-table')
            if table.is_visible():
                print("✓ Weekly picks table is visible")
                
                # Check if table has rows with data
                rows = page.locator('#wp-table tbody tr')
                row_count = rows.count()
                print(f"✓ Table has {row_count} rows")
                
                if row_count > 0:
                    # Get first row data
                    first_row = rows.first.locator('td')
                    cell_count = first_row.count()
                    print(f"✓ First row has {cell_count} cells")
                    
                    if cell_count > 0:
                        first_cell_text = first_row.first.text_content()
                        print(f"✓ First cell contains: '{first_cell_text}'")
                        
                        # Check if it's actual data (not "Loading..." or empty)
                        if first_cell_text and first_cell_text.strip() and "Loading" not in first_cell_text:
                            print("✓ WEEKLY PICKS: DATA LOADED SUCCESSFULLY")
                        else:
                            print("✗ WEEKLY PICKS: Table exists but no data displayed")
                    else:
                        print("✗ WEEKLY PICKS: No cells in first row")
                else:
                    print("✗ WEEKLY PICKS: No rows in table")
            else:
                print("✗ Weekly picks table not found")
            
            # Test Monthly Picks
            print("\n=== Testing Monthly Picks ===")
            monthly_tab = page.locator('text="Monthly Picks"').first
            monthly_tab.click()
            print("✓ Clicked Monthly Picks tab")
            
            # Wait for loading to complete
            page.wait_for_timeout(3000)
            
            # Check for error messages
            error = page.locator('.alert-danger').first
            if error.is_visible():
                print(f"✗ ERROR ALERT: {error.text_content()}")
            else:
                print("✓ No error alerts")
            
            # Check for warning messages (like "No data available")
            warning = page.locator('.alert-warning').first
            if warning.is_visible():
                print(f"⚠ WARNING: {warning.text_content()}")
            
            # Check if table has data
            table = page.locator('#mp-table')
            if table.is_visible():
                print("✓ Monthly picks table is visible")
                
                # Check if table has rows with data
                rows = page.locator('#mp-table tbody tr')
                row_count = rows.count()
                print(f"✓ Table has {row_count} rows")
                
                if row_count > 0:
                    # Get first row data
                    first_row = rows.first.locator('td')
                    cell_count = first_row.count()
                    print(f"✓ First row has {cell_count} cells")
                    
                    if cell_count > 0:
                        first_cell_text = first_row.first.text_content()
                        print(f"✓ First cell contains: '{first_cell_text}'")
                        
                        if first_cell_text and first_cell_text.strip() and "Loading" not in first_cell_text:
                            print("✓ MONTHLY PICKS: DATA LOADED SUCCESSFULLY")
                        else:
                            print("✗ MONTHLY PICKS: Table exists but no data displayed")
                    else:
                        print("✗ MONTHLY PICKS: No cells in first row")
                else:
                    print("✗ MONTHLY PICKS: No rows in table")
            else:
                print("✗ Monthly picks table not found")
            
            # Take screenshot for verification
            page.screenshot(path='reports/picks_tabs_fixed.png')
            print("\n✓ Screenshot saved to reports/picks_tabs_fixed.png")
            
            # Keep browser open for manual inspection
            print("\n=== Browser will stay open for 30 seconds for manual inspection ===")
            time.sleep(30)
            
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            page.screenshot(path='reports/picks_tabs_error.png')
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    test_picks_tabs()
