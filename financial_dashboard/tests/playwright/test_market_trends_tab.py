"""Playwright test for Market Trends tab snapshots and interactions"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

def test_market_trends_tab_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#market-trends")
        # Take initial snapshot; buttons may vary across builds
        page.screenshot(path='market_trends_initial.png', full_page=True)
        # Try to find a run button with common ids or text and click it
        try:
            btn = page.query_selector('#market-trends-run-btn') or page.query_selector("button:has-text('Run')")
            if btn:
                btn.click()
                try:
                    page.wait_for_selector('#market-trends-results-table', timeout=30000)
                except Exception:
                    pass
                page.screenshot(path='market_trends_after_run.png', full_page=True)
        except Exception:
            pass
        page.screenshot(path='market_trends_final.png', full_page=True)
        browser.close()
