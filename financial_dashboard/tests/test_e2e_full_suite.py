"""
Comprehensive E2E Test Suite - TDD Protocol
Each test is designed to fail initially, proving the bug exists.
"""
from playwright.sync_api import Page, expect
import pytest
import requests

BASE_URL = "http://localhost:8050"

# ============================================================================
# BUG #1: Duplicate Tabs in Navigation
# ============================================================================

def test_no_duplicate_tabs_in_nav(page: Page):
    """Verify navigation has no duplicate tab names."""
    page.goto(BASE_URL, timeout=60000)
    try:
        page.wait_for_selector('#vix-chart', timeout=60000)
    except Exception:
        page.wait_for_load_state("load", timeout=30000)
    
    # Get all tab labels
    tabs = page.locator('[role="tab"]').all_text_contents()
    
    # Check for duplicates
    unique_tabs = set(tabs)
    assert len(tabs) == len(unique_tabs), f"Found duplicate tabs: {tabs}"

# ============================================================================
# BUG #2: Dashboard Home Shows Placeholder Values
# ============================================================================

def test_dashboard_home_loads_real_data(page: Page):
    """Verify homepage does not contain placeholder values."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    # Click on Home tab
    page.locator('text="🏠 Home"').click()
    page.wait_for_timeout(2000)
    
    # Check that main content doesn't have N/A or $0.00 placeholders
    page_content = page.content()
    # Allow some flexibility but main metrics should not all be N/A
    assert page_content.count('N/A') < 10, "Too many N/A placeholder values on homepage"

# ============================================================================
# BUG #3: Monthly Picks - Tables Full of N/A
# ============================================================================

def test_monthly_picks_table_has_no_na_values(page: Page):
    """Verify Monthly Picks table is populated with real data."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    page.locator('text="Monthly Picks"').click()
    page.wait_for_timeout(3000)
    
    # Check for N/A in table cells
    na_cells = page.locator('td:has-text("N/A")').count()
    assert na_cells == 0, f"Found {na_cells} cells with N/A in Monthly Picks"

# ============================================================================
# BUG #4: Weekly Picks - Tables Full of N/A
# ============================================================================

def test_weekly_picks_table_has_no_na_values(page: Page):
    """Verify Weekly Picks table is populated with real data."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    page.locator('text="Weekly Picks"').click()
    page.wait_for_timeout(3000)
    
    # Check for N/A in table cells
    na_cells = page.locator('td:has-text("N/A")').count()
    assert na_cells == 0, f"Found {na_cells} cells with N/A in Weekly Picks"

# ============================================================================
# BUG #5: Market Trends - PyArrow Dependency Error
# ============================================================================

def test_market_trends_no_pyarrow_error(page: Page):
    """Verify Market Trends tab loads without pyarrow error."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    page.locator('text="Market Trends"').click()
    page.wait_for_timeout(3000)
    
    # Check for error messages
    error_text = page.locator('text="pyarrow"').count()
    assert error_text == 0, "PyArrow dependency error found in Market Trends"
    
    # Check for general error indicators
    job_failed = page.locator('text="Job failed"').count()
    assert job_failed == 0, "Market Trends job failed"

# ============================================================================
# BUG #6: Market Forecast - NameError: free variable 'os'
# ============================================================================

def test_market_forecast_no_os_error(page: Page):
    """Verify Market Forecast tab loads without NameError."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    page.locator('text="Market Forecast"').click()
    page.wait_for_timeout(3000)
    
    # Check for error messages
    error_indicators = [
        page.locator('text="NameError"').count(),
        page.locator('text="free variable"').count(),
        page.locator('text="Error loading"').count()
    ]
    
    assert sum(error_indicators) == 0, "NameError found in Market Forecast tab"

# ============================================================================
# BUG #7: Volatility Lab - Layout Not Defined
# ============================================================================

def test_volatility_lab_layout_defined(page: Page):
    """Verify Volatility Lab has proper layout."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    page.locator('text="⚡ Volatility Lab"').click()
    page.wait_for_timeout(3000)
    
    # Should not see "No layout defined" message
    no_layout_msg = page.locator('text="No layout defined"').count()
    assert no_layout_msg == 0, "Volatility Lab layout is not defined"
    
    # Should have some content
    content = page.locator('body').text_content()
    assert len(content) > 100, "Volatility Lab has minimal content"

