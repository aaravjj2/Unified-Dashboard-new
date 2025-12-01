"""Playwright test for Research tab snapshots"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

def test_research_tab_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#research")
        page.screenshot(path='research_initial.png', full_page=True)
        try:
            if page.query_selector('#research-search-input'):
                page.fill('#research-search-input', 'AAPL')
            run_btn = page.query_selector('#research-search-btn') or page.query_selector("button:has-text('Search')")
            if run_btn:
                run_btn.click()
                try:
                    page.wait_for_selector('#research-results', timeout=20000)
                except Exception:
                    pass
                page.screenshot(path='research_after_search.png', full_page=True)
        except Exception:
            pass
        page.screenshot(path='research_final.png', full_page=True)
        browser.close()
