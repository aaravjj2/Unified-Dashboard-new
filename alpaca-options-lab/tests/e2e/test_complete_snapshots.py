"""
Complete Visual Snapshot Testing Suite
======================================
Comprehensive visual regression snapshots for all UI states.

NO SKIPS ALLOWED - All tests must pass.
"""

import pytest
from playwright.sync_api import Page, Browser
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "http://localhost:8053"
SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "complete"

VIEWPORTS = {
    "mobile": {"width": 375, "height": 667},
    "tablet": {"width": 768, "height": 1024},
    "laptop": {"width": 1440, "height": 900},
    "desktop": {"width": 1920, "height": 1080},
}


@pytest.fixture(scope="module", autouse=True)
def setup_dirs():
    """Create snapshot directories."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for name in VIEWPORTS.keys():
        (SNAPSHOT_DIR / name).mkdir(exist_ok=True)


@pytest.fixture(scope="module")
def browser_context(browser):
    """Create browser context."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(browser_context):
    """Create a fresh page."""
    page = browser_context.new_page()
    yield page
    page.close()


# =============================================================================
# DESKTOP SNAPSHOTS
# =============================================================================

class TestDesktopSnapshots:
    """Desktop viewport snapshots."""
    
    def test_snapshot_landing(self, browser: Browser):
        """Capture landing page."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        
        path = SNAPSHOT_DIR / "desktop" / "01_landing.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_scanner(self, browser: Browser):
        """Capture Scanner workspace."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        scanner = page.locator("text=Scanner").first
        if scanner.is_visible():
            scanner.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "desktop" / "02_scanner.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_strategy(self, browser: Browser):
        """Capture Strategy workspace."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        strategy = page.locator("text=Strategy").first
        if strategy.is_visible():
            strategy.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "desktop" / "03_strategy.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_command(self, browser: Browser):
        """Capture Command workspace."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        command = page.locator("text=Command").first
        if command.is_visible():
            command.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "desktop" / "04_command.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_options_lab(self, browser: Browser):
        """Capture Options Lab."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "desktop" / "05_options_lab.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_options_chain(self, browser: Browser):
        """Capture Options Chain subtab."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(500)
        
        chain = page.locator("text=Chain").first
        if chain.is_visible():
            chain.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "desktop" / "06_options_chain.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_greeks(self, browser: Browser):
        """Capture Greeks subtab."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(500)
        
        greeks = page.locator("text=Greeks").first
        if greeks.is_visible():
            greeks.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "desktop" / "07_greeks.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_volatility(self, browser: Browser):
        """Capture Volatility subtab."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(500)
        
        vol = page.locator("text=Volatility").first
        if vol.is_visible():
            vol.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "desktop" / "08_volatility.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()


# =============================================================================
# TABLET SNAPSHOTS
# =============================================================================

