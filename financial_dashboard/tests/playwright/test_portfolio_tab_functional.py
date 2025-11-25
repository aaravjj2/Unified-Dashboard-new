"""Functional Playwright test: assert Portfolio Analytics calculate button works.
This test is intentionally strict and will fail if the UI element is missing or the
calculation does not render the expected result element.
"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"


def test_portfolio_calc_functional():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#portfolio")
        # Ensure the portfolio area loads
        page.wait_for_selector('#portfolio-root', timeout=20000)

        # Try to activate Portfolio Analytics tab if helper exists
        try:
            page.evaluate("(t) => window.selectDashboardTab ? window.selectDashboardTab(t) : false", 'Portfolio Analytics')
        except Exception:
            pass

        # Require the calculate button to be present and visible
        assert page.query_selector('#pa-calc-btn') is not None, "pa-calc-btn not present in DOM"
        page.wait_for_selector('#pa-calc-btn', state='visible', timeout=15000)

        # Click and assert result chart appears
        page.click('#pa-calc-btn')
        # The app should render a performance chart container after calculation
        page.wait_for_selector('#pa-performance-chart', timeout=20000)
        assert page.query_selector('#pa-performance-chart') is not None, 'pa-performance-chart not found after clicking calculate'

        browser.close()
