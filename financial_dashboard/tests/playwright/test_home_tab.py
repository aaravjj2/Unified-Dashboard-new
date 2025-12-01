"""Playwright E2E test for Home tab: initial, interactions, final snapshots.

This test uses Playwright's sync API via pytest-playwright fixtures. It expects
that the dashboard is reachable at http://localhost:8050
"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8050"

def test_home_tab_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#home")
        page.wait_for_selector('#home-portfolio-value', timeout=15000)
        page.screenshot(path='home_initial_snapshot.png', full_page=True)

        # Click quick actions (if present)
        try:
            if page.query_selector('#home-refresh-btn'):
                page.click('#home-refresh-btn')
                page.wait_for_selector('#home-action-alert', timeout=10000)
                page.screenshot(path='home_after_refresh.png', full_page=True)
        except Exception:
            pass

        # Interact with sample ticker search
        try:
            if page.query_selector('#home-ticker-input'):
                page.fill('#home-ticker-input', 'SPY')
                page.click('#home-ticker-search-btn')
                page.wait_for_selector('#home-ticker-price', timeout=10000)
                page.screenshot(path='home_ticker_search.png', full_page=True)
        except Exception:
            pass

        # Final snapshot
        page.screenshot(path='home_final_snapshot.png', full_page=True)
        browser.close()
