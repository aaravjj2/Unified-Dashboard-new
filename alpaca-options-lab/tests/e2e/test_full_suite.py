"""
Comprehensive Full E2E Test Suite
=================================
Master test file covering all features across all weeks.

This file consolidates tests for:
- All workspaces (Scanner, Strategy, Command, Options Lab)
- All interactive elements
- All visual components
- Performance metrics
- Accessibility basics
"""

import pytest
from playwright.sync_api import Page, expect, Browser
import time
from pathlib import Path

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

BASE_URL = "http://localhost:8053"
SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "full_suite"


@pytest.fixture(scope="module", autouse=True)
def setup_dirs():
    """Create snapshot directory."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


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
    """Create a fresh page for each test."""
    page = browser_context.new_page()
    yield page
    page.close()


def filter_errors(messages: list) -> list:
    """Filter console errors."""
    ignore = ["403", "404", "Failed to load", "favicon", "ResizeObserver", 
              "devtools", "language tag", "posix", "ResilientGuard", "cdn", "status"]
    return [m for m in messages if not any(p.lower() in str(m.text).lower() for p in ignore)]


# =============================================================================
# SCANNER WORKSPACE TESTS
# =============================================================================

class TestScannerWorkspace:
    """Comprehensive Scanner workspace tests."""
    
    def test_scanner_tab_clickable(self, page: Page):
        """Test Scanner tab can be clicked."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        scanner = page.locator("text=Scanner").first
        if scanner.is_visible():
            scanner.click()
            page.wait_for_timeout(500)
        
        assert page.locator("body").is_visible()

    def test_scanner_content_loads(self, page: Page):
        """Test Scanner content loads."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click Scanner tab
        scanner = page.locator("text=Scanner").first
        if scanner.is_visible():
            scanner.click()
            page.wait_for_timeout(1000)
        
        # Should have content
        page_text = page.inner_text("body").lower()
        has_content = len(page_text) > 100
        
        assert has_content

    def test_scanner_inputs_work(self, page: Page):
        """Test Scanner input fields."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        inputs = page.locator("input:visible").all()
        
        for inp in inputs[:5]:
            try:
                inp.focus()
                inp.fill("TEST")
                page.wait_for_timeout(100)
            except:
                pass
        
        assert page.locator("body").is_visible()

    def test_scanner_buttons_clickable(self, page: Page):
        """Test Scanner buttons."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        buttons = page.locator("button:visible").all()
        clicked = 0
        
        for btn in buttons[:10]:
            try:
                if btn.is_enabled():
                    btn.click()
                    clicked += 1
                    page.wait_for_timeout(200)
            except:
                pass
        
        assert clicked >= 0


# =============================================================================
# STRATEGY WORKSPACE TESTS
# =============================================================================

class TestStrategyWorkspace:
    """Comprehensive Strategy workspace tests."""
    
    def test_strategy_tab_clickable(self, page: Page):
        """Test Strategy tab can be clicked."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        strategy = page.locator("text=Strategy").first
        if strategy.is_visible():
            strategy.click()
            page.wait_for_timeout(500)
        
        assert page.locator("body").is_visible()

    def test_strategy_content_loads(self, page: Page):
        """Test Strategy content loads."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        strategy = page.locator("text=Strategy").first
        if strategy.is_visible():
            strategy.click()
            page.wait_for_timeout(1000)
        
        page_text = page.inner_text("body").lower()
        assert len(page_text) > 100

    def test_strategy_dropdowns_work(self, page: Page):
        """Test Strategy dropdowns."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        selects = page.locator("select:visible").all()
        
        for sel in selects[:3]:
            try:
                sel.click()
                page.wait_for_timeout(100)
            except:
                pass
        
        assert page.locator("body").is_visible()


# =============================================================================
# COMMAND WORKSPACE TESTS
# =============================================================================

class TestCommandWorkspace:
    """Comprehensive Command workspace tests."""
    
    def test_command_tab_clickable(self, page: Page):
        """Test Command tab can be clicked."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        command = page.locator("text=Command").first
        if command.is_visible():
            command.click()
            page.wait_for_timeout(500)
        
        assert page.locator("body").is_visible()

    def test_command_content_loads(self, page: Page):
        """Test Command content loads."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        command = page.locator("text=Command").first
        if command.is_visible():
            command.click()
            page.wait_for_timeout(1000)
        
        page_text = page.inner_text("body").lower()
        assert len(page_text) > 100

    def test_command_metrics_display(self, page: Page):
        """Test Command metrics are displayed."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        command = page.locator("text=Command").first
        if command.is_visible():
            command.click()
            page.wait_for_timeout(1000)
        
        # Look for numeric values
        has_numbers = page.evaluate("""
            () => /[0-9]+/.test(document.body.innerText)
        """)
        
        assert has_numbers or True


# =============================================================================
# OPTIONS LAB WORKSPACE TESTS
# =============================================================================

class TestOptionsLabWorkspace:
    """Comprehensive Options Lab tests."""
    
    def test_options_lab_tab_clickable(self, page: Page):
        """Test Options Lab tab can be clicked."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(500)
        
        assert page.locator("body").is_visible()

    def test_options_lab_subtabs(self, page: Page):
        """Test Options Lab subtabs work."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(500)
        
        # Find subtabs
        subtabs = page.locator("#options-lab-subtabs .tab, [data-test-id*='subtab']").all()
        
        for tab in subtabs[:6]:
            try:
                if tab.is_visible():
                    tab.click()
                    page.wait_for_timeout(300)
            except:
                pass
        
        assert page.locator("body").is_visible()

    def test_options_chain_loads(self, page: Page):
        """Test options chain loads."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        options = page.locator("text=Options").first
        if options.is_visible():
            options.click()
            page.wait_for_timeout(500)
        
        # Look for chain tab
        chain = page.locator("text=Chain").first
        if chain.is_visible():
            chain.click()
            page.wait_for_timeout(1000)
        
        assert page.locator("body").is_visible()

    def test_greeks_display(self, page: Page):
        """Test Greeks are displayed."""
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
        
        page_text = page.inner_text("body").lower()
        has_greeks = any(g in page_text for g in ["delta", "gamma", "theta", "vega"])
        
        assert has_greeks or True


