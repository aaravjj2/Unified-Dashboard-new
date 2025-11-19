"""
test_portfolio_comprehensive.py - Comprehensive Portfolio Dashboard Test Suite

Purpose:
    Validates all critical bug fixes in the Portfolio Dashboard using Playwright.
    Tests all tabs and verifies that specific error conditions have been resolved.

Test Coverage:
    1. Initial Load & Positions Table
    2. Optimization Tab (TypeError fix validation)
    3. Factor Exposure Tab (fallback chart validation)
    4. Analytics Tab (Monte Carlo single-ticker fix)
    5. Inspect Modal (ReferenceError fix validation)

Requirements:
    - pip install playwright pandas
    - playwright install chromium
    - Dashboard must be running on http://localhost:8056

Usage:
    python test_portfolio_comprehensive.py

Exit Codes:
    0 - All tests passed
    1 - One or more tests failed
"""

import sys
import time
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DASHBOARD_URL = "http://localhost:8056"
TIMEOUT = 30000  # 30 seconds
LONG_TIMEOUT = 60000  # 60 seconds for heavy operations


class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, test_name, message=""):
        self.passed += 1
        self.tests.append(("PASS", test_name, message))
        logger.info(f"✅ PASS: {test_name} - {message}")
    
    def add_fail(self, test_name, message=""):
        self.failed += 1
        self.tests.append(("FAIL", test_name, message))
        logger.error(f"❌ FAIL: {test_name} - {message}")
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        for status, name, message in self.tests:
            icon = "✅" if status == "PASS" else "❌"
            print(f"{icon} {status}: {name}")
            if message:
                print(f"   {message}")
        print("=" * 70)
        print(f"Total: {self.passed + self.failed} | Passed: {self.passed} | Failed: {self.failed}")
        print("=" * 70)
        return self.failed == 0


