# Design Document: Market Trends Tab Fix

## Overview

This design addresses critical functionality issues in the Market Trends tab of the Financial Dashboard. The tab currently suffers from outdated news display, non-functional buttons, and inconsistent data rendering. The solution involves refactoring callbacks, implementing proper cache management, and ensuring all user interactions work correctly.

## Architecture

### Current Architecture Issues

1. **Callback Conflicts**: Multiple callbacks updating the same outputs causing race conditions
2. **Cache Inconsistency**: Memory cache (RESULTS_CACHE) and disk cache (market_brief.json) out of sync
3. **News Staleness**: 5-minute TTL cache not refreshing properly
4. **Button Handlers**: Several buttons have broken or missing callback implementations

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Market Trends Tab                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Buttons    │  │  News Panel  │  │ Results Table│      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│         └──────────────────┼──────────────────┘               │
│                            │                                  │
│                    ┌───────▼────────┐                        │
│                    │   Callbacks    │                        │
│                    └───────┬────────┘                        │
│                            │                                  │
│         ┌──────────────────┼──────────────────┐              │
│         │                  │                  │              │
│    ┌────▼─────┐      ┌────▼─────┐      ┌────▼─────┐        │
│    │  Cache   │      │   News   │      │  Price   │        │
│    │ Manager  │      │  Client  │      │  Client  │        │
│    └────┬─────┘      └────┬─────┘      └────┬─────┘        │
│         │                  │                  │              │
│    ┌────▼─────────────────▼──────────────────▼─────┐        │
│    │         Shared State (RESULTS_CACHE)          │        │
│    └────┬──────────────────────────────────────────┘        │
│         │                                                     │
│    ┌────▼─────┐                                              │
│    │   Disk   │                                              │
│    │  Cache   │                                              │
│    └──────────┘                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Cache Manager

**Purpose**: Centralize cache operations to prevent inconsistencies

**Interface**:
```python
class CacheManager:
    def load_from_disk() -> Dict
    def save_to_disk(data: Dict) -> None
    def get_cached_data() -> Dict
    def update_cache(data: Dict) -> None
    def is_cache_fresh(max_age_seconds: int) -> bool
    def get_cache_timestamp() -> float
```

**Responsibilities**:
- Load data from disk cache (market_brief.json)
- Save data to disk cache with timestamps
- Synchronize memory cache (RESULTS_CACHE) with disk
- Validate cache freshness
- Thread-safe cache operations

### 2. News Manager

**Purpose**: Handle news fetching with proper caching and refresh logic

**Interface**:
```python
class NewsManager:
    def fetch_news(tickers: List[str], force_refresh: bool = False) -> Dict
    def is_news_stale() -> bool
    def get_cached_news() -> Dict
    def render_news_panel(news_data: Dict) -> html.Div
```

**Responsibilities**:
- Fetch news from providers (Finnhub, Alpaca)
- Implement 5-minute TTL cache
- Handle provider failures gracefully
- Render news items with proper formatting

### 3. Button Handlers

**Purpose**: Implement all button click handlers with proper error handling

**Callbacks**:
1. `handle_run_analysis` - Run Full Analysis button
2. `handle_reload_model` - Reload Model button
3. `handle_refresh_cached` - Refresh cached display button
4. `handle_backtest` - Backtest Trend Signals button
5. `handle_debug_logs` - Debug Logs button
6. `handle_toggle_brief` - Toggle full brief button
7. `handle_download_csv` - Download CSV button

### 4. Table Renderer

**Purpose**: Render results table with price data

**Interface**:
```python
def render_results_table(data: List[Dict], include_prices: bool = True) -> html.Div
def enrich_with_prices(data: List[Dict]) -> List[Dict]
def format_price_cell(value: float, col_name: str) -> Tuple[str, str]
```

**Responsibilities**:
- Render HTML table with proper styling
- Enrich rows with price data from cache
- Handle missing data gracefully
- Add data attributes for testing

## Data Models

### CachedResult

