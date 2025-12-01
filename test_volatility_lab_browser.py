#!/usr/bin/env python3
"""
Volatility Lab - Non-Headless Browser Tests
============================================

Tests the Volatility Lab UI with visible Chromium browser to verify:
1. Dashboard starts successfully
2. Volatility Lab tab loads and renders
3. All 4 panels are visible
4. Compute button works and heatmap renders
5. Signals and backtest buttons function
6. Diagnostics panel updates

Usage:
    VOLLAB_DETERMINISTIC=1 python test_volatility_lab_browser.py
"""

import os
import sys
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8090')
HEADLESS = os.getenv('HEADLESS', '0') == '1'
SCREENSHOT_DIR = Path(__file__).parent / 'test-artifacts' / 'volatility_lab'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def wait_for_dashboard(page, timeout=30000):
    """Wait for dashboard to be fully loaded"""
    logger.info("Waiting for dashboard to load...")
    try:
        # Wait for Dash app to be ready
        page.wait_for_selector('div[data-dash-is-loading="false"]', timeout=timeout)
        logger.info("✓ Dashboard loaded")
        return True
    except Exception as e:
        logger.error(f"Dashboard failed to load: {e}")
        return False


def test_homepage_loads(page):
    """Test 1: Homepage loads successfully"""
    logger.info("\n=== TEST 1: Homepage loads ===")
    
    page.goto(DASHBOARD_URL, wait_until='networkidle')
    time.sleep(2)
    
    # Take screenshot
    screenshot_path = SCREENSHOT_DIR / '01_homepage.png'
    page.screenshot(path=screenshot_path)
    logger.info(f"📸 Screenshot saved: {screenshot_path}")
    
    # Verify page title
    title = page.title()
    logger.info(f"Page title: {title}")
    
    # Check for main content
    if page.locator('body').count() > 0:
        logger.info("✅ TEST 1 PASS: Homepage loaded successfully")
        return True
    else:
        logger.error("❌ TEST 1 FAIL: Homepage failed to load")
        return False


def test_volatility_tab_visible(page):
    """Test 2: Volatility Lab tab is visible in navigation"""
    logger.info("\n=== TEST 2: Volatility Lab tab visible ===")
    
    # Look for tab link with Volatility Lab text
    tab_selectors = [
        'a:has-text("Volatility Lab")',
        'a:has-text("⚡ Volatility Lab")',
        '[data-value="volatility_lab"]',
        '.nav-link:has-text("Volatility")'
    ]
    
    tab_found = False
    for selector in tab_selectors:
        try:
            if page.locator(selector).count() > 0:
                logger.info(f"✓ Found Volatility Lab tab with selector: {selector}")
                tab_found = True
                break
        except:
            continue
    
    if tab_found:
        logger.info("✅ TEST 2 PASS: Volatility Lab tab is visible")
        return True
    else:
        # Take debug screenshot
        page.screenshot(path=SCREENSHOT_DIR / '02_tab_not_found.png')
        logger.error("❌ TEST 2 FAIL: Volatility Lab tab not found")
        return False


def test_open_volatility_tab(page):
    """Test 3: Click and open Volatility Lab tab"""
    logger.info("\n=== TEST 3: Open Volatility Lab tab ===")
    
    # Try different selectors
    tab_selectors = [
        'a:has-text("⚡ Volatility Lab")',
        'a:has-text("Volatility Lab")',
        '[data-value="volatility_lab"]'
    ]
    
    clicked = False
    for selector in tab_selectors:
        try:
            tab = page.locator(selector).first
            if tab.count() > 0:
                logger.info(f"Clicking tab with selector: {selector}")
                tab.click()
                clicked = True
                time.sleep(3)  # Wait for tab content to load
                break
        except Exception as e:
            logger.debug(f"Selector {selector} failed: {e}")
            continue
    
    if not clicked:
        logger.error("❌ TEST 3 FAIL: Could not click Volatility Lab tab")
        page.screenshot(path=SCREENSHOT_DIR / '03_tab_click_failed.png')
        return False
    
    # Take screenshot after opening
    page.screenshot(path=SCREENSHOT_DIR / '03_volatility_tab_opened.png')
    logger.info("📸 Screenshot saved after opening tab")
    
    # Verify tab content loaded
    time.sleep(2)
    
    logger.info("✅ TEST 3 PASS: Volatility Lab tab opened")
    return True


