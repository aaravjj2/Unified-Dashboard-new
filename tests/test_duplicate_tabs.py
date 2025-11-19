from playwright.sync_api import sync_playwright
import os


def test_duplicate_tab_names_are_not_present():
    """Fail if any tab button's visible text does not match a single expected tab name.

    Uses DASH_HOME_URL env var (default http://localhost:8050).
    """
    HOME_URL = os.environ.get("DASH_HOME_URL", "http://localhost:8050")
    expected = [
        "Market Trends",
        "Market Forecast",
        "Monthly Picks",
        "Weekly Picks",
        "Analysis Hub",
        "Portfolio",
        "Research Lab",
        # optional labs/extra buttons
        "Options Lab",
        "Backtesting Lab",
        "Volatility Lab",
        "Home",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Avoid waiting for 'networkidle' (some apps keep polling); navigate and then wait for the
        # dashboard tabs element which indicates the UI is ready for inspection.
        page.goto(HOME_URL, wait_until="load", timeout=60000)

        # Wait for top-level dashboard tabs to render and only select direct children
        page.wait_for_selector('#dashboard-tabs', timeout=15000)
        # Select only the direct top-level nav links under #dashboard-tabs
        buttons = page.query_selector_all('#dashboard-tabs > .nav-item .nav-link, #dashboard-tabs > li > a, #dashboard-tabs > a')
        # Fallback: any direct child link under #dashboard-tabs
        if not buttons:
            buttons = page.query_selector_all('#dashboard-tabs a, #dashboard-tabs button')

        assert buttons, "No tab buttons found under #dashboard-tabs"

        bad_buttons = []
        for b in buttons:
            text = b.inner_text().strip()
            # Normalize whitespace
            text = " ".join(text.split())
            # Strip leading emoji or decorative characters (e.g. '🏠 Home', '⚡ Volatility Lab')
            # Keep core text for matching against expected list
            import re
            m = re.match(r"^[^\w\d]*(.*)$", text)
            if m:
                text = m.group(1).strip()
            if text not in expected:
                bad_buttons.append((text, b))

        assert not bad_buttons, f"Found tab buttons with unexpected/duplicated text: {[t for t,_ in bad_buttons]}"

        browser.close()
