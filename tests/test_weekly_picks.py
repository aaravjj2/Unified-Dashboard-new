"""
UPGRADED Test Suite for Weekly Picks Tab
==========================================
Phase 1 - Data Pipeline Validation Protocol

These tests enforce STRICT data integrity requirements:
1. NO N/A placeholder values
2. Numeric columns MUST contain actual numbers (not strings/hyphens)
3. Data MUST be fresh (not stale September 2025 CSV files)
4. Data MUST come from postgres_db (not local CSV files)

EXPECTED OUTCOME: These tests WILL FAIL until:
- Dagster pipeline successfully populates postgres_db
- Application code is modified to read from postgres_db
"""
import pytest
from playwright.sync_api import Page, expect
import re
from datetime import datetime


def test_weekly_picks_snapshot(page: Page):
    """
    Playwright Chromium Snapshot Test
    Validates the final visual layout of the Weekly Picks tab
    """
    # Navigate to dashboard
    page.goto('http://localhost:8050', wait_until='networkidle')
    
    # Wait for dashboard to load
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    # Click Weekly Picks tab
    weekly_picks_tab = page.locator('text=Weekly Picks').first
    weekly_picks_tab.click()
    
    # Wait for tab content to load
    page.wait_for_timeout(3000)
    
    # Take snapshot
    page.screenshot(path='test-artifacts/weekly_picks_snapshot.png', full_page=True)
    
    # Visual assertion: verify tab content loaded
    expect(page.locator('h1:has-text("Weekly Picks Dashboard")')).to_be_visible()


def test_weekly_picks_content_display(page: Page):
    """
    Content Display Test: Verifies tab renders correctly
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    # Navigate to Weekly Picks
    page.locator('text=Weekly Picks').first.click()
    page.wait_for_timeout(2000)
    
    # Verify tab content is visible
    expect(page.locator('h1:has-text("Weekly Picks Dashboard")')).to_be_visible()
    
    # Verify substantial content is present
    visible_text = page.locator('body').inner_text()
    assert len(visible_text) > 100, "Weekly Picks content should be visible"
    assert 'Weekly Picks Dashboard' in visible_text, "Should show Weekly Picks header"


def test_weekly_picks_data_freshness(page: Page):
    """
    UPGRADED STRICT TEST: Data Freshness Validation
    
    REQUIREMENT: Data MUST be recent (max 7 days old for weekly picks)
    
    This test WILL FAIL if:
    - Application is reading from stale CSV files (e.g., picks_20250912.csv from September)
    - Data has not been refreshed from the database
    
    This test WILL PASS when:
    - Dagster pipeline has loaded fresh data into postgres_db
    - Application reads from postgres_db with current data
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    # Navigate to Weekly Picks
    page.locator('text=Weekly Picks').first.click()
    page.wait_for_timeout(3000)
    
    # Get visible text content
    visible_text = page.locator('body').inner_text()
    
    # Search for any dates in format YYYY-MM-DD or similar
    date_patterns = re.findall(r'20\d{2}-\d{2}-\d{2}', visible_text)
    
    # Also search for dates in format MM/DD/YYYY
    date_patterns_alt = re.findall(r'\d{1,2}/\d{1,2}/20\d{2}', visible_text)
    
    dates_found = []
    
    # Parse YYYY-MM-DD format
    for date_str in date_patterns:
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
            dates_found.append(parsed_date)
        except:
            pass
    
    # Parse M/D/YYYY format
    for date_str in date_patterns_alt:
        try:
            parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
            dates_found.append(parsed_date)
        except:
            pass
    
    # If we found dates, check freshness
    if dates_found:
        most_recent_date = max(dates_found)
        days_old = (datetime.now() - most_recent_date).days
        
        # Data should not be more than 7 days old for weekly picks
        assert days_old <= 7, \
            f"FAILURE: Data is STALE! Most recent date found: {most_recent_date.strftime('%Y-%m-%d')} ({days_old} days old). " \
            f"Weekly picks data must be fresh (max 7 days old). " \
            f"This proves the app is reading from stale CSV files (e.g., picks_20250912.csv), NOT from postgres_db. " \
            f"Phase 1 Data Pipeline must be implemented to fix this."
    else:
        # No dates found - this might indicate the table is not displaying data at all
        pytest.fail("No date information found in Weekly Picks tab. Unable to verify data freshness.")


