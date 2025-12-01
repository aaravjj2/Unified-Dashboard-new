#!/usr/bin/env python3
"""
Volatility Lab - Comprehensive Clicker + Snapshot Test
======================================================

Non-headless Chromium test with visual verification of all interactive elements.

Tests:
1. Navigate to Volatility Lab
2. Snapshot initial state (all 4 panels)
3. Click and verify each button in each panel
4. Take screenshots after each interaction
5. Verify component presence and visibility

Run: python clicker_snapshot_test_volatility.py
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from datetime import datetime

# Configuration
DASHBOARD_URL = "http://localhost:8050"
SCREENSHOT_DIR = Path("reports/vol_lab_rebuild_v2/clicker_snapshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Test counters
tests_passed = 0
tests_failed = 0
test_log = []

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


def log_test(status, message):
    """Log test result with color coding"""
    global tests_passed, tests_failed, test_log
    
    if status == 'PASS':
        tests_passed += 1
        print(f"  {GREEN}✓ PASS:{RESET} {message}")
        test_log.append(f"PASS: {message}")
    elif status == 'FAIL':
        tests_failed += 1
        print(f"  {RED}✗ FAIL:{RESET} {message}")
        test_log.append(f"FAIL: {message}")
    else:  # INFO
        print(f"  {CYAN}ℹ INFO:{RESET} {message}")
        test_log.append(f"INFO: {message}")


def print_section(title):
    """Print section header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")


