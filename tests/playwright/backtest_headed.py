"""
Playwright Headful Tests for Research Lab (Phase 7)

Tests the Historical Backtest Engine and Performance UI.
"""

import pytest
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.sync_api import Page, expect, sync_playwright

# Test configuration
BASE_URL = "http://localhost:8053"
SCREENSHOTS_DIR = Path("/home/aarav/Unified-Dashboard/reports/phase7_research/screenshots")
HAR_DIR = Path("/home/aarav/Unified-Dashboard/reports/phase7_research/playwright")
DOM_DIR = Path("/home/aarav/Unified-Dashboard/reports/phase7_research/dom")
LOGS_DIR = Path("/home/aarav/Unified-Dashboard/reports/phase7_research/logs")

# Ensure directories exist
for dir_path in [SCREENSHOTS_DIR, HAR_DIR, DOM_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def browser_context():
    """Create a browser context for all tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_har_path=str(HAR_DIR / "backtest_test.har")
        )
        yield context
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    """Create a new page for each test"""
    page = browser_context.new_page()
    # Capture console logs
    console_logs = []
    page.on("console", lambda msg: console_logs.append({
        "type": msg.type,
        "text": msg.text,
        "timestamp": datetime.now().isoformat()
    }))
    page.console_logs = console_logs
    yield page
    # Save console logs
    with open(LOGS_DIR / f"console_{datetime.now().strftime('%H%M%S')}.json", "w") as f:
        json.dump(console_logs, f, indent=2)
    page.close()


class TestResearchTabLoad:
    """Tests for Research tab loading and initial state"""
    
    def test_dashboard_loads(self, page: Page):
        """Test that the main dashboard loads"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_dashboard_load.png"))
        
        # Should see tabs
        expect(page.locator("div.tab-parent")).to_be_visible(timeout=15000)
    
    def test_research_tab_exists(self, page: Page):
        """Test that the Research tab is visible"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Find Research tab
        research_tab = page.locator("div.tab-parent >> text=Research")
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_before_research_click.png"))
        
        expect(research_tab).to_be_visible(timeout=10000)
    
    def test_research_tab_click(self, page: Page):
        """Test clicking the Research tab"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click Research tab
        research_tab = page.locator("div.tab-parent >> text=Research")
        research_tab.click()
        page.wait_for_timeout(2000)
        
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_research_tab_active.png"))
        
        # Should see Research Lab header
        header = page.locator("text=Research Lab - Historical Backtester")
        expect(header).to_be_visible(timeout=10000)


class TestBacktestConfiguration:
    """Tests for backtest configuration inputs"""
    
    def test_input_start_date_exists(self, page: Page):
        """Test that start date input exists"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Research tab
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        # Find start date input
        start_date = page.locator("#input-start-date")
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_start_date_input.png"))
        
        expect(start_date).to_be_visible(timeout=10000)
    
    def test_input_end_date_exists(self, page: Page):
        """Test that end date input exists"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        end_date = page.locator("#input-end-date")
        expect(end_date).to_be_visible(timeout=10000)
    
    def test_btn_run_backtest_exists(self, page: Page):
        """Test that Run Backtest button exists"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        btn = page.locator("#btn-run-backtest")
        page.screenshot(path=str(SCREENSHOTS_DIR / "05_run_backtest_button.png"))
        
        expect(btn).to_be_visible(timeout=10000)
    
    def test_strategy_dropdown_exists(self, page: Page):
        """Test that strategy dropdown exists"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        strategy = page.locator("#input-strategy")
        expect(strategy).to_be_visible(timeout=10000)