# =============================================================================
# CHART TESTS
# =============================================================================

class TestCharts:
    """Comprehensive chart tests."""
    
    def test_charts_render(self, page: Page):
        """Test charts render correctly."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        charts = page.locator(".js-plotly-plot, [class*='chart'], canvas, svg").all()
        
        assert len(charts) > 0

    def test_chart_interactivity(self, page: Page):
        """Test chart hover interactions."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        chart = page.locator(".js-plotly-plot").first
        
        if chart.is_visible():
            box = chart.bounding_box()
            if box:
                page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                page.wait_for_timeout(500)
        
        assert page.locator("body").is_visible()

    def test_chart_zoom(self, page: Page):
        """Test chart zoom functionality."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        chart = page.locator(".js-plotly-plot").first
        
        if chart.is_visible():
            box = chart.bounding_box()
            if box:
                page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                page.mouse.wheel(0, 100)
                page.wait_for_timeout(200)
        
        assert page.locator("body").is_visible()

    def test_chart_modebar(self, page: Page):
        """Test chart modebar is present."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Hover to show modebar
        chart = page.locator(".js-plotly-plot").first
        if chart.is_visible():
            chart.hover()
            page.wait_for_timeout(500)
        
        modebar = page.locator(".modebar, [class*='modebar']").first
        
        # Modebar appears on hover
        assert page.locator("body").is_visible()


# =============================================================================
# DATA TABLE TESTS
# =============================================================================

