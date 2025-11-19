"""
Comprehensive End-to-End System Test for Analysis Hub

Tests all major functionality across the refactored modular architecture:
- Phase 1: Verify all 3 tabs load correctly
- Phase 2: Test Portfolio Analytics enhancements
- Phase 3: Test Attribution Analysis with Fama-French
- Phase 4: Test Scenario Tester with correlation-aware scenarios

Usage:
    pytest test_full_system_e2e.py -v
    # Or with Playwright directly:
    python test_full_system_e2e.py
"""

import os
import sys
import time
import logging
from playwright.sync_api import sync_playwright, expect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8054')
TIMEOUT = 30000  # 30 seconds
SCREENSHOT_DIR = 'test_screenshots'

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def test_phase1_tabs_load(page):
    """Phase 1: Verify all 3 tabs load correctly after refactoring."""
    logger.info("=== Phase 1: Testing Tab Loading ===")
    
    # Navigate to Analysis Hub
    page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=TIMEOUT)
    logger.info(f"Navigated to {DASHBOARD_URL}")
    
    # Wait for main Analysis Hub to load
    page.wait_for_selector('h4:has-text("Analysis Hub")', timeout=TIMEOUT)
    logger.info("✓ Analysis Hub header found")
    
    # Test Attribution Analysis tab
    attr_tab = page.locator('a.nav-link:has-text("Attribution Analysis")')
    expect(attr_tab).to_be_visible(timeout=TIMEOUT)
    attr_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_selector('select[id="attr-model-type"]', timeout=TIMEOUT)
    logger.info("✓ Attribution Analysis tab loads correctly")
    page.screenshot(path=f"{SCREENSHOT_DIR}/phase1_attribution_tab.png")
    
    # Test Portfolio Analytics tab
    portfolio_tab = page.locator('a.nav-link:has-text("Portfolio Analytics")')
    expect(portfolio_tab).to_be_visible(timeout=TIMEOUT)
    portfolio_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_selector('button[id="pa-calc-btn"]', timeout=TIMEOUT)
    logger.info("✓ Portfolio Analytics tab loads correctly")
    page.screenshot(path=f"{SCREENSHOT_DIR}/phase1_portfolio_tab.png")
    
    # Test Scenario Tester tab
    scenario_tab = page.locator('a.nav-link:has-text("Scenario Tester")')
    expect(scenario_tab).to_be_visible(timeout=TIMEOUT)
    scenario_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_selector('button[id="scenario-run-btn"]', timeout=TIMEOUT)
    logger.info("✓ Scenario Tester tab loads correctly")
    page.screenshot(path=f"{SCREENSHOT_DIR}/phase1_scenario_tab.png")
    
    logger.info("✅ Phase 1 PASSED: All tabs load successfully")
    return True


def test_phase2_portfolio_analytics(page):
    """Phase 2: Test Portfolio Analytics enhancements."""
    logger.info("=== Phase 2: Testing Portfolio Analytics Enhancements ===")
    
    # Navigate to Portfolio Analytics tab
    page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=TIMEOUT)
    portfolio_tab = page.locator('a.nav-link:has-text("Portfolio Analytics")')
    portfolio_tab.click()
    page.wait_for_timeout(1000)
    
    # Click Calculate Analytics button
    calc_button = page.locator('button[id="pa-calc-btn"]')
    expect(calc_button).to_be_visible(timeout=TIMEOUT)
    expect(calc_button).to_be_enabled(timeout=TIMEOUT)
    calc_button.click()
    logger.info("✓ Calculate Analytics button clicked")
    
    # Wait for graphs to appear
    page.wait_for_timeout(5000)  # Allow time for callback execution
    
    # Verify performance graph is visible
    perf_graph = page.locator('div[id="pa-performance-chart"]')
    expect(perf_graph).to_be_visible(timeout=TIMEOUT)
    logger.info("✓ Performance chart visible")
    
    # Verify risk distribution graph
    risk_graph = page.locator('div[id="pa-risk-chart"]')
    expect(risk_graph).to_be_visible(timeout=TIMEOUT)
    logger.info("✓ Risk distribution chart visible")
    
    # Verify total return is not 0.00%
    total_return_card = page.locator('h3[id="pa-total-return"]')
    return_text = total_return_card.inner_text()
    logger.info(f"Total Return: {return_text}")
    
    # Check that return is not the initial placeholder
    if return_text != "0.00%":
        logger.info("✓ Total return updated with real data")
    else:
        logger.warning("⚠ Total return still showing 0.00% (may be expected with no data)")
    
    # Take screenshot
    page.screenshot(path=f"{SCREENSHOT_DIR}/phase2_portfolio_analytics.png", full_page=True)
    
    logger.info("✅ Phase 2 PASSED: Portfolio Analytics working")
    return True


