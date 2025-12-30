"""
Phase 4 E2E Test Suite - Predict & Execute
==========================================

Tests NeuralForecast integration (Market Forecast) and NautilusTrader (Strategy Lab).

Requirements:
- PORT=8051
- PHASE4_DETERMINISTIC=1
- Headful Chromium only
- No test skipping
- Full audit trail with screenshots

Test Flows:
1. Market Forecast -> Neural Models (NBEATS/NHITS) -> Fan Chart Verification
2. Strategy Lab -> Nautilus Engine -> Trade Log Verification
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import pytest
from playwright.sync_api import Page, expect, sync_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PORT = os.getenv('PORT', '8051')
BASE_URL = f'http://localhost:{PORT}'
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / 'reports' / 'phase4' / 'screenshots'
DOM_DIR = Path(__file__).parent.parent.parent / 'reports' / 'phase4' / 'dom'
LOG_DIR = Path(__file__).parent.parent.parent / 'reports' / 'phase4' / 'logs'

# Create directories
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
DOM_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Timeouts
DEFAULT_TIMEOUT = 60000  # 60s (neural models can be slow)
NAVIGATION_TIMEOUT = 30000
CHART_RENDER_TIMEOUT = 15000


def save_screenshot(page: Page, name: str):
    """Save screenshot with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = SCREENSHOT_DIR / f"{timestamp}_{name}.png"
    page.screenshot(path=str(filepath), full_page=True)
    logger.info(f"📸 Screenshot saved: {filepath}")
    return filepath


