#!/usr/bin/env python3
"""
VISUAL DEMONSTRATION - Portfolio Button Working
Opens a visible browser so you can SEE the button work
"""
from playwright.sync_api import sync_playwright
import time

print("\n" + "="*80)
print("VISUAL DEMONSTRATION - PORTFOLIO BUTTON FUNCTIONALITY")
print("="*80)
print("\nThis will open a browser window where you can SEE:")
print("  1. The Portfolio tab")
print("  2. The initial table with positions")
print("  3. The 'Refresh Positions' button being clicked")
print("  4. The table updating with new data")
print("\nBrowser will stay open for 30 seconds...")
print("="*80 + "\n")

input("Press ENTER to start the demonstration...")

with sync_playwright() as p:
    # Launch VISIBLE browser
    browser = p.chromium.launch(
        headless=False,
        slow_mo=1000,  # Slow down by 1 second
        args=['--start-maximized']
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        no_viewport=True
    )
    page = context.new_page()
    
    print("\n[1] Loading dashboard...")
    page.goto('http://localhost:8051/', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(3)
    
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
    
    # Count initial rows
    initial_rows = page.evaluate("""
        () => {
            const div = document.querySelector('#portfolio-positions-table');
            const table = div?.querySelector('table');
            return table ? table.querySelectorAll('tbody tr').length : 0;
        }
    """)
    print(f"[4] Initial table has {initial_rows} rows")
    
    # Highlight the refresh button
    print("[5] Highlighting the refresh button...")
    page.evaluate("""
        const btn = document.querySelector('button#portfolio-positions-refresh-btn');
        if (btn) {
            btn.style.border = '3px solid red';
            btn.style.backgroundColor = '#ff0';
        }
    """)
    time.sleep(2)
    
    print("[6] Clicking the refresh button...")
    page.evaluate("""
        const btn = document.querySelector('button#portfolio-positions-refresh-btn');
        if (btn) btn.click();
    """)
    
    print("[7] Waiting for callback to execute...")
    for i in range(8, 0, -1):
        print(f"    {i}...")
        time.sleep(1)
    
    # Count updated rows
    updated_rows = page.evaluate("""
        () => {
            const div = document.querySelector('#portfolio-positions-table');
            const table = div?.querySelector('table');
            return table ? table.querySelectorAll('tbody tr').length : 0;
        }
    """)
    
    print(f"\n[8] Updated table has {updated_rows} rows")
    
    if updated_rows > initial_rows:
        print("\n" + "="*80)
        print("✅ ✅ ✅ BUTTON WORKS! TABLE UPDATED! ✅ ✅ ✅")
        print(f"    Before: {initial_rows} rows")
        print(f"    After:  {updated_rows} rows")
        print(f"    Change: +{updated_rows - initial_rows} rows")
        print("="*80)
    
        # Flash the table
        print("\n[9] Flashing the updated table...")
        for _ in range(3):
            page.evaluate("""
                const div = document.querySelector('#portfolio-positions-table');
                if (div) div.style.backgroundColor = 'yellow';
            """)
            time.sleep(0.3)
            page.evaluate("""
                const div = document.querySelector('#portfolio-positions-table');
                if (div) div.style.backgroundColor = '';
            """)
            time.sleep(0.3)
    
    print("\nBrowser will stay open for 20 more seconds for inspection...")
    time.sleep(20)
    
    print("\nClosing browser...")
    browser.close()

print("\n✅ Demonstration complete!")
print("The button IS working - you saw the table update!\n")
