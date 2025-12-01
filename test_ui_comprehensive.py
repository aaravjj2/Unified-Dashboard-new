#!/usr/bin/env python3
"""
COMPREHENSIVE UI VALIDATION TEST
Tests Weekly Picks, Monthly Picks, and Portfolio tabs for proper rendering.
"""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

async def test_ui_rendering():
    """Test all tabs render with proper data."""
    results = {
        'timestamp': None,
        'tests': {},
        'success': False
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable console logging
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"{msg.type()}: {msg.text()}"))
        
        try:
            print("🔍 Opening dashboard...")
            await page.goto('http://localhost:8050/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            results['timestamp'] = str(page.evaluate('new Date().toISOString()'))
            
            # Test 1: Weekly Picks Tab
            print("\n📊 TEST 1: Weekly Picks Tab")
            try:
                # Click tab
                await page.click('text=Weekly Picks', timeout=10000)
                await asyncio.sleep(3)
                
                # Check if content div exists
                wp_content = await page.query_selector('#wp-content')
                if wp_content:
                    inner_html = await wp_content.inner_html()
                    has_datatable = 'DataTable' in inner_html or 'dash-table' in inner_html
                    content_length = len(inner_html.strip())
                    
                    results['tests']['weekly_picks'] = {
                        'tab_clicked': True,
                        'content_div_exists': True,
                        'content_length': content_length,
                        'has_datatable': has_datatable,
                        'passed': content_length > 100 and has_datatable
                    }
                    
                    if content_length > 100:
                        print(f"  ✅ Weekly Picks content: {content_length} chars, has DataTable: {has_datatable}")
                    else:
                        print(f"  ❌ Weekly Picks content: {content_length} chars (EMPTY)")
                else:
                    results['tests']['weekly_picks'] = {
                        'tab_clicked': True,
                        'content_div_exists': False,
                        'passed': False
                    }
                    print("  ❌ Weekly Picks #wp-content div NOT FOUND")
                    
                # Screenshot
                await page.screenshot(path='/tmp/weekly_picks.png')
                print("  📸 Screenshot saved: /tmp/weekly_picks.png")
                
            except Exception as e:
                results['tests']['weekly_picks'] = {'error': str(e), 'passed': False}
                print(f"  ❌ Weekly Picks test failed: {e}")
            
            # Test 2: Monthly Picks Tab
            print("\n📊 TEST 2: Monthly Picks Tab")
            try:
                # Click tab
                await page.click('text=Monthly Picks', timeout=10000)
                await asyncio.sleep(3)
                
                # Check if content div exists
                mp_content = await page.query_selector('#mp-content')
                if mp_content:
                    inner_html = await mp_content.inner_html()
                    has_datatable = 'DataTable' in inner_html or 'dash-table' in inner_html
                    content_length = len(inner_html.strip())
                    
                    results['tests']['monthly_picks'] = {
                        'tab_clicked': True,
                        'content_div_exists': True,
                        'content_length': content_length,
                        'has_datatable': has_datatable,
                        'passed': content_length > 100 and has_datatable
                    }
                    
                    if content_length > 100:
                        print(f"  ✅ Monthly Picks content: {content_length} chars, has DataTable: {has_datatable}")
                    else:
                        print(f"  ❌ Monthly Picks content: {content_length} chars (EMPTY)")
                else:
                    results['tests']['monthly_picks'] = {
                        'tab_clicked': True,
                        'content_div_exists': False,
                        'passed': False
                    }
                    print("  ❌ Monthly Picks #mp-content div NOT FOUND")
                    
                # Screenshot
                await page.screenshot(path='/tmp/monthly_picks.png')
                print("  📸 Screenshot saved: /tmp/monthly_picks.png")
                
            except Exception as e:
                results['tests']['monthly_picks'] = {'error': str(e), 'passed': False}
                print(f"  ❌ Monthly Picks test failed: {e}")
            
            # Test 3: Portfolio Tab
            print("\n📊 TEST 3: Portfolio Tab")
            try:
                # Click tab
                await page.click('text=Portfolio', timeout=10000)
                await asyncio.sleep(3)
                
                # Look for Portfolio values (check for "0" or actual values)
                page_text = await page.inner_text('body')
                
                # Check for common portfolio elements
                has_total_value = 'Total Value' in page_text or 'Portfolio Value' in page_text
                has_zeros = page_text.count('$0.00') > 3 or page_text.count('0.00%') > 3
                
                results['tests']['portfolio'] = {
                    'tab_clicked': True,
                    'has_portfolio_labels': has_total_value,
                    'has_many_zeros': has_zeros,
                    'passed': has_total_value and not has_zeros
                }
                
                if has_total_value and not has_zeros:
                    print(f"  ✅ Portfolio tab has values (not all zeros)")
                elif has_zeros:
                    print(f"  ⚠️  Portfolio tab showing many zeros")
                else:
                    print(f"  ❌ Portfolio tab missing expected labels")
                    
                # Screenshot
                await page.screenshot(path='/tmp/portfolio.png')
                print("  📸 Screenshot saved: /tmp/portfolio.png")
                
            except Exception as e:
                results['tests']['portfolio'] = {'error': str(e), 'passed': False}
                print(f"  ❌ Portfolio test failed: {e}")
            
            # Check console errors
            critical_errors = [log for log in console_logs if 'error' in log.lower() and 'datatable' not in log.lower()]
            results['console_errors'] = critical_errors
            results['console_log_count'] = len(console_logs)
            
            # Overall success
            all_passed = all(test.get('passed', False) for test in results['tests'].values())
            results['success'] = all_passed
            
        finally:
            await browser.close()
    
    return results

if __name__ == '__main__':
    print("="*70)
    print("COMPREHENSIVE UI VALIDATION TEST")
    print("="*70)
    
    results = asyncio.run(test_ui_rendering())
    
    # Save results
    output_file = Path('/tmp/ui_validation_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Full results saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY:")
    print("="*70)
    for test_name, test_result in results['tests'].items():
        status = "✅ PASS" if test_result.get('passed') else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n🔍 Console errors: {len(results.get('console_errors', []))}")
    print(f"📊 Overall success: {results['success']}")
    
    sys.exit(0 if results['success'] else 1)
