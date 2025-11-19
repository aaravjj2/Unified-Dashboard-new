"""Playwright test for Options tab snapshots"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

def test_options_tab_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#options")
        page.screenshot(path='options_initial.png', full_page=True)
        try:
            sel = page.query_selector('#options-strategy-select')
            if sel:
                page.select_option('#options-strategy-select', 'covered_call')
            run_btn = page.query_selector('#options-run-btn') or page.query_selector("button:has-text('Run')")
            if run_btn:
                run_btn.click()
                try:
                    page.wait_for_selector('#options-results', timeout=30000)
                except Exception:
                    pass
                page.screenshot(path='options_after_run.png', full_page=True)
        except Exception:
            pass
        page.screenshot(path='options_final.png', full_page=True)
        browser.close()
