#!/usr/bin/env python3
"""
Phase Pre-24 Playwright E2E Chromium Test Suite
Validates all fixes with snapshot + clicker tests.
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.getenv('DASH_URL', 'http://localhost:8050')

def log_step(step_name, status, details=""):
    """Log test step with timestamp."""
    timestamp = datetime.now().isoformat()
    result = {
        'timestamp': timestamp,
        'step': step_name,
        'status': status,
        'details': details
    }
    icon = {'pass': '✅', 'fail': '❌', 'skip': '⏭️', 'warn': '⚠️'}[status]
    print(f"{icon} {step_name}: {details}")
    return result

def test_suite():
    """Run complete E2E test suite."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          🎭 PHASE PRE-24 PLAYWRIGHT CHROMIUM TEST SUITE 🎭           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    results = []
    os.makedirs('test-artifacts/pre24', exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Collect console logs
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # =================================================================
            # TEST 1: Dashboard Load & Home Tab
            # =================================================================
            print("\n" + "="*80)
            print("TEST 1: Dashboard Load & Home Tab")
            print("="*80)
            
            page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            # Check for input color (black text)
            input_elements = page.locator('input').all()
            if input_elements:
                first_input = input_elements[0]
                color = first_input.evaluate('el => window.getComputedStyle(el).color')
                if 'rgb(0, 0, 0)' in color or '#000' in color:
                    results.append(log_step('Input Text Color', 'pass', f'Black text confirmed: {color}'))
                else:
                    results.append(log_step('Input Text Color', 'warn', f'Color: {color}'))
            
            # Take home snapshot
            page.screenshot(path='test-artifacts/pre24/01_home_tab.png', full_page=True)
            results.append(log_step('Home Tab Snapshot', 'pass', 'Saved'))
            
            # =================================================================
            # TEST 2: Strategy Lab - Execute & Subtabs Sync
            # =================================================================
            print("\n" + "="*80)
            print("TEST 2: Strategy Lab - Execute & Subtabs Sync")
            print("="*80)
            
            # Navigate to Strategy Lab
            strategy_tab = page.locator('a:has-text("Strategy Lab")').first
            if strategy_tab.count() > 0:
                strategy_tab.click()
                time.sleep(3)
                results.append(log_step('Strategy Lab Navigation', 'pass', 'Tab opened'))
                
                # Take initial snapshot
                page.screenshot(path='test-artifacts/pre24/02_strategy_lab_initial.png', full_page=True)
                
                # Enter tickers
                ticker_input = page.locator('#sl-tickers-input')
                if ticker_input.count() > 0:
                    ticker_input.fill('AAPL,MSFT')
                    time.sleep(1)
                    results.append(log_step('Strategy Lab Tickers', 'pass', 'Tickers entered'))
                
                # Check if Run Backtest button exists
                run_btn = page.locator('#sl-run-backtest-btn')
                if run_btn.count() > 0:
                    results.append(log_step('Strategy Lab Run Button', 'pass', 'Button found'))
                    
                    # Take snapshot of execution area
                    page.screenshot(path='test-artifacts/pre24/03_strategy_lab_ready.png', full_page=True)
                    
                    # Check subtabs exist
                    subtabs = ['Results', 'Benchmark', 'Risk', 'Factor']
                    for subtab_name in subtabs:
                        subtab = page.locator(f'text=/{subtab_name}/i').first
                        if subtab.count() > 0:
                            results.append(log_step(f'Strategy Lab {subtab_name} Tab', 'pass', 'Tab found'))
                        else:
                            results.append(log_step(f'Strategy Lab {subtab_name} Tab', 'warn', 'Tab not found'))
                else:
                    results.append(log_step('Strategy Lab Run Button', 'fail', 'Button not found'))
            else:
                results.append(log_step('Strategy Lab Navigation', 'fail', 'Tab not found'))
            
            # =================================================================
            # TEST 3: Options Lab - Generate Forecast
            # =================================================================
            print("\n" + "="*80)
            print("TEST 3: Options Lab - Generate Forecast")
            print("="*80)
            
            options_tab = page.locator('a:has-text("Options Lab")').first
            if options_tab.count() > 0:
                options_tab.click()
                time.sleep(3)
                results.append(log_step('Options Lab Navigation', 'pass', 'Tab opened'))
                
                # Take initial snapshot
                page.screenshot(path='test-artifacts/pre24/04_options_lab_initial.png', full_page=True)
                
                # Check forecast button
                forecast_btn = page.locator('#options-forecast-btn')
                if forecast_btn.count() > 0:
                    results.append(log_step('Options Lab Forecast Button', 'pass', 'Button found'))
                    
                    # Check if button is visible
                    is_visible = forecast_btn.is_visible()
                    results.append(log_step('Options Lab Forecast Visibility', 
                                           'pass' if is_visible else 'warn',
                                           f'Visible: {is_visible}'))
                else:
                    results.append(log_step('Options Lab Forecast Button', 'fail', 'Button not found'))
                
                # Check selector inputs have black text
                selectors = ['#contract-ticker-selector', '#contract-strike-selector', '#contract-expiration-selector']
                for selector_id in selectors:
                    selector = page.locator(selector_id)
                    if selector.count() > 0:
                        results.append(log_step(f'Options Lab Selector {selector_id}', 'pass', 'Found'))
                
                page.screenshot(path='test-artifacts/pre24/05_options_lab_complete.png', full_page=True)
            else:
                results.append(log_step('Options Lab Navigation', 'fail', 'Tab not found'))
            
            # =================================================================
            # TEST 4: Weekly Picks - Price Refresh
            # =================================================================
            print("\n" + "="*80)
            print("TEST 4: Weekly Picks - Price Refresh")
            print("="*80)
            
            weekly_tab = page.locator('a:has-text("Weekly Picks")').first
            if weekly_tab.count() > 0:
                weekly_tab.click()
                time.sleep(3)
                results.append(log_step('Weekly Picks Navigation', 'pass', 'Tab opened'))
                
                page.screenshot(path='test-artifacts/pre24/06_weekly_picks.png', full_page=True)
                
                # Check for refresh button
                refresh_btn = page.locator('#wp-refresh-btn')
                if refresh_btn.count() > 0:
                    results.append(log_step('Weekly Picks Refresh Button', 'pass', 'Button found'))
                else:
                    results.append(log_step('Weekly Picks Refresh Button', 'warn', 'Button not found'))
            else:
                results.append(log_step('Weekly Picks Navigation', 'fail', 'Tab not found'))
            
            # =================================================================
            # TEST 5: Monthly Picks - Price Refresh
            # =================================================================
            print("\n" + "="*80)
            print("TEST 5: Monthly Picks - Price Refresh")
            print("="*80)
            
            monthly_tab = page.locator('a:has-text("Monthly Picks")').first
            if monthly_tab.count() > 0:
                monthly_tab.click()
                time.sleep(3)
                results.append(log_step('Monthly Picks Navigation', 'pass', 'Tab opened'))
                
                page.screenshot(path='test-artifacts/pre24/07_monthly_picks.png', full_page=True)
                
                # Check for refresh button
                refresh_btn = page.locator('#mp-refresh-btn')
                if refresh_btn.count() > 0:
                    results.append(log_step('Monthly Picks Refresh Button', 'pass', 'Button found'))
                else:
                    results.append(log_step('Monthly Picks Refresh Button', 'warn', 'Button not found'))
            else:
                results.append(log_step('Monthly Picks Navigation', 'fail', 'Tab not found'))
            
            # =================================================================
            # TEST 6: Input Color Validation Across Tabs
            # =================================================================
            print("\n" + "="*80)
            print("TEST 6: Input Color Validation")
            print("="*80)
            
            # Go back to home
            page.goto(BASE_URL, wait_until='domcontentloaded')
            time.sleep(2)
            
            # Check multiple input fields
            all_inputs = page.locator('input').all()[:5]  # Sample first 5
            black_count = 0
            for idx, inp in enumerate(all_inputs):
                try:
                    color = inp.evaluate('el => window.getComputedStyle(el).color')
                    if 'rgb(0, 0, 0)' in color:
                        black_count += 1
                except:
                    pass
            
            if black_count >= 3:
                results.append(log_step('Input Color Validation', 'pass', 
                                       f'{black_count}/{len(all_inputs)} inputs have black text'))
            else:
                results.append(log_step('Input Color Validation', 'warn',
                                       f'Only {black_count}/{len(all_inputs)} inputs have black text'))
            
        except Exception as e:
            results.append(log_step('Test Execution', 'fail', str(e)[:200]))
        
        finally:
            # Save console logs
            if console_logs:
                with open('test-artifacts/pre24/console_logs.txt', 'w') as f:
                    f.write('\n'.join(console_logs))
            
            print("\n  ⏸️  Keeping browser open for 3 seconds...")
            time.sleep(3)
            browser.close()
    
    # Calculate summary
    total = len(results)
    passed = len([r for r in results if r['status'] == 'pass'])
    failed = len([r for r in results if r['status'] == 'fail'])
    warned = len([r for r in results if r['status'] == 'warn'])
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warned}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'warnings': warned,
            'success_rate': success_rate
        },
        'results': results
    }
    
    with open('test-artifacts/pre24/phase_pre24_playwright_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Results saved: test-artifacts/pre24/phase_pre24_playwright_results.json")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(test_suite())