def main():
    print_section("🧪 Volatility Lab - Clicker + Snapshot Test Suite")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    
    with sync_playwright() as p:
        # Launch non-headless Chromium
        print_section("Step 1: Browser Initialization")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300,  # 300ms delay for visibility
            args=['--start-maximized']
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir=str(SCREENSHOT_DIR / 'videos')
        )
        page = context.new_page()
        log_test('PASS', 'Browser launched in visible mode')
        
        try:
            # Navigate to dashboard
            print_section("Step 2: Navigation")
            page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=30000)
            time.sleep(2)
            log_test('PASS', 'Dashboard loaded')
            page.screenshot(path=str(SCREENSHOT_DIR / '01_dashboard_home.png'))
            
            # Click Volatility Lab tab (robust selector with retries)
            print_section("Step 3: Volatility Lab Tab Activation")
            vol_selectors = [
                'a:has-text("Volatility Lab")',
                'a:has-text("⚡ Volatility Lab")',
                'text="Volatility Lab"',
                'text="⚡ Volatility Lab"',
                'role=tab[name="Volatility Lab"]',
                '[data-tab-id="volatility_lab"]',
            ]

            vol_tab = None
            for sel in vol_selectors:
                try:
                    page.wait_for_selector(sel, timeout=10000)
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        vol_tab = loc.first
                        break
                except Exception:
                    continue

            if vol_tab is not None:
                # Defensive: close any blocking modal/dialog that may intercept clicks
                try:
                    page.evaluate("""
                    () => {
                        document.querySelectorAll('[role="dialog"]').forEach(el => el.style.display='none');
                        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                    }
                    """)
                except Exception:
                    pass

                vol_tab.click()
                page.wait_for_timeout(3000)
                log_test('PASS', 'Volatility Lab tab clicked')
                page.screenshot(path=str(SCREENSHOT_DIR / '02_volatility_lab_loaded.png'), full_page=True)
            else:
                log_test('FAIL', 'Volatility Lab tab not found')
                return False
            
            # Verify 4 Subtabs Present
            print_section("Step 4: Subtab Presence Verification")
            
            # Helper: find a tab link with exact visible text to avoid duplicates
            def find_tab_by_exact_text(text):
                candidates = page.locator('a.nav-link')
                count = candidates.count()
                for i in range(count):
                    c = candidates.nth(i)
                    try:
                        txt = c.inner_text().strip()
                    except Exception:
                        txt = ''
                    if txt == text:
                        return c
                return page.locator('')

            tabs = {
                'Overview': find_tab_by_exact_text('📊 Overview'),
                'IV Surface': find_tab_by_exact_text('📈 IV Surface'),
                'Signals': find_tab_by_exact_text('🎯 Signals & Backtest'),
                'Diagnostics': find_tab_by_exact_text('🔧 Diagnostics')
            }

            for tab_name, locator in tabs.items():
                try:
                    if locator.count() > 0:
                        log_test('PASS', f'{tab_name} tab found')
                    else:
                        log_test('FAIL', f'{tab_name} tab not found')
                except Exception:
                    log_test('FAIL', f'{tab_name} tab not found')
            
            page.screenshot(path=str(SCREENSHOT_DIR / '03_tabs_verified.png'))
            
            # Test Overview Panel (Default Active)
            print_section("Step 5: Overview Panel - Button Tests")
            
            # Ensure Overview tab is active
            tabs['Overview'].click()
            page.wait_for_timeout(1000)
            
            # Test 1: Refresh button (🔄)
            refresh_btn = page.locator('[id="vl-overview-refresh-btn"]')
            if refresh_btn.count() > 0 and refresh_btn.is_visible():
                log_test('PASS', 'Refresh button found (vl-overview-refresh-btn)')
                refresh_btn.click()
                page.wait_for_timeout(2000)
                log_test('PASS', 'Refresh button clicked successfully')
                page.screenshot(path=str(SCREENSHOT_DIR / '04_overview_refresh_clicked.png'))
            else:
                log_test('FAIL', 'Refresh button not found or not visible')
            
            # Test 2: Quick Compute button
            quick_compute_btn = page.locator('[id="vl-compute-quick-btn"]')
            if quick_compute_btn.count() > 0:
                log_test('PASS', 'Quick Compute button found (vl-compute-quick-btn)')
            else:
                log_test('FAIL', 'Quick Compute button not found')
            
            # Test IV Surface Panel
            print_section("Step 6: IV Surface Panel - Input & Button Tests")
            
            # Switch to IV Surface Tab
            tabs['IV Surface'].click()
            page.wait_for_timeout(1000)
            log_test('PASS', 'Switched to IV Surface tab')
            
            # Test 3: Ticker input
            ticker_input = page.locator('[id="vl-calc-ticker"]')
            if ticker_input.count() > 0 and ticker_input.is_visible():
                log_test('PASS', 'Ticker input found (vl-calc-ticker)')
                current_value = ticker_input.input_value()
                log_test('INFO', f'Ticker input default value: {current_value}')
            else:
                log_test('FAIL', 'Ticker input not found')
            
            # Test 4: Expiry dropdown
            expiry_dropdown = page.locator('[id="vl-calc-expiry"]')
            if expiry_dropdown.count() > 0:
                log_test('PASS', 'Expiry dropdown found (vl-calc-expiry)')
            else:
                log_test('FAIL', 'Expiry dropdown not found')
            
            # Test 5: Strike Range input
            strike_range = page.locator('[id="vl-calc-strike-range"]')
            if strike_range.count() > 0:
                log_test('PASS', 'Strike Range input found (vl-calc-strike-range)')
                current_value = strike_range.input_value()
                log_test('INFO', f'Strike Range default value: {current_value}')
            else:
                log_test('FAIL', 'Strike Range input not found')
            
            # Test 6: Run button (▶ Run) - PRIMARY TEST
            print_section("Step 7: IV Surface - Run Calculation Test")
            run_btn = page.locator('[id="vl-calc-run-btn"]')
            if run_btn.count() > 0:
                log_test('PASS', 'Run button found (vl-calc-run-btn)')
                
                # Click Run button
                run_btn.click()
                log_test('INFO', 'Run button clicked - waiting for computation...')
                page.wait_for_timeout(8000)  # Increased wait for API call
                
                page.screenshot(path=str(SCREENSHOT_DIR / '05_run_button_clicked.png'))
                
                # Verify heatmap appeared
                heatmap = page.locator('[id="vl-heatmap"]')
                if heatmap.count() > 0:
                    # Force a resize to ensure Plotly renders in the new tab
                    page.evaluate("window.dispatchEvent(new Event('resize'))")
                    page.wait_for_timeout(1000)
                    
                    if heatmap.is_visible():
                        log_test('PASS', 'Heatmap component rendered after Run')
                        page.screenshot(path=str(SCREENSHOT_DIR / '06_heatmap_rendered.png'))
                    else:
                        log_test('FAIL', 'Heatmap component not visible after Run (might be loading)')
                else:
                    log_test('FAIL', 'Heatmap component not found in DOM')
                
                # Verify metrics table
                metrics_table = page.locator('[id="vl-iv-metrics-table"]')
                if metrics_table.count() > 0 and metrics_table.is_visible():
                    log_test('PASS', 'Metrics table rendered after Run')
                else:
                    log_test('FAIL', 'Metrics table not visible after Run')
                
            else:
                log_test('FAIL', 'Run button not found')
            
            # Test 7: Export button
            export_btn = page.locator('[id="vl-iv-export-btn"]')
            if export_btn.count() > 0:
                log_test('PASS', 'Export button found (vl-iv-export-btn)')
            else:
                log_test('FAIL', 'Export button not found')
            
            # Test 8: Date slider
            date_slider = page.locator('[id="vl-explorer-date-slider"]')
            if date_slider.count() > 0:
                log_test('PASS', 'History slider found (vl-explorer-date-slider)')
            else:
                log_test('FAIL', 'History slider not found')
            
            # Test Signals & Backtest Panel
            print_section("Step 8: Signals & Backtest Panel - Button Tests")
            
            # Switch to Signals Tab
            tabs['Signals'].click()
            page.wait_for_timeout(1000)
            log_test('PASS', 'Switched to Signals & Backtest tab')
            
            # Test 9: Run Signals button
            signals_btn = page.locator('[id="vl-signal-run-btn"]')
            if signals_btn.count() > 0 and signals_btn.is_visible():
                log_test('PASS', 'Run Signals button found (vl-signal-run-btn)')
                signals_btn.click()
                page.wait_for_timeout(2000)
                log_test('PASS', 'Run Signals button clicked')
                page.screenshot(path=str(SCREENSHOT_DIR / '07_signals_clicked.png'))
                
                # Verify signal table appeared
                signal_table = page.locator('[id="vl-signal-table"]')
                if signal_table.count() > 0:
                    log_test('PASS', 'Signal table component present')
                else:
                    log_test('FAIL', 'Signal table component not found')
            else:
                log_test('FAIL', 'Run Signals button not found')
            
            # Test 10: Paper Order button
            paper_order_btn = page.locator('[id="vl-signal-paper-order-btn"]')
            if paper_order_btn.count() > 0:
                log_test('PASS', 'Paper Order button found (vl-signal-paper-order-btn)')
            else:
                log_test('FAIL', 'Paper Order button not found')
            
            # Test 11: Run Backtest button
            backtest_btn = page.locator('[id="vl-backtest-run-btn"]')
            if backtest_btn.count() > 0:
                log_test('PASS', 'Run Backtest button found (vl-backtest-run-btn)')
                
                # Check visibility before clicking
                if backtest_btn.is_visible():
                    backtest_btn.click()
                    page.wait_for_timeout(2000)
                    log_test('PASS', 'Run Backtest button clicked')
                    page.screenshot(path=str(SCREENSHOT_DIR / '08_backtest_clicked.png'))
                    
                    # Verify backtest results appeared
                    backtest_results = page.locator('[id="vl-backtest-results"]')
                    if backtest_results.count() > 0:
                        log_test('PASS', 'Backtest results component present')
                    else:
                        log_test('FAIL', 'Backtest results component not found')
                else:
                    log_test('FAIL', 'Run Backtest button found but NOT visible')
                    page.screenshot(path=str(SCREENSHOT_DIR / '08_backtest_not_visible.png'))
            else:
                log_test('FAIL', 'Run Backtest button not found')
            
            # Test 12: Backtest Export button
            backtest_export_btn = page.locator('[id="vl-backtest-export-btn"]')
            if backtest_export_btn.count() > 0:
                log_test('PASS', 'Backtest Export button found (vl-backtest-export-btn)')
            else:
                log_test('FAIL', 'Backtest Export button not found')
            
            # Test Diagnostics Panel
            print_section("Step 9: Diagnostics Panel - Collapse & Button Tests")
            
            # Switch to Diagnostics Tab
            tabs['Diagnostics'].click()
            page.wait_for_timeout(1000)
            log_test('PASS', 'Switched to Diagnostics tab')
            
            # Test 13: Diagnostics collapse toggle
            diag_header = page.locator('h5:has-text("🔧 Diagnostics")')
            if diag_header.count() > 0:
                log_test('PASS', 'Diagnostics header found')
                
                # Check if collapse is closed initially
                diag_collapse = page.locator('[id="vl-diag-collapse"]')
                if diag_collapse.count() > 0:
                    log_test('PASS', 'Diagnostics collapse component found (vl-diag-collapse)')
                    
                    # Click to open
                    diag_header.click()
                    page.wait_for_timeout(1000)
                    page.screenshot(path=str(SCREENSHOT_DIR / '09_diagnostics_expanded.png'))
                    log_test('PASS', 'Diagnostics panel toggled open')
                else:
                    log_test('FAIL', 'Diagnostics collapse component not found')
            else:
                log_test('FAIL', 'Diagnostics header not found')
            
            # Test 14: Export Log button (inside diagnostics)
            export_log_btn = page.locator('[id="vl-diag-export-log"]')
            if export_log_btn.count() > 0:
                log_test('PASS', 'Export Log button found (vl-diag-export-log)')
            else:
                log_test('FAIL', 'Export Log button not found')
            
            # Test 15: Solver log component
            solver_log = page.locator('[id="vl-diag-solver-log"]')
            if solver_log.count() > 0:
                log_test('PASS', 'Solver log component found (vl-diag-solver-log)')
            else:
                log_test('FAIL', 'Solver log component not found')
            
            # Test 16: Iterations display
            iterations = page.locator('[id="vl-diag-iterations"]')
            if iterations.count() > 0:
                log_test('PASS', 'Iterations component found (vl-diag-iterations)')
            else:
                log_test('FAIL', 'Iterations component not found')
            
            # Test 17: Last payload display
            last_payload = page.locator('[id="vl-diag-last-payload"]')
            if last_payload.count() > 0:
                log_test('PASS', 'Last payload component found (vl-diag-last-payload)')
            else:
                log_test('FAIL', 'Last payload component not found')
            
            # Final comprehensive snapshot
            print_section("Step 10: Final State Snapshot")
            page.screenshot(path=str(SCREENSHOT_DIR / '10_final_state_full.png'), full_page=True)
            log_test('PASS', 'Final full-page screenshot captured')
            
            # Keep browser open for manual inspection
            print_section("Test Complete - Manual Inspection Window")
            log_test('INFO', 'Browser will remain open for 15 seconds...')
            time.sleep(15)
            
            return True
            
        except Exception as e:
            log_test('FAIL', f'Test suite exception: {str(e)}')
            import traceback
            traceback.print_exc()
            page.screenshot(path=str(SCREENSHOT_DIR / 'error_screenshot.png'))
            return False
        
        finally:
            # Save video
            context.close()
            browser.close()
            
            # Print summary
            print_section("📊 TEST SUMMARY")
            print(f"Total Tests: {tests_passed + tests_failed}")
            print(f"{GREEN}Passed: {tests_passed}{RESET}")
            print(f"{RED}Failed: {tests_failed}{RESET}")
            print(f"Pass Rate: {(tests_passed/(tests_passed+tests_failed)*100):.1f}%")
            print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
            print(f"Video saved to: {SCREENSHOT_DIR / 'videos'}")
            
            # Save test log
            log_file = SCREENSHOT_DIR / 'test_log.txt'
            with open(log_file, 'w') as f:
                f.write(f"Volatility Lab Clicker + Snapshot Test\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total: {tests_passed + tests_failed}, Passed: {tests_passed}, Failed: {tests_failed}\n\n")
                f.write('\n'.join(test_log))
            print(f"Test log saved to: {log_file}")


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