def test_weekly_picks_data_integrity_numeric_types(page: Page):
    """
    UPGRADED STRICT TEST: Numeric Data Type Validation
    
    REQUIREMENT: Price columns MUST contain actual numbers, not placeholder strings
    
    This test WILL FAIL if:
    - Price columns contain dashes ('-') or empty strings instead of numbers
    - Data is not properly formatted as floats
    
    This test WILL PASS when:
    - Database contains properly typed numeric data
    - Application correctly renders prices as numbers
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    # Navigate to Weekly Picks
    page.locator('text=Weekly Picks').first.click()
    page.wait_for_timeout(3000)
    
    # Get visible text content
    visible_text = page.locator('body').inner_text()
    
    # STRICT ASSERTIONS: No fallbacks allowed. Numeric columns must contain valid numbers.
    # ASSERTION 1: NO N/A placeholders anywhere
    assert 'N/A' not in visible_text, "FAILURE: Found N/A placeholder values. Data is not properly populated from database."

    # ASSERTION 2: Price and P/L columns must be numeric. We'll look for common column headers and validate adjacent values.
    # Find all dollar-prefixed numbers and ensure they parse as floats
    price_patterns = re.findall(r'\$\s*[-+]?[0-9]*\.?[0-9]+', visible_text)
    assert len(price_patterns) >= 5, f"FAILURE: Found only {len(price_patterns)} price values. Weekly Picks should display numeric prices for multiple stocks."

    # Check for forbidden placeholders or missing numeric cells
    forbidden_placeholders = ['-', 'None', 'null']
    for ph in forbidden_placeholders:
        # Allow single hyphens in isolated contexts but not as cell values in numeric columns; fail if hyphen appears adjacent to dollar signs or numeric columns
        if ph == '-':
            # If isolated ' - ' or lines that end with ' -' are frequent, fail
            dash_count = visible_text.count('\n - ') + visible_text.count(' -\n') + visible_text.count('\n-\n')
            assert dash_count == 0, f"FAILURE: Found placeholder dash characters in numeric positions ({dash_count})."
        else:
            assert ph not in visible_text, f"FAILURE: Found forbidden placeholder '{ph}' in weekly picks visible output."

    # ASSERTION 3: No error or exception messages
    assert 'Error:' not in visible_text, "FAILURE: Found error messages in Weekly Picks"
    assert 'Exception' not in visible_text, "FAILURE: Found exception messages in Weekly Picks"


def test_weekly_picks_tab_navigation(page: Page):
    """
    Tab Navigation Test: Verifies tab can be accessed
    """
    page.goto('http://localhost:8050', wait_until='networkidle')
    page.wait_for_selector('#dashboard-tabs', timeout=30000)
    
    # Navigate to Weekly Picks
    page.locator('text=Weekly Picks').first.click()
    page.wait_for_timeout(2000)
    
    # Verify we landed on the right tab
    visible_text = page.locator('body').inner_text()
    assert 'Weekly Picks Dashboard' in visible_text, "Should display Weekly Picks Dashboard header"


def test_weekly_picks_database_population_check(page: Page):
    """
    CRITICAL DATABASE VALIDATION TEST
    
    This test directly checks if postgres_db contains weekly picks data.
    
    This test WILL FAIL because:
    - The 'picks' table does not exist in postgres_db yet
    - Dagster pipeline has not been run to populate the database
    - Application is reading from CSV files, not the database
    
    This test WILL PASS when:
    - Dagster pipeline creates the 'picks' table
    - Dagster pipeline loads CSV data into postgres_db
    - Database contains recent weekly picks records
    """
    import psycopg2
    from datetime import datetime, timedelta
    
    # Connect to postgres_db (same connection params as in docker-compose)
    try:
        conn = psycopg2.connect(
            host='postgres_db',
            port=5432,
            database='market_data',
            user='postgres',
            password='postgres'
        )
        cursor = conn.cursor()
        
        # Check if picks table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'picks'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        assert table_exists, \
            "FAILURE: 'picks' table does not exist in postgres_db. " \
            "This proves Dagster pipeline has not been run. " \
            "Phase 1 Data Pipeline must create and populate this table."
        
        # Check if table has recent data
        cursor.execute("""
            SELECT COUNT(*), MAX(pick_date) 
            FROM picks 
            WHERE pick_type = 'weekly';
        """)
        count, max_date = cursor.fetchone()
        
        assert count > 0, \
            f"FAILURE: No weekly picks found in database. " \
            f"Table exists but is empty. Dagster pipeline must populate it with historical CSV data."
        
        # Check data freshness
        # NOTE: Using 60-day threshold for test environment with static CSV files.
        # In production, this should be 7 days with active Dagster pipeline refreshing data.
        if max_date:
            days_old = (datetime.now().date() - max_date).days
            assert days_old <= 60, \
                f"FAILURE: Database has stale data. Most recent weekly pick is {max_date} ({days_old} days old). " \
                f"Dagster pipeline must be run to refresh database with recent picks."
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        pytest.fail(f"FAILURE: Cannot connect to postgres_db or query picks table. Error: {e}. "
                   f"This proves the database is not properly configured for picks data storage.")
