"""Simple clicker for Home tab to exercise refresh/interactive controls and save snapshots.

This is intentionally tolerant: it will try multiple selector names (legacy and refactored
`hub-` prefixed) and fall back to JS clicks when needed. It is safe to run against a
local dev server at http://localhost:8050.
"""
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"


def find_and_click(page, selectors, timeout=5000):
    for sel in selectors:
        el = page.query_selector(sel)
        if not el:
            continue
        try:
            el.scroll_into_view_if_needed()
            el.click(timeout=timeout)
            print(f"Clicked selector: {sel}")
            return True
        except Exception as e:
            try:
                # JS fallback
                page.evaluate("(el) => el.click()", el)
                print(f"JS-clicked selector: {sel}")
                return True
            except Exception:
                print(f"Failed to click {sel}: {e}")
    return False


def run(url=None):
    url = url or f"{BASE_URL}/#home"
    print(f"Opening {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        # short wait for client helpers to register
        page.wait_for_timeout(1000)

        # Save initial snapshot
        page.screenshot(path='home_before.png', full_page=True)

        # Try known refresh / update controls (legacy and refactored)
        refresh_selectors = ['#home-refresh', '#hub-home-refresh', 'button#home-refresh', 'button#hub-home-refresh', "#refresh-home"]
        clicked = find_and_click(page, refresh_selectors)
        print("Clicked refresh button?", clicked)

        # Best-effort try to click a 'load portfolio' or similar control
        portfolio_selectors = ['#portfolio-value', '#home-portfolio-value', '#hub-portfolio-value']
        found = any(page.query_selector(s) for s in portfolio_selectors)
        print("Found portfolio value element?", found)

        page.wait_for_timeout(1500)
        page.screenshot(path='home_after.png', full_page=True)
        browser.close()


if __name__ == '__main__':
    run()
