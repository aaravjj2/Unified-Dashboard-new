from playwright.sync_api import sync_playwright
import os


def test_navigation_bar_is_rendered_correctly():
    """Navigate to the app homepage and snapshot the main navigation bar element.

    This test intentionally uses a tolerant selector. Adjust HOME_URL if your app
    serves on a different host/port.
    """
    HOME_URL = os.environ.get("DASH_HOME_URL", "http://localhost:8050")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Use 'load' instead of 'networkidle' - dashboard has long-running connections
        page.goto(HOME_URL, wait_until="load", timeout=60000)

        # Attempt a few common nav selectors to find the main navigation bar
        selectors = [
            "nav",
            "#main-nav",
            ".navbar",
            "[data-testid=main-nav]",
            "header",
            ".dash-nav",
            ".nav-tabs",
            ".tab-btn",
        ]

        nav_handle = None
        for sel in selectors:
            try:
                handle = page.wait_for_selector(sel, timeout=2000)
                if handle:
                    nav_handle = handle
                    break
            except Exception:
                continue

        assert nav_handle is not None, f"Navigation bar not found using selectors: {selectors}"

        # Save a snapshot (Playwright's to_screenshot is used here)
        img_path = os.environ.get("NAV_SNAPSHOT_PATH", "navigation_snapshot.png")
        nav_handle.screenshot(path=img_path)

        # Basic sanity checks on nav HTML
        html = nav_handle.inner_html()
        assert "Duplicate" not in html, "Found 'Duplicate' placeholder text in navigation"

        browser.close()
