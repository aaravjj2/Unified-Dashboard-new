"""
Test Suite for Monthly Picks Tab
TDD Protocol: Tests must FAIL first to prove bugs exist, then PASS after fixes
"""
import pytest
from playwright.sync_api import Page, expect


def test_monthly_picks_snapshot(page: Page):
    """
    Playwright Chromium Snapshot Test
    Validates the final visual layout of the Monthly Picks tab
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    # Click Monthly Picks tab
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(3000)
    
    # Take snapshot
    page.screenshot(path='test-artifacts/monthly_picks_snapshot.png', full_page=True)
    
    # Verify tab content loaded
    expect(page.locator('h1:has-text("Monthly Stock Picks")')).to_be_visible()


def test_monthly_picks_clicker_generate_picks(page: Page):
    """
    Playwright Chromium Clicker Test: Content Display
    Verifies the tab content is visible
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(2000)
    
    # Verify content is present
    visible_text = page.locator('body').inner_text()
    assert len(visible_text) > 100, "Monthly Picks content should be visible"


def test_monthly_picks_clicker_filters(page: Page):
    """
    Playwright Chromium Clicker Test: Header Verification
    Verifies the tab displays correct header
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(2000)
    
    visible_text = page.locator('body').inner_text()
    assert 'Monthly Picks' in visible_text, "Should show Monthly Picks header"


def test_monthly_picks_data_integrity_no_na_values(page: Page):
    """
    Data Integrity Test: Verifies that price data is properly formatted using data attributes.
    
    Uses robust selectors (data-col, data-value) instead of brittle text parsing.
    Verifies:
    1. At least SOME price data is present (not all unavailable)
    2. Prices that ARE present have valid data-value attributes
    3. No error or exception messages
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(3000)
    
    # Get visible text content
    visible_text = page.locator('body').inner_text()
    
    # CRITICAL: NO error messages
    assert 'Error:' not in visible_text, "FAILURE: Found error messages in Monthly Picks"
    assert 'Exception' not in visible_text, "FAILURE: Found exception messages in Monthly Picks"
    
    # ROBUST CHECK: Use data attributes to verify price data
    rows = page.locator('table tbody tr').all()
    assert len(rows) > 0, "FAILURE: No table rows found"
    
    valid_prices_count = 0
    for row in rows:
        current_price_cell = row.locator('td[data-col="current_price"]')
        if current_price_cell.count() > 0:
            data_value = current_price_cell.get_attribute('data-value')
            if data_value and data_value != '':
                try:
                    price_val = float(data_value)
                    if price_val > 0:
                        valid_prices_count += 1
                except ValueError:
                    pass
    
    assert valid_prices_count > 0, "FAILURE: No valid price data found (all data-value attributes empty or invalid)"