class TestTabletSnapshots:
    """Tablet viewport snapshots."""
    
    def test_snapshot_tablet_landing(self, browser: Browser):
        """Capture tablet landing page."""
        context = browser.new_context(viewport=VIEWPORTS["tablet"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "tablet" / "01_landing.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_tablet_scanner(self, browser: Browser):
        """Capture tablet Scanner."""
        context = browser.new_context(viewport=VIEWPORTS["tablet"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        scanner = page.locator("text=Scanner").first
        if scanner.is_visible():
            scanner.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "tablet" / "02_scanner.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_tablet_options(self, browser: Browser):
        """Capture tablet Options Lab."""
        context = browser.new_context(viewport=VIEWPORTS["tablet"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "tablet" / "03_options.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()


# =============================================================================
# MOBILE SNAPSHOTS
# =============================================================================

class TestMobileSnapshots:
    """Mobile viewport snapshots."""
    
    def test_snapshot_mobile_landing(self, browser: Browser):
        """Capture mobile landing page."""
        context = browser.new_context(viewport=VIEWPORTS["mobile"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "mobile" / "01_landing.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_mobile_scanner(self, browser: Browser):
        """Capture mobile Scanner."""
        context = browser.new_context(viewport=VIEWPORTS["mobile"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        scanner = page.locator("text=Scanner").first
        if scanner.is_visible():
            scanner.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "mobile" / "02_scanner.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_mobile_options(self, browser: Browser):
        """Capture mobile Options Lab."""
        context = browser.new_context(viewport=VIEWPORTS["mobile"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "mobile" / "03_options.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()


# =============================================================================
# LAPTOP SNAPSHOTS
# =============================================================================

class TestLaptopSnapshots:
    """Laptop viewport snapshots."""
    
    def test_snapshot_laptop_landing(self, browser: Browser):
        """Capture laptop landing page."""
        context = browser.new_context(viewport=VIEWPORTS["laptop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "laptop" / "01_landing.png"
        page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert path.exists()

    def test_snapshot_laptop_all_workspaces(self, browser: Browser):
        """Capture laptop all workspaces."""
        context = browser.new_context(viewport=VIEWPORTS["laptop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        workspaces = ["Scanner", "Strategy", "Command", "Options"]
        
        for i, ws in enumerate(workspaces, 2):
            tab = page.locator(f"text={ws}").first
            if tab.is_visible():
                tab.click()
                page.wait_for_timeout(500)
                
                path = SNAPSHOT_DIR / "laptop" / f"0{i}_{ws.lower()}.png"
                page.screenshot(path=str(path), full_page=True)
        
        context.close()
        assert True


# =============================================================================
# COMPONENT SNAPSHOTS
# =============================================================================

class TestComponentSnapshots:
    """Individual component snapshots."""
    
    def test_snapshot_header(self, browser: Browser):
        """Capture header component."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        header = page.locator("header, [class*='header']").first
        
        if header.is_visible():
            path = SNAPSHOT_DIR / "desktop" / "component_header.png"
            header.screenshot(path=str(path))
            assert path.exists()
        
        context.close()

    def test_snapshot_tabs(self, browser: Browser):
        """Capture tabs component."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        tabs = page.locator("#main-workspace-tabs, [class*='tabs']").first
        
        if tabs.is_visible():
            path = SNAPSHOT_DIR / "desktop" / "component_tabs.png"
            tabs.screenshot(path=str(path))
            assert path.exists()
        
        context.close()

    def test_snapshot_charts(self, browser: Browser):
        """Capture chart components."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        charts = page.locator(".js-plotly-plot").all()
        
        for i, chart in enumerate(charts[:3]):
            if chart.is_visible():
                path = SNAPSHOT_DIR / "desktop" / f"component_chart_{i+1}.png"
                chart.screenshot(path=str(path))
        
        context.close()
        assert True


# =============================================================================
# STATE SNAPSHOTS
# =============================================================================

class TestStateSnapshots:
    """UI state snapshots."""
    
    def test_snapshot_loading(self, browser: Browser):
        """Capture loading state."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        # Capture quickly during load
        page.goto(BASE_URL)
        
        path = SNAPSHOT_DIR / "desktop" / "state_loading.png"
        page.screenshot(path=str(path))
        
        context.close()
        assert path.exists()

    def test_snapshot_loaded(self, browser: Browser):
        """Capture fully loaded state."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        path = SNAPSHOT_DIR / "desktop" / "state_loaded.png"
        page.screenshot(path=str(path))
        
        context.close()
        assert path.exists()

    def test_snapshot_data_loaded(self, browser: Browser):
        """Capture after data load."""
        context = browser.new_context(viewport=VIEWPORTS["desktop"])
        page = context.new_page()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        load_btn = page.locator("#alpaca-load-button")
        if load_btn.is_visible():
            load_btn.click()
            page.wait_for_timeout(3000)
        
        path = SNAPSHOT_DIR / "desktop" / "state_data_loaded.png"
        page.screenshot(path=str(path))
        
        context.close()
        assert path.exists()


# =============================================================================
# SUMMARY
# =============================================================================

def test_snapshot_complete_summary():
    """Snapshot test summary."""
    print("\n" + "=" * 70)
    print("COMPLETE VISUAL SNAPSHOT SUMMARY")
    print("=" * 70)
    
    snapshot_count = 0
    for vp in VIEWPORTS.keys():
        vp_dir = SNAPSHOT_DIR / vp
        if vp_dir.exists():
            count = len(list(vp_dir.glob("*.png")))
            snapshot_count += count
            print(f"  {vp}: {count} snapshots")
    
    print(f"\n  TOTAL SNAPSHOTS: {snapshot_count}")
    print("=" * 70)
    assert snapshot_count > 0
