#!/usr/bin/env python3
"""
ACTUAL Options Lab Clicker Test - Load Chain Diagnosis
======================================================
Real browser automation to test Load Chain functionality
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, '.')

# Ensure directories
Path('test-artifacts/options_lab_actual').mkdir(parents=True, exist_ok=True)

def test_load_chain_actual():
    """Actually click Load Chain and diagnose what happens."""
    print("="*80)
    print("🔬 ACTUAL OPTIONS LAB LOAD CHAIN TEST")
    print("="*80)
    
    try:
        from playwright.sync_api import sync_playwright
        import requests
        
        # Check if app is running
        try:
            response = requests.get('http://localhost:8050', timeout=2)
            print("✅ Dash app is running on http://localhost:8050")
        except:
            print("❌ Dash app not running. Start with: python financial_dashboard/app.py")
            return 1
        
        with sync_playwright() as p:
            print("\n🌐 Launching browser...")
            browser = p.chromium.launch(headless=False, slow_mo=500)  # Visible + slow for debugging
            page = browser.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Enable console logging
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
            
            print("📄 Loading dashboard...")
            page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            time.sleep(2)
            
            # Take initial screenshot
            page.screenshot(path='test-artifacts/options_lab_actual/00_homepage.png', full_page=True)
            print("📸 Screenshot: 00_homepage.png")
            
            # Find and click Options Lab tab
            print("\n🎯 Looking for Options Lab tab...")
            try:
                # Try multiple selectors
                selectors = [
                    'text=💹 Options Lab',
                    'a:has-text("Options Lab")',
                    '.nav-link:has-text("Options Lab")',
                    'a[role="tab"]:has-text("Options Lab")'
                ]
                
                options_tab = None
                for selector in selectors:
                    try:
                        options_tab = page.wait_for_selector(selector, timeout=3000)
                        if options_tab:
                            print(f"✅ Found Options Lab using: {selector}")
                            break
                    except:
                        continue
                
                if not options_tab:
                    print("❌ Could not find Options Lab tab")
                    page.screenshot(path='test-artifacts/options_lab_actual/ERROR_no_tab.png', full_page=True)
                    browser.close()
                    return 1
                
                print("🖱️  Clicking Options Lab tab...")
                options_tab.click()
                time.sleep(3)
                
                page.screenshot(path='test-artifacts/options_lab_actual/01_options_lab_opened.png', full_page=True)
                print("📸 Screenshot: 01_options_lab_opened.png")
                
            except Exception as e:
                print(f"❌ Failed to open Options Lab: {e}")
                page.screenshot(path='test-artifacts/options_lab_actual/ERROR_tab_click.png', full_page=True)
                browser.close()
                return 1
            
            # Find ticker input
            print("\n📝 Looking for ticker input...")
            try:
                ticker_input = page.wait_for_selector('input.options-ticker-input', timeout=5000)
                if ticker_input:
                    print("✅ Found ticker input")
                    current_value = ticker_input.input_value()
                    print(f"   Current value: '{current_value}'")
                    
                    # Clear and enter SPY
                    ticker_input.fill('')
                    time.sleep(0.5)
                    ticker_input.fill('SPY')
                    print("✅ Entered ticker: SPY")
                    time.sleep(1)
                else:
                    print("❌ Ticker input not found")
                    page.screenshot(path='test-artifacts/options_lab_actual/ERROR_no_input.png', full_page=True)
                    
            except Exception as e:
                print(f"❌ Ticker input error: {e}")
                page.screenshot(path='test-artifacts/options_lab_actual/ERROR_ticker_input.png', full_page=True)
            
            page.screenshot(path='test-artifacts/options_lab_actual/02_ticker_entered.png', full_page=True)
            print("📸 Screenshot: 02_ticker_entered.png")
            
            # Find Load Chain button
            print("\n🔘 Looking for Load Chain button...")
            try:
                load_selectors = [
                    'button.options-load-btn',
                    'button:has-text("Load Chain")',
                    '#options-load-btn'
                ]
                
                load_btn = None
                for selector in load_selectors:
                    try:
                        load_btn = page.wait_for_selector(selector, timeout=3000)
                        if load_btn:
                            print(f"✅ Found Load Chain button using: {selector}")
                            is_visible = load_btn.is_visible()
                            is_enabled = load_btn.is_enabled()
                            print(f"   Visible: {is_visible}, Enabled: {is_enabled}")
                            break
                    except:
                        continue
                
                if not load_btn:
                    print("❌ Load Chain button not found")
                    page.screenshot(path='test-artifacts/options_lab_actual/ERROR_no_button.png', full_page=True)
                    
                    # Debug: Show all buttons
                    print("\n🔍 Debug: All buttons on page:")
                    buttons = page.query_selector_all('button')
                    for i, btn in enumerate(buttons[:10]):
                        text = btn.inner_text()
                        classes = btn.get_attribute('class')
                        print(f"   Button {i+1}: '{text}' | classes: {classes}")
                    
                    browser.close()
                    return 1
                
                print("🖱️  Clicking Load Chain button...")
                print("⏳ Waiting for response...")
                
                # Click and wait
                load_btn.click()
                time.sleep(5)  # Give it time to load
                
                page.screenshot(path='test-artifacts/options_lab_actual/03_after_load_click.png', full_page=True)
                print("📸 Screenshot: 03_after_load_click.png")
                
            except Exception as e:
                print(f"❌ Load Chain button error: {e}")
                page.screenshot(path='test-artifacts/options_lab_actual/ERROR_button_click.png', full_page=True)
            
            # Check for status message
            print("\n💬 Checking status message...")
            try:
                status_elem = page.query_selector('#options-status-message')
                if status_elem:
                    status_text = status_elem.inner_text()
                    print(f"✅ Status message: '{status_text}'")
                else:
                    print("⚠️  No status message found")
            except Exception as e:
                print(f"⚠️  Status check error: {e}")
            
            # Check for expiration dropdown
            print("\n📅 Checking expiration dropdown...")
            try:
                # Dash dropdowns use a custom component, check for the container
                dropdown_container = page.query_selector('#chain-expiration-dropdown')
                if dropdown_container:
                    is_visible = dropdown_container.is_visible()
                    print(f"✅ Expiration dropdown found, visible: {is_visible}")
                    
                    # For Dash dropdowns, we need to click to see options
                    # Or check the dropdown's properties via JavaScript
                    time.sleep(1)
                    
                    # Try to evaluate the Dropdown's props from the React component
                    try:
                        dropdown_value = page.evaluate('''
                            () => {
                                const dropdown = document.getElementById('chain-expiration-dropdown');
                                if (dropdown && dropdown.__dash_react_props) {
                                    const props = dropdown.__dash_react_props;
                                    return {
                                        value: props.value,
                                        options_count: props.options ? props.options.length : 0,
                                        first_option: props.options && props.options.length > 0 ? props.options[0] : null
                                    };
                                }
                                return null;
                            }
                        ''')
                        
                        if dropdown_value:
                            options_count = dropdown_value.get('options_count', 0)
                            print(f"   Options count: {options_count}")
                            if options_count > 0:
                                print(f"   ✅ Dropdown HAS {options_count} options!")
                                first_opt = dropdown_value.get('first_option')
                                if first_opt:
                                    print(f"      First option: {first_opt}")
                                current_value = dropdown_value.get('value')
                                if current_value:
                                    print(f"      Selected value: {current_value}")
                            else:
                                print("   ❌ Dropdown is EMPTY (no options)")
                        else:
                            print("   ⚠️  Could not read dropdown props")
                    except Exception as js_error:
                        print(f"   ⚠️  Could not evaluate dropdown props: {js_error}")
                        # Fallback: just check if the dropdown is visible
                        print("   ℹ️  Dropdown container exists but props not readable")
                else:
                    print("❌ Expiration dropdown not found")
            except Exception as e:
                print(f"⚠️  Dropdown check error: {e}")
            
            # Check for data table
            print("\n📊 Checking options data table...")
            try:
                # Table is rendered inside chain-table-container
                table_container = page.query_selector('#chain-table-container')
                if table_container:
                    is_visible = table_container.is_visible()
                    container_text = table_container.inner_text()
                    print(f"✅ Table container found, visible: {is_visible}")
                    
                    # Check if it contains a DataTable or just text
                    dash_table = table_container.query_selector('table.dash-table')
                    if dash_table:
                        print("   ✅ DataTable component found!")
                        # Count rows
                        rows = dash_table.query_selector_all('tr')
                        print(f"   Table rows: {len(rows)}")
                    elif "No data loaded" in container_text or "Click 'Load Chain'" in container_text:
                        print(f"   ⚠️  Table shows: {container_text[:100]}")
                    elif len(container_text) > 20:
                        print(f"   ✅ Table has content ({len(container_text)} chars)")
                        print(f"   Preview: {container_text[:100]}...")
                    else:
                        print(f"   ⚠️  Table appears empty: '{container_text}'")
                else:
                    print("❌ Table container not found")
            except Exception as e:
                print(f"⚠️  Table check error: {e}")
            
            page.screenshot(path='test-artifacts/options_lab_actual/04_final_state.png', full_page=True)
            print("📸 Screenshot: 04_final_state.png")
            
            # Check console logs
            print("\n📝 Console Logs:")
            if console_logs:
                for log in console_logs[-20:]:  # Last 20 logs
                    print(f"   {log}")
            else:
                print("   (No console logs captured)")
            
            # Check for errors
            errors = [log for log in console_logs if 'error' in log.lower()]
            if errors:
                print(f"\n❌ {len(errors)} console errors found:")
                for err in errors:
                    print(f"   {err}")
            else:
                print("\n✅ No console errors")
            
            print("\n" + "="*80)
            print("TEST COMPLETE - Check screenshots in test-artifacts/options_lab_actual/")
            print("="*80)
            
            browser.close()
            
    except ImportError:
        print("❌ Playwright not installed: pip install playwright && playwright install")
        return 1
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(test_load_chain_actual())
