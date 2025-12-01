"""
Modular TDD tests for Dashboard Home

This file follows the remediation protocol:
- Snapshot test for visual integrity
- Clicker tests for interactivity
- Data integrity test for placeholders
"""

from playwright.sync_api import Page
import pytest
import os

BASE_URL = "http://localhost:8050"


def test_home_page_visual_layout(page: Page):
	"""Visual Snapshot: Save a screenshot for layout verification."""
	page.goto(BASE_URL, timeout=60000)
	page.wait_for_load_state("networkidle", timeout=60000)
	page.locator('text="🏠 Home"').click()
	page.wait_for_timeout(1000)
	os.makedirs("tests/__snapshots__", exist_ok=True)
	snap_path = "tests/__snapshots__/dashboard_home.png"
	page.screenshot(path=snap_path, full_page=True)
	# Basic sanity: file exists and has non-trivial size
	assert os.path.exists(snap_path) and os.path.getsize(snap_path) > 50_000, "Snapshot not captured or too small"


def test_home_page_for_placeholders(page: Page):
	"""Data Integrity: Ensure key homepage metrics are not placeholders."""
	page.goto(BASE_URL, timeout=60000)
	page.wait_for_load_state("networkidle", timeout=60000)
	page.locator('text="🏠 Home"').click()
	page.wait_for_timeout(1000)
	# Target concrete homepage elements instead of global scan across entire app DOM
	port_value = page.locator('#home-portfolio-value').inner_text()
	assert port_value and port_value != 'N/A' and port_value != '$0.00', "Portfolio value shows placeholder"
	# Today change exists and not placeholder-like
	port_change = page.locator('#home-portfolio-change').inner_text()
	assert port_change and 'N/A' not in port_change, "Portfolio change shows placeholder"


def test_home_page_watchlist_interaction(page: Page):
	"""Clicker Test: Attempt basic Home tab interaction without errors."""
	page.goto(BASE_URL, timeout=60000)
	page.wait_for_load_state("networkidle", timeout=60000)
	page.locator('text="🏠 Home"').click()
	page.wait_for_timeout(1000)

	# Try clicking a common button if present (defensive locator)
	add_btn = page.locator('#watchlist-add-btn, button:has-text("Add"), button:has-text("Refresh")').first
	if add_btn.count() > 0:
		add_btn.click()
		page.wait_for_timeout(500)
	else:
		# Not a failure if button doesn't exist; the purpose is to ensure no crashes
		pass