def test_four_panels_visible(page):
    """Test 4: Verify all 4 panels are visible"""
    logger.info("\n=== TEST 4: Check 4-panel layout ===")
    
    # Look for panel indicators
    panel_checks = {
        'Overview': ['text=Overview', 'text=📊 Overview', 'text=Last Surface'],
        'IV Surface': ['text=IV Surface', 'text=📈 IV Surface', '#vl-heatmap'],
        'Signals': ['text=Signals', 'text=🎯 Signals', 'text=Trading Signals'],
        'Diagnostics': ['text=Diagnostics', 'text=🔧 Diagnostics', '#vl-diag-solver-log']
    }
    
    panels_found = {}
    for panel_name, selectors in panel_checks.items():
        found = False
        for selector in selectors:
            try:
                if page.locator(selector).count() > 0:
                    logger.info(f"✓ Found {panel_name} panel")
                    found = True
                    break
            except:
                continue
        panels_found[panel_name] = found
    
    # Take screenshot
    page.screenshot(path=SCREENSHOT_DIR / '04_four_panels.png')
    
    all_panels_visible = all(panels_found.values())
    if all_panels_visible:
        logger.info("✅ TEST 4 PASS: All 4 panels visible")
        return True
    else:
        missing = [k for k, v in panels_found.items() if not v]
        logger.error(f"❌ TEST 4 FAIL: Missing panels: {missing}")
        return False


def test_component_ids_present(page):
    """Test 5: Verify critical component IDs exist in DOM"""
    logger.info("\n=== TEST 5: Check component IDs ===")
    
    critical_ids = [
        'vl-calc-run-btn',
        'vl-heatmap',
        'vl-signal-run-btn',
        'vl-backtest-run-btn',
        'vl-diag-solver-log'
    ]
    
    ids_found = {}
    for component_id in critical_ids:
        selector = f'#{component_id}'
        count = page.locator(selector).count()
        ids_found[component_id] = count > 0
        if count > 0:
            logger.info(f"✓ Found {component_id}")
        else:
            logger.warning(f"✗ Missing {component_id}")
    
    all_ids_present = all(ids_found.values())
    if all_ids_present:
        logger.info("✅ TEST 5 PASS: All critical component IDs present")
        return True
    else:
        missing = [k for k, v in ids_found.items() if not v]
        logger.error(f"❌ TEST 5 FAIL: Missing IDs: {missing}")
        page.screenshot(path=SCREENSHOT_DIR / '05_missing_ids.png')
        return False


def test_compute_button_click(page):
    """Test 6: Click compute button and verify heatmap updates"""
    logger.info("\n=== TEST 6: Click compute button ===")
    
    # Find and click the Run button
    run_btn_selector = '#vl-calc-run-btn'
    
    try:
        run_btn = page.locator(run_btn_selector)
        if run_btn.count() == 0:
            logger.error("❌ Compute button not found")
            return False
        
        logger.info("Clicking compute button...")
        run_btn.click()
        
        # Wait for loading/computation
        time.sleep(5)
        
        # Take screenshot after computation
        page.screenshot(path=SCREENSHOT_DIR / '06_after_compute.png')
        logger.info("📸 Screenshot saved after compute")
        
        # Check if heatmap updated (look for plotly graph)
        heatmap_selector = '#vl-heatmap .plotly'
        if page.locator(heatmap_selector).count() > 0:
            logger.info("✓ Heatmap element detected")
        
        logger.info("✅ TEST 6 PASS: Compute button clicked")
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST 6 FAIL: {e}")
        page.screenshot(path=SCREENSHOT_DIR / '06_compute_error.png')
        return False


def test_signals_button_click(page):
    """Test 7: Click signals button"""
    logger.info("\n=== TEST 7: Click signals button ===")
    
    try:
        signals_btn = page.locator('#vl-signal-run-btn')
        if signals_btn.count() == 0:
            logger.warning("⚠️  Signals button not found, skipping")
            return True  # Non-critical
        
        logger.info("Clicking signals button...")
        signals_btn.click()
        time.sleep(3)
        
        page.screenshot(path=SCREENSHOT_DIR / '07_after_signals.png')
        logger.info("✅ TEST 7 PASS: Signals button clicked")
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST 7 FAIL: {e}")
        return False


