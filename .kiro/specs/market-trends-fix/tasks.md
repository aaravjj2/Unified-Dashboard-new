# Implementation Plan: Market Trends Tab Fix

- [x] 1. Create Cache Manager module
  - Create `financial_dashboard/utils/cache_manager.py` with CacheManager class
  - Implement `load_from_disk()` method to read market_brief.json
  - Implement `save_to_disk(data)` method with atomic writes
  - Implement `get_cached_data()` to access RESULTS_CACHE
  - Implement `update_cache(data)` to sync memory and disk
  - Implement `is_cache_fresh(max_age_seconds)` for TTL validation
  - Implement `get_cache_timestamp()` to extract cache age
  - Add thread locking for concurrent access safety
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 1.1 Write property test for cache persistence
  - **Property 4: Cache Persistence Round Trip**
  - **Validates: Requirements 6.1, 6.2, 6.3**
  - Generate random analysis results with Hypothesis
  - Test save_to_disk then load_from_disk preserves all fields
  - Test with various data types (floats, strings, None values)
  - Verify timestamps are preserved correctly

- [x] 1.2 Write unit tests for CacheManager
  - Test load_from_disk with valid JSON file
  - Test load_from_disk with missing file (returns empty dict)
  - Test load_from_disk with corrupted JSON (handles gracefully)
  - Test save_to_disk creates file with correct structure
  - Test is_cache_fresh with various timestamps
  - Test thread safety with concurrent reads/writes
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 2. Create News Manager module
  - Create `financial_dashboard/utils/news_manager.py` with NewsManager class
  - Implement `fetch_news(tickers, force_refresh)` with TTL cache logic
  - Implement `is_news_stale()` to check 5-minute TTL
  - Implement `get_cached_news()` to access module-level cache
  - Implement `render_news_panel(news_data)` to generate html.Div
  - Add error handling for provider failures
  - Add logging for cache hits/misses
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2.1 Write property test for news cache freshness
  - **Property 1: News Cache Freshness**
  - **Validates: Requirements 1.2, 5.2**
  - Generate random ticker lists and timestamps with Hypothesis
  - Test that fresh cache (<5 min) returns cached data without API call
  - Test that stale cache (>5 min) triggers new API call
  - Test that ticker list mismatch triggers new API call
  - Mock external API calls to verify behavior

- [x] 2.2 Write unit tests for NewsManager
  - Test fetch_news with mocked Finnhub responses
  - Test fetch_news with mocked Alpaca responses
  - Test cache hit scenario (no API call)
  - Test cache miss scenario (API call made)
  - Test provider failure fallback
  - Test render_news_panel with various data shapes
  - Test render_news_panel with empty data
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 3. Fix "Run Full Analysis" button
  - Update callback in `financial_dashboard/tabs/market_trends.py`
  - Add proper error handling with try/except
  - Ensure job_id is correctly generated and tracked
  - Update status display with clear messages
  - Add logging for debugging
  - Test button click triggers analysis
  - _Requirements: 2.1, 4.1, 4.2_

- [ ] 3.1 Write integration test for Run Analysis flow
  - Test button click starts background job
  - Test job completion updates results table
  - Test job failure displays error message
  - Test cache is updated after successful job
  - _Requirements: 2.1, 6.1_

- [ ] 4. Fix "Reload Model" button
  - Update callback to reload from disk cache
  - Clear memory cache before reload
  - Update results table with reloaded data
  - Add status message on success/failure
  - Test button click reloads data
  - _Requirements: 2.2, 6.2_

- [ ] 5. Fix "Refresh cached display" button
  - Update callback to use CacheManager.load_from_disk()
  - Re-render table with cached data
  - Add timestamp display showing cache age
  - Test button click refreshes display
  - _Requirements: 2.3, 5.1_

- [ ] 6. Fix "Backtest Trend Signals" button
  - Update callback to execute backtest logic
  - Display results in modal with proper formatting
  - Add metrics explanation in modal
  - Handle backtest errors gracefully
  - Test button click opens modal with results
  - _Requirements: 2.4, 4.1, 4.2_

- [ ] 6.1 Write unit test for backtest modal
  - Test modal opens on button click
  - Test modal displays backtest metrics
  - Test modal close button works
  - Test error handling in backtest execution
  - _Requirements: 2.4_

- [ ] 7. Fix "Debug Logs" button
  - Update callback to read recent log entries
  - Display logs in modal with monospace font
  - Add auto-scroll to bottom of logs
  - Test button click opens modal with logs
  - _Requirements: 2.5_

- [ ] 8. Fix "Toggle full brief" button
  - Update callback to show/hide full brief section
  - Maintain toggle state across clicks
  - Add smooth transition animation
  - Test button toggles visibility
  - _Requirements: 2.6_

- [ ] 9. Fix "Download CSV" button
  - Update callback to generate CSV from cached data
  - Use dcc.Download component for file download
  - Include all columns in CSV export
  - Add timestamp to filename
  - Test button click downloads CSV file
  - _Requirements: 2.7_

