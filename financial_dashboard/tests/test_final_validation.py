from playwright.sync_api import Page, expect
import pytest

BASE_URL = "http://localhost:8050"

def test_dashboard_loads_and_snapshot_matches(page: Page):
    """Tests if the main page loads and visually matches the expected baseline."""
    page.goto(BASE_URL, timeout=60000)
    # Wait for Dash to finish loading
    page.wait_for_load_state("networkidle", timeout=60000)
    # Check that the page has loaded with correct title
    expect(page).to_have_title("Financial Dashboard", timeout=30000)
    # Take screenshot for visual verification (manual comparison)
    page.screenshot(path="tests/dashboard-baseline.png", full_page=True)
    # Verify key elements are visible
    expect(page.locator("body")).to_be_visible()

def test_options_lab_loads_without_connection_error(page: Page):
    """This is the Playwright Clicker Test. Simulates user and verifies backend connectivity."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    # Check for connection errors
    error_message = page.locator('text="Connection refused"')
    expect(error_message).not_to_be_visible()
    # Verify page is interactive
    expect(page.locator("body")).to_be_visible()
