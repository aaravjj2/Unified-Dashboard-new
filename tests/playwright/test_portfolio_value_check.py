import os
import re
import pytest

BASE_URL = os.environ.get("DASH_URL", "http://localhost:8050")
OUT_DIR = "test-artifacts"


def _parse_currency(s: str) -> float:
    if not s:
        return 0.0
    # Remove currency symbols, commas and non-numeric
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(cleaned)
    except Exception:
        return 0.0


def test_portfolio_value_is_positive_and_reasonable(page):
    os.makedirs(OUT_DIR, exist_ok=True)

    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Click the top-level Portfolio tab (by visible text)
    portfolio_tab = page.locator("text=Portfolio").first
    assert portfolio_tab.count() > 0, "Top-level Portfolio tab not found"
    portfolio_tab.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)

    # Wait for the portfolio value element to appear and be non-empty
    val_locator = page.locator("#portfolio-value")
    val_locator.wait_for(state="visible", timeout=15000)

    raw = val_locator.inner_text().strip()
    # Save screenshot for evidence
    filename = os.path.join(OUT_DIR, "portfolio_value_check.png")
    page.screenshot(path=filename, full_page=True)

    value = _parse_currency(raw)
    print(f"Portfolio value raw text: '{raw}' -> parsed: {value}")

    assert value > 0, f"Portfolio value not positive: {value}"
    # Optional sanity bound check: expect reasonable account (e.g., 5k-500k)
    assert 5000 <= value <= 500000, f"Portfolio value {value} outside expected sanity bounds"