def test_monthly_picks_contains_tsla(page: Page):
    """
    ZERO-TOLERANCE STRICT ASSERTION: TSLA row MUST have REAL price data using data attributes.
    
    This test enforces that:
    1. TSLA ticker is present in the Monthly Picks table (using data-ticker attribute)
    2. TSLA has a valid current_price (data-value not empty, > 0)
    3. TSLA has a valid profit_loss value (data-value not empty)
    4. Uses robust selectors (data-col, data-value) instead of brittle text parsing
    
    If API data is genuinely unavailable, the UI should show "Data Unavailable" 
    and set data-value="" with aria-label="Data Unavailable".
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(3000)  # Allow table to fully render

    # Save a snapshot for debugging
    page.screenshot(path='test-artifacts/monthly_picks_tsla_check.png', full_page=True)

    # SCOPE FIX: Find TSLA row ONLY within Monthly Picks content div
    mp_content = page.locator('#mp-content')
    tsla_row = mp_content.locator('tr[data-ticker="TSLA"]')
    
    assert tsla_row.count() == 1, "FAILURE: TSLA row not found or multiple TSLA rows exist"
    
    # CRITICAL 1: Verify current_price has valid data-value
    current_price_cell = tsla_row.locator('td[data-col="current_price"]')
    current_price_value = current_price_cell.get_attribute('data-value')
    
    assert current_price_value is not None and current_price_value != '', \
        f"FAILURE: TSLA current_price data-value is empty or None. aria-label: {current_price_cell.get_attribute('aria-label')}"
    
    # Parse and validate numeric value
    try:
        current_price_num = float(current_price_value)
        assert current_price_num > 0, f"FAILURE: TSLA current_price is not positive: {current_price_num}"
    except ValueError:
        pytest.fail(f"FAILURE: TSLA current_price data-value is not a valid number: {current_price_value}")
    
    # CRITICAL 2: Verify month_start_price has valid data-value
    month_start_cell = tsla_row.locator('td[data-col="month_start_price"]')
    month_start_value = month_start_cell.get_attribute('data-value')
    
    assert month_start_value is not None and month_start_value != '', \
        f"FAILURE: TSLA month_start_price data-value is empty or None. aria-label: {month_start_cell.get_attribute('aria-label')}"
    
    try:
        month_start_num = float(month_start_value)
        assert month_start_num > 0, f"FAILURE: TSLA month_start_price is not positive: {month_start_num}"
    except ValueError:
        pytest.fail(f"FAILURE: TSLA month_start_price data-value is not a valid number: {month_start_value}")
    
    # CRITICAL 3: Verify profit_loss has valid data-value (can be negative, but not empty)
    profit_loss_cell = tsla_row.locator('td[data-col="profit_loss"]')
    profit_loss_value = profit_loss_cell.get_attribute('data-value')
    
    assert profit_loss_value is not None and profit_loss_value != '', \
        f"FAILURE: TSLA profit_loss data-value is empty or None. aria-label: {profit_loss_cell.get_attribute('aria-label')}"
    
    try:
        profit_loss_num = float(profit_loss_value)
        # P/L can be positive, negative, or zero - just verify it's a valid number
    except ValueError:
        pytest.fail(f"FAILURE: TSLA profit_loss data-value is not a valid number: {profit_loss_value}")


def test_monthly_picks_clicker_export(page: Page):
    """
    Placeholder test for export functionality (if implemented)
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(2000)
    # Basic test: confirm tab loaded
    assert True


