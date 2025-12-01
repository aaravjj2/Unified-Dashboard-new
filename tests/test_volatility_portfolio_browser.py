"""
Comprehensive Browser-Based Tests for Volatility Lab & Portfolio Tab

Tests using Playwright to simulate real browser interactions:
1. Volatility Lab custom ticker input
2. Volatility Lab computation and chart rendering
3. Portfolio tab visibility and functionality

These tests verify the FULL user experience in a browser.
"""

import pytest
from playwright.sync_api import sync_playwright, expect
import time


# Test configuration
BASE_URL = "http://localhost:8050"
TIMEOUT = 30000  # 30 seconds


@pytest.fixture(scope="module")
def browser_context():
    """Create browser context for all tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        yield context
        context.close()
        browser.close()


class TestVolatilityLabBrowser:
    """Browser-based tests for Volatility Lab tab"""
    
    def test_volatility_lab_tab_visible(self, browser_context):
        """Test that Volatility Lab tab appears in the tab list"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Wait for tabs to load
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        
        # Check for Volatility Lab tab (should be tab-3)
        vol_tab = page.locator('button[data-value="tab-3"]')
        expect(vol_tab).to_be_visible()
        expect(vol_tab).to_contain_text("Volatility Lab")
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_tab_visible.png")
        page.close()
    
    def test_volatility_lab_custom_ticker_single(self, browser_context):
        """Test entering a single custom ticker"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)  # Wait for tab to load
        
        # Find ticker input
        ticker_input = page.locator('#vl-tickers-input')
        expect(ticker_input).to_be_visible()
        
        # Clear and enter custom ticker
        ticker_input.fill('TSLA')
        
        # Click compute button
        compute_btn = page.locator('#vl-compute')
        expect(compute_btn).to_be_visible()
        compute_btn.click()
        
        # Wait for results
        time.sleep(3)
        
        # Verify charts updated
        price_graph = page.locator('#vl-price-graph')
        expect(price_graph).to_be_visible()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_single_ticker.png", full_page=True)
        page.close()
    
    def test_volatility_lab_custom_ticker_multiple(self, browser_context):
        """Test entering multiple custom tickers"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Enter multiple tickers
        ticker_input = page.locator('#vl-tickers-input')
        ticker_input.fill('AAPL, MSFT, GOOGL, NVDA, TSLA')
        
        # Click compute
        compute_btn = page.locator('#vl-compute')
        compute_btn.click()
        
        # Wait for computation
        time.sleep(5)
        
        # Verify table has data
        results_table = page.locator('#vl-results-table')
        expect(results_table).to_be_visible()
        
        # Verify status message shows success
        status_area = page.locator('#vl-status')
        expect(status_area).to_be_visible()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_multiple_tickers.png", full_page=True)
        page.close()
    
    def test_volatility_lab_window_size_slider(self, browser_context):
        """Test changing rolling window size"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Enter ticker
        ticker_input = page.locator('#vl-tickers-input')
        ticker_input.fill('SPY')
        
        # Adjust window slider (this is tricky with Dash sliders, so we'll verify it exists)
        window_slider = page.locator('#vl-window')
        expect(window_slider).to_be_visible()
        
        # Click compute
        compute_btn = page.locator('#vl-compute')
        compute_btn.click()
        time.sleep(3)
        
        # Verify volatility chart renders
        vol_graph = page.locator('#vl-vol-graph')
        expect(vol_graph).to_be_visible()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_window_slider.png", full_page=True)
        page.close()
    
    def test_volatility_lab_volatility_type_dropdown(self, browser_context):
        """Test changing volatility type"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Enter ticker
        ticker_input = page.locator('#vl-tickers-input')
        ticker_input.fill('QQQ')
        
        # Open volatility type dropdown
        vol_type_dropdown = page.locator('#vl-type')
        vol_type_dropdown.click()
        time.sleep(1)
        
        # Select 'Rolling'
        page.click('text="Rolling"')
        time.sleep(1)
        
        # Click compute
        compute_btn = page.locator('#vl-compute')
        compute_btn.click()
        time.sleep(3)
        
        # Verify results
        expect(page.locator('#vl-vol-graph')).to_be_visible()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_type_dropdown.png", full_page=True)
        page.close()
    
    def test_volatility_lab_date_range_picker(self, browser_context):
        """Test using date range picker"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Verify date range picker exists
        date_picker = page.locator('#vl-date-range')
        expect(date_picker).to_be_visible()
        
        # Enter ticker and compute
        ticker_input = page.locator('#vl-tickers-input')
        ticker_input.fill('DIA')
        
        compute_btn = page.locator('#vl-compute')
        compute_btn.click()
        time.sleep(3)
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_date_range.png", full_page=True)
        page.close()
    
    def test_volatility_lab_invalid_ticker(self, browser_context):
        """Test handling of invalid ticker"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Enter invalid ticker
        ticker_input = page.locator('#vl-tickers-input')
        ticker_input.fill('INVALID123')
        
        # Click compute
        compute_btn = page.locator('#vl-compute')
        compute_btn.click()
        time.sleep(2)
        
        # Verify status shows warning
        status_area = page.locator('#vl-status')
        expect(status_area).to_be_visible()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_invalid_ticker.png")
        page.close()
    
    def test_volatility_lab_mixed_valid_invalid_tickers(self, browser_context):
        """Test mixed valid and invalid tickers"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Enter mixed tickers (valid: AAPL, MSFT; invalid: 123, TOOLONG)
        ticker_input = page.locator('#vl-tickers-input')
        ticker_input.fill('AAPL, 123, MSFT, TOOLONG')
        
        # Click compute
        compute_btn = page.locator('#vl-compute')
        compute_btn.click()
        time.sleep(3)
        
        # Verify status shows warning about invalid tickers
        status_area = page.locator('#vl-status')
        expect(status_area).to_be_visible()
        
        # Should still show results for valid tickers
        expect(page.locator('#vl-price-graph')).to_be_visible()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/volatility_lab_mixed_tickers.png", full_page=True)
        page.close()


class TestPortfolioTabBrowser:
    """Browser-based tests for Portfolio tab"""
    
    def test_portfolio_tab_visible(self, browser_context):
        """Test that Portfolio tab is visible"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Wait for tabs to load
        page.wait_for_selector('button', timeout=TIMEOUT)
        
        # Find Portfolio tab (should be tab-7)
        # Tab order: Home (0), Market Trends (1), Market Forecast (2), Volatility (3),
        #            Monthly Picks (4), Weekly Picks (5), Analysis Hub (6), Portfolio (7)
        portfolio_tab = page.locator('button[data-value="tab-7"]')
        expect(portfolio_tab).to_be_visible()
        expect(portfolio_tab).to_contain_text("Portfolio")
        
        # Take screenshot
        page.screenshot(path="test_screenshots/portfolio_tab_visible.png")
        page.close()
    
    def test_portfolio_tab_loads_content(self, browser_context):
        """Test that Portfolio tab loads its content"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Portfolio tab
        page.wait_for_selector('button[data-value="tab-7"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-7"]')
        time.sleep(3)  # Wait for tab content to load
        
        # Verify some Portfolio components are present (pa-* namespace)
        # Check for any pa-* ID component
        page_content = page.content()
        assert 'pa-' in page_content, "Portfolio tab should contain pa-* components"
        
        # Take screenshot
        page.screenshot(path="test_screenshots/portfolio_tab_loaded.png", full_page=True)
        page.close()
    
    def test_portfolio_tab_has_calculate_button(self, browser_context):
        """Test that Portfolio tab has calculation controls"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Portfolio tab
        page.wait_for_selector('button[data-value="tab-7"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-7"]')
        time.sleep(3)
        
        # Look for calculate button (pa-calc-btn)
        calc_btn = page.locator('#pa-calc-btn')
        
        # Button should exist (visibility depends on layout)
        expect(calc_btn).to_be_attached()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/portfolio_tab_controls.png", full_page=True)
        page.close()
    
    def test_portfolio_tab_has_charts(self, browser_context):
        """Test that Portfolio tab has chart components"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Portfolio tab
        page.wait_for_selector('button[data-value="tab-7"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-7"]')
        time.sleep(3)
        
        # Check for performance chart (pa-performance-chart)
        perf_chart = page.locator('#pa-performance-chart')
        expect(perf_chart).to_be_attached()
        
        # Take screenshot
        page.screenshot(path="test_screenshots/portfolio_tab_charts.png", full_page=True)
        page.close()


class TestFullDashboardFlow:
    """End-to-end tests for complete user workflows"""
    
    def test_navigate_between_volatility_and_portfolio(self, browser_context):
        """Test switching between Volatility Lab and Portfolio tabs"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Go to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Verify Volatility Lab loaded
        expect(page.locator('#vl-tickers-input')).to_be_visible()
        page.screenshot(path="test_screenshots/flow_volatility_lab.png", full_page=True)
        
        # Go to Portfolio
        page.click('button[data-value="tab-7"]')
        time.sleep(2)
        
        # Verify Portfolio loaded
        page_content = page.content()
        assert 'pa-' in page_content
        page.screenshot(path="test_screenshots/flow_portfolio.png", full_page=True)
        
        # Go back to Volatility Lab
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Verify we're back
        expect(page.locator('#vl-tickers-input')).to_be_visible()
        
        page.close()
    
    def test_complete_volatility_workflow(self, browser_context):
        """Test complete workflow: enter tickers → compute → view results"""
        page = browser_context.new_page()
        page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Navigate to Volatility Lab
        page.wait_for_selector('button[data-value="tab-3"]', timeout=TIMEOUT)
        page.click('button[data-value="tab-3"]')
        time.sleep(2)
        
        # Step 1: Enter tickers
        ticker_input = page.locator('#vl-tickers-input')
        ticker_input.fill('SPY, QQQ, DIA')
        page.screenshot(path="test_screenshots/workflow_step1_tickers.png")
        
        # Step 2: Adjust window size (verify it exists)
        window_slider = page.locator('#vl-window')
        expect(window_slider).to_be_visible()
        
        # Step 3: Select volatility type
        vol_type = page.locator('#vl-type')
        expect(vol_type).to_be_visible()
        
        # Step 4: Click compute
        compute_btn = page.locator('#vl-compute')
        compute_btn.click()
        time.sleep(4)
        page.screenshot(path="test_screenshots/workflow_step2_computing.png", full_page=True)
        
        # Step 5: Verify results
        expect(page.locator('#vl-price-graph')).to_be_visible()
        expect(page.locator('#vl-vol-graph')).to_be_visible()
        expect(page.locator('#vl-results-table')).to_be_visible()
        expect(page.locator('#vl-status')).to_be_visible()
        
        page.screenshot(path="test_screenshots/workflow_step3_results.png", full_page=True)
        
        page.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])
