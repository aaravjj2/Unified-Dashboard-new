"""Playwright test for Backtester tab snapshots"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

def test_backtester_tab_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#backtester")
        page.screenshot(path='backtester_initial.png', full_page=True)
        try:
            btn = page.query_selector('#backtester-run-btn') or page.query_selector("button:has-text('Run')")
            if btn:
                btn.click()
                try:
                    page.wait_for_selector('#backtester-results', timeout=60000)
                except Exception:
                    pass
                page.screenshot(path='backtester_after_run.png', full_page=True)
        except Exception:
            pass
        page.screenshot(path='backtester_final.png', full_page=True)
        browser.close()
