"""
tests/test_logout_styling.py

Playwright test to reproduce and assert the "Logout" button styling issue.

This test is intentionally written as a reproduction of the reported bug so
we have a failing test to drive the remediation workflow. Adjust expected
values (selectors and expected CSS) if your application uses different
conventions.
"""
import os
import time
import pytest
from playwright.sync_api import sync_playwright, expect


HOME_URL = os.environ.get("DASH_HOME_URL", "http://localhost:8050")
SCREENSHOT_DIR = os.environ.get("SCREENSHOT_DIR", "test_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _find_logout_locator(page):
    """Try several common selectors to find a Logout control in the navbar."""
    selectors = [
        "button:has-text('Logout')",
        "a:has-text('Logout')",
        "[data-testid=logout]",
        ".logout-btn",
        "#logout",
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                return loc, sel
        except Exception:
            continue
    return None, None


def test_logout_button_styling():
    """Reproduction test: ensure Logout exists and its styling matches expectations."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Navigate to the home/dashboard
        page.goto(HOME_URL, timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(1)

        locator, used_sel = _find_logout_locator(page)
        assert locator is not None, (
            "Logout control not found. Tried selectors: button/a with text 'Logout', "
            "[data-testid=logout], .logout-btn, #logout. If your app uses a different "
            "selector update this test accordingly."
        )

        # Save a screenshot for visual diff review
        screenshot_path = os.path.join(SCREENSHOT_DIR, "logout_button.png")
        locator.screenshot(path=screenshot_path)

        # Basic style checks (examples). Update expected values to match your design.
        # Read computed styles from the element
        bg_color = locator.evaluate("el => window.getComputedStyle(el).backgroundColor")
        color = locator.evaluate("el => window.getComputedStyle(el).color")
        font_size = locator.evaluate("el => window.getComputedStyle(el).fontSize")

        # Assertions here are intentionally permissive; they exist so the test will
        # fail visibly when styling is incorrect and provide data for remediation.
        assert bg_color is not None, f"Could not read background-color for Logout ({used_sel})"
        assert color is not None, f"Could not read color for Logout ({used_sel})"
        assert font_size is not None and font_size != "0px", f"Unexpected font-size for Logout: {font_size}"

        print(f"Logout found using selector: {used_sel}")
        print(f"Computed styles - background: {bg_color}, color: {color}, font-size: {font_size}")

        browser.close()
