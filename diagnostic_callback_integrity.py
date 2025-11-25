#!/usr/bin/env python3
"""
DIAGNOSTIC: Callback Integrity Checker
Validates that all Market Trends callbacks are properly registered and functional.
"""
import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def check_callback_integrity():
    """Check if callbacks are registered and firing correctly."""
    
    results = {
        'server_responding': False,
        'callbacks_registered': {},
        'callbacks_fired': {},
        'console_errors': [],
        'network_errors': []
    }
    
    print("=" * 80)
    print("CALLBACK INTEGRITY DIAGNOSTIC")
    print("=" * 80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Collect console messages
        console_messages = []
        page.on('console', lambda msg: console_messages.append({
            'type': msg.type,
            'text': msg.text
        }))
        
        # Collect network errors
        page.on('requestfailed', lambda request: results['network_errors'].append({
            'url': request.url,
            'failure': request.failure
        }))
        
        try:
            print("\n[1] Loading dashboard... (90s timeout for slow startup)")
            page.goto('http://localhost:8050', wait_until='load', timeout=90000)
            results['server_responding'] = True
            print("✅ Server responded")
            
            # Wait for React to initialize
            page.wait_for_timeout(3000)
            
            # Check for Dash callback errors
            print("\n[2] Checking for callback registration errors...")
            dash_errors = [msg for msg in console_messages if 'callback' in msg['text'].lower() and msg['type'] == 'error']
            
            if dash_errors:
                print(f"❌ Found {len(dash_errors)} callback errors:")
                for err in dash_errors[:5]:
                    print(f"   - {err['text'][:150]}")
                    results['console_errors'].append(err['text'])
            else:
                print("✅ No callback registration errors found")
            
            # Click Market Trends tab
            print("\n[3] Clicking Market Trends tab...")
            try:
                market_trends_tab = page.locator('a.nav-link:has-text("Market Trends")')
                if market_trends_tab.count() > 0:
                    market_trends_tab.first.click()
                    page.wait_for_timeout(2000)
                    print("✅ Market Trends tab clicked")
                    results['callbacks_fired']['market_trends_tab'] = True
                else:
                    print("❌ Market Trends tab not found in DOM")
                    results['callbacks_fired']['market_trends_tab'] = False
            except Exception as e:
                print(f"❌ Error clicking Market Trends: {e}")
                results['callbacks_fired']['market_trends_tab'] = False
            
            # Check if Market Trends table loaded
            print("\n[4] Checking Market Trends table...")
            table_selector = '#market-trends-table, table[data-testid="market-trends-table"]'
            try:
                table = page.locator(table_selector).first
                if table.count() > 0:
                    rows = page.locator(f'{table_selector} tbody tr').count()
                    print(f"✅ Market Trends table found with {rows} rows")
                    results['callbacks_fired']['market_trends_table_render'] = True
                    
                    # Check for "Data Unavailable"
                    page_content = page.content()
                    if 'Data Unavailable' in page_content or 'N/A' in page_content:
                        print("⚠️  WARNING: 'Data Unavailable' or 'N/A' found in page")
                        results['callbacks_fired']['market_trends_data_complete'] = False
                    else:
                        print("✅ No 'Data Unavailable' values detected")
                        results['callbacks_fired']['market_trends_data_complete'] = True
                else:
                    print("❌ Market Trends table not found")
                    results['callbacks_fired']['market_trends_table_render'] = False
            except Exception as e:
                print(f"❌ Error checking table: {e}")
                results['callbacks_fired']['market_trends_table_render'] = False
            
            # Click Weekly Picks tab
            print("\n[5] Clicking Weekly Picks tab...")
            try:
                weekly_tab = page.locator('a.nav-link:has-text("Weekly Picks")')
                if weekly_tab.count() > 0:
                    weekly_tab.first.click()
                    page.wait_for_timeout(2000)
                    print("✅ Weekly Picks tab clicked")
                    results['callbacks_fired']['weekly_picks_tab'] = True
                    
                    # Check for Weekly Picks table
                    wp_content = page.locator('#wp-content').inner_text()
                    if len(wp_content) > 50:  # Has meaningful content
                        print(f"✅ Weekly Picks content loaded ({len(wp_content)} chars)")
                        results['callbacks_fired']['weekly_picks_render'] = True
                    else:
                        print(f"❌ Weekly Picks content empty or minimal ({len(wp_content)} chars)")
                        results['callbacks_fired']['weekly_picks_render'] = False
                else:
                    print("❌ Weekly Picks tab not found")
                    results['callbacks_fired']['weekly_picks_tab'] = False
            except Exception as e:
                print(f"❌ Error with Weekly Picks: {e}")
                results['callbacks_fired']['weekly_picks_tab'] = False
            
            # Click Monthly Picks tab
            print("\n[6] Clicking Monthly Picks tab...")
            try:
                monthly_tab = page.locator('a.nav-link:has-text("Monthly Picks")')
                if monthly_tab.count() > 0:
                    monthly_tab.first.click()
                    page.wait_for_timeout(2000)
                    print("✅ Monthly Picks tab clicked")
                    results['callbacks_fired']['monthly_picks_tab'] = True
                    
                    # Check for Monthly Picks table
                    mp_content = page.locator('#mp-content').inner_text()
                    if len(mp_content) > 50:
                        print(f"✅ Monthly Picks content loaded ({len(mp_content)} chars)")
                        results['callbacks_fired']['monthly_picks_render'] = True
                    else:
                        print(f"❌ Monthly Picks content empty ({len(mp_content)} chars)")
                        results['callbacks_fired']['monthly_picks_render'] = False
                else:
                    print("❌ Monthly Picks tab not found")
                    results['callbacks_fired']['monthly_picks_tab'] = False
            except Exception as e:
                print(f"❌ Error with Monthly Picks: {e}")
                results['callbacks_fired']['monthly_picks_tab'] = False
            
            # Check for console errors
            print("\n[7] Analyzing console messages...")
            error_messages = [msg for msg in console_messages if msg['type'] == 'error']
            warning_messages = [msg for msg in console_messages if msg['type'] == 'warning']
            
            print(f"   Total console messages: {len(console_messages)}")
            print(f"   Errors: {len(error_messages)}")
            print(f"   Warnings: {len(warning_messages)}")
            
            # Check for specific error patterns
            datatable_errors = [msg for msg in console_messages if 'DataTable' in msg['text']]
            qo_errors = [msg for msg in console_messages if 'Qo @' in msg['text']]
            callback_errors = [msg for msg in console_messages if 'callback' in msg['text'].lower() and msg['type'] == 'error']
            
            if datatable_errors:
                print(f"\n⚠️  Found {len(datatable_errors)} DataTable-related messages:")
                for msg in datatable_errors[:3]:
                    print(f"   - {msg['text'][:100]}")
            
            if qo_errors:
                print(f"\n⚠️  Found {len(qo_errors)} 'Qo @' errors:")
                for msg in qo_errors[:3]:
                    print(f"   - {msg['text'][:100]}")
            
            if callback_errors:
                print(f"\n❌ Found {len(callback_errors)} callback errors:")
                for msg in callback_errors[:3]:
                    print(f"   - {msg['text'][:100]}")
            
            results['console_errors'].extend([msg['text'] for msg in error_messages])
            
            # Take screenshot for visual inspection
            page.screenshot(path='diagnostic_callback_integrity.png')
            print("\n📸 Screenshot saved: diagnostic_callback_integrity.png")
            
        except PlaywrightTimeout as e:
            print(f"\n❌ Timeout error: {e}")
            results['server_responding'] = False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    # Save results
    with open('diagnostic_callback_integrity_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Server responding: {results['server_responding']}")
    print(f"Callbacks fired: {sum(1 for v in results['callbacks_fired'].values() if v)}/{len(results['callbacks_fired'])}")
    print(f"Console errors: {len(results['console_errors'])}")
    print(f"Network errors: {len(results['network_errors'])}")
    print("\nResults saved to: diagnostic_callback_integrity_results.json")
    
    # Return success if all critical callbacks fired
    critical_callbacks = ['market_trends_tab', 'weekly_picks_tab', 'monthly_picks_tab']
    success = all(results['callbacks_fired'].get(cb, False) for cb in critical_callbacks)
    
    return success

if __name__ == '__main__':
    success = check_callback_integrity()
    sys.exit(0 if success else 1)
