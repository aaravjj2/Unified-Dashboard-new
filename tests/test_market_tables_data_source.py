"""
RED Phase Tests: Data Source Column in Market Tables
Mission: A1-FULL-TABLE-INTEGRITY-AND-DATA-SOURCE

Tests to verify:
1. Market Trends table has "Data Source" column header
2. All rows in Market Trends have non-empty data-col="data_source" values
3. Weekly Picks and Monthly Picks tables also have Data Source column

Expected: ALL TESTS FAIL initially (RED phase - column doesn't exist yet)
After fixes: ALL TESTS PASS (GREEN phase)

Run with: pytest tests/test_market_tables_data_source.py --browser chromium -v
"""

import pytest
from playwright.sync_api import Page


BASE_URL = "http://localhost:8050"


def test_market_trends_data_source_column_exists(page: Page):
    """
    Test that Market Trends table has a "Data Source" column header.
    
    RED: Expected to FAIL - column doesn't exist yet.
    GREEN: Should PASS when rightmost column "Data Source" is added.
    """
    page.goto(BASE_URL)
    page.wait_for_selector('a:has-text("Market Trends")', timeout=10000)
    
    # Navigate to Market Trends
    page.locator('a:has-text("Market Trends")').click()
    page.wait_for_selector('h3:has-text("Market Trends")', timeout=10000)
    print("📍 Market Trends page loaded")
    
    # Wait for table
    page.wait_for_timeout(3000)
    
    # Take screenshot
    page.screenshot(path='test-artifacts/market_trends_data_source_header_check.png', full_page=True)
    
    # Get table headers
    table = page.locator('table').first
    assert table.count() > 0, "FAILURE: No table found"
    
    headers = table.locator('thead th')
    header_count = headers.count()
    
    print(f"📊 Found {header_count} column headers")
    
    # Get all header texts
    header_texts = []
    for i in range(header_count):
        header_text = headers.nth(i).inner_text().strip()
        header_texts.append(header_text)
        print(f"  Column {i+1}: '{header_text}'")
    
    # Check for "Data Source" header (case-insensitive)
    data_source_found = any('data source' in h.lower() for h in header_texts)
    
    # Also check for data-col attribute on header
    data_source_header_attr = table.locator('th[data-col="data_source"]').count() > 0
    
    print(f"\n🔍 'Data Source' in header texts: {data_source_found}")
    print(f"🔍 th[data-col='data_source'] found: {data_source_header_attr}")
    
    # CRITICAL ASSERTION: Header must exist
    assert data_source_found or data_source_header_attr, (
        f"FAILURE: 'Data Source' column header not found.\n"
        f"Found {header_count} headers: {header_texts}\n"
        f"Expected: Rightmost column should be 'Data Source'\n"
        "Screenshot: test-artifacts/market_trends_data_source_header_check.png"
    )
    
    print("✅ SUCCESS: 'Data Source' column header exists")


def test_market_trends_data_source_has_values(page: Page):
    """
    Test that all rows in Market Trends have non-empty data_source values.
    
    RED: Expected to FAIL - column doesn't exist or has empty values.
    GREEN: Should PASS when all rows show provider (Finnhub/Alpaca/Yahoo/Local).
    """
    page.goto(BASE_URL)
    page.wait_for_selector('a:has-text("Market Trends")', timeout=10000)
    
    # Navigate to Market Trends
    page.locator('a:has-text("Market Trends")').click()
    page.wait_for_selector('h3:has-text("Market Trends")', timeout=10000)
    print("📍 Market Trends page loaded")
    
    # Wait for table
    page.wait_for_timeout(3000)
    
    # Take screenshot
    page.screenshot(path='test-artifacts/market_trends_data_source_values_check.png', full_page=True)
    
    table = page.locator('table').first
    rows = table.locator('tbody tr')
    row_count = rows.count()
    
    assert row_count > 0, "FAILURE: No table rows found"
    
    print(f"📊 Total rows: {row_count}")
    
    # Check each row for data_source
    rows_with_source = 0
    rows_without_source = []
    source_distribution = {}
    
    for i in range(row_count):
        row = rows.nth(i)
        ticker = row.get_attribute('data-ticker') or f"row_{i}"
        
        # Find data_source cell
        source_cell = row.locator('td[data-col="data_source"]').first
        
        if source_cell.count() > 0:
            data_value = source_cell.get_attribute('data-value')
            display_text = source_cell.inner_text().strip()
            
            # Check if data_value is non-empty
            if data_value and data_value.strip() != "":
                rows_with_source += 1
                
                # Track distribution
                source_distribution[data_value] = source_distribution.get(data_value, 0) + 1
                
                print(f"  ✓ {ticker}: {data_value} (display: '{display_text}')")
            else:
                rows_without_source.append(f"{ticker} (empty data-value, display: '{display_text}')")
                print(f"  ✗ {ticker}: Empty data-value, display='{display_text}'")
        else:
            rows_without_source.append(f"{ticker} (no data_source column)")
            print(f"  ✗ {ticker}: No data_source column found")
    
    coverage_pct = (rows_with_source / row_count * 100) if row_count > 0 else 0
    print(f"\n📈 Data Source Coverage: {rows_with_source}/{row_count} rows ({coverage_pct:.1f}%)")
    
    if source_distribution:
        print(f"\n📊 Source Distribution:")
        for source, count in sorted(source_distribution.items(), key=lambda x: -x[1]):
            pct = (count / row_count * 100)
            print(f"    {source}: {count} rows ({pct:.1f}%)")
    
    if rows_without_source:
        print(f"\n⚠️  Rows without data source ({len(rows_without_source)}):")
        for ticker_info in rows_without_source[:10]:
            print(f"    - {ticker_info}")
        if len(rows_without_source) > 10:
            print(f"    ... and {len(rows_without_source) - 10} more")
    
    # CRITICAL ASSERTION: At least 90% must have data source
    assert coverage_pct >= 90.0, (
        f"FAILURE: Data source coverage is {coverage_pct:.1f}%, expected ≥90%.\n"
        f"Rows with source: {rows_with_source}/{row_count}\n"
        f"Missing/empty: {len(rows_without_source)} rows\n"
        f"Sample missing: {rows_without_source[:5]}\n"
        f"Screenshot: test-artifacts/market_trends_data_source_values_check.png"
    )
    
    print(f"✅ SUCCESS: {coverage_pct:.1f}% data source coverage (≥90% required)")


