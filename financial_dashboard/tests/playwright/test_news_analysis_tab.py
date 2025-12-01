"""Playwright test for News Analysis tab snapshots"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

def test_news_analysis_tab_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#news-analysis")
        page.screenshot(path='news_initial.png', full_page=True)
        try:
            # try common input or button selectors
            if page.query_selector('#news-keywords-input'):
                page.fill('#news-keywords-input', 'AI')
            run_btn = page.query_selector('#news-run-btn') or page.query_selector("button:has-text('Run')")
            if run_btn:
                run_btn.click()
                try:
                    page.wait_for_selector('#news-results', timeout=20000)
                except Exception:
                    pass
                page.screenshot(path='news_after_run.png', full_page=True)
        except Exception:
            pass
        page.screenshot(path='news_final.png', full_page=True)
        browser.close()
