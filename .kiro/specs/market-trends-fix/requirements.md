# Requirements Document: Market Trends Tab Fix

## Introduction

The Market Trends tab in the Financial Dashboard has multiple issues affecting user experience:
- News section displays outdated headlines
- Several buttons are non-functional
- User interactions don't produce expected results

This specification addresses these issues to restore full functionality to the Market Trends tab.

## Glossary

- **Market Trends Tab**: Dashboard tab displaying market analysis, price data, and news
- **News Panel**: UI component showing recent financial news headlines
- **Price Data**: Current and historical price information for tickers
- **Callback**: Dash framework function that responds to user interactions
- **Cache**: Temporary storage for API responses to reduce external calls

## Requirements

### Requirement 1: News Freshness

**User Story:** As a user, I want to see current financial news, so that I can make informed decisions based on recent market events.

#### Acceptance Criteria

1. WHEN the Market Trends tab loads THEN the system SHALL fetch news from providers within the last 24 hours
2. WHEN news data is older than 5 minutes THEN the system SHALL refresh the news automatically
3. WHEN news providers return no data THEN the system SHALL display a clear message indicating no news is available
4. WHEN news is loading THEN the system SHALL show a loading indicator to the user
5. WHEN news fetch fails THEN the system SHALL display an error message with the failure reason

### Requirement 2: Button Functionality

**User Story:** As a user, I want all buttons to work correctly, so that I can interact with the dashboard features.

#### Acceptance Criteria

1. WHEN the "Run Full Analysis" button is clicked THEN the system SHALL execute market analysis and display results
2. WHEN the "Reload Model" button is clicked THEN the system SHALL refresh cached data and update the display
3. WHEN the "Refresh cached display" button is clicked THEN the system SHALL reload data from cache without re-fetching
4. WHEN the "Backtest Trend Signals" button is clicked THEN the system SHALL execute backtest and display results in a modal
5. WHEN the "Debug Logs" button is clicked THEN the system SHALL open a modal showing recent log entries
6. WHEN the "Toggle full brief" button is clicked THEN the system SHALL show or hide the full market brief
7. WHEN the "Download CSV" button is clicked THEN the system SHALL download the latest results as a CSV file

### Requirement 3: Price Data Display

**User Story:** As a user, I want to see accurate current prices, so that I can track market movements.

#### Acceptance Criteria

1. WHEN the results table renders THEN the system SHALL display current_price for each ticker
2. WHEN the results table renders THEN the system SHALL display week_start_price for each ticker
3. WHEN the results table renders THEN the system SHALL display month_start_price for each ticker
4. WHEN the results table renders THEN the system SHALL display daily_change for each ticker
5. WHEN the results table renders THEN the system SHALL display profit_loss for each ticker
6. WHEN price data is unavailable THEN the system SHALL display "Data Unavailable" in the cell
7. WHEN the table renders THEN the system SHALL include a data_source column showing the price provider

### Requirement 4: Error Handling

**User Story:** As a user, I want clear error messages, so that I understand what went wrong and can take corrective action.

#### Acceptance Criteria

1. WHEN a callback fails THEN the system SHALL log the error with full stack trace
2. WHEN a callback fails THEN the system SHALL display a user-friendly error message
3. WHEN an API call times out THEN the system SHALL retry once before failing
4. WHEN external providers are unavailable THEN the system SHALL fall back to cached data
5. WHEN no cached data exists THEN the system SHALL display a message prompting the user to run analysis

### Requirement 5: Performance

**User Story:** As a user, I want the tab to load quickly, so that I can access information without delays.

#### Acceptance Criteria

1. WHEN the Market Trends tab activates THEN the system SHALL render cached data within 2 seconds
2. WHEN fetching news THEN the system SHALL use cached data if available and less than 5 minutes old
3. WHEN fetching prices THEN the system SHALL batch requests to minimize API calls
4. WHEN rendering the table THEN the system SHALL use virtualization for datasets larger than 50 rows
5. WHEN background jobs complete THEN the system SHALL update the UI without blocking user interactions

### Requirement 6: Data Consistency

**User Story:** As a developer, I want data to persist correctly, so that page reloads show the same information.

#### Acceptance Criteria

1. WHEN analysis completes THEN the system SHALL persist results to disk in JSON format
2. WHEN the page reloads THEN the system SHALL load persisted data from disk
3. WHEN enriching data with prices THEN the system SHALL preserve all price fields in the cache
4. WHEN saving to cache THEN the system SHALL include timestamps for cache invalidation
5. WHEN multiple tabs access the cache THEN the system SHALL ensure thread-safe read/write operations
