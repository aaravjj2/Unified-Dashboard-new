"""Playwright test for Portfolio tab snapshots and interactions"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

def test_portfolio_tab_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#portfolio")
        # Wait for either the portfolio value to appear or the analytics chart
        # Take an initial snapshot; elements may be $0.00 in dev without Alpaca keys
        page.screenshot(path='portfolio_initial_snapshot.png', full_page=True)
        # Click analytics calc button if present, but don't fail if it's missing
        try:
            if page.query_selector('#pa-calc-btn'):
                page.click('#pa-calc-btn')
                # best-effort wait for outcome
                try:
                    page.wait_for_selector('#pa-performance-chart', timeout=10000)
                except Exception:
                    pass
                page.screenshot(path='portfolio_after_calc.png', full_page=True)
        except Exception:
            pass
        page.screenshot(path='portfolio_final_snapshot.png', full_page=True)
        browser.close()