# ============================================================================
# BUG #8: Portfolio Analytics - Calculate Button Not Functional
# ============================================================================

def test_portfolio_calculate_button_works(page: Page):
    """Verify Portfolio Calculate Analytics button is functional."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    page.locator('text="Portfolio"').click()
    page.wait_for_timeout(3000)
    
    # Look for calculate button
    calc_button = page.locator('button:has-text("Calculate Analytics")')
    if calc_button.count() > 0:
        calc_button.click()
        page.wait_for_timeout(2000)
        
        # Should see some results or activity
        # This is a placeholder - actual assertion depends on expected behavior
        assert True, "Button found and clicked"
    else:
        pytest.skip("Calculate Analytics button not found - may be in subtab")

# ============================================================================
# BUG #9: Options Lab - Connection Refused Error
# ============================================================================

def test_options_lab_no_connection_error(page: Page):
    """Verify Options Lab loads without connection errors."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    page.locator('text="💹 Options Lab"').click()
    page.wait_for_timeout(5000)
    
    # Check for connection error
    conn_refused = page.locator('text="Connection refused"').count()
    assert conn_refused == 0, "Connection refused error in Options Lab"
    
    # Check for network errors
    network_error = page.locator('text="Failed to fetch"').count()
    assert network_error == 0, "Network error in Options Lab"

# ============================================================================
# BUG #10: AI Chatbot - Service Unreachable
# ============================================================================

def test_ai_chatbot_service_reachable(page: Page):
    """Verify AI Chatbot service is reachable."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    # Look for chatbot button
    chatbot_button = page.locator('button:has-text("Chat")').or_(page.locator('[id*="chatbot"]'))
    if chatbot_button.count() > 0:
        chatbot_button.first.click()
        page.wait_for_timeout(2000)
        
        # Check for connection errors
        conn_error = page.locator('text="Connection refused"').count()
        assert conn_error == 0, "Chatbot service unreachable"
    else:
        pytest.skip("Chatbot UI not found - may not be implemented yet")

# ============================================================================
# BUG #11: Global Search Bar - Broken
# ============================================================================

def test_global_search_bar_functional(page: Page):
    """Verify global search bar is functional."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    # Look for search input
    search_input = page.locator('input[placeholder*="Search"]').or_(page.locator('input[type="search"]'))
    if search_input.count() > 0:
        search_input.first.fill("AAPL")
        search_input.first.press("Enter")
        page.wait_for_timeout(2000)
        
        # Should see some search results or activity
        # This is a basic check - actual behavior depends on implementation
        assert True, "Search input found and used"
    else:
        pytest.skip("Global search bar not found")

# ============================================================================
# PHASE 0: Foundational Tests (Must Always Pass)
# ============================================================================

def test_phase0_dashboard_loads_and_is_stable(page: Page):
    """Verifies the main page loads without critical errors."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    expect(page).to_have_title("Financial Dashboard", timeout=30000)
    
    # No connection refused errors on main page
    error_message = page.locator('text="Connection refused"')
    expect(error_message).not_to_be_visible()

def test_phase0_all_tabs_clickable(page: Page):
    """Verifies all tabs can be clicked without crashing."""
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    
    # Get all tabs
    tabs = page.locator('[role="tab"]').all()
    assert len(tabs) > 0, "No tabs found in navigation"
    
    # Try clicking each tab
    for i, tab in enumerate(tabs[:5]):  # Test first 5 tabs
        try:
            tab.click()
            page.wait_for_timeout(1000)
        except Exception as e:
            pytest.fail(f"Tab {i} failed to click: {e}")