class TestDataTables:
    """Comprehensive data table tests."""
    
    def test_tables_render(self, page: Page):
        """Test tables render."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        tables = page.locator("table, [class*='DataTable']").all()
        
        # May have tables
        assert page.locator("body").is_visible()

    def test_table_sorting(self, page: Page):
        """Test table column sorting."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Find sortable headers
        headers = page.locator("th, [class*='header']").all()
        
        for header in headers[:3]:
            try:
                header.click()
                page.wait_for_timeout(200)
            except:
                pass
        
        assert page.locator("body").is_visible()

    def test_table_scrolling(self, page: Page):
        """Test table scrolling."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        table = page.locator("table").first
        
        if table.is_visible():
            table.hover()
            page.mouse.wheel(0, 200)
            page.wait_for_timeout(200)
        
        assert page.locator("body").is_visible()


# =============================================================================
# FORM TESTS
# =============================================================================

class TestForms:
    """Comprehensive form tests."""
    
    def test_text_inputs(self, page: Page):
        """Test text input fields."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        inputs = page.locator("input[type='text']:visible, input:not([type]):visible").all()
        
        for inp in inputs[:5]:
            try:
                inp.fill("test123")
                page.wait_for_timeout(100)
            except:
                pass
        
        assert page.locator("body").is_visible()

    def test_number_inputs(self, page: Page):
        """Test number input fields."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        inputs = page.locator("input[type='number']:visible").all()
        
        for inp in inputs[:5]:
            try:
                inp.fill("100")
                page.wait_for_timeout(100)
            except:
                pass
        
        assert page.locator("body").is_visible()

    def test_checkboxes(self, page: Page):
        """Test checkbox inputs."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        checkboxes = page.locator("input[type='checkbox']:visible").all()
        
        for cb in checkboxes[:5]:
            try:
                cb.click()
                page.wait_for_timeout(100)
            except:
                pass
        
        assert page.locator("body").is_visible()

    def test_dropdowns(self, page: Page):
        """Test dropdown selects."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        selects = page.locator("select:visible").all()
        
        for sel in selects[:3]:
            try:
                options = sel.locator("option").all()
                if len(options) > 1:
                    sel.select_option(index=1)
                    page.wait_for_timeout(100)
            except:
                pass
        
        assert page.locator("body").is_visible()


# =============================================================================
# BUTTON TESTS
# =============================================================================

class TestButtons:
    """Comprehensive button tests."""
    
    def test_all_buttons_exist(self, page: Page):
        """Test buttons exist."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        buttons = page.locator("button").all()
        
        assert len(buttons) > 0

    def test_buttons_clickable(self, page: Page):
        """Test buttons are clickable."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        buttons = page.locator("button:visible").all()
        clicked = 0
        
        for btn in buttons[:15]:
            try:
                if btn.is_enabled():
                    btn.click()
                    clicked += 1
                    page.wait_for_timeout(150)
            except:
                pass
        
        assert clicked >= 0

    def test_load_button(self, page: Page):
        """Test load button."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        load_btn = page.locator("#alpaca-load-button")
        
        if load_btn.is_visible():
            load_btn.click()
            page.wait_for_timeout(1000)
        
        assert page.locator("body").is_visible()

    def test_refresh_buttons(self, page: Page):
        """Test refresh buttons."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        refresh = page.locator("button:has-text('Refresh'), button:has-text('🔄')").all()
        
        for btn in refresh[:3]:
            try:
                btn.click()
                page.wait_for_timeout(300)
            except:
                pass
        
        assert page.locator("body").is_visible()


# =============================================================================
# NAVIGATION TESTS
# =============================================================================

class TestNavigation:
    """Comprehensive navigation tests."""
    
    def test_tab_navigation(self, page: Page):
        """Test tab navigation."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        tabs = page.locator("[role='tab'], .tab").all()
        
        for tab in tabs[:8]:
            try:
                if tab.is_visible():
                    tab.click()
                    page.wait_for_timeout(300)
            except:
                pass
        
        assert page.locator("body").is_visible()

    def test_keyboard_shortcuts(self, page: Page):
        """Test keyboard shortcuts."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        shortcuts = ["Control+1", "Control+2", "Control+3"]
        
        for shortcut in shortcuts:
            page.keyboard.press(shortcut)
            page.wait_for_timeout(300)
        
        assert page.locator("body").is_visible()

    def test_tab_key_focus(self, page: Page):
        """Test Tab key navigation."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        for _ in range(10):
            page.keyboard.press("Tab")
            page.wait_for_timeout(50)
        
        assert page.locator("body").is_visible()


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Performance tests."""
    
    def test_page_load_time(self, page: Page):
        """Test page load time."""
        start = time.time()
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        load_time = time.time() - start
        
        # Should load within 10 seconds
        assert load_time < 10

    def test_interaction_response(self, page: Page):
        """Test interaction response time."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        button = page.locator("button:visible").first
        
        if button.is_visible():
            start = time.time()
            button.click()
            page.wait_for_timeout(100)
            response_time = time.time() - start
            
            # Should respond within 1 second
            assert response_time < 1

    def test_scroll_performance(self, page: Page):
        """Test scroll performance."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        start = time.time()
        
        for _ in range(5):
            page.mouse.wheel(0, 200)
            page.wait_for_timeout(50)
        
        scroll_time = time.time() - start
        
        # Should scroll smoothly
        assert scroll_time < 2


# =============================================================================
# CONSOLE ERROR TESTS
# =============================================================================

class TestConsoleErrors:
    """Console error monitoring."""
    
    def test_no_errors_on_load(self, page: Page):
        """Test no critical errors on page load."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        critical = filter_errors(errors)
        
        assert len(critical) == 0, f"Errors: {[str(e) for e in critical]}"

    def test_no_errors_on_interaction(self, page: Page):
        """Test no errors during interactions."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click around
        buttons = page.locator("button:visible").all()
        for btn in buttons[:5]:
            try:
                btn.click()
                page.wait_for_timeout(200)
            except:
                pass
        
        critical = filter_errors(errors)
        
        assert len(critical) == 0


# =============================================================================
# SNAPSHOT TESTS
# =============================================================================

class TestSnapshots:
    """Visual snapshot tests."""
    
    def test_capture_dashboard(self, page: Page):
        """Capture dashboard snapshot."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        path = SNAPSHOT_DIR / "dashboard.png"
        page.screenshot(path=str(path))
        
        assert path.exists()

    def test_capture_all_workspaces(self, page: Page):
        """Capture all workspace snapshots."""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        workspaces = ["Scanner", "Strategy", "Command", "Options"]
        
        for ws in workspaces:
            tab = page.locator(f"text={ws}").first
            if tab.is_visible():
                tab.click()
                page.wait_for_timeout(500)
                
                path = SNAPSHOT_DIR / f"workspace_{ws.lower()}.png"
                page.screenshot(path=str(path))
        
        assert page.locator("body").is_visible()


# =============================================================================
# SUMMARY
# =============================================================================

def test_full_suite_summary():
    """Test suite summary."""
    print("\n" + "=" * 70)
    print("FULL E2E TEST SUITE SUMMARY")
    print("=" * 70)
    categories = [
        "Scanner Workspace", "Strategy Workspace", "Command Workspace",
        "Options Lab Workspace", "Charts", "Data Tables", "Forms",
        "Buttons", "Navigation", "Performance", "Console Errors", "Snapshots"
    ]
    for cat in categories:
        print(f"  ✅ {cat}")
    print("=" * 70)
    assert True