- [ ] 10. Refactor table rendering with price enrichment
  - Update `_render_html_table_with_prices()` function
  - Implement `enrich_with_prices(data)` helper function
  - Fetch missing prices from PriceClient
  - Update all 5 price fields (current, week_start, month_start, daily_change, profit_loss)
  - Add "Data Unavailable" fallback for missing prices
  - Add data_source column showing provider
  - Test table renders with complete price data
  - Test table renders with missing price data
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ] 10.1 Write property test for price data completeness
  - **Property 3: Price Data Completeness**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
  - Generate random ticker data with prices using Hypothesis
  - Test that all 5 price fields are present in rendered output
  - Test with various price value ranges (positive, negative, zero)
  - Test with missing price data (fallback to "Data Unavailable")

- [ ] 10.2 Write unit tests for table renderer
  - Test render_results_table with complete data
  - Test render_results_table with missing price fields
  - Test enrich_with_prices fetches missing data
  - Test enrich_with_prices preserves existing data
  - Test format_price_cell with various values
  - Test format_price_cell with None/NaN values
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ] 11. Fix news auto-refresh callback
  - Update news polling callback to check cache staleness
  - Only refresh if cache is >5 minutes old
  - Update news-container with new data
  - Add loading indicator during fetch
  - Handle fetch errors gracefully
  - Test news refreshes automatically after 5 minutes
  - _Requirements: 1.2, 1.4, 1.5_

- [ ] 11.1 Write integration test for news refresh
  - Test news displays on initial tab load
  - Test news refreshes after 5 minutes
  - Test news doesn't refresh if cache is fresh
  - Test error handling when providers fail
  - _Requirements: 1.2, 1.4, 1.5_

- [ ] 12. Fix tab activation callback
  - Update render_on_tab_activation callback
  - Use CacheManager to load cached data
  - Render table within 2 seconds
  - Add cache timestamp comparison to avoid unnecessary re-renders
  - Test tab activation renders table quickly
  - _Requirements: 5.1, 6.2_

- [ ] 12.1 Write property test for tab activation rendering
  - **Property 7: Tab Activation Rendering**
  - **Validates: Requirements 5.1**
  - Generate tab activation events with various cache states
  - Test table renders within 2 seconds
  - Test with empty cache (shows prompt message)
  - Test with stale cache (still renders quickly)

- [ ] 13. Add comprehensive error handling
  - Create `@safe_callback` decorator for error wrapping
  - Apply decorator to all button callbacks
  - Ensure all exceptions are logged with stack traces
  - Display user-friendly error messages in UI
  - Test error handling with various exception types
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 13.1 Write property test for error message display
  - **Property 5: Error Message Display**
  - **Validates: Requirements 4.1, 4.2**
  - Generate callbacks that raise various exceptions
  - Test that error message is displayed in UI
  - Test that full error is logged
  - Test that UI doesn't break on error

- [ ] 13.2 Write property test for fallback to cache
  - **Property 6: Fallback to Cache**
  - **Validates: Requirements 4.4**
  - Simulate API failures with cached data present
  - Test that cached data is used
  - Test that warning message is shown
  - Test with no cached data (error message shown)

- [ ] 14. Update all callbacks to use CacheManager
  - Replace direct RESULTS_CACHE access with CacheManager methods
  - Replace direct file I/O with CacheManager methods
  - Ensure all cache updates sync memory and disk
  - Test cache consistency across all operations
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [ ] 15. Checkpoint - Ensure all tests pass
  - Run all unit tests
  - Run all property-based tests
  - Run all integration tests
  - Fix any failing tests
  - Verify all buttons work in browser
  - Verify news refreshes correctly
  - Verify prices display correctly
  - Ask the user if questions arise

- [ ] 16. Performance optimization
  - Add batch price fetching for multiple tickers
  - Implement table virtualization for >50 rows
  - Add debouncing for rapid button clicks
  - Optimize cache file I/O (use atomic writes)
  - Test performance with large datasets (100+ tickers)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 16.1 Write performance benchmark tests
  - Test tab activation time with various cache sizes
  - Test table rendering time with 50, 100, 200 rows
  - Test news fetch time with cache hit vs miss
  - Test button response time
  - Verify all operations meet performance requirements

- [ ] 17. Final integration testing
  - Test complete user flow: load tab → run analysis → view results
  - Test news refresh flow: stale cache → auto-refresh → new data
  - Test button flow: click each button → verify expected behavior
  - Test error scenarios: API failures → fallback to cache
  - Test cache persistence: run analysis → reload page → data persists
  - _Requirements: All_

- [ ] 18. Final Checkpoint - Ensure all tests pass
  - Run full test suite
  - Verify all 7 buttons work correctly
  - Verify news displays and refreshes
  - Verify prices display correctly
  - Verify cache persists across page reloads
  - Ask the user if questions arise
