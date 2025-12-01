#!/usr/bin/env python3
"""
Quick test of picks tabs data display.
"""
import requests
import time

print("=" * 70)
print("Testing Picks Tabs Data Fixes")
print("=" * 70)

# Test API endpoints
print("\n1. Testing API Endpoints:")
print("-" * 70)

# Weekly Picks
try:
    resp = requests.get("http://localhost:8051/api/weekly_picks", timeout=10)
    data = resp.json()
    print(f"✓ Weekly Picks API: {data['status']}, count={data.get('count', 0)}")
    if data.get('data'):
        first_pick = data['data'][0]
        print(f"  First pick: {first_pick.get('ticker')} with fields: {', '.join(list(first_pick.keys())[:5])}")
except Exception as e:
    print(f"✗ Weekly Picks API failed: {e}")

# Monthly Picks
try:
    resp = requests.get("http://localhost:8051/api/monthly_picks", timeout=10)
    data = resp.json()
    print(f"✓ Monthly Picks API: {data['status']}, count={data.get('count', 0)}")
    if data.get('data'):
        first_pick = data['data'][0]
        print(f"  First pick: {first_pick.get('ticker')} with fields: {', '.join(list(first_pick.keys())[:5])}")
except Exception as e:
    print(f"✗ Monthly Picks API failed: {e}")

print("\n2. Testing UI (headless):")
print("-" * 70)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Load dashboard
    page.goto("http://localhost:8051", wait_until="networkidle", timeout=30000)
    print("✓ Dashboard loaded")
    
    # Test Weekly Picks
    print("\n--- Weekly Picks Tab ---")
    weekly_link = page.locator('text="Weekly Picks"').first
    weekly_link.click()
    page.wait_for_timeout(5000)  # Wait for callback
    
    # Check for errors
    errors = page.locator('.alert-danger')
    if errors.count() > 0:
        print(f"✗ ERROR: {errors.first.text_content()}")
    else:
        print("✓ No error messages")
    
    # Check table
    table = page.locator('#wp-table')
    if table.is_visible():
        print("✓ Table is visible")
        
        # Check table data attribute
        table_data = table.get_attribute('data')
        if table_data:
            print(f"✓ Table has data attribute")
        
        # Check for actual cell content
        cells = page.locator('#wp-table td')
        cell_count = cells.count()
        print(f"  Cells found: {cell_count}")
        
        if cell_count > 0:
            first_cell = cells.first.text_content()
            print(f"  First cell: '{first_cell}'")
            print("✓ WEEKLY PICKS: DATA DISPLAYED")
        else:
            # Check if columns are defined
            headers = page.locator('#wp-table th')
            header_count = headers.count()
            print(f"  Headers found: {header_count}")
            if header_count > 0:
                print(f"  First header: '{headers.first.text_content()}'")
            print("✗ WEEKLY PICKS: Table exists but no cells")
    else:
        print("✗ Table not visible")
    
    # Test Monthly Picks
    print("\n--- Monthly Picks Tab ---")
    monthly_link = page.locator('text="Monthly Picks"').first
    monthly_link.click()
    page.wait_for_timeout(5000)  # Wait for callback
    
    # Check for errors/warnings
    errors = page.locator('.alert-danger')
    warnings = page.locator('.alert-warning')
    
    if errors.count() > 0:
        print(f"✗ ERROR: {errors.first.text_content()}")
    elif warnings.count() > 0:
        print(f"⚠ WARNING: {warnings.first.text_content()}")
    else:
        print("✓ No error/warning messages")
    
    # Check table
    table = page.locator('#mp-table')
    if table.is_visible():
        print("✓ Table is visible")
        
        cells = page.locator('#mp-table td')
        cell_count = cells.count()
        print(f"  Cells found: {cell_count}")
        
        if cell_count > 0:
            first_cell = cells.first.text_content()
            print(f"  First cell: '{first_cell}'")
            print("✓ MONTHLY PICKS: DATA DISPLAYED")
        else:
            headers = page.locator('#mp-table th')
            header_count = headers.count()
            print(f"  Headers found: {header_count}")
            if header_count > 0:
                print(f"  First header: '{headers.first.text_content()}'")
            print("✗ MONTHLY PICKS: Table exists but no cells")
    else:
        print("✗ Table not visible")
    
    browser.close()

print("\n" + "=" * 70)
print("Test Complete")
print("=" * 70)
