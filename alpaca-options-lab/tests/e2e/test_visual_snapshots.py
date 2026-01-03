"""
Visual Regression Snapshot Testing Suite
==========================================
Captures baseline screenshots for all major UI elements and workspaces.

Test Categories:
1. Full page screenshots
2. Component screenshots
3. Workspace screenshots
4. Responsive screenshots
"""

import pytest
from playwright.sync_api import Page, expect
import os
from pathlib import Path

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

BASE_URL = "http://localhost:8053"
SCREENSHOT_DIR = Path(__file__).parent / "snapshots" / "baseline"

@pytest.fixture(scope="module", autouse=True)
def setup_screenshot_dir():
    """Create screenshot directory if it doesn't exist."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def browser_context(browser):
    """Create browser context for screenshots."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        device_scale_factor=1,
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(browser_context):
    """Create a fresh page for each test."""
    page = browser_context.new_page()
    yield page
    page.close()


# =============================================================================
# FULL PAGE SCREENSHOTS
# =============================================================================

class TestFullPageSnapshots:
    """Capture full page screenshots."""
    
    def test_snapshot_landing_page(self, page: Page):
        """Capture landing page screenshot."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Allow animations to complete
        
        path = SCREENSHOT_DIR / "landing_page.png"
        page.screenshot(path=str(path), full_page=True)
        
        assert path.exists()

    def test_snapshot_scanner_workspace(self, page: Page):
        """Capture Scanner workspace screenshot."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Scanner
        scanner_tab = page.locator("text=Scanner").first
        if scanner_tab.is_visible():
            scanner_tab.click()
            page.wait_for_timeout(2000)
        
        path = SCREENSHOT_DIR / "scanner_workspace.png"
        page.screenshot(path=str(path), full_page=True)
        
        assert path.exists()

    def test_snapshot_strategy_workspace(self, page: Page):
        """Capture Strategy workspace screenshot."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Strategy
        strategy_tab = page.locator("text=Strategy").first
        if strategy_tab.is_visible():
            strategy_tab.click()
            page.wait_for_timeout(2000)
        
        path = SCREENSHOT_DIR / "strategy_workspace.png"
        page.screenshot(path=str(path), full_page=True)
        
        assert path.exists()

    def test_snapshot_command_workspace(self, page: Page):
        """Capture Command workspace screenshot."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Command
        command_tab = page.locator("text=Command").first
        if command_tab.is_visible():
            command_tab.click()
            page.wait_for_timeout(2000)
        
        path = SCREENSHOT_DIR / "command_workspace.png"
        page.screenshot(path=str(path), full_page=True)
        
        assert path.exists()

    def test_snapshot_options_lab(self, page: Page):
        """Capture Options Lab screenshot."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Options Lab
        options_tab = page.locator("text=Options Lab").first
        if options_tab.is_visible():
            options_tab.click()
            page.wait_for_timeout(2000)
        
        path = SCREENSHOT_DIR / "options_lab.png"
        page.screenshot(path=str(path), full_page=True)
        
        assert path.exists()


# =============================================================================
# COMPONENT SCREENSHOTS
# =============================================================================

class TestComponentSnapshots:
    """Capture individual component screenshots."""
    
    def test_snapshot_header(self, page: Page):
        """Capture header component."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        header = page.locator("header, [class*='header'], [id*='header']").first
        
        if header.is_visible():
            path = SCREENSHOT_DIR / "component_header.png"
            header.screenshot(path=str(path))
            assert path.exists()

    def test_snapshot_sidebar(self, page: Page):
        """Capture sidebar/navigation component."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        sidebar = page.locator("[class*='sidebar'], [class*='nav'], aside").first
        
        if sidebar.is_visible():
            path = SCREENSHOT_DIR / "component_sidebar.png"
            sidebar.screenshot(path=str(path))
            assert path.exists()

    def test_snapshot_main_tabs(self, page: Page):
        """Capture main workspace tabs."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        tabs = page.locator("#main-workspace-tabs, [class*='workspace-tabs']").first
        
        if tabs.is_visible():
            path = SCREENSHOT_DIR / "component_tabs.png"
            tabs.screenshot(path=str(path))
            assert path.exists()

    def test_snapshot_charts(self, page: Page):
        """Capture chart components."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        charts = page.locator(".js-plotly-plot").all()
        
        for i, chart in enumerate(charts[:3]):
            if chart.is_visible():
                path = SCREENSHOT_DIR / f"component_chart_{i+1}.png"
                chart.screenshot(path=str(path))
                assert path.exists()

    def test_snapshot_data_tables(self, page: Page):
        """Capture data table components."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        tables = page.locator("table, [class*='DataTable']").all()
        
        for i, table in enumerate(tables[:2]):
            if table.is_visible():
                path = SCREENSHOT_DIR / f"component_table_{i+1}.png"
                table.screenshot(path=str(path))
                assert path.exists()


# =============================================================================
# OPTIONS LAB SUBTAB SCREENSHOTS
# =============================================================================

