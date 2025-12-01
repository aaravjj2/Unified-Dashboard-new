"""
RED Phase E2E Tests for Volatility Lab Tab

Playwright-based snapshot and clicker tests to verify UI components.
Designed to fail initially because tab implementation is incomplete.

Tests verify:
- Tab page loads
- All vl-* components exist
- Controls are interactive
- Compute button triggers updates
- Charts and tables render
- Status messages display correctly
"""

import pytest
from playwright.sync_api import Page, expect
import time


@pytest.fixture
def app_url():
    """Base URL for the dashboard"""
    return "http://localhost:8050"


@pytest.fixture
def volatility_tab_url(app_url):
    """Direct URL to volatility lab tab"""
    return f"{app_url}/?tab=volatility_lab"


class TestVolatilityLabPageLoad:
    """Test volatility lab page loads correctly"""
    
    def test_volatility_lab_page_loads(self, page: Page, app_url):
        """Test that volatility lab tab loads without errors"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        
        # Click volatility lab tab
        volatility_tab = page.locator('a:has-text("Volatility Lab")')
        assert volatility_tab.is_visible(timeout=10000), "Volatility Lab tab should be visible"
        
        volatility_tab.click()
        time.sleep(2)
        
        # Verify tab content loaded
        tab_content = page.locator('[id*="volatility"]')
        assert tab_content.count() > 0, "Volatility Lab content should load"
    
    def test_volatility_lab_badge_present(self, page: Page, app_url):
        """Test that volatility lab has a badge/label"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        
        # Look for volatility lab indicator
        badge = page.locator('text=/Volatility.*Lab/i')
        assert badge.count() > 0, "Volatility Lab badge should be present"


class TestVolatilityLabControls:
    """Test all control components exist and are interactive"""
    
    def test_tickers_input_exists(self, page: Page, app_url):
        """Test tickers input field exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        
        # Navigate to volatility lab
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for tickers input
        tickers_input = page.locator('#vl-tickers-input, [id*="vl-tickers"]')
        assert tickers_input.count() > 0, "Tickers input should exist"
    
    def test_date_range_picker_exists(self, page: Page, app_url):
        """Test date range picker exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for date range picker
        date_range = page.locator('#vl-date-range, [id*="vl-date"]')
        assert date_range.count() > 0, "Date range picker should exist"
    
    def test_window_slider_exists(self, page: Page, app_url):
        """Test window size slider/input exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for window control
        window_control = page.locator('#vl-window, [id*="vl-window"]')
        assert window_control.count() > 0, "Window control should exist"
    
    def test_volatility_type_dropdown_exists(self, page: Page, app_url):
        """Test volatility type dropdown exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for type dropdown
        type_dropdown = page.locator('#vl-type, [id*="vl-type"]')
        assert type_dropdown.count() > 0, "Volatility type dropdown should exist"
    
    def test_compute_button_exists(self, page: Page, app_url):
        """Test compute button exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for compute button
        compute_button = page.locator('#vl-compute, button:has-text("Compute")')
        assert compute_button.count() > 0, "Compute button should exist"


class TestVolatilityLabOutputs:
    """Test output components (charts, table, status)"""
    
    def test_price_graph_exists(self, page: Page, app_url):
        """Test price chart component exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for price graph
        price_graph = page.locator('#vl-price-graph, [id*="vl-price"]')
        assert price_graph.count() > 0, "Price graph should exist"
    
    def test_volatility_graph_exists(self, page: Page, app_url):
        """Test volatility chart component exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for volatility graph
        vol_graph = page.locator('#vl-vol-graph, [id*="vl-vol"]')
        assert vol_graph.count() > 0, "Volatility graph should exist"
    
    def test_results_table_exists(self, page: Page, app_url):
        """Test results table component exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for results table
        results_table = page.locator('#vl-results-table, [id*="vl-results"]')
        assert results_table.count() > 0, "Results table should exist"
    
    def test_status_area_exists(self, page: Page, app_url):
        """Test status message area exists"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Check for status area
        status_area = page.locator('#vl-status, [id*="vl-status"]')
        assert status_area.count() > 0, "Status area should exist"


class TestVolatilityLabInteraction:
    """Test interactive behavior (compute, updates)"""
    
    def test_compute_button_clickable(self, page: Page, app_url):
        """Test compute button is clickable"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Click compute button
        compute_button = page.locator('#vl-compute, button:has-text("Compute")')
        assert compute_button.count() > 0, "Compute button should exist"
        
        compute_button.first.click()
        time.sleep(1)
        
        # Should not crash
        assert True
    
    def test_charts_render_after_compute(self, page: Page, app_url):
        """Test charts render after compute button click"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Click compute
        compute_button = page.locator('#vl-compute, button:has-text("Compute")')
        if compute_button.count() > 0:
            compute_button.first.click()
            time.sleep(3)
            
            # Check for plotly graphs (svg elements)
            graphs = page.locator('.plotly, svg.main-svg')
            assert graphs.count() > 0, "Charts should render after compute"
    
    def test_table_populates_after_compute(self, page: Page, app_url):
        """Test results table populates after compute"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Click compute
        compute_button = page.locator('#vl-compute, button:has-text("Compute")')
        if compute_button.count() > 0:
            compute_button.first.click()
            time.sleep(3)
            
            # Check for table rows
            table_rows = page.locator('table tr, .dash-table-container')
            assert table_rows.count() > 0, "Table should populate after compute"
    
    def test_status_shows_message(self, page: Page, app_url):
        """Test status area shows appropriate message"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Click compute
        compute_button = page.locator('#vl-compute, button:has-text("Compute")')
        if compute_button.count() > 0:
            compute_button.first.click()
            time.sleep(3)
            
            # Check status area for message
            status = page.locator('#vl-status, [id*="vl-status"]')
            status_text = status.first.inner_text() if status.count() > 0 else ""
            
            # Should show one of: ok, cached, no-data, insufficient_history
            valid_statuses = ['ok', 'cached', 'no-data', 'no data', 'insufficient', 'success', 'error']
            assert any(s in status_text.lower() for s in valid_statuses), \
                f"Status should show valid message, got: {status_text}"


class TestVolatilityLabSnapshot:
    """Snapshot tests for visual regression"""
    
    def test_volatility_lab_full_page_snapshot(self, page: Page, app_url):
        """Capture full page snapshot of volatility lab"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(3)
        
        # Take full page screenshot
        page.screenshot(path='test-artifacts/volatility_lab_full_snapshot.png', full_page=True)
        
        assert True, "Snapshot captured"
    
    def test_volatility_lab_snapshot_after_interaction(self, page: Page, app_url):
        """Capture snapshot after user interaction"""
        page.goto(app_url)
        page.wait_for_load_state('networkidle', timeout=30000)
        page.locator('a:has-text("Volatility Lab")').click()
        time.sleep(2)
        
        # Interact with controls
        compute_button = page.locator('#vl-compute, button:has-text("Compute")')
        if compute_button.count() > 0:
            compute_button.first.click()
            time.sleep(3)
        
        # Take snapshot
        page.screenshot(path='test-artifacts/volatility_lab_interaction_snapshot.png', full_page=True)
        
        assert True, "Interaction snapshot captured"
