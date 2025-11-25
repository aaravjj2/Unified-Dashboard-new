"""
Modular TDD tests for Portfolio (Portfolio Tracker > Analytics subtab)

Includes:
- Snapshot test (saved image file)
- Clicker test (Run Monte Carlo Simulation -> results visible)
- Data integrity test (key analytics metrics not placeholders)
"""

from playwright.sync_api import Page
import pytest
import os

BASE_URL = "http://localhost:8050"


def _goto_portfolio_analytics(page: Page):
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    page.locator('text="Portfolio"').click()
    page.wait_for_timeout(1000)
    page.locator('text="Analytics"').first.click()
    page.wait_for_timeout(1000)


def test_portfolio_visual_layout(page: Page):
    """Visual Snapshot: Verify layout of Portfolio > Analytics subtab."""
    _goto_portfolio_analytics(page)
    os.makedirs("tests/__snapshots__", exist_ok=True)
    snap_path = "tests/__snapshots__/portfolio_analytics.png"
    page.screenshot(path=snap_path, full_page=True)
    assert os.path.exists(snap_path) and os.path.getsize(snap_path) > 50_000, "Snapshot not captured or too small"


def test_portfolio_monte_carlo_clicker(page: Page):
    """Clicker: Clicking Run Monte Carlo should render results container with content."""
    _goto_portfolio_analytics(page)
    # Click Monte Carlo
    btn = page.locator('button:has-text("Run Monte Carlo Simulation")')
    assert btn.count() > 0, "Monte Carlo button should be present"
    btn.click()
    page.wait_for_timeout(2500)
    # Results container should have some content (alert, chart, or text)
    results = page.locator('#monte-carlo-results')
    assert results.count() > 0, "Results container should exist"
    text = results.inner_text()
    assert text is not None and len(text.strip()) > 0, "Results container should not be empty"


def test_portfolio_analytics_data_integrity(page: Page):
    """Data Integrity: Verify core analytics values are present (not placeholders)."""
    _goto_portfolio_analytics(page)
    # Check that risk/analytics elements are rendered
    var_val = page.locator('#portfolio-var')
    sharpe_val = page.locator('#portfolio-sharpe')
    beta_val = page.locator('#portfolio-beta')
    assert var_val.count() > 0 and sharpe_val.count() > 0 and beta_val.count() > 0, "Analytics elements missing"
    # Basic placeholder avoidance
    assert 'N/A' not in var_val.inner_text(), "VaR shows placeholder"
    assert 'N/A' not in sharpe_val.inner_text(), "Sharpe shows placeholder"
    assert 'N/A' not in beta_val.inner_text(), "Beta shows placeholder"


def test_portfolio_calculate_analytics_results(page: Page):
    """Clicker: Calculate Analytics should reveal populated results container."""
    _goto_portfolio_analytics(page)

    calc_btn = page.locator('#pa-calc-btn')
    assert calc_btn.count() > 0, "Calculate Analytics button should exist"
    print("DEBUG", page.evaluate("(function(){var el=document.querySelector('#pa-calc-btn'); return el ? el.outerHTML : 'missing';})()"))
    print("DEBUG style", page.evaluate("(function(){var el=document.querySelector('#pa-calc-btn'); if(!el) return 'missing'; var cs=getComputedStyle(el); return JSON.stringify({display:cs.display, visibility:cs.visibility, opacity:cs.opacity, transform:cs.transform});})()"))
    print("DEBUG geom", page.evaluate("(function(){var el=document.querySelector('#pa-calc-btn'); if(!el) return 'missing'; var rect=el.getBoundingClientRect(); return JSON.stringify({width:rect.width,height:rect.height, top:rect.top,left:rect.left,offsetParent:!!el.offsetParent});})()"))
    print("DEBUG parent", page.evaluate("(function(){var el=document.querySelector('#pa-calc-btn'); if(!el || !el.parentElement) return 'missing'; return el.parentElement.outerHTML;})()"))
    print("DEBUG flag", page.evaluate("window.__paCalcResultsInjected || false"))
    calc_btn.first.click()
    page.wait_for_timeout(2500)

    results_container = page.locator('#pa-results-container')
    assert results_container.count() > 0, "Results container should be rendered after calculation"

    summary = page.locator('#pa-results-summary')
    assert summary.count() > 0, "Results summary text should be present"
    summary_text = summary.inner_text().strip()
    assert summary_text, "Results summary should not be empty"
    assert 'No analytics' not in summary_text, "Results summary should reflect calculated analytics"
"""Modular tests for Portfolio (to be populated in TDD loop)."""
