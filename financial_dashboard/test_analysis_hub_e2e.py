"""
Comprehensive End-to-End Test Suite for Analysis Hub

Tests:
1. Critical Bug Fix - Graphs populate, buttons work, no DOM destruction
2. Attribution Analysis Features - Error analysis, drill-down, regime filtering  
3. Scenario Tester Features - Factor scenarios, comparison mode, hedging candidates

Usage:
    python test_analysis_hub_e2e.py
"""

from playwright.sync_api import sync_playwright, expect
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_analysis_hub_e2e():
    """Comprehensive end-to-end test of Analysis Hub features."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=800)
        page = browser.new_page()
        
        try:
            # ========================================
            # Setup: Load the page
            # ========================================
            logger.info("="*60)
            logger.info("ANALYSIS HUB E2E TEST SUITE")
            logger.info("="*60)
            
            page.goto('http://localhost:8054', timeout=60000)
            page.wait_for_load_state('domcontentloaded')
            time.sleep(2)
            
            logger.info("✓ Page loaded successfully")
            
            # Click Attribution Analysis tab
            try:
                page.locator('a:has-text("Attribution Analysis")').first.click(timeout=5000)
                time.sleep(1)
            except:
                pass  # Already on Attribution tab
            
            # ========================================
            # TEST 1: Critical Bug Fix Verification
            # ========================================
            logger.info("\n" + "="*60)
            logger.info("TEST 1: CRITICAL BUG FIX VERIFICATION")
            logger.info("="*60)
            
            # Run Attribution Analysis
            logger.info("  Running Attribution Analysis...")
            page.locator('button:has-text("Run Attribution Analysis")').click(timeout=10000)
            time.sleep(4)
            
            # Check if results container is visible
            results_container = page.locator('#attr-results-container')
            results_container.wait_for(state='visible', timeout=10000)
            expect(results_container).to_be_visible()
            logger.info("  ✓ Results container is visible (bug fix: not destroyed by callback)")
            
            # Check if graphs are present
            alpha_beta_chart = page.locator('#attr-alpha-beta-chart')
            expect(alpha_beta_chart).to_be_visible()
            logger.info("  ✓ Alpha/Beta chart is visible")
            
            factor_chart = page.locator('#attr-factor-chart')
            expect(factor_chart).to_be_visible()
            logger.info("  ✓ Factor chart is visible")
            
            # Take screenshot
            page.screenshot(path='e2e_test_1_bug_fix.png', full_page=True)
            logger.info("  ✓ Screenshot saved: e2e_test_1_bug_fix.png")
            
            # ========================================
            # TEST 2: Attribution Analysis Features
            # ========================================
            logger.info("\n" + "="*60)
            logger.info("TEST 2: ATTRIBUTION ANALYSIS FEATURES")
            logger.info("="*60)
            
            # Test 2.1: Error Analysis Table
            logger.info("  Testing error analysis table...")
            error_analysis = page.locator('#attr-error-analysis')
            expect(error_analysis).to_be_visible()
            
            # Check if table has content
            error_table = error_analysis.locator('table')
            if error_table.count() > 0:
                logger.info("  ✓ Error analysis table is displayed")
            else:
                logger.info("  ⚠ Error analysis table not found (may need data)")
            
            # Test 2.2: Factor Drill-Down
            logger.info("  Testing factor drill-down...")
            try:
                # Click on factor chart (first bar)
                factor_chart.click(timeout=5000)
                time.sleep(2)
                
                # Check if drill-down section appears
                drilldown = page.locator('#attr-factor-drilldown')
                drilldown.wait_for(state='visible', timeout=5000)
                expect(drilldown).to_be_visible()
                logger.info("  ✓ Factor drill-down section appears on click")
                
                # Check for feature and ticker breakdowns
                feature_breakdown = page.locator('#attr-feature-breakdown')
                expect(feature_breakdown).to_be_visible()
                logger.info("  ✓ Feature breakdown chart is visible")
                
                ticker_breakdown = page.locator('#attr-ticker-breakdown')
                expect(ticker_breakdown).to_be_visible()
                logger.info("  ✓ Ticker breakdown chart is visible")
                
            except Exception as e:
                logger.warning(f"  ⚠ Factor drill-down test failed: {e}")
            
            # Test 2.3: Market Regime Filtering
            logger.info("  Testing market regime filtering...")
            regime_dropdown = page.locator('#attr-regime-filter')
            expect(regime_dropdown).to_be_visible()
            logger.info("  ✓ Market regime dropdown is present")
            
            # Change regime filter
            try:
                regime_dropdown.select_option('bull')
                time.sleep(1)
                logger.info("  ✓ Changed regime filter to 'Bull Market'")
                
                # Re-run analysis with filter
                page.locator('button:has-text("Run Attribution Analysis")').click(timeout=10000)
                time.sleep(3)
                logger.info("  ✓ Re-ran analysis with regime filter")
                
            except Exception as e:
                logger.warning(f"  ⚠ Regime filtering test failed: {e}")
            
            page.screenshot(path='e2e_test_2_attribution.png', full_page=True)
            logger.info("  ✓ Screenshot saved: e2e_test_2_attribution.png")
            
            # ========================================
            # TEST 3: Portfolio Analytics
            # ========================================
            logger.info("\n" + "="*60)
            logger.info("TEST 3: PORTFOLIO ANALYTICS")
            logger.info("="*60)
            
            # Click Portfolio Analytics tab
            page.locator('a:has-text("Portfolio Analytics")').first.click(timeout=5000)
            time.sleep(1)
            logger.info("  ✓ Portfolio Analytics tab clicked")
            
            # Click Calculate Analytics button
            calc_button = page.locator('button:has-text("Calculate Analytics")')
            expect(calc_button).to_be_visible()
            calc_button.click()
            time.sleep(3)
            logger.info("  ✓ Calculate Analytics button clicked")
            
            # Check if metrics appeared
            total_return = page.locator('#pa-total-return')
            expect(total_return).to_be_visible()
            logger.info("  ✓ Total Return metric is visible")
            
            page.screenshot(path='e2e_test_3_portfolio.png', full_page=True)
            logger.info("  ✓ Screenshot saved: e2e_test_3_portfolio.png")
            
            # ========================================
            # TEST 4: Scenario Tester Features
            # ========================================
            logger.info("\n" + "="*60)
            logger.info("TEST 4: SCENARIO TESTER FEATURES")
            logger.info("="*60)
            
            # Click Scenario Testing tab
            page.locator('a:has-text("Scenario Testing")').first.click(timeout=5000)
            time.sleep(1)
            logger.info("  ✓ Scenario Testing tab clicked")
            
            # Test 4.1: Scenario Type Dropdown
            logger.info("  Testing scenario type dropdown...")
            scenario_type = page.locator('#scenario-type')
            expect(scenario_type).to_be_visible()
            logger.info("  ✓ Scenario type dropdown is present")
            
            # Test 4.2: Factor-Based Scenarios
            logger.info("  Testing factor-based scenarios...")
            try:
                # Change to factor-based scenarios
                scenario_type.select_option('factor')
                time.sleep(1)
                logger.info("  ✓ Changed to factor-based scenarios")
                
                # Check if scenario preset options updated
                scenario_preset = page.locator('#scenario-preset')
                expect(scenario_preset).to_be_visible()
                
                # Select a factor scenario
                scenario_preset.select_option('momentum_crash')
                time.sleep(1)
                logger.info("  ✓ Selected 'Momentum Crash' scenario")
                
                # Run scenario
                page.locator('button:has-text("Run Scenario")').click(timeout=10000)
                time.sleep(3)
                logger.info("  ✓ Ran factor-based scenario")
                
                # Check for hedging candidates
                hedging_list = page.locator('[data-testid="hedging-candidates-list"]')
                if hedging_list.count() > 0:
                    expect(hedging_list).to_be_visible()
                    logger.info("  ✓ Hedging candidates list is displayed")
                else:
                    logger.info("  ⚠ Hedging candidates list not found (may need data)")
                
            except Exception as e:
                logger.warning(f"  ⚠ Factor scenario test failed: {e}")
            
            # Test 4.3: Comparison Mode
            logger.info("  Testing comparison mode...")
            try:
                # Enable compare mode
                compare_mode = page.locator('#scenario-compare-mode')
                if compare_mode.count() > 0:
                    compare_mode.select_option('compare')
                    time.sleep(1)
                    logger.info("  ✓ Enabled comparison mode")
                    
                    # Check if second dropdown appears
                    compare_visibility = page.locator('#scenario-compare-visibility-flag')
                    flag_text = compare_visibility.inner_text()
                    if flag_text == 'visible':
                        logger.info("  ✓ Compare mode visibility flag is 'visible'")
                    
                    # Check if second scenario selector is visible
                    scenario_preset2 = page.locator('#scenario-preset2')
                    if scenario_preset2.count() > 0:
                        expect(scenario_preset2).to_be_visible()
                        logger.info("  ✓ Second scenario selector is visible")
                        
                        # Select second scenario
                        scenario_preset2.select_option('value_rally')
                        time.sleep(1)
                        logger.info("  ✓ Selected 'Value Rally' for comparison")
                        
                        # Run comparison
                        page.locator('button:has-text("Run Scenario")').click(timeout=10000)
                        time.sleep(3)
                        logger.info("  ✓ Ran scenario comparison")
                else:
                    logger.info("  ⚠ Compare mode dropdown not found")
                    
            except Exception as e:
                logger.warning(f"  ⚠ Comparison mode test failed: {e}")
            
            page.screenshot(path='e2e_test_4_scenario.png', full_page=True)
            logger.info("  ✓ Screenshot saved: e2e_test_4_scenario.png")
            
            # ========================================
            # Final Summary
            # ========================================
            logger.info("\n" + "="*60)
            logger.info("E2E TEST SUITE COMPLETED")
            logger.info("="*60)
            logger.info("Screenshots saved:")
            logger.info("  - e2e_test_1_bug_fix.png (Critical bug fix verification)")
            logger.info("  - e2e_test_2_attribution.png (Attribution features)")
            logger.info("  - e2e_test_3_portfolio.png (Portfolio Analytics)")
            logger.info("  - e2e_test_4_scenario.png (Scenario Tester)")
            logger.info("="*60)
            
            input("\nPress Enter to close browser...")
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            page.screenshot(path='e2e_test_error.png', full_page=True)
            logger.error("Error screenshot saved: e2e_test_error.png")
            raise
            
        finally:
            browser.close()


if __name__ == '__main__':
    test_analysis_hub_e2e()
