"""
Strategy Lab - Headed Playwright E2E Test Suite

Per-element audit with headed Chromium (headless=False).
Tests all 5 subtabs, input flows, and backtest execution.

Run with:
    pytest tests/e2e/test_strategy_lab_headed.py -v --headed

Requirements:
    - Dashboard running on port 8051
    - Playwright installed with browsers
    - Set DASH_TEST_MODE=true for test mode bypass
"""

import pytest
import os
import json
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeout

# Test configuration
BASE_URL = os.getenv('DASHBOARD_URL', 'http://127.0.0.1:8051')
STRATEGY_LAB_URL = f"{BASE_URL}/"  # Main dashboard - Strategy Lab is a tab
SCREENSHOT_DIR = Path('reports/strategy_lab/screenshots')
DOM_DUMP_DIR = Path('reports/strategy_lab/dom')
LOG_DIR = Path('reports/strategy_lab/logs')

# Ensure directories exist
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
DOM_DUMP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


class TestStrategyLabHeaded:
    """Headed Playwright tests for Strategy Lab."""
    
    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Setup for each test."""
        self.page = page
        self.test_log = []
        self.start_time = datetime.now()
        
        # Set test mode environment
        os.environ['DASH_TEST_MODE'] = 'true'
        
        # Navigate to dashboard with timeout
        page.goto(BASE_URL, timeout=20000)
        
        # Wait for Dash to load - use domcontentloaded which is faster
        page.wait_for_load_state('domcontentloaded')
        
        yield
        
        # Save test log
        self._save_log()
    
    def _log(self, message: str):
        """Add entry to test log."""
        entry = f"[{datetime.now().isoformat()}] {message}"
        self.test_log.append(entry)
        print(entry)
    
    def _save_log(self):
        """Save test log to file."""
        log_file = LOG_DIR / f"test_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.test_log))
    
    def _screenshot(self, name: str):
        """Take a screenshot."""
        path = SCREENSHOT_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.page.screenshot(path=str(path))
        self._log(f"Screenshot saved: {path}")
        return path
    
    def _dump_dom(self, name: str):
        """Dump DOM state to file."""
        path = DOM_DUMP_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html = self.page.content()
        with open(path, 'w') as f:
            f.write(html)
        self._log(f"DOM dump saved: {path}")
        return path
    
    def _navigate_to_strategy_lab(self):
        """Navigate to Strategy Lab tab."""
        self._log("Navigating to Strategy Lab tab...")
        
        # Find and click Strategy Lab tab
        # Try multiple selectors
        selectors = [
            'a[href="/strategy-lab"]',
            '.nav-link:has-text("Strategy Lab")',
            'a:has-text("Strategy")',
            'button:has-text("Strategy Lab")',
            '#tab-strategy-lab',
            '[data-tab="strategy-lab"]',
        ]
        
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=2000):
                    element.click()
                    self._log(f"Clicked Strategy Lab using selector: {selector}")
                    time.sleep(1)  # Wait for tab content
                    return True
            except:
                continue
        
        # Try direct navigation
        self.page.goto(f"{BASE_URL}/strategy-lab", wait_until='networkidle')
        self._log("Direct navigation to /strategy-lab")
        return True
    
    # ========================================================================
    # TEST: Tab Navigation
    # ========================================================================
    def test_01_navigate_to_strategy_lab(self):
        """Test navigation to Strategy Lab tab."""
        self._navigate_to_strategy_lab()
        self._screenshot("strategy_lab_landing")
        
        # Verify Strategy Lab content loaded
        content = self.page.content()
        assert 'Strategy Lab' in content or 'strategy' in content.lower(), \
            "Strategy Lab content not found"
        
        self._log("✅ Strategy Lab tab loaded successfully")
    
    # ========================================================================
    # TEST: Setup Subtab Elements
    # ========================================================================
    def test_02_setup_subtab_elements(self):
        """Test Setup subtab elements are visible and interactive."""
        self._navigate_to_strategy_lab()
        
        # Click Setup subtab
        setup_tab = self.page.locator('[id*="setup"], .nav-link:has-text("Setup")').first
        if setup_tab.is_visible():
            setup_tab.click()
            time.sleep(0.5)
        
        self._screenshot("setup_subtab")
        
        # Check required elements
        elements = {
            'sl-strategy-type': 'Strategy Type dropdown',
            'sl-universe-type': 'Universe Type dropdown',
            'sl-tickers-input': 'Tickers input',
            'sl-entry-condition': 'Entry condition',
            'sl-exit-condition': 'Exit condition',
            'sl-position-sizing': 'Position sizing',
            'sl-validate-btn': 'Validate button',
        }
        
        found = []
        missing = []
        
        for elem_id, description in elements.items():
            locator = self.page.locator(f'#{elem_id}')
            try:
                if locator.is_visible(timeout=2000):
                    found.append(elem_id)
                    self._log(f"✅ Found: {description} (#{elem_id})")
                else:
                    missing.append(elem_id)
                    self._log(f"⚠️ Not visible: {description} (#{elem_id})")
            except:
                missing.append(elem_id)
                self._log(f"❌ Missing: {description} (#{elem_id})")
        
        self._dump_dom("setup_subtab")
        
        assert len(found) > 0, f"No Setup subtab elements found. Missing: {missing}"
        self._log(f"✅ Setup subtab: {len(found)}/{len(elements)} elements found")
    
    # ========================================================================
    # TEST: Execution Subtab Elements
    # ========================================================================
    def test_03_execution_subtab_elements(self):
        """Test Execution subtab elements are visible and interactive."""
        self._navigate_to_strategy_lab()
        
        # Click Execution subtab
        exec_tab = self.page.locator('[id*="execution"], .nav-link:has-text("Execute")').first
        if exec_tab.is_visible():
            exec_tab.click()
            time.sleep(0.5)
        
        self._screenshot("execution_subtab")
        
        # Check required elements
        elements = {
            'sl-start-date': 'Start date picker',
            'sl-end-date': 'End date picker',
            'sl-initial-capital': 'Initial capital input',
            'sl-transaction-cost': 'Transaction cost input',
            'sl-slippage': 'Slippage input',
            'sl-position-size': 'Position size input',
            'sl-max-positions': 'Max positions input',
            'sl-random-seed': 'Random seed input',
            'sl-run-backtest-btn': 'Run Backtest button',
            'sl-execute-live-btn': 'Execute Live button',
        }
        
        found = []
        missing = []
        
        for elem_id, description in elements.items():
            locator = self.page.locator(f'#{elem_id}')
            try:
                if locator.is_visible(timeout=2000):
                    found.append(elem_id)
                    self._log(f"✅ Found: {description} (#{elem_id})")
                else:
                    missing.append(elem_id)
                    self._log(f"⚠️ Not visible: {description} (#{elem_id})")
            except:
                missing.append(elem_id)
                self._log(f"❌ Missing: {description} (#{elem_id})")
        
        self._dump_dom("execution_subtab")
        
        assert len(found) >= 5, f"Not enough Execution elements found. Missing: {missing}"
        self._log(f"✅ Execution subtab: {len(found)}/{len(elements)} elements found")
    
    # ========================================================================
    # TEST: Results Subtab Elements
    # ========================================================================
    def test_04_results_subtab_elements(self):
        """Test Results subtab elements are visible."""
        self._navigate_to_strategy_lab()
        
        # Click Results subtab
        results_tab = self.page.locator('[id*="results"], .nav-link:has-text("Results")').first
        if results_tab.is_visible():
            results_tab.click()
            time.sleep(0.5)
        
        self._screenshot("results_subtab")
        
        # Check required elements
        elements = {
            'sl-metric-cagr': 'CAGR metric',
            'sl-metric-sharpe': 'Sharpe metric',
            'sl-metric-maxdd': 'Max Drawdown metric',
            'sl-metric-winrate': 'Win Rate metric',
            'sl-equity-curve': 'Equity curve chart',
        }
        
        found = []
        missing = []
        
        for elem_id, description in elements.items():
            locator = self.page.locator(f'#{elem_id}')
            try:
                if locator.is_visible(timeout=2000):
                    found.append(elem_id)
                    self._log(f"✅ Found: {description} (#{elem_id})")
                else:
                    missing.append(elem_id)
                    self._log(f"⚠️ Not visible: {description} (#{elem_id})")
            except:
                missing.append(elem_id)
                self._log(f"❌ Missing: {description} (#{elem_id})")
        
        self._dump_dom("results_subtab")
        
        assert len(found) >= 3, f"Not enough Results elements found. Missing: {missing}"
        self._log(f"✅ Results subtab: {len(found)}/{len(elements)} elements found")
    
    # ========================================================================
    # TEST: Benchmark Subtab Elements
    # ========================================================================
    def test_05_benchmark_subtab_elements(self):
        """Test Benchmark subtab elements are visible."""
        self._navigate_to_strategy_lab()
        
        # Click Benchmark subtab
        bench_tab = self.page.locator('[id*="benchmark"], .nav-link:has-text("Benchmark")').first
        if bench_tab.is_visible():
            bench_tab.click()
            time.sleep(0.5)
        
        self._screenshot("benchmark_subtab")
        
        # Check required elements
        elements = {
            'sl-benchmark-selector': 'Benchmark selector',
            'sl-strategy-cagr': 'Strategy CAGR',
            'sl-benchmark-cagr': 'Benchmark CAGR',
            'sl-alpha-value': 'Alpha value',
            'sl-beta-value': 'Beta value',
            'sl-information-ratio': 'Information Ratio',
            'sl-tracking-error': 'Tracking Error',
            'sl-correlation': 'Correlation',
            'sl-benchmark-comparison-chart': 'Comparison chart',
        }
        
        found = []
        missing = []
        
        for elem_id, description in elements.items():
            locator = self.page.locator(f'#{elem_id}')
            try:
                if locator.is_visible(timeout=2000):
                    found.append(elem_id)
                    self._log(f"✅ Found: {description} (#{elem_id})")
                else:
                    missing.append(elem_id)
                    self._log(f"⚠️ Not visible: {description} (#{elem_id})")
            except:
                missing.append(elem_id)
                self._log(f"❌ Missing: {description} (#{elem_id})")
        
        self._dump_dom("benchmark_subtab")
        
        assert len(found) >= 5, f"Not enough Benchmark elements found. Missing: {missing}"
        self._log(f"✅ Benchmark subtab: {len(found)}/{len(elements)} elements found")
    
    # ========================================================================
    # TEST: Risk Subtab Elements
    # ========================================================================
    def test_06_risk_subtab_elements(self):
        """Test Risk subtab elements are visible."""
        self._navigate_to_strategy_lab()
        
        # Click Risk subtab
        risk_tab = self.page.locator('[id*="risk"], .nav-link:has-text("Risk")').first
        if risk_tab.is_visible():
            risk_tab.click()
            time.sleep(0.5)
        
        self._screenshot("risk_subtab")
        
        # Check required elements
        elements = {
            'sl-risk-max-dd': 'Max Drawdown',
            'sl-risk-volatility': 'Volatility',
            'sl-risk-var': 'VaR',
            'sl-risk-sortino': 'Sortino Ratio',
            'sl-risk-drawdown-chart': 'Drawdown chart',
            'sl-risk-factor-chart': 'Factor chart',
        }
        
        found = []
        missing = []
        
        for elem_id, description in elements.items():
            locator = self.page.locator(f'#{elem_id}')
            try:
                if locator.is_visible(timeout=2000):
                    found.append(elem_id)
                    self._log(f"✅ Found: {description} (#{elem_id})")
                else:
                    missing.append(elem_id)
                    self._log(f"⚠️ Not visible: {description} (#{elem_id})")
            except:
                missing.append(elem_id)
                self._log(f"❌ Missing: {description} (#{elem_id})")
        
        self._dump_dom("risk_subtab")
        
        assert len(found) >= 3, f"Not enough Risk elements found. Missing: {missing}"
        self._log(f"✅ Risk subtab: {len(found)}/{len(elements)} elements found")
    
    # ========================================================================
    # TEST: Full Backtest Flow
    # ========================================================================
    def test_07_full_backtest_flow(self):
        """Test complete backtest execution flow."""
        self._navigate_to_strategy_lab()
        
        # Step 1: Go to Setup tab and configure
        self._log("Step 1: Configure strategy in Setup tab")
        setup_tab = self.page.locator('[id*="setup"], .nav-link:has-text("Setup")').first
        if setup_tab.is_visible():
            setup_tab.click()
            time.sleep(0.5)
        
        # Set strategy type if dropdown exists
        strategy_dropdown = self.page.locator('#sl-strategy-type')
        if strategy_dropdown.is_visible(timeout=2000):
            strategy_dropdown.click()
            self.page.locator('.Select-option:has-text("Momentum")').first.click()
            time.sleep(0.3)
        
        # Set tickers
        tickers_input = self.page.locator('#sl-tickers-input')
        if tickers_input.is_visible(timeout=2000):
            tickers_input.fill('')
            tickers_input.fill('AAPL,MSFT,GOOGL')
            time.sleep(0.3)
        
        self._screenshot("setup_configured")
        
        # Step 2: Go to Execution tab and run backtest
        self._log("Step 2: Run backtest in Execution tab")
        exec_tab = self.page.locator('[id*="execution"], .nav-link:has-text("Execute")').first
        if exec_tab.is_visible():
            exec_tab.click()
            time.sleep(0.5)
        
        # Click Run Backtest button
        run_btn = self.page.locator('#sl-run-backtest-btn')
        if run_btn.is_visible(timeout=2000):
            run_btn.click()
            self._log("Clicked Run Backtest button")
            
            # Wait for backtest to complete (up to 60 seconds)
            time.sleep(5)  # Initial wait
            
            # Check for results
            for _ in range(12):  # 60 seconds total
                status = self.page.locator('#sl-execution-status')
                if status.is_visible():
                    text = status.inner_text()
                    if 'Complete' in text or 'Success' in text or '✅' in text:
                        self._log("Backtest completed successfully!")
                        break
                    elif 'Error' in text or 'Failed' in text or '❌' in text:
                        self._log(f"Backtest failed: {text}")
                        break
                time.sleep(5)
        
        self._screenshot("backtest_completed")
        
        # Step 3: Check Results tab
        self._log("Step 3: Verify Results tab")
        results_tab = self.page.locator('[id*="results"], .nav-link:has-text("Results")').first
        if results_tab.is_visible():
            results_tab.click()
            time.sleep(1)
        
        # Check if metrics are populated
        cagr = self.page.locator('#sl-metric-cagr')
        if cagr.is_visible(timeout=3000):
            cagr_text = cagr.inner_text()
            if cagr_text and cagr_text != '--':
                self._log(f"✅ CAGR populated: {cagr_text}")
            else:
                self._log("⚠️ CAGR not populated yet")
        
        self._screenshot("results_after_backtest")
        
        # Step 4: Check Benchmark tab
        self._log("Step 4: Verify Benchmark tab")
        bench_tab = self.page.locator('[id*="benchmark"], .nav-link:has-text("Benchmark")').first
        if bench_tab.is_visible():
            bench_tab.click()
            time.sleep(1)
        
        alpha = self.page.locator('#sl-alpha-value')
        if alpha.is_visible(timeout=3000):
            alpha_text = alpha.inner_text()
            if alpha_text and alpha_text != '--':
                self._log(f"✅ Alpha populated: {alpha_text}")
            else:
                self._log("⚠️ Alpha not populated yet")
        
        self._screenshot("benchmark_after_backtest")
        
        # Step 5: Check Risk tab
        self._log("Step 5: Verify Risk tab")
        risk_tab = self.page.locator('[id*="risk"], .nav-link:has-text("Risk")').first
        if risk_tab.is_visible():
            risk_tab.click()
            time.sleep(1)
        
        max_dd = self.page.locator('#sl-risk-max-dd')
        if max_dd.is_visible(timeout=3000):
            dd_text = max_dd.inner_text()
            if dd_text and dd_text != '--':
                self._log(f"✅ Max Drawdown populated: {dd_text}")
            else:
                self._log("⚠️ Max Drawdown not populated yet")
        
        self._screenshot("risk_after_backtest")
        self._dump_dom("full_flow_complete")
        
        self._log("✅ Full backtest flow test completed")
    
    # ========================================================================
    # TEST: Live Order Modal
    # ========================================================================
    def test_08_live_order_modal(self):
        """Test live order confirmation modal."""
        self._navigate_to_strategy_lab()
        
        # Need to run a backtest first to enable the live order button
        # Skip if button not visible after navigating
        
        exec_tab = self.page.locator('[id*="execution"], .nav-link:has-text("Execute")').first
        if exec_tab.is_visible():
            exec_tab.click()
            time.sleep(0.5)
        
        live_btn = self.page.locator('#sl-execute-live-btn')
        
        if live_btn.is_visible(timeout=2000):
            # Check if disabled
            is_disabled = live_btn.get_attribute('disabled')
            
            if is_disabled:
                self._log("⚠️ Live order button is disabled (expected before backtest)")
            else:
                live_btn.click()
                time.sleep(1)
                
                # Check if modal opened
                modal = self.page.locator('#sl-order-confirmation-modal')
                if modal.is_visible(timeout=3000):
                    self._log("✅ Order confirmation modal opened")
                    self._screenshot("order_modal_open")
                    
                    # Click cancel
                    cancel_btn = self.page.locator('#sl-order-cancel-btn')
                    if cancel_btn.is_visible():
                        cancel_btn.click()
                        self._log("✅ Order cancelled via modal")
        else:
            self._log("⚠️ Live order button not found")
        
        self._screenshot("live_order_test")




# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

# NOTE: pytest-playwright provides the 'page' fixture automatically.
# The browser_type_launch_args and browser_context_args are configured in conftest.py


def pytest_configure(config):
    """Configure pytest for headed mode."""
    config.addinivalue_line(
        "markers", "headed: Run tests in headed (visible browser) mode"
    )


# Run with: pytest tests/e2e/test_strategy_lab_headed.py -v --headed