def test_weekly_and_monthly_tables_have_data_source(page: Page):
    """
    Test that Weekly Picks and Monthly Picks tables also have Data Source column.
    
    RED: Expected to FAIL - column doesn't exist in these tables yet.
    GREEN: Should PASS when Data Source column added to all three tables.
    """
    page.goto(BASE_URL)
    
    results = {}
    
    # Check Weekly Picks
    print("\n📍 Checking Weekly Picks...")
    page.wait_for_selector('a:has-text("Weekly Picks")', timeout=10000)
    page.locator('a:has-text("Weekly Picks")').click()
    page.wait_for_selector('h3:has-text("Weekly Picks")', timeout=10000)
    page.wait_for_timeout(2000)
    
    page.screenshot(path='test-artifacts/weekly_picks_data_source_check.png', full_page=True)
    
    weekly_table = page.locator('table').first
    if weekly_table.count() > 0:
        # Check for data_source column
        weekly_has_column = weekly_table.locator('th[data-col="data_source"]').count() > 0
        weekly_header_text = any('data source' in weekly_table.locator('thead th').nth(i).inner_text().lower() 
                                   for i in range(weekly_table.locator('thead th').count()))
        
        results['Weekly Picks'] = weekly_has_column or weekly_header_text
        print(f"  Data Source column: {results['Weekly Picks']}")
    else:
        results['Weekly Picks'] = False
        print(f"  ⚠️  No table found")
    
    # Check Monthly Picks
    print("\n📍 Checking Monthly Picks...")
    page.wait_for_selector('a:has-text("Monthly Picks")', timeout=10000)
    page.locator('a:has-text("Monthly Picks")').click()
    page.wait_for_selector('h3:has-text("Monthly Picks")', timeout=10000)
    page.wait_for_timeout(2000)
    
    page.screenshot(path='test-artifacts/monthly_picks_data_source_check.png', full_page=True)
    
    monthly_table = page.locator('table').first
    if monthly_table.count() > 0:
        # Check for data_source column
        monthly_has_column = monthly_table.locator('th[data-col="data_source"]').count() > 0
        monthly_header_text = any('data source' in monthly_table.locator('thead th').nth(i).inner_text().lower() 
                                    for i in range(monthly_table.locator('thead th').count()))
        
        results['Monthly Picks'] = monthly_has_column or monthly_header_text
        print(f"  Data Source column: {results['Monthly Picks']}")
    else:
        results['Monthly Picks'] = False
        print(f"  ⚠️  No table found")
    
    print(f"\n📊 Data Source Column Status:")
    for tab, has_column in results.items():
        status = "✓" if has_column else "✗"
        print(f"    {status} {tab}: {has_column}")
    
    # CRITICAL ASSERTION: Both tables must have Data Source column
    missing_tables = [tab for tab, has_column in results.items() if not has_column]
    
    assert len(missing_tables) == 0, (
        f"FAILURE: {len(missing_tables)}/2 tables missing 'Data Source' column.\n"
        f"Missing from: {missing_tables}\n"
        f"Screenshots:\n"
        f"  - test-artifacts/weekly_picks_data_source_check.png\n"
        f"  - test-artifacts/monthly_picks_data_source_check.png"
    )
    
    print(f"✅ SUCCESS: All tables have 'Data Source' column")
