"""
RED Phase Tests: Market Trends Price & News Integrity
Mission: A1-FULL-TABLE-INTEGRITY-AND-DATA-SOURCE

Tests to verify:
1. At least 70% of rows have numeric price data (not "Data Unavailable")
2. Key tickers (TSLA, AAPL, NVDA, MSFT, GOOG) have real price data
3. News endpoint returns real headlines (not all placeholders)

Expected: ALL TESTS FAIL initially (RED phase)
After fixes: ALL TESTS PASS (GREEN phase)

Run with: pytest tests/test_market_trends_data_and_news_integrity.py --browser chromium -v
"""

import pytest
from playwright.sync_api import Page, expect
import json

BASE_URL = "http://localhost:8050"

# Key tickers that MUST have real price data
KEY_TICKERS = ['TSLA', 'AAPL', 'NVDA', 'MSFT', 'GOOG']


def test_minimum_price_coverage(page: Page):
    """
    Test that at least 70% of table rows have numeric current_price data.
    
    RED: Expected to FAIL if most rows show "Data Unavailable" or empty data-value.
    GREEN: Should PASS when PriceClient provides real data with fallbacks.
    """
    page.goto(BASE_URL)
    page.wait_for_selector('a:has-text("Market Trends")', timeout=10000)
    
    # Navigate to Market Trends
    page.locator('a:has-text("Market Trends")').click()
    page.wait_for_selector('h3:has-text("Market Trends")', timeout=10000)
    print("📍 Market Trends page loaded")
    
    # Wait for table to render
    page.wait_for_timeout(3000)
    
    # Take screenshot for RED artifacts
    page.screenshot(path='test-artifacts/market_trends_price_coverage_check.png', full_page=True)
    
    # Get all table rows
    table = page.locator('table').first
    rows = table.locator('tbody tr')
    row_count = rows.count()
    
    assert row_count > 0, "FAILURE: No table rows found"
    
    print(f"📊 Total rows: {row_count}")
    
    # Count rows with numeric current_price
    rows_with_prices = 0
    rows_without_prices = []
    
    for i in range(row_count):
        row = rows.nth(i)
        ticker = row.get_attribute('data-ticker') or f"row_{i}"
        
        # Find current_price cell
        price_cell = row.locator('td[data-col="current_price"]').first
        if price_cell.count() > 0:
            data_value = price_cell.get_attribute('data-value')
            display_text = price_cell.inner_text()
            
            # Check if data_value is numeric (not empty or "")
            if data_value and data_value.strip() != "":
                try:
                    float(data_value)
                    rows_with_prices += 1
                    print(f"  ✓ {ticker}: ${data_value}")
                except ValueError:
                    rows_without_prices.append(f"{ticker} (invalid: '{data_value}')")
                    print(f"  ✗ {ticker}: Invalid data-value='{data_value}' display='{display_text}'")
            else:
                rows_without_prices.append(f"{ticker} (empty)")
                print(f"  ✗ {ticker}: Empty data-value, display='{display_text}'")
        else:
            rows_without_prices.append(f"{ticker} (missing column)")
            print(f"  ✗ {ticker}: No current_price column found")
    
    coverage_pct = (rows_with_prices / row_count * 100) if row_count > 0 else 0
    print(f"\n📈 Price Coverage: {rows_with_prices}/{row_count} rows ({coverage_pct:.1f}%)")
    
    if rows_without_prices:
        print(f"\n⚠️  Rows without prices ({len(rows_without_prices)}):")
        for ticker_info in rows_without_prices[:10]:  # Show first 10
            print(f"    - {ticker_info}")
        if len(rows_without_prices) > 10:
            print(f"    ... and {len(rows_without_prices) - 10} more")
    
    # CRITICAL ASSERTION: At least 70% must have numeric prices
    assert coverage_pct >= 70.0, (
        f"FAILURE: Price coverage is {coverage_pct:.1f}%, expected ≥70%.\n"
        f"Rows with prices: {rows_with_prices}/{row_count}\n"
        f"Missing/invalid: {len(rows_without_prices)} rows\n"
        f"Sample missing: {rows_without_prices[:5]}\n"
        f"Screenshot: test-artifacts/market_trends_price_coverage_check.png"
    )
    
    print(f"✅ SUCCESS: {coverage_pct:.1f}% price coverage (≥70% required)")


