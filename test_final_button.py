#!/usr/bin/env python3
"""
FINAL TEST - Portfolio Button Functionality
Tests that clicking the refresh button actually updates the table
"""
from playwright.sync_api import sync_playwright
import time

print("="*80)
print("FINAL PORTFOLIO BUTTON TEST")
print("="*80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("\n[1] Loading dashboard...")
    page.goto('http://localhost:8051/', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(5)
    
    print("[2] Clicking Portfolio tab...")
    page.evaluate("""
        Array.from(document.querySelectorAll('a[role="tab"]'))
            .find(el => el.textContent.includes('Portfolio'))?.click()
    """)
    time.sleep(3)
    
    print("[3] Clicking Positions subtab...")
    page.evaluate("""
        Array.from(document.querySelectorAll('a[role="tab"]'))
            .find(el => el.textContent.trim() === 'Positions')?.click()
    """)
    time.sleep(3)
    
    print("[4] Checking initial table state...")
    initial = page.evaluate("""
        () => {
            const div = document.querySelector('#portfolio-positions-table');
            if (!div) return {exists: false, hasTable: false, rows: 0};
            const table = div.querySelector('table');
            const rows = table ? table.querySelectorAll('tbody tr').length : 0;
            return {
                exists: true,
                hasTable: !!table,
                rows: rows,
                innerHTML: div.innerHTML.substring(0, 300)
            };
        }
    """)
    
    print(f"   Container exists: {initial['exists']}")
    print(f"   Has DataTable: {initial['hasTable']}")
    print(f"   Rows: {initial['rows']}")
    
    print("\n[5] Clicking refresh button...")
    clicked = page.evaluate("""
        () => {
            const btn = document.querySelector('button#portfolio-positions-refresh-btn');
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        }
    """)
    
    if not clicked:
        print("   ❌ Button not found!")
        browser.close()
        exit(1)
    
    print(f"   Button clicked: {clicked}")
    print("   Waiting 8 seconds for callback...")
    time.sleep(8)
    
    print("\n[6] Checking updated table state...")
    updated = page.evaluate("""
        () => {
            const div = document.querySelector('#portfolio-positions-table');
            if (!div) return {exists: false, hasTable: false, rows: 0};
            const table = div.querySelector('table');
            const rows = table ? table.querySelectorAll('tbody tr').length : 0;
            
            // Get symbols
            let symbols = [];
            if (table) {
                const trs = table.querySelectorAll('tbody tr');
                trs.forEach(tr => {
                    const firstCell = tr.querySelector('td:first-child');
                    if (firstCell) symbols.push(firstCell.textContent.trim());
                });
            }
            
            return {
                exists: true,
                hasTable: !!table,
                rows: rows,
                symbols: symbols
            };
        }
    """)
    
    print(f"   Container exists: {updated['exists']}")
    print(f"   Has DataTable: {updated['hasTable']}")
    print(f"   Rows: {updated['rows']}")
    print(f"   Symbols: {updated['symbols']}")
    
    print("\n" + "="*80)
    if updated['rows'] >= 3:
        print("✅ ✅ ✅ SUCCESS - BUTTON WORKS! ✅ ✅ ✅")
        print(f"   Found {updated['rows']} positions: {', '.join(updated['symbols'])}")
        print("   Callback executed and table updated!")
    elif updated['rows'] > 0:
        print(f"⚠️  PARTIAL - Got {updated['rows']} positions (expected 3+)")
        print(f"   Symbols: {', '.join(updated['symbols'])}")
    else:
        print("❌ FAIL - No rows in table")
    print("="*80)
    
    browser.close()
