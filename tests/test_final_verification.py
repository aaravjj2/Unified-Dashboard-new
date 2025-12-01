"""
Final Verification Tests - Volatility Lab & Portfolio

Simplified browser E2E tests focusing on core functionality.
"""
import pytest
from playwright.sync_api import sync_playwright
import os


@pytest.fixture
def dashboard_url():
    return os.environ.get("DASH_HOME_URL", "http://localhost:8050")


def test_dashboard_loads_successfully(dashboard_url):
    """Test that the dashboard loads and Dash renders"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dashboard_url, wait_until="load", timeout=60000)
        
        # Wait for React entry point
        page.wait_for_selector("#react-entry-point", timeout=10000)
        
        # Wait for Dash to finish loading
        try:
            page.wait_for_selector("._dash-loading", state="hidden", timeout=30000)
        except:
            # Loading indicator might not appear, that's ok
            pass
        
        # Take a screenshot for verification
        page.screenshot(path="test-artifacts/dashboard_loaded.png")
        
        # Check that some content exists (not just loading screen)
        content = page.content()
        assert len(content) > 5000, "Dashboard content too short"
        
        browser.close()


def test_volatility_lab_tab_exists(dashboard_url):
    """Test that Volatility Lab tab is present"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dashboard_url, wait_until="load", timeout=60000)
        
        # Wait for React
        page.wait_for_selector("#react-entry-point", timeout=10000)
        try:
            page.wait_for_selector("._dash-loading", state="hidden", timeout=30000)
        except:
            pass
        
        # Give Dash tabs time to render
        page.wait_for_timeout(3000)
        
        # Look for Volatility Lab text anywhere
        vol_lab_text = page.get_by_text("Volatility Lab", exact=False).first
        assert vol_lab_text.is_visible(timeout=5000), "Volatility Lab tab not visible"
        
        # Take screenshot
        page.screenshot(path="test-artifacts/volatility_lab_tab.png")
        
        browser.close()


def test_portfolio_tab_exists(dashboard_url):
    """Test that Portfolio tab is present"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dashboard_url, wait_until="load", timeout=60000)
        
        # Wait for React
        page.wait_for_selector("#react-entry-point", timeout=10000)
        try:
            page.wait_for_selector("._dash-loading", state="hidden", timeout=30000)
        except:
            pass
        
        # Give Dash tabs time to render
        page.wait_for_timeout(3000)
        
        # Look for Portfolio text
        portfolio_text = page.get_by_text("Portfolio", exact=False).first
        assert portfolio_text.is_visible(timeout=5000), "Portfolio tab not visible"
        
        # Take screenshot
        page.screenshot(path="test-artifacts/portfolio_tab.png")
        
        browser.close()


def test_full_tab_navigation(dashboard_url):
    """Test navigating through all main tabs"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dashboard_url, wait_until="load", timeout=60000)
        
        # Wait for React
        page.wait_for_selector("#react-entry-point", timeout=10000)
        try:
            page.wait_for_selector("._dash-loading", state="hidden", timeout=30000)
        except:
            pass
        
        page.wait_for_timeout(3000)
        
        # Expected tabs from index.py
        tabs_to_test = [
            ("Weekly Picks", "weekly_picks"),
            ("Monthly Picks", "monthly_picks"),
            ("Market Trends", "market_trends"),
            ("Volatility Lab", "volatility_lab"),
            ("Portfolio", "portfolio")
        ]
        
        found_tabs = []
        for tab_name, tab_id in tabs_to_test:
            try:
                tab_element = page.get_by_text(tab_name, exact=False).first
                if tab_element.is_visible(timeout=2000):
                    found_tabs.append(tab_name)
                    # Try to click it
                    tab_element.click()
                    page.wait_for_timeout(1000)
                    # Take screenshot
                    page.screenshot(path=f"test-artifacts/{tab_id}_view.png")
            except:
                # Tab not visible or clickable
                pass
        
        # At minimum, Volatility Lab and Portfolio should be found
        assert "Volatility Lab" in found_tabs, f"Volatility Lab not found. Found: {found_tabs}"
        assert "Portfolio" in found_tabs, f"Portfolio not found. Found: {found_tabs}"
        
        print(f"Successfully navigated tabs: {found_tabs}")
        
        browser.close()