class TestOptionsLabSubtabSnapshots:
    """Capture all Options Lab subtab screenshots."""
    
    def _navigate_to_options_lab(self, page: Page):
        """Helper to navigate to Options Lab."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options_tab = page.locator("text=Options Lab").first
        if options_tab.is_visible():
            options_tab.click()
            page.wait_for_timeout(1000)
    
    def test_snapshot_overview_subtab(self, page: Page):
        """Capture Overview subtab."""
        self._navigate_to_options_lab(page)
        
        overview = page.locator("text=Overview").first
        if overview.is_visible():
            overview.click()
            page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "optionslab_overview.png"
        page.screenshot(path=str(path))
        assert path.exists()

    def test_snapshot_chain_subtab(self, page: Page):
        """Capture Chain subtab."""
        self._navigate_to_options_lab(page)
        
        chain = page.locator("text=Chain").first
        if chain.is_visible():
            chain.click()
            page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "optionslab_chain.png"
        page.screenshot(path=str(path))
        assert path.exists()

    def test_snapshot_greeks_subtab(self, page: Page):
        """Capture Greeks subtab."""
        self._navigate_to_options_lab(page)
        
        greeks = page.locator("text=Greeks").first
        if greeks.is_visible():
            greeks.click()
            page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "optionslab_greeks.png"
        page.screenshot(path=str(path))
        assert path.exists()

    def test_snapshot_volatility_subtab(self, page: Page):
        """Capture Volatility subtab."""
        self._navigate_to_options_lab(page)
        
        vol = page.locator("text=Volatility").first
        if vol.is_visible():
            vol.click()
            page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "optionslab_volatility.png"
        page.screenshot(path=str(path))
        assert path.exists()


# =============================================================================
# RESPONSIVE SCREENSHOTS
# =============================================================================

class TestResponsiveSnapshots:
    """Capture screenshots at different viewport sizes."""
    
    def test_snapshot_desktop_1920x1080(self, browser):
        """Capture at 1920x1080."""
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "responsive_1920x1080.png"
        page.screenshot(path=str(path))
        
        context.close()
        assert path.exists()

    def test_snapshot_laptop_1440x900(self, browser):
        """Capture at 1440x900."""
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "responsive_1440x900.png"
        page.screenshot(path=str(path))
        
        context.close()
        assert path.exists()

    def test_snapshot_tablet_1024x768(self, browser):
        """Capture at 1024x768 (tablet)."""
        context = browser.new_context(viewport={"width": 1024, "height": 768})
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "responsive_1024x768.png"
        page.screenshot(path=str(path))
        
        context.close()
        assert path.exists()

    def test_snapshot_mobile_375x667(self, browser):
        """Capture at 375x667 (mobile)."""
        context = browser.new_context(viewport={"width": 375, "height": 667})
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SCREENSHOT_DIR / "responsive_375x667.png"
        page.screenshot(path=str(path))
        
        context.close()
        assert path.exists()


# =============================================================================
# STATE-BASED SCREENSHOTS
# =============================================================================

class TestStateSnapshots:
    """Capture screenshots of different UI states."""
    
    def test_snapshot_loading_state(self, page: Page):
        """Capture loading state if visible."""
        page.goto(BASE_URL)
        
        # Try to capture loading state quickly
        path = SCREENSHOT_DIR / "state_loading.png"
        page.screenshot(path=str(path))
        
        assert path.exists()

    def test_snapshot_data_loaded(self, page: Page):
        """Capture after data is loaded."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click load button
        load_btn = page.locator("#alpaca-load-button")
        if load_btn.is_visible():
            load_btn.click()
            page.wait_for_timeout(3000)
        
        path = SCREENSHOT_DIR / "state_data_loaded.png"
        page.screenshot(path=str(path))
        
        assert path.exists()

    def test_snapshot_hover_states(self, page: Page):
        """Capture hover state on buttons."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        button = page.locator("button:visible").first
        if button.is_visible():
            button.hover()
            page.wait_for_timeout(300)
            
            path = SCREENSHOT_DIR / "state_button_hover.png"
            page.screenshot(path=str(path))
            assert path.exists()


# =============================================================================
# SUMMARY TEST
# =============================================================================

def test_visual_snapshot_summary():
    """Generate summary of captured snapshots."""
    snapshot_count = len(list(SCREENSHOT_DIR.glob("*.png")))
    
    print("\n" + "=" * 60)
    print("VISUAL REGRESSION SNAPSHOT SUMMARY")
    print("=" * 60)
    print(f"  📸 Total Snapshots Captured: {snapshot_count}")
    print(f"  📁 Location: {SCREENSHOT_DIR}")
    print("=" * 60)
    print("\nSnapshot Categories:")
    print("  • Full Page Screenshots")
    print("  • Component Screenshots")
    print("  • Options Lab Subtab Screenshots")
    print("  • Responsive Screenshots")
    print("  • State-Based Screenshots")
    print("=" * 60)
    
    assert snapshot_count > 0, "Should have captured at least some snapshots"