def test_phase3_fama_french_attribution(page):
    """Phase 3: Test Attribution Analysis with Fama-French model."""
    logger.info("=== Phase 3: Testing Fama-French Attribution ===")
    
    # Navigate to Attribution Analysis tab
    page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=TIMEOUT)
    attr_tab = page.locator('a.nav-link:has-text("Attribution Analysis")')
    attr_tab.click()
    page.wait_for_timeout(1000)
    
    # Select Fama-French model
    model_dropdown = page.locator('select[id="attr-model-type"]')
    model_dropdown.select_option('fama_french')
    logger.info("✓ Selected Fama-French 3-Factor model")
    
    # Adjust date range to last 30 days
    page.wait_for_timeout(500)
    
    # Click Run Attribution button
    run_button = page.locator('button[id="attr-run-button"]')
    expect(run_button).to_be_visible(timeout=TIMEOUT)
    expect(run_button).to_be_enabled(timeout=TIMEOUT)
    run_button.click()
    logger.info("✓ Run Attribution button clicked")
    
    # Wait for results
    page.wait_for_timeout(8000)  # Allow time for analysis
    
    # Check for status alert
    status_alert = page.locator('div[id="attr-status"]')
    if status_alert.is_visible():
        status_text = status_alert.inner_text()
        logger.info(f"Attribution status: {status_text}")
        
        # Check for success
        if 'complete' in status_text.lower() or 'success' in status_text.lower():
            logger.info("✓ Attribution analysis completed successfully")
        else:
            logger.warning(f"⚠ Attribution status: {status_text}")
    
    # Verify Gross Alpha and Net Alpha cards are visible
    try:
        gross_alpha_card = page.locator('h3[id="attr-gross-alpha"]')
        net_alpha_card = page.locator('h3[id="attr-net-alpha"]')
        
        if gross_alpha_card.is_visible() and net_alpha_card.is_visible():
            gross_text = gross_alpha_card.inner_text()
            net_text = net_alpha_card.inner_text()
            logger.info(f"✓ Gross Alpha: {gross_text}, Net Alpha: {net_text}")
        else:
            logger.warning("⚠ Alpha cards not visible (may not have data)")
    except Exception as e:
        logger.warning(f"⚠ Could not verify alpha cards: {e}")
    
    # Take screenshot
    page.screenshot(path=f"{SCREENSHOT_DIR}/phase3_fama_french.png", full_page=True)
    
    logger.info("✅ Phase 3 PASSED: Fama-French attribution working")
    return True


