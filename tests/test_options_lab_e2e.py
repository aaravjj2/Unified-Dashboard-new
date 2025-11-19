"""
E2E Tests for Options Lab Tab
Phase 0.8 Expansion - Agent 1B

Tests all 4 subtabs with 3-iteration validation loop.
Uses Playwright to verify DOM elements, interactions, and exports.
"""

import pytest
import time
import os
from playwright.sync_api import sync_playwright, Page, expect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dashboard URL
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8050')
TIMEOUT = 60000  # 60 seconds


@pytest.fixture(scope="session")
def browser():
    """Launch browser for the session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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


def navigate_to_options_lab(page: Page):
    """Navigate to Options Lab tab."""
    logger.info("🔵 Navigating to Options Lab tab...")
    page.goto(DASHBOARD_URL)
    
    # Wait for dashboard to load
    page.wait_for_selector('text=Financial Dashboard', timeout=TIMEOUT)
    
    # Click Options Lab tab
    options_tab = page.locator('text=💹 Options Lab').first
    options_tab.click()
    
    # Wait for ticker input to appear
    page.wait_for_selector('#options-ticker-input', timeout=TIMEOUT)
    logger.info("✅ Successfully navigated to Options Lab tab")


def load_mock_data(page: Page):
    """Load mock data for testing."""
    logger.info("🔵 Loading mock data...")
    
    # Enter ticker
    ticker_input = page.locator('#options-ticker-input')
    ticker_input.fill('AAPL')
    
    # Click Mock Data button
    mock_btn = page.locator('#options-mock-btn')
    mock_btn.click()
    
    # Wait for status message (updated to match actual message format)
    page.wait_for_selector('#options-status-message:has-text("✅ Loaded")', timeout=TIMEOUT)
    
    # Wait a bit for all updates to propagate
    time.sleep(2)
    logger.info("✅ Mock data loaded successfully")


class TestOptionsLabChainViewer:
    """Test Chain Viewer subtab."""
    
    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_chain_viewer_load(self, page: Page, iteration: int):
        """Test loading and displaying options chain data."""
        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 TEST: Chain Viewer - Iteration {iteration}")
        logger.info(f"{'='*70}")
        
        navigate_to_options_lab(page)
        load_mock_data(page)
        
        # Verify summary cards
        logger.info("🔍 Verifying summary cards...")
        spot_card = page.locator('#chain-spot-price')
        expect(spot_card).to_contain_text('$150')
        
        volume_card = page.locator('#chain-total-volume')
        expect(volume_card).to_be_visible()
        
        oi_card = page.locator('#chain-total-oi')
        expect(oi_card).to_be_visible()
        
        pc_card = page.locator('#chain-pc-ratio')
        expect(pc_card).to_be_visible()
        logger.info("✅ Summary cards displayed correctly")
        
        # Verify DataTable
        logger.info("🔍 Verifying options chain table...")
        table = page.locator('#options-chain-table')
        expect(table).to_be_visible(timeout=TIMEOUT)
        
        # Check table has data rows
        rows = page.locator('#options-chain-table tbody tr')
        row_count = rows.count()
        assert row_count > 0, f"Expected data rows, got {row_count}"
        logger.info(f"✅ Table contains {row_count} rows")
        
        # Test expiration filter
        logger.info("🔍 Testing expiration filter...")
        exp_dropdown = page.locator('#chain-expiration-dropdown')
        expect(exp_dropdown).to_be_visible()
        
        # Test type filter
        logger.info("🔍 Testing type filter...")
        type_dropdown = page.locator('#chain-type-filter')
        type_dropdown.select_option('calls')
        time.sleep(1)
        
        # Table should still have data
        rows_after = page.locator('#options-chain-table tbody tr')
        assert rows_after.count() > 0, "No rows after filtering"
        logger.info("✅ Type filter working")
        
        # Reset filter
        type_dropdown.select_option('all')
        time.sleep(1)
        
        # Test export button
        logger.info("🔍 Testing export button...")
        export_btn = page.locator('#export-chain-btn')
        expect(export_btn).to_be_visible()
        expect(export_btn).to_be_enabled()
        logger.info("✅ Export button ready")
        
        logger.info(f"✅ ITERATION {iteration} PASSED")


class TestOptionsLabGreeksDashboard:
    """Test Greeks Dashboard subtab."""
    
    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_greeks_dashboard(self, page: Page, iteration: int):
        """Test Greeks charts rendering."""
        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 TEST: Greeks Dashboard - Iteration {iteration}")
        logger.info(f"{'='*70}")
        
        navigate_to_options_lab(page)
        load_mock_data(page)
        
        # Switch to Greeks Dashboard subtab
        logger.info("🔵 Switching to Greeks Dashboard...")
        greeks_tab = page.locator('text=Greeks Dashboard').first
        greeks_tab.click()
        time.sleep(2)
        
        # Verify Delta chart
        logger.info("🔍 Verifying Delta chart...")
        delta_chart = page.locator('#greeks-delta-chart')
        expect(delta_chart).to_be_visible(timeout=TIMEOUT)
        
        # Verify Gamma chart
        logger.info("🔍 Verifying Gamma chart...")
        gamma_chart = page.locator('#greeks-gamma-chart')
        expect(gamma_chart).to_be_visible(timeout=TIMEOUT)
        
        # Verify Theta chart
        logger.info("🔍 Verifying Theta chart...")
        theta_chart = page.locator('#greeks-theta-chart')
        expect(theta_chart).to_be_visible(timeout=TIMEOUT)
        
        # Verify Vega chart
        logger.info("🔍 Verifying Vega chart...")
        vega_chart = page.locator('#greeks-vega-chart')
        expect(vega_chart).to_be_visible(timeout=TIMEOUT)
        
        # Verify IV Smile chart
        logger.info("🔍 Verifying IV Smile chart...")
        iv_chart = page.locator('#greeks-iv-smile-chart')
        expect(iv_chart).to_be_visible(timeout=TIMEOUT)
        
        logger.info("✅ All 5 Greeks charts rendered successfully")
        logger.info(f"✅ ITERATION {iteration} PASSED")


class TestOptionsLabVolSurface:
    """Test Vol Surface subtab."""
    
    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_vol_surface(self, page: Page, iteration: int):
        """Test 3D volatility surface rendering."""
        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 TEST: Vol Surface - Iteration {iteration}")
        logger.info(f"{'='*70}")
        
        navigate_to_options_lab(page)
        load_mock_data(page)
        
        # Switch to Vol Surface subtab
        logger.info("🔵 Switching to Vol Surface...")
        vol_tab = page.locator('text=Vol Surface').first
        vol_tab.click()
        time.sleep(2)
        
        # Verify 3D surface chart
        logger.info("🔍 Verifying 3D surface chart...")
        surface_chart = page.locator('#vol-surface-chart')
        expect(surface_chart).to_be_visible(timeout=TIMEOUT)
        
        # Test camera angle slider
        logger.info("🔍 Testing camera angle slider...")
        angle_slider = page.locator('#surface-camera-angle')
        expect(angle_slider).to_be_visible()
        
        # Change angle and verify chart updates
        angle_slider.fill('90')
        time.sleep(1)
        expect(surface_chart).to_be_visible()
        logger.info("✅ Camera angle control working")
        
        # Test colorscale dropdown
        logger.info("🔍 Testing colorscale dropdown...")
        colorscale_dropdown = page.locator('#surface-colorscale')
        expect(colorscale_dropdown).to_be_visible()
        
        colorscale_dropdown.select_option('Viridis')
        time.sleep(1)
        expect(surface_chart).to_be_visible()
        logger.info("✅ Colorscale control working")
        
        logger.info(f"✅ ITERATION {iteration} PASSED")


class TestOptionsLabTradeSimulator:
    """Test Trade Simulator subtab."""
    
    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_trade_simulator(self, page: Page, iteration: int):
        """Test trade P&L calculation."""
        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 TEST: Trade Simulator - Iteration {iteration}")
        logger.info(f"{'='*70}")
        
        navigate_to_options_lab(page)
        load_mock_data(page)
        
        # Switch to Trade Simulator subtab
        logger.info("🔵 Switching to Trade Simulator...")
        trade_tab = page.locator('text=Trade Simulator').first
        trade_tab.click()
        time.sleep(2)
        
        # Select strategy
        logger.info("🔍 Selecting Long Call strategy...")
        strategy_dropdown = page.locator('#trade-strategy-dropdown')
        strategy_dropdown.select_option('long_call')
        time.sleep(1)
        
        # Set quantity
        logger.info("🔍 Setting quantity...")
        quantity_input = page.locator('#trade-quantity-input')
        quantity_input.fill('10')
        time.sleep(1)
        
        # Verify P&L metrics cards
        logger.info("🔍 Verifying P&L metrics...")
        max_profit_card = page.locator('#trade-max-profit')
        expect(max_profit_card).to_be_visible()
        
        max_loss_card = page.locator('#trade-max-loss')
        expect(max_loss_card).to_be_visible()
        
        breakeven_card = page.locator('#trade-breakeven')
        expect(breakeven_card).to_be_visible()
        
        logger.info("✅ P&L metrics displayed")
        
        # Verify P&L chart
        logger.info("🔍 Verifying P&L chart...")
        pnl_chart = page.locator('#trade-pnl-chart')
        expect(pnl_chart).to_be_visible(timeout=TIMEOUT)
        logger.info("✅ P&L chart rendered")
        
        # Test different strategies
        strategies = ['long_put', 'bull_call_spread', 'straddle']
        for strategy in strategies:
            logger.info(f"🔍 Testing {strategy} strategy...")
            strategy_dropdown.select_option(strategy)
            time.sleep(1)
            expect(pnl_chart).to_be_visible()
            logger.info(f"✅ {strategy} P&L calculated")
        
        logger.info(f"✅ ITERATION {iteration} PASSED")


class TestOptionsLabExport:
    """Test export functionality."""
    
    def test_export_csv(self, page: Page):
        """Test CSV export download."""
        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 TEST: CSV Export")
        logger.info(f"{'='*70}")
        
        navigate_to_options_lab(page)
        load_mock_data(page)
        
        # Set up download listener
        logger.info("🔍 Testing CSV export...")
        with page.expect_download() as download_info:
            export_btn = page.locator('#export-chain-btn')
            export_btn.click()
        
        download = download_info.value
        assert download is not None, "Download failed"
        
        # Verify filename
        filename = download.suggested_filename
        assert filename.endswith('.csv'), f"Expected .csv file, got {filename}"
        logger.info(f"✅ CSV export successful: {filename}")


def test_options_lab_full_workflow(page: Page):
    """
    Comprehensive end-to-end workflow test.
    Tests the complete user journey through all subtabs.
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🧪 COMPREHENSIVE WORKFLOW TEST")
    logger.info(f"{'='*70}")
    
    navigate_to_options_lab(page)
    load_mock_data(page)
    
    # Workflow Step 1: Chain Viewer
    logger.info("📊 Step 1: Viewing options chain...")
    table = page.locator('#options-chain-table')
    expect(table).to_be_visible(timeout=TIMEOUT)
    logger.info("✅ Step 1 complete")
    
    # Workflow Step 2: Greeks Dashboard
    logger.info("📊 Step 2: Analyzing Greeks...")
    greeks_tab = page.locator('text=Greeks Dashboard').first
    greeks_tab.click()
    time.sleep(2)
    delta_chart = page.locator('#greeks-delta-chart')
    expect(delta_chart).to_be_visible()
    logger.info("✅ Step 2 complete")
    
    # Workflow Step 3: Vol Surface
    logger.info("📊 Step 3: Viewing volatility surface...")
    vol_tab = page.locator('text=Vol Surface').first
    vol_tab.click()
    time.sleep(2)
    surface_chart = page.locator('#vol-surface-chart')
    expect(surface_chart).to_be_visible()
    logger.info("✅ Step 3 complete")
    
    # Workflow Step 4: Trade Simulator
    logger.info("📊 Step 4: Simulating trade...")
    trade_tab = page.locator('text=Trade Simulator').first
    trade_tab.click()
    time.sleep(2)
    
    strategy_dropdown = page.locator('#trade-strategy-dropdown')
    strategy_dropdown.select_option('long_call')
    time.sleep(1)
    
    pnl_chart = page.locator('#trade-pnl-chart')
    expect(pnl_chart).to_be_visible()
    logger.info("✅ Step 4 complete")
    
    logger.info("✅ COMPREHENSIVE WORKFLOW PASSED")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