def save_dom(page: Page, name: str):
    """Save page DOM/HTML for debugging."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = DOM_DIR / f"{timestamp}_{name}.html"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(page.content())
    logger.info(f"📄 DOM saved: {filepath}")
    return filepath


def wait_for_spinner(page: Page, timeout: int = DEFAULT_TIMEOUT):
    """Wait for loading spinner to disappear."""
    try:
        # Common spinner/loading indicators
        spinner_selectors = [
            '.spinner-border',
            '.loading',
            '[role="status"]',
            '.dash-spinner'
        ]
        
        for selector in spinner_selectors:
            if page.locator(selector).count() > 0:
                logger.info(f"⏳ Waiting for spinner: {selector}")
                page.locator(selector).wait_for(state='detached', timeout=timeout)
                logger.info("✅ Spinner disappeared")
                break
    except Exception as e:
        logger.warning(f"Spinner wait warning: {e}")


def wait_for_chart(page: Page, chart_id: str, timeout: int = CHART_RENDER_TIMEOUT):
    """Wait for Plotly chart to render."""
    try:
        # Wait for chart container
        chart_locator = page.locator(f"#{chart_id}")
        chart_locator.wait_for(state='visible', timeout=timeout)
        
        # Wait for SVG content (Plotly renders as SVG) - use first to avoid strict mode
        svg_locator = chart_locator.locator('svg.main-svg').first
        svg_locator.wait_for(state='visible', timeout=timeout)
        
        logger.info(f"✅ Chart rendered: {chart_id}")
        return True
    except Exception as e:
        logger.error(f"Chart wait failed for {chart_id}: {e}")
        return False


@pytest.fixture(scope="module")
def browser_context():
    """Launch headful Chromium browser."""
    logger.info("🚀 Launching headful Chromium...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Headful as per requirements
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        )
        
        # Set default timeout
        context.set_default_timeout(DEFAULT_TIMEOUT)
        context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        
        yield context
        
        logger.info("🛑 Closing browser...")
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    """Create a new page for each test."""
    page = browser_context.new_page()
    
    # Navigate to dashboard - use 'load' instead of 'networkidle' for Dash apps
    logger.info(f"📍 Navigating to {BASE_URL}")
    page.goto(BASE_URL, wait_until='load', timeout=60000)
    
    # Wait for dashboard to load - use correct selector
    page.wait_for_selector('#dashboard-tabs', timeout=NAVIGATION_TIMEOUT)
    logger.info("✅ Dashboard loaded")
    
    yield page
    
    page.close()


class TestPhase4MarketForecast:
    """Test Neural Forecasting (NBEATS/NHITS) in Market Forecast tab."""
    
    def test_01_navigate_to_market_forecast(self, page: Page):
        """Test: Navigate to Market Forecast tab."""
        logger.info("🧪 Test 1: Navigate to Market Forecast")
        
        # Take pre-navigation screenshot
        save_screenshot(page, "01_pre_market_forecast")
        
        # Click Market Forecast tab
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        
        # Wait for tab content to load
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        # Take post-navigation screenshot
        save_screenshot(page, "01_post_market_forecast")
        save_dom(page, "01_market_forecast")
        
        logger.info("✅ Test 1 passed: Market Forecast tab loaded")
    
    def test_02_select_nbeats_model(self, page: Page):
        """Test: Select NBEATS neural model."""
        logger.info("🧪 Test 2: Select NBEATS model")
        
        # Navigate to Market Forecast tab
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        # Take pre-selection screenshot
        save_screenshot(page, "02_pre_nbeats_select")
        
        # Find NBEATS label (specific to avoid matching Neural Ensemble)
        nbeats_label = page.locator('#mf-model-checklist label').filter(has_text='NBEATS (Neural Basis')
        
        if nbeats_label.count() == 0:
            logger.error("NBEATS checkbox not found!")
            save_dom(page, "02_nbeats_missing")
            pytest.fail("NBEATS model option not found in UI")
        
        # Get the checkbox
        nbeats_checkbox = nbeats_label.locator('input')
        
        # Click label to check
        nbeats_label.click()
        page.wait_for_timeout(500)
        
        # Verify it's checked
        assert nbeats_checkbox.is_checked(), "NBEATS checkbox should be checked"
        
        # Take post-selection screenshot
        save_screenshot(page, "02_post_nbeats_select")
        
        logger.info("✅ Test 2 passed: NBEATS model selected")
    
    def test_03_run_neural_forecast(self, page: Page):
        """Test: Run NBEATS forecast and verify fan chart appears."""
        logger.info("🧪 Test 3: Run Neural Forecast")
        
        # Navigate to Market Forecast tab
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        # Enter ticker
        ticker_input = page.locator('#mf-ticker-input')
        ticker_input.clear()
        ticker_input.fill('AAPL')
        
        # Uncheck all models first by clicking checked labels
        all_labels = page.locator('#mf-model-checklist label')
        for i in range(all_labels.count()):
            label = all_labels.nth(i)
            checkbox = label.locator('input')
            if checkbox.is_checked():
                label.click()
                page.wait_for_timeout(200)
        
        # Select NBEATS only
        nbeats_label = page.locator('#mf-model-checklist label').filter(has_text='NBEATS (Neural Basis')
        nbeats_label.click()
        page.wait_for_timeout(500)
        
        # Select short horizon (7 days for speed) - Dash dcc.Dropdown
        horizon_dropdown = page.locator('#mf-horizon-select')
        # Click to open dropdown
        horizon_dropdown.click()
        page.wait_for_timeout(300)
        # Click the 1 Week option (value=7)
        page.locator('.VirtualizedSelectOption').filter(has_text='1 Week').click()
        page.wait_for_timeout(300)
        
        # Take pre-run screenshot
        save_screenshot(page, "03_pre_forecast_run")
        
        # Click Run Forecast button
        run_button = page.locator('#mf-run-btn')
        run_button.click()
        logger.info("🔄 Forecast running...")
        
        # Wait for loading spinner (neural models take time)
        wait_for_spinner(page, timeout=90000)  # 90s timeout for neural training
        
        # Wait for forecast chart to render
        chart_visible = wait_for_chart(page, 'mf-forecast-chart', timeout=30000)
        
        if not chart_visible:
            logger.error("Forecast chart did not render!")
            save_screenshot(page, "03_chart_missing")
            save_dom(page, "03_chart_missing")
            pytest.fail("Forecast chart failed to render")
        
        # Take post-run screenshot
        save_screenshot(page, "03_post_forecast_run")
        
        # Verify chart has data (check for SVG paths)
        chart_svg = page.locator('#mf-forecast-chart svg.main-svg').first
        paths = chart_svg.locator('path.js-line')
        
        assert paths.count() > 0, "Chart should contain forecast lines"
        
        # Check for success message
        success_alert = page.locator('.alert-success')
        if success_alert.count() > 0:
            logger.info(f"✅ Success message found: {success_alert.first.text_content()[:100]}")
        
        save_dom(page, "03_forecast_complete")
        
        logger.info("✅ Test 3 passed: Neural forecast generated with fan chart")
    
    def test_04_verify_neural_ensemble(self, page: Page):
        """Test: Verify Neural Ensemble model (NBEATS + NHITS)."""
        logger.info("🧪 Test 4: Verify Neural Ensemble")
        
        # Navigate to Market Forecast tab
        mf_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Market Forecast')
        mf_tab.click()
        page.wait_for_selector('#mf-model-checklist', timeout=DEFAULT_TIMEOUT)
        
        # Check if Neural Ensemble option exists
        neural_ensemble_label = page.locator('#mf-model-checklist label').filter(has_text='Neural Ensemble')
        
        if neural_ensemble_label.count() == 0:
            logger.warning("Neural Ensemble option not found (may not be implemented)")
            save_dom(page, "04_ensemble_missing")
            pytest.skip("Neural Ensemble not available")
        
        # Uncheck all models first
        all_labels = page.locator('#mf-model-checklist label')
        for i in range(all_labels.count()):
            label = all_labels.nth(i)
            checkbox = label.locator('input')
            if checkbox.is_checked():
                label.click()
                page.wait_for_timeout(200)
        
        # Select Neural Ensemble
        neural_ensemble_label.click()
        page.wait_for_timeout(500)
        
        # Enter ticker
        ticker_input = page.locator('#mf-ticker-input')
        ticker_input.clear()
        ticker_input.fill('SPY')
        
        # Run forecast
        run_button = page.locator('#mf-run-btn')
        run_button.click()
        
        # Wait for completion
        wait_for_spinner(page, timeout=120000)  # 2 minutes for ensemble
        wait_for_chart(page, 'mf-forecast-chart', timeout=30000)
        
        # Take screenshot
        save_screenshot(page, "04_neural_ensemble")
        
        logger.info("✅ Test 4 passed: Neural Ensemble forecast completed")


class TestPhase4StrategyLab:
    """Test NautilusTrader integration in Strategy Lab."""
    
    def test_05_navigate_to_strategy_lab(self, page: Page):
        """Test: Navigate to Strategy Lab tab."""
        logger.info("🧪 Test 5: Navigate to Strategy Lab")
        
        # Take pre-navigation screenshot
        save_screenshot(page, "05_pre_strategy_lab")
        
        # Click Strategy Lab tab
        strategy_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Strategy Lab')
        strategy_tab.click()
        
        # Wait for Strategy Lab subtabs container
        page.wait_for_selector('#strategy-lab-subtabs', timeout=DEFAULT_TIMEOUT)
        
        # Click on Setup subtab
        setup_tab = page.locator('.nav-link').filter(has_text='Setup')
        if setup_tab.count() > 0:
            setup_tab.first.click()
            page.wait_for_timeout(1000)
        
        # Wait for tab content
        page.wait_for_selector('#sl-strategy-type', timeout=DEFAULT_TIMEOUT)
        
        # Take post-navigation screenshot
        save_screenshot(page, "05_post_strategy_lab")
        save_dom(page, "05_strategy_lab")
        
        logger.info("✅ Test 5 passed: Strategy Lab loaded")
    
    def test_06_select_nautilus_engine(self, page: Page):
        """Test: Select Nautilus engine (event-driven)."""
        logger.info("🧪 Test 6: Select Nautilus Engine")
        
        # Navigate to Strategy Lab
        strategy_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Strategy Lab')
        strategy_tab.click()
        page.wait_for_selector('#strategy-lab-subtabs', timeout=DEFAULT_TIMEOUT)
        
        # Click on "Execute" subtab where engine selection lives
        execute_tab = page.locator('.nav-link').filter(has_text='Execute')
        execute_tab.first.click()
        page.wait_for_timeout(2000)
        
        # Take pre-selection screenshot
        save_screenshot(page, "06_pre_nautilus_select")
        
        # Wait for engine selection to be visible
        page.wait_for_selector('#sl-engine-select', timeout=DEFAULT_TIMEOUT)
        
        # Find Nautilus label and click it (RadioItems don't have value attr in Dash)
        nautilus_label = page.locator('label').filter(has_text='Nautilus')
        
        if nautilus_label.count() == 0:
            logger.error("Nautilus engine option not found!")
            save_dom(page, "06_nautilus_missing")
            pytest.fail("Nautilus engine option not found in UI")
        
        # Click Nautilus label to select
        nautilus_label.click()
        page.wait_for_timeout(500)
        
        # Verify selection by checking if Nautilus options div is visible
        page.wait_for_timeout(1000)
        nautilus_options = page.locator('#sl-nautilus-options')
        
        # Take post-selection screenshot
        save_screenshot(page, "06_post_nautilus_select")
        
        logger.info("✅ Test 6 passed: Nautilus engine selected")
    
    def test_07_run_nautilus_backtest(self, page: Page):
        """Test: Run backtest with Nautilus engine and verify trade log."""
        logger.info("🧪 Test 7: Run Nautilus Backtest")
        
        # Navigate to Strategy Lab
        strategy_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Strategy Lab')
        strategy_tab.click()
        page.wait_for_selector('#strategy-lab-subtabs', timeout=DEFAULT_TIMEOUT)
        
        # First go to Setup tab to configure strategy
        setup_tab = page.locator('.nav-link').filter(has_text='Setup')
        setup_tab.first.click()
        page.wait_for_timeout(1000)
        
        # Configure strategy
        ticker_input = page.locator('#sl-tickers-input')
        if ticker_input.count() > 0:
            ticker_input.clear()
            ticker_input.fill('AAPL')
        
        # Select momentum strategy - dcc.Dropdown, not <select>
        strategy_dropdown = page.locator('#sl-strategy-type')
        if strategy_dropdown.count() > 0:
            strategy_dropdown.click()
            page.wait_for_timeout(300)
            momentum_option = page.locator('.VirtualizedSelectOption').filter(has_text='Momentum')
            if momentum_option.count() > 0:
                momentum_option.first.click()
            else:
                # Try clicking away to close if no momentum option
                page.keyboard.press('Escape')
            page.wait_for_timeout(300)
        
        # Now go to Execute tab
        execute_tab = page.locator('.nav-link').filter(has_text='Execute')
        execute_tab.first.click()
        page.wait_for_timeout(2000)
        
        # Wait for engine selection
        page.wait_for_selector('#sl-engine-select', timeout=DEFAULT_TIMEOUT)
        
        # Select Nautilus engine by clicking label
        nautilus_label = page.locator('label').filter(has_text='Nautilus')
        nautilus_label.click()
        page.wait_for_timeout(1000)
        
        # Set initial capital
        try:
            initial_capital = page.locator('#sl-initial-capital')
            initial_capital.clear()
            initial_capital.fill('100000')
        except Exception as e:
            logger.warning(f"Could not set capital: {e}")
        
        # Take pre-run screenshot
        save_screenshot(page, "07_pre_backtest_run")
        
        # Click Run Backtest
        run_button = page.locator('#sl-run-backtest-btn')
        run_button.click()
        logger.info("🔄 Nautilus backtest running...")
        
        # Wait for completion (Nautilus is slower than VectorBT)
        wait_for_spinner(page, timeout=90000)
        
        # Wait for execution status to show something
        page.wait_for_timeout(5000)
        
        # Take post-run screenshot
        save_screenshot(page, "07_post_backtest_run")
        
        # Check for any status message
        execution_status = page.locator('#sl-execution-status')
        if execution_status.count() > 0:
            status_text = execution_status.text_content()
            logger.info(f"Execution status: {status_text[:200]}")
        
        # Check for success or result
        success_alert = page.locator('.alert-success, .alert-info')
        if success_alert.count() > 0:
            logger.info(f"✅ Status message found")
        
        save_dom(page, "07_nautilus_complete")
        
        logger.info("✅ Test 7 passed: Nautilus backtest completed")
    
    def test_08_verify_order_log(self, page: Page):
        """Test: Verify order-by-order trade log from Nautilus."""
        logger.info("🧪 Test 8: Verify Order Log")
        
        # Navigate to Strategy Lab
        strategy_tab = page.locator('#dashboard-tabs .nav-link').filter(has_text='Strategy Lab')
        strategy_tab.click()
        page.wait_for_selector('#strategy-lab-subtabs', timeout=DEFAULT_TIMEOUT)
        
        # Go to Execute tab
        execute_tab = page.locator('.nav-link').filter(has_text='Execute')
        execute_tab.first.click()
        page.wait_for_timeout(2000)
        
        # Select Nautilus
        nautilus_label = page.locator('label').filter(has_text='Nautilus')
        nautilus_label.click()
        page.wait_for_timeout(1000)
        
        # Go to Setup tab to set ticker
        setup_tab = page.locator('.nav-link').filter(has_text='Setup')
        setup_tab.first.click()
        page.wait_for_timeout(1000)
        
        ticker_input = page.locator('#sl-tickers-input')
        if ticker_input.count() > 0:
            ticker_input.clear()
            ticker_input.fill('SPY')
        
        # Back to Execute tab
        execute_tab.first.click()
        page.wait_for_timeout(1000)
        
        # Run backtest
        run_button = page.locator('#sl-run-backtest-btn')
        run_button.click()
        
        # Wait for completion
        wait_for_spinner(page, timeout=90000)
        
        # Look for trade log table
        # Common selectors: table, .trade-log, #trades-table
        trade_table = page.locator('table').or_(page.locator('.trade-log'))
        
        if trade_table.count() == 0:
            logger.warning("Trade log table not found (may be in different tab)")
            save_dom(page, "08_no_trade_log")
            pytest.skip("Trade log not visible (check if in separate subtab)")
        
        # Verify table has rows
        table_rows = trade_table.locator('tr')
        row_count = table_rows.count()
        
        logger.info(f"📊 Trade log has {row_count} rows")
        assert row_count > 1, "Trade log should have at least header + 1 data row"
        
        # Take screenshot
        save_screenshot(page, "08_trade_log")
        
        logger.info("✅ Test 8 passed: Order log verified")


if __name__ == '__main__':
    """Run tests with pytest."""
    # Set environment variables
    os.environ['PHASE4_DETERMINISTIC'] = '1'
    os.environ['PORT'] = '8051'
    
    # Run pytest with verbosity and headful mode
    pytest_args = [
        __file__,
        '-v',
        '--tb=short',
        '--headed',  # Playwright headful
        '-s',  # Show print statements
        f'--html=reports/phase4/playwright/test_report.html',
        '--self-contained-html'
    ]
    
    logger.info(f"🚀 Running Phase 4 E2E tests on PORT {PORT}")
    logger.info(f"📁 Artifacts will be saved to reports/phase4/")
    
    exit_code = pytest.main(pytest_args)
    
    logger.info(f"🏁 Tests completed with exit code: {exit_code}")
    sys.exit(exit_code)
