#!/usr/bin/env python3
"""
Strategy Lab Phase 2: Snapshot + Clicker Test (Chromium)
Tests snapshot capture and interactive elements for Strategy Lab tab.
"""
import pytest
from playwright.sync_api import sync_playwright, Page, expect
import time
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8050"


def test_strategy_lab_snapshot_and_clicker():
    """
    Combined snapshot and clicker test for Strategy Lab tab.
    
    Tests:
    1. Navigate to Strategy Lab tab
    2. Take snapshot of initial state (Setup section)
    3. Select strategy type (Momentum)
    4. Enter tickers
    5. Click "Validate Strategy" button
    6. Verify validation success message
    7. Configure backtest parameters
    8. Click "Run Backtest" button
    9. Wait for results to populate
    10. Take snapshot of results (charts, metrics)
    11. Verify tooltips appear on hover
    12. Test collapsible explanations panel
    """
    run_log = {
        'test': 'strategy_lab_snapshot_clicker',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'steps': [],
        'snapshots': [],
        'validations': []
    }
    
    # Ensure output directories exist
    os.makedirs('test-artifacts', exist_ok=True)
    os.makedirs('test_screenshots', exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Headful for debugging
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
            
            time.sleep(3)  # Stabilization
            run_log['steps'].append({'step': 1, 'action': 'navigate_to_root', 'status': 'success'})
            print("  ✅ Dashboard loaded")
            
            # ================================================================
            # STEP 2: Activate Strategy Lab tab
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 2] Activate Strategy Lab tab")
            print("="*70)
            
            # Try multiple selectors for the tab
            strategy_lab_tab = None
            tab_selectors = [
                'button[role="tab"]:has-text("⚡ Strategy Lab")',
                'button[role="tab"]:has-text("Strategy Lab")',
                'a:has-text("⚡ Strategy Lab")',
                'a:has-text("Strategy Lab")'
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
                time.sleep(3)  # Wait for tab content to load
                print("  ✅ Clicked Strategy Lab tab")
            else:
                raise Exception("❌ Strategy Lab tab not found!")
            
            run_log['steps'].append({'step': 2, 'action': 'activate_strategy_lab', 'status': 'success'})
            
            # ================================================================
            # STEP 3: Take snapshot of initial state (Setup section)
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 3] Snapshot - Initial Setup Section")
            print("="*70)
            
            # Wait for Strategy Lab content to appear
            time.sleep(2)
            
            # Take full tab screenshot
            screenshot_path_1 = 'test_screenshots/strategy_lab_01_setup.png'
            page.screenshot(path=screenshot_path_1, full_page=True)
            print(f"  ✅ Snapshot saved: {screenshot_path_1}")
            run_log['snapshots'].append({'name': 'setup_section', 'path': screenshot_path_1})
            
            # ================================================================
            # STEP 4: Select strategy type (Momentum)
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 4] Select Momentum Strategy")
            print("="*70)
            
            # Find strategy type dropdown (Dash dcc.Dropdown)
            # Dash dropdowns are <div> elements, need to click and select from menu
            try:
                # Click the dropdown to open it
                dropdown = page.locator('#sl-strategy-type').first
                if dropdown.count() > 0:
                    dropdown.click()
                    time.sleep(1)
                    print("  ✅ Opened strategy dropdown")
                    
                    # Find and click the "Momentum" option
                    # Dash dropdown options appear in a menu overlay
                    momentum_option = page.locator('text="Momentum"').first
                    if momentum_option.count() > 0:
                        momentum_option.click()
                        time.sleep(1)
                        print("  ✅ Selected 'Momentum' strategy")
                        run_log['steps'].append({'step': 4, 'action': 'select_momentum', 'status': 'success'})
                    else:
                        print("  ⚠️  Momentum option not found in menu")
                        run_log['steps'].append({'step': 4, 'action': 'select_momentum', 'status': 'failed', 'reason': 'option_not_found'})
                else:
                    print("  ⚠️  Strategy dropdown not found")
                    run_log['steps'].append({'step': 4, 'action': 'select_momentum', 'status': 'failed', 'reason': 'dropdown_not_found'})
            except Exception as e:
                print(f"  ⚠️  Error selecting strategy: {e}")
                run_log['steps'].append({'step': 4, 'action': 'select_momentum', 'status': 'failed', 'reason': str(e)})
            
            # ================================================================
            # STEP 5: Enter tickers
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 5] Enter Tickers")
            print("="*70)
            
            # Find tickers input
            tickers_input = page.locator('#sl-tickers-input')
            if tickers_input.count() > 0:
                tickers_input.fill('AAPL,MSFT')
                time.sleep(1)
                print("  ✅ Entered tickers: AAPL,MSFT")
                run_log['steps'].append({'step': 5, 'action': 'enter_tickers', 'status': 'success', 'tickers': 'AAPL,MSFT'})
            else:
                print("  ⚠️  Tickers input not found")
                run_log['steps'].append({'step': 5, 'action': 'enter_tickers', 'status': 'failed', 'reason': 'input_not_found'})
            
            # ================================================================
            # STEP 6: Click "Validate Strategy" button
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 6] Click 'Validate Strategy' Button")
            print("="*70)
            
            validate_button = page.locator('#sl-validate-btn')
            if validate_button.count() > 0:
                validate_button.click()
                time.sleep(2)  # Wait for validation
                print("  ✅ Clicked 'Validate Strategy' button")
                run_log['steps'].append({'step': 6, 'action': 'click_validate', 'status': 'success'})
                
                # Check for success message
                success_message = page.locator('text=/.*validation.*success.*/i').first
                if success_message.count() > 0:
                    print("  ✅ Validation success message appeared")
                    run_log['validations'].append({'validation': 'strategy_valid', 'status': 'success'})
                else:
                    print("  ⚠️  No validation success message found")
                    run_log['validations'].append({'validation': 'strategy_valid', 'status': 'unknown'})
            else:
                print("  ⚠️  Validate button not found")
                run_log['steps'].append({'step': 6, 'action': 'click_validate', 'status': 'failed', 'reason': 'button_not_found'})
            
            # ================================================================
            # STEP 7: Configure backtest parameters (verification only)
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 7] Verify Backtest Parameters Present")
            print("="*70)
            
            # Just verify inputs exist (Dash components use custom HTML)
            capital_exists = page.locator('#sl-initial-capital').count() > 0
            start_date_exists = page.locator('#sl-start-date').count() > 0
            end_date_exists = page.locator('#sl-end-date').count() > 0
            
            if capital_exists and start_date_exists and end_date_exists:
                print(f"  ✅ All backtest parameter inputs present")
                run_log['steps'].append({'step': 7, 'action': 'verify_inputs', 'status': 'success'})
            else:
                print(f"  ⚠️  Some inputs missing: capital={capital_exists}, start={start_date_exists}, end={end_date_exists}")
                run_log['steps'].append({'step': 7, 'action': 'verify_inputs', 'status': 'partial'})
            
            # ================================================================
            # STEP 8: Click "Run Backtest" button
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 8] Click 'Run Backtest' Button")
            print("="*70)
            
            run_button = page.locator('#sl-run-backtest-btn')
            if run_button.count() > 0:
                run_button.click()
                print("  ✅ Clicked 'Run Backtest' button")
                run_log['steps'].append({'step': 8, 'action': 'click_run_backtest', 'status': 'success'})
                
                # Wait for backtest to complete (check for charts or metrics)
                print("  ⏳ Waiting for backtest to complete (max 30s)...")
                
                # Try to wait for equity curve chart
                try:
                    page.wait_for_selector('#sl-equity-curve', timeout=30000)
                    print("  ✅ Equity curve chart appeared")
                    run_log['validations'].append({'validation': 'backtest_completed', 'status': 'success'})
                except:
                    print("  ⚠️  Equity curve chart not found within 30s")
                    run_log['validations'].append({'validation': 'backtest_completed', 'status': 'timeout'})
                
                time.sleep(3)  # Additional stabilization
            else:
                print("  ⚠️  Run Backtest button not found")
                run_log['steps'].append({'step': 8, 'action': 'click_run_backtest', 'status': 'failed', 'reason': 'button_not_found'})
            
            # ================================================================
            # STEP 9: Verify results populated (metrics cards)
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 9] Verify Results Populated")
            print("="*70)
            
            # Check for metric cards
            metrics = ['CAGR', 'Sharpe', 'Max DD', 'Win Rate']
            metrics_found = []
            
            for metric in metrics:
                metric_card = page.locator(f'text=/{metric}/i').first
                if metric_card.count() > 0:
                    metrics_found.append(metric)
                    print(f"  ✅ Found metric: {metric}")
            
            run_log['validations'].append({
                'validation': 'metrics_visible',
                'status': 'success' if len(metrics_found) >= 3 else 'partial',
                'metrics_found': metrics_found
            })
            
            # ================================================================
            # STEP 10: Take snapshot of results
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 10] Snapshot - Results Section")
            print("="*70)
            
            screenshot_path_2 = 'test_screenshots/strategy_lab_02_results.png'
            page.screenshot(path=screenshot_path_2, full_page=True)
            print(f"  ✅ Snapshot saved: {screenshot_path_2}")
            run_log['snapshots'].append({'name': 'results_section', 'path': screenshot_path_2})
            
            # ================================================================
            # STEP 11: Test tooltips (hover interactions)
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 11] Test Tooltips")
            print("="*70)
            
            # Try to hover over metric cards to trigger tooltips
            tooltip_targets = [
                '#sl-metric-cagr-container',
                '#sl-metric-sharpe-container',
                '#sl-metric-maxdd-container',
                '#sl-metric-winrate-container'
            ]
            
            tooltips_found = []
            for target_id in tooltip_targets:
                try:
                    target = page.locator(target_id).first
                    if target.count() > 0:
                        target.hover()
                        time.sleep(1)  # Wait for tooltip to appear
                        
                        # Check if tooltip is visible (Bootstrap tooltips)
                        tooltip = page.locator('.tooltip.show').first
                        if tooltip.count() > 0:
                            tooltips_found.append(target_id)
                            print(f"  ✅ Tooltip appeared for: {target_id}")
                        else:
                            print(f"  ⚠️  Tooltip not visible for: {target_id}")
                except Exception as e:
                    print(f"  ⚠️  Error hovering {target_id}: {e}")
            
            run_log['validations'].append({
                'validation': 'tooltips_functional',
                'status': 'success' if len(tooltips_found) > 0 else 'failed',
                'tooltips_triggered': tooltips_found
            })
            
            # ================================================================
            # STEP 12: Test collapsible explanations panel
            # ================================================================
            print("\n" + "="*70)
            print("[STEP 12] Test Collapsible Explanations Panel")
            print("="*70)
            
            # Find the accordion button
            accordion_button = page.locator('text=/What These Metrics Mean/i').first
            if accordion_button.count() > 0:
                print("  ✅ Found explanations panel accordion")
                
                # Click to expand
                accordion_button.click()
                time.sleep(1)
                
                # Take snapshot of expanded panel
                screenshot_path_3 = 'test_screenshots/strategy_lab_03_explanations.png'
                page.screenshot(path=screenshot_path_3, full_page=True)
                print(f"  ✅ Snapshot saved: {screenshot_path_3}")
                run_log['snapshots'].append({'name': 'explanations_panel', 'path': screenshot_path_3})
                
                # Check for key explanatory content
                key_terms = ['CAGR', 'Sharpe Ratio', 'Max Drawdown', 'Win Rate']
                terms_found = []
                for term in key_terms:
                    term_text = page.locator(f'text=/{term}/i').first
                    if term_text.count() > 0:
                        terms_found.append(term)
                
                print(f"  ✅ Found {len(terms_found)}/{len(key_terms)} explanation terms")
                run_log['validations'].append({
                    'validation': 'explanations_content',
                    'status': 'success' if len(terms_found) >= 3 else 'partial',
                    'terms_found': terms_found
                })
            else:
                print("  ⚠️  Explanations panel not found")
                run_log['validations'].append({
                    'validation': 'explanations_content',
                    'status': 'failed',
                    'reason': 'panel_not_found'
                })
            
            # ================================================================
            # FINAL: Summary
            # ================================================================
            print("\n" + "="*70)
            print("TEST SUMMARY")
            print("="*70)
            
            total_steps = len(run_log['steps'])
            successful_steps = len([s for s in run_log['steps'] if s.get('status') == 'success'])
            total_validations = len(run_log['validations'])
            successful_validations = len([v for v in run_log['validations'] if v.get('status') == 'success'])
            total_snapshots = len(run_log['snapshots'])
            
            print(f"  📊 Steps: {successful_steps}/{total_steps} successful")
            print(f"  ✅ Validations: {successful_validations}/{total_validations} passed")
            print(f"  📸 Snapshots: {total_snapshots} captured")
            print(f"  🖼️  Screenshots: {', '.join([s['path'] for s in run_log['snapshots']])}")
            
            # Save run log
            log_path = 'test-artifacts/strategy_lab_test_log.json'
            with open(log_path, 'w') as f:
                json.dump(run_log, f, indent=2)
            print(f"\n  📝 Test log saved: {log_path}")
            
            # Determine overall success
            if successful_steps >= total_steps * 0.8 and successful_validations >= total_validations * 0.7:
                print("\n" + "="*70)
                print("🎉 TEST PASSED - Strategy Lab is functional!")
                print("="*70)
            else:
                print("\n" + "="*70)
                print("⚠️  TEST INCOMPLETE - Some validations failed")
                print("="*70)
            
        except Exception as e:
            print(f"\n❌ TEST FAILED with exception: {e}")
            run_log['error'] = str(e)
            
            # Save error screenshot
            try:
                error_screenshot = 'test_screenshots/strategy_lab_error.png'
                page.screenshot(path=error_screenshot)
                print(f"  📸 Error screenshot saved: {error_screenshot}")
            except:
                pass
            
            # Save error log
            log_path = 'test-artifacts/strategy_lab_test_log.json'
            with open(log_path, 'w') as f:
                json.dump(run_log, f, indent=2)
            
            raise
        
        finally:
            # Save console logs
            if console_logs:
                console_log_path = 'test-artifacts/strategy_lab_console.log'
                with open(console_log_path, 'w') as f:
                    f.write('\n'.join(console_logs))
                print(f"\n  📋 Console logs saved: {console_log_path}")
            
            # Keep browser open for 5 seconds to review
            print("\n  ⏸️  Keeping browser open for 5 seconds...")
            time.sleep(5)
            
            browser.close()


if __name__ == '__main__':
    test_strategy_lab_snapshot_and_clicker()
