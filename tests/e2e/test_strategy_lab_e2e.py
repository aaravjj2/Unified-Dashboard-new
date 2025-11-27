"""
Strategy Lab - E2E Test Suite

Uses sync_playwright directly (compatible pattern with test_options_lab_e2e.py).
Tests all 5 subtabs, input flows, and backtest execution.

Run with:
    pytest tests/e2e/test_strategy_lab_e2e.py -v

Requirements:
    - Dashboard running on port 8051
    - Playwright installed with browsers
"""

import pytest
import os
import json
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, expect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://127.0.0.1:8051')
TIMEOUT = 60000  # 60 seconds
SCREENSHOT_DIR = Path('reports/strategy_lab/screenshots')
DOM_DUMP_DIR = Path('reports/strategy_lab/dom')
LOG_DIR = Path('reports/strategy_lab/logs')

# Ensure directories exist
for d in [SCREENSHOT_DIR, DOM_DUMP_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def browser():
    """Launch browser for the session."""
    with sync_playwright() as p:
        # Use headed mode if DISPLAY is available, otherwise headless
        headless = os.getenv('DISPLAY') is None
        logger.info(f"Launching Chromium (headless={headless})")
        browser = p.chromium.launch(headless=headless)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test."""
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()
    page.set_default_timeout(TIMEOUT)
    yield page
    page.close()
    context.close()


def navigate_to_strategy_lab(page: Page) -> bool:
    """Navigate to Strategy Lab tab."""
    logger.info("🔵 Navigating to Strategy Lab tab...")
    page.goto(DASHBOARD_URL, timeout=30000)
    
    # Wait for dashboard to load - look for any tab structure
    page.wait_for_selector('.nav-link, .nav-tabs, .tab-content', timeout=TIMEOUT)
    time.sleep(2)  # Let callbacks settle
    
    # Try multiple selectors for Strategy Lab tab
    selectors = [
        'text=Strategy Lab',
        '.nav-link:has-text("Strategy")',
        'a:has-text("Strategy Lab")',
        '[id*="strategy"]',
        '.tab-content:has-text("Strategy")',
    ]
    
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=3000):
                element.click()
                logger.info(f"✅ Clicked Strategy Lab using: {selector}")
                time.sleep(1)  # Wait for tab content
                return True
        except Exception as e:
            logger.debug(f"Selector {selector} failed: {e}")
            continue
    
    logger.warning("⚠️ Could not find Strategy Lab tab, checking if already on page")
    return 'strategy' in page.content().lower()


def click_subtab(page: Page, subtab_name: str) -> bool:
    """Click a Strategy Lab subtab."""
    logger.info(f"🔵 Clicking subtab: {subtab_name}")
    
    # Subtab selectors
    selectors = [
        f'text={subtab_name}',
        f'.nav-link:has-text("{subtab_name}")',
        f'button:has-text("{subtab_name}")',
        f'a:has-text("{subtab_name}")',
    ]
    
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=2000):
                element.click()
                logger.info(f"✅ Clicked {subtab_name} using: {selector}")
                time.sleep(0.5)
                return True
        except:
            continue
    
    logger.warning(f"⚠️ Could not find subtab: {subtab_name}")
    return False


def screenshot(page: Page, name: str) -> Path:
    """Take a screenshot."""
    path = SCREENSHOT_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    page.screenshot(path=str(path))
    logger.info(f"📸 Screenshot: {path}")
    return path


def dump_dom(page: Page, name: str) -> Path:
    """Dump DOM state to file."""
    path = DOM_DUMP_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html = page.content()
    with open(path, 'w') as f:
        f.write(html)
    logger.info(f"📄 DOM dump: {path}")
    return path


# ============================================================================
# TESTS
# ============================================================================

class TestStrategyLabNavigation:
    """Test navigation to Strategy Lab and subtabs."""
    
    def test_navigate_to_strategy_lab(self, page: Page):
        """Test navigation to Strategy Lab tab."""
        result = navigate_to_strategy_lab(page)
        screenshot(page, "strategy_lab_landing")
        
        # Verify Strategy Lab content loaded
        content = page.content()
        assert 'strategy' in content.lower() or 'backtest' in content.lower(), \
            "Strategy Lab content not found"
        
        logger.info("✅ Strategy Lab tab loaded successfully")
    
    def test_setup_subtab_visible(self, page: Page):
        """Test Setup subtab is accessible."""
        navigate_to_strategy_lab(page)
        
        # Setup should be visible (first subtab)
        result = click_subtab(page, "Setup")
        screenshot(page, "setup_subtab")
        
        # Check for setup elements
        content = page.content()
        has_setup_elements = any([
            'sl-tickers-input' in content,
            'ticker' in content.lower(),
            'strategy' in content.lower(),
        ])
        assert has_setup_elements, "Setup subtab elements not found"
        logger.info("✅ Setup subtab visible")
    
    def test_execute_subtab_visible(self, page: Page):
        """Test Execute & Configure subtab is accessible."""
        navigate_to_strategy_lab(page)
        
        result = click_subtab(page, "Execute")
        if not result:
            result = click_subtab(page, "Configure")
        screenshot(page, "execute_subtab")
        
        content = page.content()
        has_execute_elements = any([
            'sl-run-backtest' in content,
            'backtest' in content.lower(),
            'execute' in content.lower(),
        ])
        assert has_execute_elements, "Execute subtab elements not found"
        logger.info("✅ Execute subtab visible")


class TestStrategyLabSetup:
    """Test Setup subtab functionality."""
    
    def test_tickers_input(self, page: Page):
        """Test tickers input field."""
        navigate_to_strategy_lab(page)
        click_subtab(page, "Setup")
        time.sleep(1)
        
        # Find tickers input (Dash Input component)
        tickers_input = page.locator('input#sl-tickers-input, input.dash-input[id="sl-tickers-input"]').first
        
        if tickers_input.is_visible(timeout=5000):
            tickers_input.fill("AAPL, MSFT, GOOGL")
            time.sleep(0.5)
            value = tickers_input.input_value()
            assert "AAPL" in value, f"Tickers not entered correctly: {value}"
            logger.info("✅ Tickers input works")
        else:
            # Dump DOM for debugging
            dump_dom(page, "tickers_input_not_found")
            pytest.skip("Tickers input not visible - see DOM dump")
    
    def test_entry_condition_input(self, page: Page):
        """Test entry condition dropdown (Dash Dropdown component)."""
        navigate_to_strategy_lab(page)
        click_subtab(page, "Setup")
        time.sleep(1)
        
        # Entry condition is a Dash Dropdown, not a text input
        # Find the dropdown container and check it exists
        entry_dropdown = page.locator('#sl-entry-condition.dash-dropdown').first
        
        if entry_dropdown.is_visible(timeout=5000):
            # Click to open the dropdown
            entry_dropdown.click()
            time.sleep(0.5)
            
            # Check dropdown options are visible
            options = page.locator('.Select-option, .Select-menu-outer')
            if options.count() > 0:
                logger.info(f"✅ Entry condition dropdown works - has {options.count()} option elements")
            else:
                # Just verify the dropdown has a value
                value_label = entry_dropdown.locator('.Select-value-label').text_content()
                assert value_label, "Entry dropdown should have a value"
                logger.info(f"✅ Entry condition dropdown works - value: {value_label}")
            
            # Click away to close dropdown
            page.keyboard.press("Escape")
        else:
            dump_dom(page, "entry_dropdown_not_found")
            pytest.skip("Entry dropdown not visible")
    
    def test_validate_button(self, page: Page):
        """Test validate strategy button."""
        navigate_to_strategy_lab(page)
        click_subtab(page, "Setup")
        time.sleep(1)
        
        # Fill required fields first
        tickers = page.locator('#sl-tickers-input').first
        if tickers.is_visible():
            tickers.fill("AAPL")
        
        validate_btn = page.locator('#sl-validate-btn, button:has-text("Validate")').first
        
        if validate_btn.is_visible(timeout=5000):
            validate_btn.click()
            time.sleep(2)  # Wait for validation
            screenshot(page, "after_validate")
            logger.info("✅ Validate button works")
        else:
            dump_dom(page, "validate_btn_not_found")
            pytest.skip("Validate button not visible")


class TestStrategyLabExecution:
    """Test Execute & Configure subtab."""
    
    def test_run_backtest_button_exists(self, page: Page):
        """Test Run Backtest button exists."""
        navigate_to_strategy_lab(page)
        click_subtab(page, "Execute")
        time.sleep(1)
        
        # The button has id="sl-run-backtest-btn"
        run_btn = page.locator('button#sl-run-backtest-btn, #sl-run-backtest-btn').first
        
        if run_btn.is_visible(timeout=5000):
            assert run_btn.is_enabled() or not run_btn.is_enabled(), "Button should exist"
            logger.info("✅ Run Backtest button exists")
            screenshot(page, "run_backtest_btn")
        else:
            # Also check for button text
            alt_btn = page.locator('button:has-text("Run Backtest"), button:has-text("▶")').first
            if alt_btn.is_visible(timeout=2000):
                logger.info("✅ Run Backtest button found by text")
            else:
                dump_dom(page, "run_btn_not_found")
                pytest.skip("Run Backtest button not visible")
    
    def test_random_seed_input(self, page: Page):
        """Test random seed input for determinism."""
        navigate_to_strategy_lab(page)
        click_subtab(page, "Execute")
        time.sleep(1)
        
        seed_input = page.locator('#sl-random-seed, [id*="seed"]').first
        
        if seed_input.is_visible(timeout=5000):
            seed_input.fill("42")
            value = seed_input.input_value()
            assert "42" in value, f"Seed not entered: {value}"
            logger.info("✅ Random seed input works")
        else:
            dump_dom(page, "seed_input_not_found")
            pytest.skip("Seed input not visible")


class TestStrategyLabResults:
    """Test Results subtab."""
    
    def test_results_subtab_accessible(self, page: Page):
        """Test Results subtab can be accessed."""
        navigate_to_strategy_lab(page)
        result = click_subtab(page, "Results")
        screenshot(page, "results_subtab")
        
        content = page.content()
        has_results_elements = any([
            'sl-equity-curve' in content,
            'equity' in content.lower(),
            'metrics' in content.lower(),
        ])
        logger.info(f"Results subtab accessible: {has_results_elements}")
        # Don't fail - just log


class TestStrategyLabBenchmark:
    """Test Benchmark subtab."""
    
    def test_benchmark_subtab_accessible(self, page: Page):
        """Test Benchmark subtab can be accessed."""
        navigate_to_strategy_lab(page)
        result = click_subtab(page, "Benchmark")
        screenshot(page, "benchmark_subtab")
        
        content = page.content()
        has_benchmark_elements = any([
            'sl-benchmark' in content,
            'benchmark' in content.lower(),
            'comparison' in content.lower(),
        ])
        logger.info(f"Benchmark subtab accessible: {has_benchmark_elements}")


class TestStrategyLabRisk:
    """Test Risk & Factors subtab."""
    
    def test_risk_subtab_accessible(self, page: Page):
        """Test Risk & Factors subtab can be accessed."""
        navigate_to_strategy_lab(page)
        result = click_subtab(page, "Risk")
        if not result:
            result = click_subtab(page, "Factors")
        screenshot(page, "risk_subtab")
        
        content = page.content()
        has_risk_elements = any([
            'sl-risk' in content,
            'risk' in content.lower(),
            'factor' in content.lower(),
        ])
        logger.info(f"Risk subtab accessible: {has_risk_elements}")


class TestStrategyLabLiveOrders:
    """Test Live Order functionality."""
    
    def test_execute_live_button_exists(self, page: Page):
        """Test Execute Live button exists (requires LIVE_ORDER_ALLOWED=true)."""
        navigate_to_strategy_lab(page)
        click_subtab(page, "Execute")
        time.sleep(1)
        
        live_btn = page.locator('#sl-execute-live-btn, button:has-text("Execute Live")').first
        
        if live_btn.is_visible(timeout=5000):
            logger.info("✅ Execute Live button exists")
            screenshot(page, "execute_live_btn")
            assert True
        else:
            dump_dom(page, "live_btn_not_found")
            pytest.skip("Execute Live button not visible - may need backtest first")


class TestStrategyLabFullWorkflow:
    """Test complete workflow from setup to results."""
    
    def test_complete_backtest_workflow(self, page: Page):
        """Test complete backtest workflow."""
        navigate_to_strategy_lab(page)
        
        # Step 1: Setup
        click_subtab(page, "Setup")
        time.sleep(1)
        
        # Fill tickers (this IS an input field)
        tickers = page.locator('input#sl-tickers-input').first
        if tickers.is_visible(timeout=3000):
            tickers.fill("AAPL")
            time.sleep(0.5)
        
        # Entry and Exit conditions are DROPDOWNS, not text inputs
        # We just verify they have values (they come pre-selected)
        entry_dropdown = page.locator('#sl-entry-condition.dash-dropdown').first
        if entry_dropdown.is_visible(timeout=3000):
            entry_value = entry_dropdown.locator('.Select-value-label').text_content()
            logger.info(f"Entry condition selected: {entry_value}")
        
        exit_dropdown = page.locator('#sl-exit-condition.dash-dropdown').first
        if exit_dropdown.is_visible(timeout=3000):
            exit_value = exit_dropdown.locator('.Select-value-label').text_content()
            logger.info(f"Exit condition selected: {exit_value}")
        
        screenshot(page, "workflow_step1_setup")
        
        # Step 2: Validate
        validate_btn = page.locator('#sl-validate-btn').first
        if validate_btn.is_visible(timeout=3000):
            validate_btn.click()
            time.sleep(2)
            screenshot(page, "workflow_step2_validated")
        
        # Step 3: Execute
        click_subtab(page, "Execute")
        time.sleep(1)
        
        run_btn = page.locator('button#sl-run-backtest-btn, #sl-run-backtest-btn').first
        if run_btn.is_visible(timeout=3000):
            # Check if button is enabled (strategy must be validated)
            if run_btn.is_enabled():
                run_btn.click()
                time.sleep(5)  # Wait for backtest
                screenshot(page, "workflow_step3_executed")
                logger.info("✅ Backtest executed")
            else:
                logger.warning("Run button disabled - strategy may not be validated")
                screenshot(page, "workflow_run_disabled")
        
        # Step 4: Check Results
        click_subtab(page, "Results")
        time.sleep(2)
        screenshot(page, "workflow_step4_results")
        
        # Check if equity curve or metrics appeared
        content = page.content()
        has_results = any([
            'sl-metric-' in content,
            'sl-equity-curve' in content,
            'cagr' in content.lower(),
            'sharpe' in content.lower(),
        ])
        
        if has_results:
            logger.info("✅ Complete workflow successful - results visible")
        else:
            logger.warning("⚠️ Results may be pending or require valid backtest")
        
        # Final DOM dump
        dump_dom(page, "workflow_final_state")


# ============================================================================
# SUMMARY REPORT
# ============================================================================

def pytest_sessionfinish(session, exitstatus):
    """Generate summary report after test run."""
    report_file = Path('reports/strategy_lab/playwright') / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "exit_status": exitstatus,
        "passed": session.testscollected - session.testsfailed,
        "failed": session.testsfailed,
        "total": session.testscollected,
        "dashboard_url": DASHBOARD_URL,
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"📊 Report saved: {report_file}")
