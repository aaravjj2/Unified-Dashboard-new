"""
A small Playwright-based clicker (synchronous) to exercise the Portfolio UI.
Run with the same venv where Playwright is installed.
"""
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8056/'
SCREEN_DIR = 'test_screenshots/clicker'

import os
os.makedirs(SCREEN_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.goto(URL, timeout=15000)
    page.wait_for_timeout(1500)
    page.screenshot(path=os.path.join(SCREEN_DIR, '01_landing.png'))

    # Click Portfolio tab if there is a tab with text 'Portfolio'
    try:
        page.locator("text=Portfolio").first.click(timeout=3000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREEN_DIR, '02_portfolio_tab.png'))
    except Exception:
        pass

    # Click Positions sub-tab if present
    try:
        page.locator("text=Positions").first.click(timeout=3000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREEN_DIR, '03_positions.png'))
    except Exception:
        pass

    # Click Inspect on first row if button exists
    try:
        page.locator("button:has-text('Inspect')").first.click(timeout=3000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREEN_DIR, '04_inspect_modal.png'))
    except Exception:
        pass

    browser.close()
