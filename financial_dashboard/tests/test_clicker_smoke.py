"""Playwright clicker smoke tests (separate, minimal file).

Created to avoid the corrupted large test file while we fix it.
"""

import os

import pytest
from playwright.sync_api import Page

# Allow CI to point at the dockerized Dash app (usually on :8050) while keeping
# the legacy 8000 default for local dev runs.
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000")
NAV_WAIT = "domcontentloaded"

TAB_PRIMARY = [
    '#mp-refresh-btn',
    '#mf-run',
    '#mp-refresh-btn',
    '#wp-refresh-btn',
    '#hub-attr-run-button',
    '#portfolio-refresh-btn',
    '#exp-run-btn',
    '#opt-get-chain-btn',
]


def click_tab_by_index(page: Page, idx: int) -> bool:
    try:
        page.wait_for_selector('#dashboard-tabs', timeout=3000)
        loc = page.locator("#dashboard-tabs a, #dashboard-tabs button")
        if loc.count() <= idx:
            return False
        loc.nth(idx).click()
        return True
    except Exception:
        return False


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    page.close()
    context.close()


def test_tab_clicks_simple(page: Page):
    page.goto(DASHBOARD_URL, wait_until=NAV_WAIT)
    for i in range(4):
        assert click_tab_by_index(page, i), f"Could not click tab {i}"
        page.wait_for_timeout(200)


def test_tabs_have_primary_controls(page: Page):
    page.goto(DASHBOARD_URL, wait_until=NAV_WAIT)
    for idx, sel in enumerate(TAB_PRIMARY):
        assert click_tab_by_index(page, idx), f"Could not click tab {idx}"
        page.wait_for_timeout(500)
        assert page.query_selector(sel) is not None, f"Missing selector {sel} for tab {idx}"
