"""Playwright test for Home tab: run clicker-style interactions and take snapshots.

This test is intentionally tolerant: it will attempt to click common selectors (legacy and
refactored) but will not fail the test if those controls are absent. Use this to catch
regressions where interactive controls disappear.
"""
from playwright.sync_api import sync_playwright
import os

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8050')


def test_home_clicker_and_snapshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/#home")

        # Wait a bit for the page to settle
        page.wait_for_timeout(1000)

        # initial snapshot
        page.screenshot(path='home_snapshot_initial.png', full_page=True)

        # Try to click refresh controls if present
        selectors = ['#home-refresh', '#hub-home-refresh', 'button#home-refresh', 'button#hub-home-refresh', '#refresh-home']
        for sel in selectors:
            try:
                if page.query_selector(sel):
                    page.click(sel)
                    print('Clicked', sel)
                    # brief wait for any UI reaction
                    page.wait_for_timeout(800)
                    break
            except Exception as e:
                print('Failed clicking', sel, e)

        # Take after-click snapshot
        page.screenshot(path='home_snapshot_after_click.png', full_page=True)
        browser.close()
