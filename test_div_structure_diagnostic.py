#!/usr/bin/env python3
"""Diagnostic script to inspect the actual HTML structure and div IDs."""
import time
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Navigate to the app
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        print("Loaded dashboard home page")
        time.sleep(2)
        
        # Click Weekly Picks
        weekly_tab = page.get_by_text("Weekly Picks", exact=True)
        weekly_tab.click()
        time.sleep(3)
        
        # Find all divs with id="wp-content" or id="mp-content"
        print("\n" + "="*60)
        print("SEARCHING FOR CONTENT DIVS")
        print("="*60)
        
        wp_content_divs = page.query_selector_all('[id="wp-content"]')
        mp_content_divs = page.query_selector_all('[id="mp-content"]')
        
        print(f"Divs with id='wp-content': {len(wp_content_divs)}")
        print(f"Divs with id='mp-content': {len(mp_content_divs)}")
        
        # Check if mp-content exists and what it contains
        if mp_content_divs:
            print("\nInspecting mp-content div:")
            for i, div in enumerate(mp_content_divs):
                inner_html = div.inner_html()
                print(f"  mp-content div {i}: {len(inner_html)} chars")
                # Check if it has tables
                tables_in_mp = div.query_selector_all('table')
                rows_in_mp = div.query_selector_all('tr[data-ticker]')
                print(f"    Tables: {len(tables_in_mp)}, Rows with data-ticker: {len(rows_in_mp)}")
                if rows_in_mp:
                    first = rows_in_mp[0]
                    ticker = first.get_attribute('data-ticker')
                    cells = first.query_selector_all('td')
                    if len(cells) > 4:
                        col4 = cells[4].get_attribute('data-col')
                        print(f"    First ticker: {ticker}, Cell 4 col: {col4}")
        
        if wp_content_divs:
            print("\nInspecting wp-content div:")
            for i, div in enumerate(wp_content_divs):
                inner_html = div.inner_html()
                print(f"  wp-content div {i}: {len(inner_html)} chars")
                # Check if it has tables
                tables_in_wp = div.query_selector_all('table')
                rows_in_wp = div.query_selector_all('tr[data-ticker]')
                print(f"    Tables: {len(tables_in_wp)}, Rows with data-ticker: {len(rows_in_wp)}")
                if rows_in_wp:
                    first = rows_in_wp[0]
                    ticker = first.get_attribute('data-ticker')
                    cells = first.query_selector_all('td')
                    if len(cells) > 4:
                        col4 = cells[4].get_attribute('data-col')
                        print(f"    First ticker: {ticker}, Cell 4 col: {col4}")
        
        # Now click Monthly Picks and check again
        print("\n" + "="*60)
        print("SWITCHING TO MONTHLY PICKS TAB")
        print("="*60)
        monthly_tab = page.get_by_text("Monthly Picks", exact=True)
        monthly_tab.click()
        time.sleep(3)
        
        # Check visible content
        visible_rows = page.query_selector_all('tr[data-ticker]:visible')
        print(f"Visible rows with data-ticker: {len(visible_rows)}")
        if visible_rows:
            first = visible_rows[0]
            ticker = first.get_attribute('data-ticker')
            cells = first.query_selector_all('td')
            if len(cells) > 4:
                col4 = cells[4].get_attribute('data-col')
                print(f"First visible ticker: {ticker}, Cell 4 col: {col4}")
        
        # Dump all tab content div IDs
        print("\n" + "="*60)
        print("ALL DIVS IN TAB CONTENT AREA")
        print("="*60)
        tab_content = page.query_selector('.tab-content')
        if tab_content:
            all_divs = tab_content.query_selector_all('div[id]')
            for div in all_divs[:20]:  # Limit to first 20
                div_id = div.get_attribute('id')
                classes = div.get_attribute('class') or ''
                print(f"  div id='{div_id}', class='{classes}'")
        
        browser.close()

if __name__ == '__main__':
    main()
