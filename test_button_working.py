#!/usr/bin/env python3
"""
Final verification test - Portfolio button functionality
Tests that the button callback fires and updates the table
"""

from playwright.sync_api import sync_playwright
import time

print("="*80)
print("PORTFOLIO BUTTON FUNCTIONALITY TEST")
print("="*80)

with sync_playwright() as p:
    # Use chromium with visible browser
    browser = p.chromium.launch(headless=False, slow_mo=1000)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    print("\n1. Loading dashboard...")
    page.goto('http://localhost:8051/', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(5)
    
    print("\n2. Clicking Portfolio tab...")
    page.evaluate("""
        const portfolioTab = Array.from(document.querySelectorAll('a[role="tab"]'))
            .find(el => el.textContent.includes('Portfolio'));
        if (portfolioTab) {
            portfolioTab.click();
            console.log('Clicked Portfolio tab');
        }
    """)
    time.sleep(3)
    
    print("\n3. Clicking Positions subtab...")
    page.evaluate("""
        const positionsTab = Array.from(document.querySelectorAll('a[role="tab"]'))
            .find(el => el.textContent.trim() === 'Positions');
        if (positionsTab) {
            positionsTab.click();
            console.log('Clicked Positions subtab');
        }
    """)
    time.sleep(3)
    
    print("\n4. Checking initial state...")
    initial_state = page.evaluate("""
        () => {
            const table = document.querySelector('table#positions-datatable');
            const rows = table ? table.querySelectorAll('tbody tr').length : 0;
            const content = table ? table.innerHTML : '';
            return {
                exists: !!table,
                rows: rows,
                hasData: rows > 0,
                sample: content.substring(0, 200)
            };
        }
    """)
    print(f"   Table exists: {initial_state['exists']}")
    print(f"   Rows: {initial_state['rows']}")
    print(f"   Has data: {initial_state['hasData']}")
    
    print("\n5. Clicking refresh button...")
    page.evaluate("""
        const btn = document.querySelector('button#portfolio-positions-refresh-btn');
        if (btn) {
            btn.click();
            console.log('Clicked refresh button');
        }
    """)
    
    print("   Waiting 10 seconds for callback to execute...")
    time.sleep(10)
    
    print("\n6. Checking updated state...")
    updated_state = page.evaluate("""
        () => {
            const table = document.querySelector('table#positions-datatable');
            const rows = table ? table.querySelectorAll('tbody tr').length : 0;
            const content = table ? table.innerHTML : '';
            
            // Get first row content
            const firstRow = table ? table.querySelector('tbody tr:first-child') : null;
            const firstSymbol = firstRow ? firstRow.querySelector('td:first-child')?.textContent : 'N/A';
            
            return {
                exists: !!table,
                rows: rows,
                hasData: rows > 0,
                firstSymbol: firstSymbol,
                sample: content.substring(0, 200)
            };
        }
    """)
    print(f"   Table exists: {updated_state['exists']}")
    print(f"   Rows: {updated_state['rows']}")
    print(f"   Has data: {updated_state['hasData']}")
    print(f"   First symbol: {updated_state['firstSymbol']}")
    
    print("\n" + "="*80)
    if updated_state['hasData'] and updated_state['rows'] >= 3:
        print("✅ SUCCESS - Button is working! Table has multiple positions")
        print(f"   Found {updated_state['rows']} positions")
    elif updated_state['rows'] > initial_state['rows']:
        print(f"⚠️  PARTIAL - Button works but only {updated_state['rows']} positions (expected 3+)")
    else:
        print(f"❌ FAIL - Button callback did not update table")
        print(f"   Before: {initial_state['rows']} rows")
        print(f"   After: {updated_state['rows']} rows")
    print("="*80)
    
    print("\nBrowser will stay open for 10 seconds for manual inspection...")
    time.sleep(10)
    
    browser.close()