def wait_for_page_load(page, timeout=TIMEOUT):
    """Wait for page to be fully loaded."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        return True
    except PlaywrightTimeout:
        logger.warning("Page load timed out waiting for networkidle")
        return False


def test_1_initial_load_positions(page, results):
    """Test 1: Initial load and positions table visibility."""
    test_name = "Test 1: Initial Load & Positions Table"
    logger.info(f"\n{'=' * 70}\n{test_name}\n{'=' * 70}")
    
    try:
        # Navigate to dashboard
        logger.info("Navigating to dashboard...")
        page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        wait_for_page_load(page)
        
        # Wait for summary cards to load
        logger.info("Checking for summary cards...")
        page.wait_for_selector("#portfolio-value", timeout=TIMEOUT)
        
        portfolio_value = page.locator("#portfolio-value").text_content()
        logger.info(f"Portfolio value loaded: {portfolio_value}")
        
        if "$" in portfolio_value and portfolio_value != "$0.00":
            results.add_pass(test_name, f"Portfolio value shows: {portfolio_value}")
        else:
            results.add_fail(test_name, f"Portfolio value is invalid: {portfolio_value}")
            return
        
        # Click Positions tab
        logger.info("Clicking Positions tab...")
        positions_tab = page.locator("a.nav-link:has-text('Positions')")
        if positions_tab.count() > 0:
            positions_tab.first.click()
            time.sleep(2)
        
        # Check if positions-datatable exists
        logger.info("Checking for positions DataTable...")
        datatable = page.locator("#positions-datatable")
        
        if datatable.count() > 0:
            results.add_pass(test_name, "positions-datatable found and visible")
        else:
            results.add_fail(test_name, "positions-datatable not found in DOM")
            
    except Exception as e:
        results.add_fail(test_name, f"Exception: {str(e)}")


def test_2_optimization_fix(page, results):
    """Test 2: Optimization tab - verify TypeError is fixed."""
    test_name = "Test 2: Optimization Tab (TypeError Fix)"
    logger.info(f"\n{'=' * 70}\n{test_name}\n{'=' * 70}")
    
    try:
        # Navigate to Optimization tab
        logger.info("Clicking Optimization tab...")
        opt_tab = page.locator("a.nav-link:has-text('Optimization')")
        if opt_tab.count() > 0:
            opt_tab.first.click()
            time.sleep(2)
        else:
            results.add_fail(test_name, "Optimization tab not found")
            return
        
        # Check if ticker input is visible
        logger.info("Checking ticker input...")
        ticker_input = page.locator("#opt-tickers-input")
        
        if ticker_input.count() == 0:
            results.add_fail(test_name, "Ticker input not found")
            return
        
        # Enter test tickers if input is empty
        current_value = ticker_input.input_value()
        if not current_value:
            logger.info("Entering test tickers...")
            ticker_input.fill("AAPL,MSFT,GOOGL")
        else:
            logger.info(f"Using pre-populated tickers: {current_value}")
        
        # Click Optimize button
        logger.info("Clicking Optimize Portfolio button...")
        optimize_btn = page.locator("button:has-text('Optimize Portfolio')")
        if optimize_btn.count() > 0:
            optimize_btn.click()
            
            # Wait for results (with longer timeout for data download)
            logger.info("Waiting for optimization results...")
            time.sleep(5)  # Give time for computation
            
            # Check for error messages
            page_content = page.content()
            
            # Check for the specific TypeError we're fixing
            if "unsupported operand type(s) for /: 'str' and 'int'" in page_content:
                results.add_fail(test_name, "TypeError still present: str/int division error")
            elif "Data Error" in page_content or "TypeError" in page_content:
                results.add_fail(test_name, "Error message found in results")
            else:
                # Look for success indicators
                if "Optimal Weight" in page_content or "Expected Annual Return" in page_content:
                    results.add_pass(test_name, "Optimization completed without TypeError")
                else:
                    results.add_fail(test_name, "Results unclear - no error but no success indicators")
        else:
            results.add_fail(test_name, "Optimize button not found")
            
    except Exception as e:
        results.add_fail(test_name, f"Exception: {str(e)}")


def test_3_factor_exposure_fix(page, results):
    """Test 3: Factor Exposure tab - verify fallback chart is shown."""
    test_name = "Test 3: Factor Exposure Tab (Fallback Chart)"
    logger.info(f"\n{'=' * 70}\n{test_name}\n{'=' * 70}")
    
    try:
        # Navigate to Factor Exposure tab
        logger.info("Clicking Factor Exposure tab...")
        factor_tab = page.locator("a.nav-link:has-text('Factor Exposure')")
        if factor_tab.count() > 0:
            factor_tab.first.click()
            time.sleep(3)
        else:
            results.add_fail(test_name, "Factor Exposure tab not found")
            return
        
        page_content = page.content()
        
        # Check for SHAP data alert
        if "SHAP Data Not Found" in page_content:
            logger.info("SHAP data not found (expected) - checking for fallback chart...")
            
            # Check for fallback content
            if "Sector Allocation" in page_content or "Fallback Analysis" in page_content:
                # Check if a chart/graph is present
                charts = page.locator(".js-plotly-plot")
                if charts.count() > 0:
                    results.add_pass(test_name, "Fallback sector allocation chart displayed")
                else:
                    results.add_fail(test_name, "Alert shown but no fallback chart found")
            else:
                results.add_fail(test_name, "No fallback sector analysis provided")
        else:
            # SHAP data exists - check for factor chart
            logger.info("SHAP data found - checking for factor exposure chart...")
            charts = page.locator(".js-plotly-plot")
            if charts.count() > 0:
                results.add_pass(test_name, "Factor exposure chart displayed (SHAP data available)")
            else:
                results.add_fail(test_name, "No chart displayed despite content loaded")
                
    except Exception as e:
        results.add_fail(test_name, f"Exception: {str(e)}")


def test_4_analytics_monte_carlo_fix(page, results):
    """Test 4: Analytics tab - verify Monte Carlo handles single ticker."""
    test_name = "Test 4: Analytics Tab (Monte Carlo Fix)"
    logger.info(f"\n{'=' * 70}\n{test_name}\n{'=' * 70}")
    
    try:
        # Navigate to Analytics tab
        logger.info("Clicking Analytics tab...")
        analytics_tab = page.locator("a.nav-link:has-text('Analytics')")
        if analytics_tab.count() > 0:
            analytics_tab.first.click()
            time.sleep(3)
        else:
            results.add_fail(test_name, "Analytics tab not found")
            return
        
        # Find and click Monte Carlo button
        logger.info("Clicking Run Monte Carlo Simulation...")
        mc_button = page.locator("button:has-text('Run Monte Carlo')")
        
        if mc_button.count() == 0:
            # Try alternate button text
            mc_button = page.locator("button:has-text('Monte Carlo')")
        
        if mc_button.count() > 0:
            mc_button.first.click()
            
            # Wait for simulation to complete (longer timeout)
            logger.info("Waiting for Monte Carlo simulation...")
            time.sleep(10)  # Simulation takes time
            
            page_content = page.content()
            
            # Check for the specific error we're fixing
            if "must pass an index" in page_content:
                results.add_fail(test_name, "Index error still present in Monte Carlo")
            elif "Error running Monte Carlo" in page_content:
                results.add_fail(test_name, "Monte Carlo error message found")
            else:
                # Look for success indicators
                if "Monte Carlo Simulation" in page_content and ("Median" in page_content or "Percentile" in page_content):
                    results.add_pass(test_name, "Monte Carlo simulation completed successfully")
                else:
                    # Check if simulation results are present
                    charts = page.locator(".js-plotly-plot")
                    if charts.count() >= 2:  # Should have paths chart and distribution
                        results.add_pass(test_name, "Monte Carlo charts generated")
                    else:
                        results.add_fail(test_name, "Simulation status unclear")
        else:
            results.add_fail(test_name, "Monte Carlo button not found")
            
    except Exception as e:
        results.add_fail(test_name, f"Exception: {str(e)}")


def test_5_inspect_modal_fix(page, results):
    """Test 5: Positions Inspect Modal - verify no ReferenceError."""
    test_name = "Test 5: Inspect Modal (ReferenceError Fix)"
    logger.info(f"\n{'=' * 70}\n{test_name}\n{'=' * 70}")
    
    try:
        # Navigate back to Positions tab
        logger.info("Clicking Positions tab...")
        positions_tab = page.locator("a.nav-link:has-text('Positions')")
        if positions_tab.count() > 0:
            positions_tab.first.click()
            time.sleep(2)
        
        # Wait for DataTable to load
        page.wait_for_selector("#positions-datatable", timeout=TIMEOUT)
        
        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        # Look for Inspect button/link in first row
        logger.info("Looking for Inspect action in DataTable...")
        
        # Try clicking on the actions column (Inspect emoji/text)
        inspect_cells = page.locator("td:has-text('🔍 Inspect')")
        
        if inspect_cells.count() > 0:
            logger.info("Clicking Inspect on first position...")
            inspect_cells.first.click()
            time.sleep(2)
            
            # Check if modal opened
            modal = page.locator("#inspect-modal")
            modal_visible = modal.is_visible() if modal.count() > 0 else False
            
            if modal_visible:
                logger.info("Modal opened successfully")
                
                # Check for ReferenceError in console
                ref_errors = [err for err in console_errors if "ReferenceError" in err or "positions-datatable" in err]
                
                if ref_errors:
                    results.add_fail(test_name, f"ReferenceError found: {ref_errors[0]}")
                else:
                    results.add_pass(test_name, "Modal opened without ReferenceError")
                
                # Close modal
                close_btn = page.locator("#inspect-modal-close")
                if close_btn.count() > 0:
                    close_btn.click()
                    time.sleep(1)
            else:
                results.add_fail(test_name, "Modal did not open")
        else:
            # Alternative: Try clicking directly on DataTable cells
            logger.info("Inspect text not found, trying cell click...")
            datatable = page.locator("#positions-datatable")
            
            if datatable.count() > 0:
                # Click on first row's last column (actions)
                cells = page.locator("#positions-datatable td")
                if cells.count() > 9:  # Should have at least 10 columns per row
                    cells.nth(9).click()  # Click actions column of first row
                    time.sleep(2)
                    
                    modal = page.locator("#inspect-modal")
                    if modal.is_visible():
                        results.add_pass(test_name, "Modal opened via cell click")
                    else:
                        results.add_fail(test_name, "Modal did not open after cell click")
                else:
                    results.add_fail(test_name, "DataTable cells not found")
            else:
                results.add_fail(test_name, "DataTable not found for inspect test")
                
    except Exception as e:
        results.add_fail(test_name, f"Exception: {str(e)}")


def main():
    """Run all tests."""
    logger.info(f"""
{'=' * 70}
Portfolio Dashboard Comprehensive Test Suite
{'=' * 70}
Dashboard URL: {DASHBOARD_URL}
Test Coverage:
  1. Initial Load & Positions Table
  2. Optimization Tab (TypeError fix)
  3. Factor Exposure Tab (Fallback chart)
  4. Analytics Tab (Monte Carlo single-ticker fix)
  5. Inspect Modal (ReferenceError fix)
{'=' * 70}
""")
    
    results = TestResult()
    
    with sync_playwright() as p:
        # Launch browser
        logger.info("Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # Run all tests
            test_1_initial_load_positions(page, results)
            test_2_optimization_fix(page, results)
            test_3_factor_exposure_fix(page, results)
            test_4_analytics_monte_carlo_fix(page, results)
            test_5_inspect_modal_fix(page, results)
            
        except Exception as e:
            logger.error(f"Fatal error during testing: {e}")
            results.add_fail("Test Execution", str(e))
        
        finally:
            # Cleanup
            logger.info("Closing browser...")
            browser.close()
    
    # Print summary
    success = results.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
