#!/usr/bin/env python3
"""Diagnostic script to inspect BOTH Weekly and Monthly Picks tabs and compare their content."""
import time
import os
from playwright.sync_api import sync_playwright

def inspect_tab(page, tab_name, tab_id):
    """Navigate to a tab and inspect its content."""
    print(f"\n{'='*60}")
    print(f"INSPECTING {tab_name.upper()} TAB")
    print(f"{'='*60}")
    
    # Navigate to the tab by clicking
    tab_selector = f'[tab-id="{tab_id}"]'
    print(f"Looking for tab selector: {tab_selector}")
    
    # Wait for and click the tab
    tab_button = page.wait_for_selector(tab_selector, timeout=30000)
    tab_button.click()
    print(f"Clicked {tab_name} tab")
    
    # Wait for content to load
    time.sleep(3)
    
    # Look for all tables with data-ticker rows
    tables = page.query_selector_all('table')
    print(f"Tables found: {len(tables)}")
    
    all_rows = page.query_selector_all('tr[data-ticker]')
    print(f"Rows with data-ticker: {len(all_rows)}")
    
    if all_rows:
        first_row = all_rows[0]
        ticker_attr = first_row.get_attribute('data-ticker')
        print(f"First ticker: {ticker_attr}")
        
        cells = first_row.query_selector_all('td')
        print(f"Cells in first row: {len(cells)}")
        
        for i, cell in enumerate(cells):
            col = cell.get_attribute('data-col')
            val = cell.get_attribute('data-value')
            print(f"  Cell {i}: data-col={col}, data-value={val}")
    
    # Take screenshot
    screenshot_dir = '/mnt/c/Aarav/fin_env/unified-dashboard/test-artifacts'
    os.makedirs(screenshot_dir, exist_ok=True)
    screenshot_path = os.path.join(screenshot_dir, f'{tab_id}_diagnostic.png')
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"Screenshot saved to {screenshot_path}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Navigate to the app
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        print("Loaded dashboard home page")
        
        # Wait for initial load
        time.sleep(2)
        
        # First, let's find all tabs and print their attributes
        print("\n" + "="*60)
        print("DISCOVERING ALL TABS")
        print("="*60)
        all_tabs = page.query_selector_all('.nav-link')  # Bootstrap tab class
        print(f"Found {len(all_tabs)} tabs with class 'nav-link'")
        for i, tab in enumerate(all_tabs):
            tab_id = tab.get_attribute('tab-id') or tab.get_attribute('id')
            tab_text = tab.inner_text()
            print(f"  Tab {i}: id/tab-id={tab_id}, text='{tab_text}'")
        
        # Try finding by text content instead
        weekly_tab = page.get_by_text("Weekly Picks", exact=True)
        monthly_tab = page.get_by_text("Monthly Picks", exact=True)
        
        # Inspect Weekly Picks tab
        print("\n" + "="*60)
        print("INSPECTING WEEKLY PICKS TAB")
        print("="*60)
        weekly_tab.click()
        time.sleep(3)
        
        all_rows = page.query_selector_all('tr[data-ticker]')
        print(f"Rows with data-ticker: {len(all_rows)}")
        if all_rows:
            first_row = all_rows[0]
            ticker_attr = first_row.get_attribute('data-ticker')
            print(f"First ticker: {ticker_attr}")
            cells = first_row.query_selector_all('td')
            print(f"Cells in first row: {len(cells)}")
            for i, cell in enumerate(cells):
                col = cell.get_attribute('data-col')
                val = cell.get_attribute('data-value')
                print(f"  Cell {i}: data-col={col}, data-value={val}")
        
        # Screenshot
        page.screenshot(path='/mnt/c/Aarav/fin_env/unified-dashboard/test-artifacts/weekly_diagnostic.png', full_page=True)
        
        # Inspect Monthly Picks tab
        print("\n" + "="*60)
        print("INSPECTING MONTHLY PICKS TAB")
        print("="*60)
        monthly_tab.click()
        time.sleep(3)
        
        all_rows = page.query_selector_all('tr[data-ticker]')
        print(f"Rows with data-ticker: {len(all_rows)}")
        if all_rows:
            first_row = all_rows[0]
            ticker_attr = first_row.get_attribute('data-ticker')
            print(f"First ticker: {ticker_attr}")
            cells = first_row.query_selector_all('td')
            print(f"Cells in first row: {len(cells)}")
            for i, cell in enumerate(cells):
                col = cell.get_attribute('data-col')
                val = cell.get_attribute('data-value')
                print(f"  Cell {i}: data-col={col}, data-value={val}")
        
        # Screenshot
        page.screenshot(path='/mnt/c/Aarav/fin_env/unified-dashboard/test-artifacts/monthly_diagnostic.png', full_page=True)
        
        browser.close()

if __name__ == '__main__':
    main()