```python
{
    "detailed": [
        {
            "ticker": str,
            "current_price": float,
            "week_start_price": float,
            "month_start_price": float,
            "daily_change": float,
            "profit_loss": float,
            "data_source": str,
            # ... other analysis fields
        }
    ],
    "market_trend": {
        "label": str,  # "Strong Bull", "Bull", "Neutral", "Bear", "Strong Bear"
        "composite": float,
        "scores": Dict[str, float],
        "generated_at": str  # ISO timestamp
    },
    "generated_at": str,  # ISO timestamp
    "tickers": List[str]
}
```

### NewsCache

```python
{
    "data": {
        "AAPL": [
            {
                "headline": str,
                "url": str,
                "source": str,
                "published_at": str
            }
        ]
    },
    "tickers": List[str],
    "timestamp": float  # Unix timestamp
}
```

### PriceData

```python
{
    "ticker": {
        "current_price": float,
        "week_start_price": float,
        "month_start_price": float,
        "daily_change": float,
        "profit_loss": float,
        "source": str,  # "yfinance", "alpaca", "cached"
        "start_date": str
    }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: News Cache Freshness

*For any* news fetch request, if the cache timestamp is less than 5 minutes old and the ticker list matches, the system should return cached data without making external API calls.

**Validates: Requirements 1.2, 5.2**

### Property 2: Button Click Response

*For any* button click event, the system should execute the corresponding callback and update at least one output component (either UI element or status message).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

### Property 3: Price Data Completeness

*For any* ticker in the results table, if price data exists in the cache, all five price fields (current_price, week_start_price, month_start_price, daily_change, profit_loss) should be populated in the rendered row.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 4: Cache Persistence Round Trip

*For any* analysis result, saving to disk and then loading should produce equivalent data (all fields preserved).

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 5: Error Message Display

*For any* callback that raises an exception, the system should display a user-friendly error message in the UI and log the full error details.

**Validates: Requirements 4.1, 4.2**

### Property 6: Fallback to Cache

*For any* external API call that fails or times out, if cached data exists, the system should use the cached data and display a warning about using stale data.

**Validates: Requirements 4.4**

### Property 7: Tab Activation Rendering

*For any* tab activation event where Market Trends becomes the active tab, the system should render the results table within 2 seconds using cached data.

**Validates: Requirements 5.1**

## Error Handling

### Error Categories

1. **Network Errors**: API timeouts, connection failures
   - Retry once with exponential backoff
   - Fall back to cached data if available
   - Display clear error message to user

2. **Data Errors**: Missing fields, invalid formats
   - Log detailed error with data sample
   - Use default values or "Data Unavailable"
   - Continue rendering other valid data

3. **Callback Errors**: Exceptions in callback execution
   - Catch all exceptions at callback boundary
   - Log full stack trace
   - Return user-friendly error message
   - Prevent UI from breaking

4. **Cache Errors**: File read/write failures
   - Log error details
   - Continue with memory cache only
   - Warn user about persistence issues

### Error Recovery Strategies

```python
def safe_callback(func):
    """Decorator to wrap callbacks with error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Callback {func.__name__} failed")
            return html.Div(
                f"Error: {str(e)[:100]}",
                style={'color': 'red', 'padding': '10px'}
            )
    return wrapper
```

## Testing Strategy

### Unit Tests

1. **Cache Manager Tests**
   - Test load_from_disk with valid/invalid JSON
   - Test save_to_disk creates proper file structure
   - Test is_cache_fresh with various timestamps
   - Test thread-safe operations with concurrent access

2. **News Manager Tests**
   - Test fetch_news with mocked API responses
   - Test cache hit/miss scenarios
   - Test error handling for provider failures
   - Test render_news_panel with various data shapes

3. **Button Handler Tests**
   - Test each button callback with valid inputs
   - Test callbacks with missing/invalid state
   - Test error handling in each callback
   - Test output updates for each callback

4. **Table Renderer Tests**
   - Test render with complete price data
   - Test render with missing price data
   - Test enrich_with_prices updates all fields
   - Test format_price_cell with various values

### Property-Based Tests

We will use **Hypothesis** (Python property-based testing library) for property tests.

Each property-based test will run a minimum of 100 iterations with randomly generated inputs.

1. **Property Test 1: News Cache Freshness**
   - **Feature: market-trends-fix, Property 1: News Cache Freshness**
   - Generate random ticker lists and timestamps
   - Verify cache is used when fresh, API called when stale

2. **Property Test 2: Button Click Response**
   - **Feature: market-trends-fix, Property 2: Button Click Response**
   - Generate random button click events
   - Verify each produces output update

3. **Property Test 3: Price Data Completeness**
   - **Feature: market-trends-fix, Property 3: Price Data Completeness**
   - Generate random ticker data with prices
   - Verify all 5 price fields present in output

4. **Property Test 4: Cache Persistence Round Trip**
   - **Feature: market-trends-fix, Property 4: Cache Persistence Round Trip**
   - Generate random analysis results
   - Verify save then load preserves all data

5. **Property Test 5: Error Message Display**
   - **Feature: market-trends-fix, Property 5: Error Message Display**
   - Generate callbacks that raise various exceptions
   - Verify error message displayed and logged

6. **Property Test 6: Fallback to Cache**
   - **Feature: market-trends-fix, Property 6: Fallback to Cache**
   - Simulate API failures with cached data present
   - Verify cached data used and warning shown

7. **Property Test 7: Tab Activation Rendering**
   - **Feature: market-trends-fix, Property 7: Tab Activation Rendering**
   - Generate tab activation events with various cache states
   - Verify table renders within 2 seconds

### Integration Tests

1. **End-to-End Button Flow**
   - Click "Run Full Analysis"
   - Verify job starts, completes, and results display
   - Verify cache updated on disk

2. **News Refresh Flow**
   - Load tab with stale news cache
   - Verify news refreshes automatically
   - Verify new cache timestamp

3. **Price Enrichment Flow**
   - Run analysis with missing price data
   - Verify prices fetched and enriched
   - Verify enriched data persisted

## Implementation Notes

### Callback Registration Pattern

All callbacks should use `@app.callback` (not `@callback`) to avoid registration issues:

```python
def register_callbacks(app):
    @app.callback(
        Output('results-area', 'children'),
        Input('run-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_run_analysis(n_clicks):
        # Implementation
        pass
```

### Cache Synchronization

Always update both memory and disk cache together:

```python
def update_cache(data):
    # Update memory cache
    SH.RESULTS_CACHE['results'] = data
    SH.RESULTS_CACHE['loaded_at'] = time.time()
    
    # Update disk cache
    cache_file = os.path.join(SH.OUT_ROOT, 'market_brief.json')
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
```

### News Polling

Use dcc.Interval for automatic news refresh:

```python
dcc.Interval(
    id='news-poll-interval',
    interval=5000,  # 5 seconds
    n_intervals=0
)

@app.callback(
    Output('news-container', 'children'),
    Input('news-poll-interval', 'n_intervals')
)
def refresh_news(n_intervals):
    if news_manager.is_news_stale():
        return news_manager.fetch_and_render()
    raise PreventUpdate
```

### Performance Optimization

1. Use `prevent_initial_call=True` for buttons to avoid unnecessary execution
2. Use `allow_duplicate=True` when multiple callbacks update same output
3. Batch price fetches to minimize API calls
4. Use virtualization for large tables (>50 rows)
5. Implement debouncing for rapid button clicks

## Migration Strategy

### Phase 1: Cache Manager (Low Risk)
- Extract cache operations into CacheManager class
- Update existing code to use CacheManager
- Add unit tests for cache operations

### Phase 2: News Manager (Medium Risk)
- Extract news logic into NewsManager class
- Fix news refresh callback
- Add property tests for cache freshness

### Phase 3: Button Handlers (High Risk)
- Fix each button callback one at a time
- Add comprehensive error handling
- Add integration tests for each button

### Phase 4: Table Renderer (Medium Risk)
- Refactor table rendering logic
- Fix price enrichment
- Add property tests for data completeness

### Phase 5: Integration Testing (Low Risk)
- Run end-to-end tests
- Verify all buttons work
- Verify news refreshes
- Verify prices display correctly

## Rollback Plan

If issues arise during implementation:

1. **Cache Manager Issues**: Revert to direct cache access, keep disk/memory sync
2. **News Manager Issues**: Disable auto-refresh, keep manual refresh working
3. **Button Handler Issues**: Disable problematic button, keep others working
4. **Table Renderer Issues**: Fall back to simple table without price enrichment

Each phase can be rolled back independently without affecting other phases.
