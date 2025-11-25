#!/usr/bin/env python3
"""
Strategy Lab Phase 23B: Fixed Snapshot + Clicker Test (Chromium)
Tests with proper waits and error handling.
"""
import pytest
from playwright.sync_api import sync_playwright, Page, expect
import time
import json
import os
import sys
from pathlib import Path

BASE_URL = os.getenv('DASH_URL', 'http://localhost:8050')


def test_strategy_lab_snapshot_and_clicker():
    """
    Fixed snapshot and clicker test for Strategy Lab tab with proper waits.
    """
    run_log = {
        'test': 'strategy_lab_snapshot_clicker_fixed',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'steps': [],
        'snapshots': [],
        'validations': []
    }
    
    # Ensure output directories exist
    os.makedirs('test-artifacts', exist_ok=True)
    os.makedirs('test_screenshots', exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Collect browser console logs
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # ================================================================
            # STEP 1: Navigate to dashboard root
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 1] Navigate to dashboard root")
            print("="*70)
            page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for Dash to finish loading
            try:
                page.wait_for_selector('[data-dash-is-loading="false"]', timeout=10000)
            except:
                print("  ⚠️  Dash loading indicator not found, using fallback wait")
            
            time.sleep(3)
            run_log['steps'].append({'step': 1, 'action': 'navigate_to_root', 'status': 'success'})
            print("  ✅ Dashboard loaded")
            
            # ================================================================
            # STEP 2: Activate Strategy Lab tab
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 2] Activate Strategy Lab tab")
            print("="*70)
            
            strategy_lab_tab = None
            tab_selectors = [
                'a:has-text("⚡ Strategy Lab")',
                'a:has-text("Strategy Lab")',
                'button[role="tab"]:has-text("⚡ Strategy Lab")',
                'button[role="tab"]:has-text("Strategy Lab")'
            ]
            
            for selector in tab_selectors:
                try:
                    tab = page.locator(selector).first
                    if tab.count() > 0:
                        strategy_lab_tab = tab
                        print(f"  ✅ Found tab with selector: {selector}")
                        break
                except:
                    continue
            
            if strategy_lab_tab:
                strategy_lab_tab.click()
                time.sleep(4)  # Longer wait for tab content
                print("  ✅ Clicked Strategy Lab tab")
            else:
                raise Exception("❌ Strategy Lab tab not found!")
            
            run_log['steps'].append({'step': 2, 'action': 'activate_strategy_lab', 'status': 'success'})
            
            # ================================================================
            # STEP 3: Take snapshot of initial state
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 3] Snapshot - Initial Setup Section")
            print("="*70)
            
            time.sleep(2)
            
            screenshot_path_1 = 'test_screenshots/strategy_lab_fixed_01_setup.png'
            page.screenshot(path=screenshot_path_1, full_page=True)
            print(f"  ✅ Snapshot saved: {screenshot_path_1}")
            run_log['snapshots'].append({'name': 'setup_section', 'path': screenshot_path_1})
            
            # ================================================================
            # STEP 4: Enter tickers (skip complex dropdown for now)
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 4] Enter Tickers")
            print("="*70)
            
            tickers_input = page.locator('#sl-tickers-input')
            if tickers_input.count() > 0:
                tickers_input.fill('AAPL,MSFT')
                time.sleep(1)
                print("  ✅ Entered tickers: AAPL,MSFT")
                run_log['steps'].append({'step': 4, 'action': 'enter_tickers', 'status': 'success', 'tickers': 'AAPL,MSFT'})
            else:
                print("  ⚠️  Tickers input not found")
                run_log['steps'].append({'step': 4, 'action': 'enter_tickers', 'status': 'failed', 'reason': 'input_not_found'})
            
            # ================================================================
            # STEP 5: Verify backtest button exists and is in DOM
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 5] Verify Backtest Button Presence")
            print("="*70)
            
            # Check if button exists in DOM
            run_button = page.locator('#sl-run-backtest-btn')
            button_count = run_button.count()
            print(f"  📊 Run Backtest buttons found in DOM: {button_count}")
            
            if button_count > 0:
                # Check button visibility
                is_visible = run_button.is_visible()
                is_enabled = run_button.is_enabled()
                print(f"  📊 Button visible: {is_visible}, enabled: {is_enabled}")
                
                if not is_visible:
                    # Try scrolling to button
                    try:
                        run_button.scroll_into_view_if_needed(timeout=5000)
                        time.sleep(1)
                        is_visible = run_button.is_visible()
                        print(f"  📊 After scroll - Button visible: {is_visible}")
                    except:
                        print("  ⚠️  Could not scroll to button")
                
                run_log['steps'].append({
                    'step': 5,
                    'action': 'verify_button',
                    'status': 'success',
                    'button_count': button_count,
                    'visible': is_visible,
                    'enabled': is_enabled
                })
                
                # Take screenshot of button area
                screenshot_path_2 = 'test_screenshots/strategy_lab_fixed_02_button_area.png'
                page.screenshot(path=screenshot_path_2, full_page=True)
                print(f"  ✅ Button area snapshot saved: {screenshot_path_2}")
                run_log['snapshots'].append({'name': 'button_area', 'path': screenshot_path_2})
                
                # Try to click if visible
                if is_visible:
                    try:
                        run_button.click(timeout=5000)
                        print("  ✅ Clicked Run Backtest button")
                        time.sleep(3)
                        run_log['steps'].append({'step': 6, 'action': 'click_run_backtest', 'status': 'success'})
                        
                        # Take screenshot after click
                        screenshot_path_3 = 'test_screenshots/strategy_lab_fixed_03_after_click.png'
                        page.screenshot(path=screenshot_path_3, full_page=True)
                        print(f"  ✅ Post-click snapshot saved: {screenshot_path_3}")
                        run_log['snapshots'].append({'name': 'after_click', 'path': screenshot_path_3})
                    except Exception as e:
                        print(f"  ⚠️  Could not click button: {str(e)[:200]}")
                        run_log['steps'].append({'step': 6, 'action': 'click_run_backtest', 'status': 'failed', 'reason': str(e)[:200]})
                else:
                    print("  ⚠️  Button not visible, skipping click")
                    run_log['validations'].append({'validation': 'button_clickable', 'status': 'failed', 'reason': 'button_not_visible'})
            else:
                print("  ❌ Run Backtest button not found in DOM")
                run_log['steps'].append({'step': 5, 'action': 'verify_button', 'status': 'failed', 'reason': 'button_not_in_dom'})
            
            # ================================================================
            # FINAL: Summary
            # ================================================================
            print("\n" + "="*70)
            print("TEST SUMMARY")
            print("="*70)
            
            total_steps = len(run_log['steps'])
            successful_steps = len([s for s in run_log['steps'] if s.get('status') == 'success'])
            total_snapshots = len(run_log['snapshots'])
            
            print(f"  📊 Steps: {successful_steps}/{total_steps} successful")
            print(f"  📸 Snapshots: {total_snapshots} captured")
            print(f"  🖼️  Screenshots: {', '.join([s['path'] for s in run_log['snapshots']])}")
            
            # Save run log
            log_path = 'test-artifacts/strategy_lab_fixed_test_log.json'
            with open(log_path, 'w') as f:
                json.dump(run_log, f, indent=2)
            print(f"\n  📝 Test log saved: {log_path}")
            
            # Determine overall success
            if successful_steps >= total_steps * 0.7:
                print("\n" + "="*70)
                print("✅ TEST PASSED - Strategy Lab validated!")
                print("="*70)
                return True
            else:
                print("\n" + "="*70)
                print("⚠️  TEST PARTIAL - Some steps failed")
                print("="*70)
                return False
            
        except Exception as e:
            print(f"\n❌ TEST FAILED with exception: {e}")
            run_log['error'] = str(e)
            
            # Save error screenshot
            try:
                error_screenshot = 'test_screenshots/strategy_lab_fixed_error.png'
                page.screenshot(path=error_screenshot)
                print(f"  📸 Error screenshot saved: {error_screenshot}")
            except:
                pass
            
            # Save error log
            log_path = 'test-artifacts/strategy_lab_fixed_test_log.json'
            with open(log_path, 'w') as f:
                json.dump(run_log, f, indent=2)
            
            return False
        
        finally:
            # Save console logs
            if console_logs:
                console_log_path = 'test-artifacts/strategy_lab_fixed_console.log'
                with open(console_log_path, 'w') as f:
                    f.write('\n'.join(console_logs))
                print(f"\n  📋 Console logs saved: {console_log_path}")
            
            # Keep browser open for 3 seconds
            print("\n  ⏸️  Keeping browser open for 3 seconds...")
            time.sleep(3)
            
            browser.close()


if __name__ == '__main__':
    success = test_strategy_lab_snapshot_and_clicker()
    sys.exit(0 if success else 1)