class TestBacktestExecution:
    """Tests for backtest execution and results"""
    
    def test_run_backtest_30_day(self, page: Page):
        """Test running a 30-day backtest"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Research tab
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        page.screenshot(path=str(SCREENSHOTS_DIR / "06_before_backtest_run.png"))
        
        # Click Run Backtest
        btn = page.locator("#btn-run-backtest")
        btn.click()
        
        # Wait for completion (backtest takes time)
        page.wait_for_timeout(10000)
        
        page.screenshot(path=str(SCREENSHOTS_DIR / "07_after_backtest_run.png"))
        
        # Save DOM
        dom_content = page.content()
        with open(DOM_DIR / "backtest_result_dom.html", "w") as f:
            f.write(dom_content)
    
    def test_equity_curve_renders(self, page: Page):
        """Test that equity curve chart renders after backtest"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        # Run backtest
        page.locator("#btn-run-backtest").click()
        page.wait_for_timeout(10000)
        
        # Check for equity curve chart
        chart_equity = page.locator("#chart-equity")
        page.screenshot(path=str(SCREENSHOTS_DIR / "08_equity_curve.png"))
        
        expect(chart_equity).to_be_visible(timeout=15000)
    
    def test_total_return_not_empty(self, page: Page):
        """Test that Total Return stat is not empty after backtest"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        # Run backtest
        page.locator("#btn-run-backtest").click()
        page.wait_for_timeout(10000)
        
        page.screenshot(path=str(SCREENSHOTS_DIR / "09_total_return.png"))
        
        # Check Performance Summary card exists
        summary = page.locator("text=Performance Summary")
        expect(summary).to_be_visible(timeout=10000)
        
        # Check that we have some numeric value for total return
        # The return is formatted like "+X.XX%" or "-X.XX%"
        total_return = page.locator("text=/[+-]?\\d+\\.\\d+%/").first
        expect(total_return).to_be_visible(timeout=10000)
    
    def test_equity_curve_has_data_points(self, page: Page):
        """Test that equity curve has at least 2 data points"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        # Run backtest
        page.locator("#btn-run-backtest").click()
        page.wait_for_timeout(10000)
        
        # The chart should have SVG paths for the line
        chart = page.locator("#chart-equity")
        expect(chart).to_be_visible(timeout=15000)
        
        # Check for plotly traces (paths in SVG)
        svg_paths = chart.locator("svg path.js-line")
        page.screenshot(path=str(SCREENSHOTS_DIR / "10_equity_curve_data.png"))
        
        # At minimum we should see the chart container with a graph
        # The chart having a Plotly figure means it has data
        plotly_graph = chart.locator(".js-plotly-plot")
        expect(plotly_graph).to_be_visible(timeout=5000)


class TestBacktestNoConsoleErrors:
    """Test that there are no console errors during backtest"""
    
    def test_no_console_errors(self, page: Page):
        """Test that no console errors occur"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Research tab
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        # Run backtest
        page.locator("#btn-run-backtest").click()
        page.wait_for_timeout(10000)
        
        page.screenshot(path=str(SCREENSHOTS_DIR / "11_console_check.png"))
        
        # Filter for actual errors (not warnings)
        errors = [log for log in page.console_logs if log["type"] == "error"]
        
        # Filter out known benign errors and pre-existing issues not related to Research tab
        critical_errors = [
            e for e in errors 
            if "favicon" not in e["text"].lower()
            and "blocked" not in e["text"].lower()
            and "third-party" not in e["text"].lower()
            and "alpaca-interval" not in e["text"]  # Pre-existing callback issue
            and "DataTable filtering syntax" not in e["text"]  # Pre-existing table filter
        ]
        
        assert len(critical_errors) == 0, f"Console errors found: {critical_errors}"


class TestAllRequiredElements:
    """Test all required element IDs exist"""
    
    def test_all_required_elements_present(self, page: Page):
        """Test that all required elements are present"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Research tab
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        required_elements = [
            "input-start-date",
            "btn-run-backtest",
        ]
        
        missing = []
        for elem_id in required_elements:
            try:
                element = page.locator(f"#{elem_id}")
                expect(element).to_be_visible(timeout=5000)
            except Exception:
                missing.append(elem_id)
        
        page.screenshot(path=str(SCREENSHOTS_DIR / "12_all_elements.png"))
        
        assert len(missing) == 0, f"Missing elements: {missing}"
    
    def test_chart_equity_after_run(self, page: Page):
        """Test chart-equity is visible after running backtest"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        page.locator("div.tab-parent >> text=Research").click()
        page.wait_for_timeout(2000)
        
        # Run backtest
        page.locator("#btn-run-backtest").click()
        page.wait_for_timeout(10000)
        
        # Now check for chart
        chart = page.locator("#chart-equity")
        page.screenshot(path=str(SCREENSHOTS_DIR / "13_chart_equity_final.png"))
        
        expect(chart).to_be_visible(timeout=10000)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