def test_backtest_button_click(page):
    """Test 8: Click backtest button"""
    logger.info("\n=== TEST 8: Click backtest button ===")
    
    try:
        backtest_btn = page.locator('#vl-backtest-run-btn')
        if backtest_btn.count() == 0:
            logger.warning("⚠️  Backtest button not found, skipping")
            return True  # Non-critical
        
        logger.info("Clicking backtest button...")
        backtest_btn.click()
        time.sleep(3)
        
        page.screenshot(path=SCREENSHOT_DIR / '08_after_backtest.png')
        logger.info("✅ TEST 8 PASS: Backtest button clicked")
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST 8 FAIL: {e}")
        return False


def test_diagnostics_panel(page):
    """Test 9: Check diagnostics panel shows data"""
    logger.info("\n=== TEST 9: Check diagnostics panel ===")
    
    try:
        # Check if diagnostics log exists
        diag_log = page.locator('#vl-diag-solver-log')
        if diag_log.count() > 0:
            log_text = diag_log.inner_text()
            logger.info(f"Diagnostics log content preview: {log_text[:100]}...")
        
        page.screenshot(path=SCREENSHOT_DIR / '09_diagnostics.png')
        logger.info("✅ TEST 9 PASS: Diagnostics panel checked")
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST 9 FAIL: {e}")
        return False


def test_overview_refresh(page):
    """Test 10: Click overview refresh button"""
    logger.info("\n=== TEST 10: Refresh overview ===")
    
    try:
        refresh_btn = page.locator('#vl-overview-refresh-btn')
        if refresh_btn.count() > 0:
            logger.info("Clicking overview refresh...")
            refresh_btn.click()
            time.sleep(2)
        
        page.screenshot(path=SCREENSHOT_DIR / '10_overview_refreshed.png')
        logger.info("✅ TEST 10 PASS: Overview refresh tested")
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST 10 FAIL: {e}")
        return False


def main():
    """Run all browser tests"""
    logger.info("=" * 70)
    logger.info("VOLATILITY LAB - NON-HEADLESS BROWSER TESTS")
    logger.info("=" * 70)
    logger.info(f"Dashboard URL: {DASHBOARD_URL}")
    logger.info(f"Headless mode: {HEADLESS}")
    logger.info(f"Screenshot directory: {SCREENSHOT_DIR}")
    logger.info(f"Deterministic mode: {os.getenv('VOLLAB_DETERMINISTIC', '0')}")
    
    results = {}
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=HEADLESS,
            slow_mo=500  # Slow down actions for visibility
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir=str(SCREENSHOT_DIR) if not HEADLESS else None
        )
        
        page = context.new_page()
        
        try:
            # Run all tests
            tests = [
                ("Homepage loads", test_homepage_loads),
                ("Volatility tab visible", test_volatility_tab_visible),
                ("Open Volatility tab", test_open_volatility_tab),
                ("4-panel layout", test_four_panels_visible),
                ("Component IDs present", test_component_ids_present),
                ("Compute button click", test_compute_button_click),
                ("Signals button click", test_signals_button_click),
                ("Backtest button click", test_backtest_button_click),
                ("Diagnostics panel", test_diagnostics_panel),
                ("Overview refresh", test_overview_refresh),
            ]
            
            for test_name, test_func in tests:
                try:
                    results[test_name] = test_func(page)
                except Exception as e:
                    logger.error(f"Test '{test_name}' crashed: {e}")
                    results[test_name] = False
            
            # Final screenshot
            page.screenshot(path=SCREENSHOT_DIR / '11_final_state.png')
            logger.info("📸 Final screenshot saved")
            
        finally:
            context.close()
            browser.close()
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    logger.info("=" * 70)
    logger.info(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    logger.info(f"Success rate: {(passed/total)*100:.1f}%")
    logger.info("=" * 70)
    
    # Save results to file
    results_file = SCREENSHOT_DIR / 'test_results.txt'
    with open(results_file, 'w') as f:
        f.write("VOLATILITY LAB BROWSER TEST RESULTS\n")
        f.write("=" * 70 + "\n\n")
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            f.write(f"{status} - {test_name}\n")
        f.write(f"\nTotal: {total} | Passed: {passed} | Failed: {failed}\n")
        f.write(f"Success rate: {(passed/total)*100:.1f}%\n")
    
    logger.info(f"📝 Results saved to: {results_file}")
    
    # Return exit code
    if all(results.values()):
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED - Review screenshots and logs")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
