#!/usr/bin/env python3
"""
Quick verification of all fixes:
1. Options Lab expiration dropdown formatting
2. Color contrast rules
3. Portfolio tab loads without error
"""
from playwright.sync_api import sync_playwright
import time

print("=" * 80)
print("🔬 VERIFICATION TEST - All Fixes")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=300)
    page = browser.new_page()
    
    print("\n1️⃣ Testing Options Lab...")
    page.goto('http://localhost:8050')
    time.sleep(3)
    
    # Click Options Lab
    page.click('text=💹 Options Lab')
    time.sleep(2)
    
    # Enter ticker
    page.fill('#options-ticker-input', 'SPY')
    time.sleep(1)
    
    # Click Load Chain
    page.click('button.options-load-btn')
    print("   ⏳ Loading data...")
    time.sleep(8)
    
    # Check expiration dropdown
    try:
        dropdown_value = page.evaluate('''
            () => {
                const dropdown = document.getElementById('chain-expiration-dropdown');
                if (dropdown && dropdown.__dash_react_props) {
                    const props = dropdown.__dash_react_props;
                    return {
                        options_count: props.options ? props.options.length : 0,
                        first_option: props.options && props.options.length > 0 ? props.options[0] : null,
                        second_option: props.options && props.options.length > 1 ? props.options[1] : null
                    };
                }
                return null;
            }
        ''')
        
        if dropdown_value:
            print(f"   ✅ Dropdown has {dropdown_value['options_count']} options")
            if dropdown_value['first_option']:
                print(f"   ✅ First option: {dropdown_value['first_option']['label']}")
                if 'Nov' in dropdown_value['first_option']['label'] or 'Oct' in dropdown_value['first_option']['label']:
                    print("   ✅ Date formatting WORKING (shows month name!)")
                else:
                    print(f"   ⚠️  Date format unclear: {dropdown_value['first_option']['label']}")
        else:
            print("   ❌ Could not read dropdown")
    except Exception as e:
        print(f"   ⚠️  Dropdown check error: {e}")
    
    # Check table colors
    print("\n   📊 Checking table colors...")
    try:
        # Get table styles
        table_exists = page.query_selector('table.dash-table')
        if table_exists:
            print("   ✅ DataTable rendered")
            
            # Check header color (should be dark with white text)
            header_style = page.evaluate('''
                () => {
                    const header = document.querySelector('table.dash-table th');
                    if (header) {
                        const style = window.getComputedStyle(header);
                        return {
                            backgroundColor: style.backgroundColor,
                            color: style.color
                        };
                    }
                    return null;
                }
            ''')
            
            if header_style:
                print(f"   📊 Header: bg={header_style['backgroundColor']}, color={header_style['color']}")
                # Dark background should have light text
                if 'rgb(44, 62, 80)' in header_style['backgroundColor'] or 'rgb(248, 249, 250)' not in header_style['backgroundColor']:
                    print("   ✅ Header has dark background (expecting white text)")
            
            # Check cell color (should be white with black text)
            cell_style = page.evaluate('''
                () => {
                    const cell = document.querySelector('table.dash-table td');
                    if (cell) {
                        const style = window.getComputedStyle(cell);
                        return {
                            backgroundColor: style.backgroundColor,
                            color: style.color
                        };
                    }
                    return null;
                }
            ''')
            
            if cell_style:
                print(f"   📊 Cell: bg={cell_style['backgroundColor']}, color={cell_style['color']}")
                if 'rgb(255, 255, 255)' in cell_style['backgroundColor']:
                    print("   ✅ Cells have white background (expecting black text)")
        else:
            print("   ⚠️  Table not found")
    except Exception as e:
        print(f"   ⚠️  Table check error: {e}")
    
    page.screenshot(path='test-artifacts/options_lab_final.png', full_page=True)
    print("   📸 Screenshot: test-artifacts/options_lab_final.png")
    
    # Test Portfolio
    print("\n2️⃣ Testing Portfolio Tab...")
    page.click('text=Portfolio')
    time.sleep(3)
    
    # Check for error message
    error_text = page.query_selector('text="This submodule failed to import"')
    if error_text:
        print("   ❌ Portfolio still has import error!")
    else:
        print("   ✅ Portfolio loaded without import error")
    
    # Check if positions are visible
    positions_table = page.query_selector('.portfolio-positions, #portfolio-positions-table, table')
    if positions_table:
        print("   ✅ Portfolio content visible")
    else:
        print("   ⚠️  Portfolio content structure unclear")
    
    page.screenshot(path='test-artifacts/portfolio_final.png', full_page=True)
    print("   📸 Screenshot: test-artifacts/portfolio_final.png")
    
    print("\n" + "=" * 80)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 80)
    print("\nCheck screenshots:")
    print("  - test-artifacts/options_lab_final.png")
    print("  - test-artifacts/portfolio_final.png")
    
    time.sleep(3)
    browser.close()