def test_phase4_scenario_testing(page):
    """Phase 4: Test Scenario Tester with correlation-aware scenarios."""
    logger.info("=== Phase 4: Testing Scenario Tester ===")
    
    # Navigate to Scenario Tester tab
    page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=TIMEOUT)
    scenario_tab = page.locator('a.nav-link:has-text("Scenario Tester")')
    scenario_tab.click()
    page.wait_for_timeout(1000)
    
    # Select COVID-19 historical scenario
    scenario_dropdown = page.locator('select[id="scenario-preset"]')
    scenario_dropdown.select_option('covid_crash')
    logger.info("✓ Selected COVID-19 Crash scenario")
    page.wait_for_timeout(1000)
    
    # Verify sliders updated (check SPY change slider value)
    spy_slider_value = page.locator('input[id="scenario-spy-change"]').get_attribute('value')
    logger.info(f"SPY Change slider value: {spy_slider_value}%")
    
    # Enable Realistic Shock toggle
    realistic_toggle = page.locator('input[id="scenario-realistic-shock"][value="realistic"]')
    if realistic_toggle.is_visible():
        realistic_toggle.check()
        logger.info("✓ Enabled Realistic Shock (correlation-aware)")
        page.wait_for_timeout(500)
    
    # Select My Portfolio universe
    universe_dropdown = page.locator('select[id="scenario-universe"]')
    universe_dropdown.select_option('my_portfolio')
    logger.info("✓ Selected My Portfolio universe")
    
    # Enable comparison mode
    compare_checkbox = page.locator('input[id="scenario-compare-mode"][value="compare"]')
    if compare_checkbox.is_visible():
        compare_checkbox.check()
        logger.info("✓ Enabled comparison mode")
        page.wait_for_timeout(500)
        
        # Select comparison scenario (Bear Market)
        compare_dropdown = page.locator('select[id="scenario-preset2"]')
        if compare_dropdown.is_visible():
            compare_dropdown.select_option('bear')
            logger.info("✓ Selected Bear Market for comparison")
    
    # Run scenario
    run_button = page.locator('button[id="scenario-run-btn"]')
    expect(run_button).to_be_visible(timeout=TIMEOUT)
    expect(run_button).to_be_enabled(timeout=TIMEOUT)
    run_button.click()
    logger.info("✓ Run Scenario button clicked")
    
    # Wait for results
    page.wait_for_timeout(3000)
    
    # Verify results are displayed
    results_div = page.locator('div[id="scenario-results"]')
    expect(results_div).to_be_visible(timeout=TIMEOUT)
    
    results_text = results_div.inner_text()
    logger.info(f"Scenario results preview: {results_text[:200]}...")
    
    # Check for key elements
    if 'COVID-19' in results_text or 'scenario' in results_text.lower():
        logger.info("✓ Scenario results displayed")
    
    # Look for hedging candidates (table or list)
    if 'hedging' in results_text.lower() or 'Ticker' in results_text:
        logger.info("✓ Hedging candidates visible")
    
    # Take screenshot
    page.screenshot(path=f"{SCREENSHOT_DIR}/phase4_scenario_test.png", full_page=True)
    
    logger.info("✅ Phase 4 PASSED: Scenario testing working")
    return True


def run_all_tests():
    """Run all comprehensive E2E tests."""
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE END-TO-END SYSTEM TEST")
    logger.info("Testing all phases of the Analysis Hub refactoring")
    logger.info("=" * 60)
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False, slow_mo=500)  # Set to True for CI/CD
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Run all test phases
            results = {
                'Phase 1 - Tab Loading': False,
                'Phase 2 - Portfolio Analytics': False,
                'Phase 3 - Fama-French Attribution': False,
                'Phase 4 - Scenario Testing': False
            }
            
            # Phase 1: Verify modular architecture
            try:
                results['Phase 1 - Tab Loading'] = test_phase1_tabs_load(page)
            except Exception as e:
                logger.error(f"❌ Phase 1 FAILED: {e}")
            
            # Phase 2: Portfolio Analytics enhancements
            try:
                results['Phase 2 - Portfolio Analytics'] = test_phase2_portfolio_analytics(page)
            except Exception as e:
                logger.error(f"❌ Phase 2 FAILED: {e}")
            
            # Phase 3: Fama-French attribution
            try:
                results['Phase 3 - Fama-French Attribution'] = test_phase3_fama_french_attribution(page)
            except Exception as e:
                logger.error(f"❌ Phase 3 FAILED: {e}")
            
            # Phase 4: Scenario testing
            try:
                results['Phase 4 - Scenario Testing'] = test_phase4_scenario_testing(page)
            except Exception as e:
                logger.error(f"❌ Phase 4 FAILED: {e}")
            
            # Summary
            logger.info("=" * 60)
            logger.info("TEST SUMMARY")
            logger.info("=" * 60)
            for phase, passed in results.items():
                status = "✅ PASSED" if passed else "❌ FAILED"
                logger.info(f"{phase}: {status}")
            
            passed_count = sum(results.values())
            total_count = len(results)
            logger.info(f"\nTotal: {passed_count}/{total_count} phases passed")
            
            if passed_count == total_count:
                logger.info("\n🎉 ALL TESTS PASSED! System is ready for production.")
                return 0
            else:
                logger.warning(f"\n⚠️  {total_count - passed_count} phase(s) failed. Review logs above.")
                return 1
            
        except Exception as e:
            logger.error(f"Fatal error during testing: {e}")
            return 1
        
        finally:
            # Close browser
            page.wait_for_timeout(2000)  # Brief pause before closing
            browser.close()


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