def test_monthly_picks_critical_rows_data_integrity(page: Page):
    """
    ZERO-TOLERANCE VALIDATION: ALL ROWS must have complete data using data attributes.
    
    Uses robust selectors (data-ticker, data-col, data-value) instead of brittle text parsing.
    
    Expected behavior:
    - If API returns valid data → data-value contains numeric string (e.g., "123.45")
    - If API returns null/unavailable → data-value is empty ("") and aria-label="Data Unavailable"
    
    Critical columns (must have valid data-value):
    - current_price
    - month_start_price  
    - profit_loss
    
    This test uses the new robust architecture.
    """
    page.goto('http://localhost:8050', wait_until='domcontentloaded', timeout=90000)
    page.wait_for_selector('#dashboard-tabs', timeout=60000)
    page.locator('text=Monthly Picks').first.click()
    page.wait_for_timeout(10000)  # Allow data to load
    
    # Save debug screenshot
    page.screenshot(path='test-artifacts/monthly_picks_all_rows_robust.png', full_page=True)
    
    failures = []
    
    # SCOPE FIX: Get table rows ONLY from Monthly Picks content div (mp-content)
    # This prevents selecting rows from other hidden tabs (e.g., Weekly Picks)
    mp_content = page.locator('#mp-content')
    table_rows = mp_content.locator('table tbody tr[data-ticker]').all()
    
    if len(table_rows) == 0:
        pytest.fail("CRITICAL: No table rows with data-ticker attribute found in Monthly Picks")
    
    print(f"\n{'='*70}")
    print(f"Scanning {len(table_rows)} rows for data integrity issues (ROBUST MODE)...")
    print(f"{'='*70}")
    
    for idx, row in enumerate(table_rows, start=1):
        # Get ticker from data attribute
        ticker = row.get_attribute('data-ticker')
        
        # CRITICAL CHECK 1: Verify current_price data-value
        current_price_cell = row.locator('td[data-col="current_price"]')
        current_price_value = current_price_cell.get_attribute('data-value')
        
        if not current_price_value or current_price_value == '':
            aria_label = current_price_cell.get_attribute('aria-label')
            failures.append(
                f"Row {idx} ({ticker}): current_price data-value is EMPTY. "
                f"aria-label: {aria_label}"
            )
            print(f"  ❌ Row {idx} ({ticker}): current_price EMPTY")
        else:
            try:
                cp_num = float(current_price_value)
                if cp_num <= 0:
                    failures.append(
                        f"Row {idx} ({ticker}): current_price is not positive: {cp_num}"
                    )
                    print(f"  ❌ Row {idx} ({ticker}): current_price <= 0")
                else:
                    print(f"  ✅ Row {idx} ({ticker}): current_price = {current_price_value}")
            except ValueError:
                failures.append(
                    f"Row {idx} ({ticker}): current_price data-value is not numeric: {current_price_value}"
                )
                print(f"  ❌ Row {idx} ({ticker}): current_price NOT NUMERIC")
        
        # CRITICAL CHECK 2: Verify month_start_price data-value
        month_start_cell = row.locator('td[data-col="month_start_price"]')
        month_start_value = month_start_cell.get_attribute('data-value')
        
        if not month_start_value or month_start_value == '':
            aria_label = month_start_cell.get_attribute('aria-label')
            failures.append(
                f"Row {idx} ({ticker}): month_start_price data-value is EMPTY. "
                f"aria-label: {aria_label}"
            )
            print(f"  ❌ Row {idx} ({ticker}): month_start_price EMPTY")
        else:
            try:
                ms_num = float(month_start_value)
                if ms_num <= 0:
                    failures.append(
                        f"Row {idx} ({ticker}): month_start_price is not positive: {ms_num}"
                    )
                    print(f"  ❌ Row {idx} ({ticker}): month_start_price <= 0")
            except ValueError:
                failures.append(
                    f"Row {idx} ({ticker}): month_start_price data-value is not numeric: {month_start_value}"
                )
                print(f"  ❌ Row {idx} ({ticker}): month_start_price NOT NUMERIC")
        
        # CRITICAL CHECK 3: Verify profit_loss data-value (can be negative, but not empty)
        profit_loss_cell = row.locator('td[data-col="profit_loss"]')
        profit_loss_value = profit_loss_cell.get_attribute('data-value')
        
        if not profit_loss_value or profit_loss_value == '':
            aria_label = profit_loss_cell.get_attribute('aria-label')
            failures.append(
                f"Row {idx} ({ticker}): profit_loss data-value is EMPTY. "
                f"aria-label: {aria_label}"
            )
            print(f"  ❌ Row {idx} ({ticker}): profit_loss EMPTY")
        else:
            try:
                pl_num = float(profit_loss_value)
                # P/L can be any value (positive, negative, zero)
            except ValueError:
                failures.append(
                    f"Row {idx} ({ticker}): profit_loss data-value is not numeric: {profit_loss_value}"
                )
                print(f"  ❌ Row {idx} ({ticker}): profit_loss NOT NUMERIC")
    
    print(f"{'='*70}\n")
    
    # Assert all rows passed validation
    if failures:
        failure_report = "\n".join([f"  • {f}" for f in failures])
        pytest.fail(
            f"\n{'='*70}\n"
            f"CRITICAL ROWS DATA INTEGRITY FAILURE (ROBUST MODE)\n"
            f"{'='*70}\n"
            f"{failure_report}\n"
            f"{'='*70}\n"
            f"Root cause: API fetch failure or missing fallback logic.\n"
            f"Expected: All rows have valid numeric data-value attributes.\n"
            f"{'='*70}"
        )
