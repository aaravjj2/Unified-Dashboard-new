import os
import time
import pytest

# Focused Playwright snapshot test for Portfolio subtabs.
# It navigates to the dashboard, opens the Portfolio tab, finds subtab buttons
# within the Portfolio container, clicks each one (robust waits) and saves
# screenshots to test-artifacts/. Designed to be resilient to rendering timing.

BASE_URL = os.environ.get("DASH_URL", "http://localhost:8050")
OUT_DIR = "test-artifacts"


def _safe_text(el):
    try:
        return el.inner_text().strip()
    except Exception:
        return ""


def _safe_filename(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)[:80]


def test_portfolio_subtabs_snapshots(page):
    os.makedirs(OUT_DIR, exist_ok=True)

    # Open the dashboard
    page.goto(BASE_URL, timeout=60000)
    # give the app some time to render main layout
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)

    # Try to find and click the main Portfolio tab by visible text
    portfolio_tab = page.locator("text=Portfolio").first
    assert portfolio_tab.count() > 0, "Could not find a top-level 'Portfolio' tab on the page"
    portfolio_tab.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Save an overview screenshot
    page.screenshot(path=os.path.join(OUT_DIR, "portfolio_view.png"), full_page=True)

    # Heuristic: find tab-like buttons inside a container that contains the word 'Portfolio'
    selector = (
        "div:has-text('Portfolio') button,"
        "div:has-text('Portfolio') .tab-btn,"
        "div:has-text('Portfolio') [data-tab-id]"
    )
    locator = page.locator(selector)

    # Give additional time for dynamic tab buttons to appear
    page.wait_for_timeout(800)

    try:
        count = locator.count()
    except Exception:
        count = 0

    assert count > 0, f"No subtab buttons found inside Portfolio container (tried selector: {selector})"

    saved_any = False
    for i in range(count):
        el = locator.nth(i)
        # read label safely
        try:
            label = el.inner_text().strip()
        except Exception:
            label = f"subtab_{i}"

        short = _safe_filename(label or f"subtab_{i}") or f"subtab_{i}"
        filename = os.path.join(OUT_DIR, f"portfolio_subtab_{i}_{short}.png")

        # Click with retry and fallback to JS click if needed
        try:
            el.scroll_into_view_if_needed()
            el.click(timeout=10000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(700)
        except Exception:
            try:
                # fallback: evaluate click on element handle
                el.evaluate("el => el.click()")
                page.wait_for_timeout(700)
            except Exception:
                # if clicking fails, still take a screenshot of the current view
                pass

        # Save screenshot for this subtab
        try:
            page.screenshot(path=filename, full_page=True)
            saved_any = True
        except Exception:
            # ignore screenshot failures but continue
            pass

    assert saved_any, "No subtab screenshots were produced"