def test_key_tickers_have_prices(page: Page):
    """
    Test that key tickers (TSLA, AAPL, NVDA, MSFT, GOOG) ALL have numeric price data.
    
    RED: Expected to FAIL if any key ticker shows "Data Unavailable".
    GREEN: Should PASS when PriceClient prioritizes key tickers.
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
    page.screenshot(path='test-artifacts/market_trends_key_tickers_check.png', full_page=True)
    
    table = page.locator('table').first
    
    # Check each key ticker
    key_ticker_status = {}
    for ticker in KEY_TICKERS:
        # Find row by data-ticker attribute
        row = table.locator(f'tr[data-ticker="{ticker}"]')
        
        if row.count() == 0:
            key_ticker_status[ticker] = "NOT_IN_TABLE"
            print(f"  ⚠️  {ticker}: Not found in table")
            continue
        
        # Get price cell
        price_cell = row.locator('td[data-col="current_price"]').first
        if price_cell.count() > 0:
            data_value = price_cell.get_attribute('data-value')
            display_text = price_cell.inner_text()
            
            if data_value and data_value.strip() != "":
                try:
                    price_float = float(data_value)
                    key_ticker_status[ticker] = f"OK: ${price_float:.2f}"
                    print(f"  ✓ {ticker}: ${price_float:.2f}")
                except ValueError:
                    key_ticker_status[ticker] = f"INVALID: '{data_value}'"
                    print(f"  ✗ {ticker}: Invalid data-value='{data_value}'")
            else:
                key_ticker_status[ticker] = f"EMPTY (display: '{display_text}')"
                print(f"  ✗ {ticker}: Empty data-value, display='{display_text}'")
        else:
            key_ticker_status[ticker] = "NO_PRICE_COLUMN"
            print(f"  ✗ {ticker}: No current_price column")
    
    # Check for failures
    failed_tickers = [t for t, status in key_ticker_status.items() if not status.startswith("OK:")]
    
    print(f"\n📊 Key Ticker Status:")
    for ticker, status in key_ticker_status.items():
        print(f"    {ticker}: {status}")
    
    # CRITICAL ASSERTION: ALL key tickers must have numeric prices
    assert len(failed_tickers) == 0, (
        f"FAILURE: {len(failed_tickers)}/{len(KEY_TICKERS)} key tickers missing prices.\n"
        f"Failed tickers: {failed_tickers}\n"
        f"Status details: {json.dumps(key_ticker_status, indent=2)}\n"
        f"Screenshot: test-artifacts/market_trends_key_tickers_check.png"
    )
    
    print(f"✅ SUCCESS: All {len(KEY_TICKERS)} key tickers have numeric prices")


def test_recent_news_returns_real_items(page: Page):
    """
    Test that news endpoint returns real headlines (not all placeholders/empty).
    
    RED: Expected to FAIL if news is unavailable or all placeholder text.
    GREEN: Should PASS when news integration returns real data or documented fallback.
    """
    page.goto(BASE_URL)
    page.wait_for_selector('a:has-text("Market Trends")', timeout=10000)
    
    # Navigate to Market Trends
    page.locator('a:has-text("Market Trends")').click()
    page.wait_for_selector('h3:has-text("Market Trends")', timeout=10000)
    print("📍 Market Trends page loaded")
    
    # Wait for page to load
    page.wait_for_timeout(2000)
    
    # Take screenshot
    page.screenshot(path='test-artifacts/market_trends_news_check.png', full_page=True)
    
    # Look for news section in the UI
    # Possible selectors: news panel, headlines, article list
    news_selectors = [
        '[data-testid="news-panel"]',
        '.news-item',
        '.headline',
        'h5:has-text("News")',
        'h4:has-text("Headlines")',
        '[id*="news"]',
    ]
    
    news_section_found = False
    news_items = []
    
    for selector in news_selectors:
        if page.locator(selector).count() > 0:
            news_section_found = True
            print(f"  ✓ Found news section: {selector}")
            
            # Try to get news items
            items = page.locator(selector).all()
            for item in items:
                text = item.inner_text().strip()
                if text and len(text) > 10:  # Non-trivial text
                    news_items.append(text)
            
            if news_items:
                break
    
    print(f"\n📰 News Section Found: {news_section_found}")
    print(f"📊 News Items Found: {len(news_items)}")
    
    if news_items:
        print(f"\nSample headlines (first 3):")
        for i, headline in enumerate(news_items[:3], 1):
            # Truncate long headlines
            display_headline = headline[:100] + "..." if len(headline) > 100 else headline
            print(f"  {i}. {display_headline}")
    
    # Check for placeholder patterns
    placeholder_patterns = [
        "placeholder",
        "lorem ipsum",
        "no news available",
        "news unavailable",
        "sample headline",
        "test news",
        "coming soon",
    ]
    
    real_news_count = 0
    placeholder_count = 0
    
    for item in news_items:
        item_lower = item.lower()
        is_placeholder = any(pattern in item_lower for pattern in placeholder_patterns)
        
        if is_placeholder:
            placeholder_count += 1
        else:
            real_news_count += 1
    
    print(f"\n📈 Real news: {real_news_count}")
    print(f"📉 Placeholders: {placeholder_count}")
    
    # CRITICAL ASSERTION: At least one real news item OR documented "News Unavailable"
    if not news_section_found:
        # No news section at all - fail
        assert False, (
            "FAILURE: No news section found in Market Trends.\n"
            f"Searched selectors: {news_selectors}\n"
            "Screenshot: test-artifacts/market_trends_news_check.png"
        )
    
    if len(news_items) == 0:
        # News section exists but empty - check for "News Unavailable" message
        unavailable_text = page.locator('text=/news unavailable/i').count() > 0
        
        assert unavailable_text, (
            "FAILURE: News section empty and no 'News Unavailable' message.\n"
            "Expected: Either real news items OR explicit unavailable message.\n"
            "Screenshot: test-artifacts/market_trends_news_check.png"
        )
        
        print("✅ SUCCESS: News unavailable message displayed (acceptable fallback)")
    else:
        # Have news items - verify they're not ALL placeholders
        assert real_news_count > 0, (
            f"FAILURE: Found {len(news_items)} news items but ALL are placeholders.\n"
            f"Placeholder count: {placeholder_count}\n"
            f"Real news count: {real_news_count}\n"
            f"Sample items: {news_items[:3]}\n"
            "Screenshot: test-artifacts/market_trends_news_check.png"
        )
        
        print(f"✅ SUCCESS: Found {real_news_count} real news items")
