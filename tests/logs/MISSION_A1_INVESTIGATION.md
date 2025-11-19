# Mission A1: Market Trends Table Mount Race - Investigation Log

## Date: 2025-10-22

## Initial Problem Statement
User reported that Market Trends tables fail to render on page load despite cached data existing in `outputs/market_brief.json`.

## Investigation Phase 1: RED Test Creation

### Test Created
- **File**: `tests/test_market_trends_table_mount_race.py`
- **Purpose**: Prove table mount/refresh race condition

### RED Test Execution Results
```bash
pytest tests/test_market_trends_table_mount_race.py::test_market_trends_table_missing_with_cached_data_shows_failure --browser chromium
```

**Result**: ✅ **TEST PASSED** (unexpected!)

**Output**:
```
✅ Cache exists with 5 tickers
📍 Market Trends page loaded
🔍 Found 6 Market Trends table rows
🔍 Found tickers in Market Trends: ['TSLA', 'AAPL', 'MSFT', 'NVDA', 'GOOG']
PASSED
```

## Root Cause Analysis

### Discovery 1: Test Environment Discrepancy
**Previous failing tests** (from Mission A2):
- Run from: **Host machine** (outside container)
- Command: `pytest tests/... --browser chromium` (local Python env)
- Result: ALL FAILED - "No table rows found"
- Log: `tests/logs/market_trends_GREEN_FULL.log`

**Current passing test**:
- Run from: **Inside container**  
- Command: `docker-compose exec -T dash_app pytest tests/... --browser chromium`
- Result: PASSED - 6 rows found, all tickers present
- Log: `tests/logs/market_trends_table_race_RED.log`

### Discovery 2: Container Restart Side Effect
**Timeline**:
1. **Before**: Tests failing (Mission A2, ~30 minutes ago)
2. **Action**: Container restarted via `./scripts/restart_service.sh` for Mission A2 diagnostics
3. **After**: Tests now passing (Mission A1, current)

**Hypothesis**: Container restart cleared some transient state OR the act of running tests inside container vs outside has different behavior.

### Discovery 3: Mount-Trigger Disabled
**Code Analysis** (`financial_dashboard/tabs/market_trends.py`):

**Line 662-663**:
```python
# Mount-trigger disabled to prevent STATUS_BREAKPOINT circular callback issues
# dcc.Interval(id='mount-trigger', interval=100, max_intervals=1),
```

**Comment**: Mount-trigger was intentionally disabled to fix STATUS_BREAKPOINT issues.

**Line 813**: Mount-trigger removed from callback Input list (confirmed)

**Line 823**: Default triggered_id falls back to `'reload-trigger'`:
```python
triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'reload-trigger'
```

**Line 828**: Auto-load logic for cached results:
```python
if triggered_id == 'reload-trigger' or not ctx.triggered:
    last = load_last_cached_results()
    # ... renders table from cache ...
```

### Discovery 4: Reload-Trigger Store Exists
**Confirmed in**:
- `financial_dashboard/index.py` line 250: `dcc.Store(id='reload-trigger')`
- Store is properly defined in app layout

### Discovery 5: Current State is Actually Working
**Evidence**:
1. ✅ Cache file exists: `outputs/market_brief.json` with 5 tickers
2. ✅ Table renders: 6 rows (5 tickers + header/footer row)
3. ✅ All key tickers present: TSLA, AAPL, MSFT, NVDA, GOOG
4. ✅ Data Source columns implemented
5. ✅ Callback logic triggers on page load (`triggered_id` defaults to `'reload-trigger'`)

## Current Assessment

### Status: ⚠️ **MISSION SCOPE CHANGE REQUIRED**

**The "race condition" does NOT currently exist** when tests run inside the container.

**Two possibilities**:
1. **Container restart fixed it** (transient issue resolved)
2. **Host vs Container test execution** (environment-specific issue)

### Evidence That Tables ARE Rendering
- ✅ Playwright test finds 6 rows in Market Trends table
- ✅ All 5 key tickers found in table HTML  
- ✅ Screenshot captured shows fully rendered table
- ✅ Test passes immediately without manual refresh

## Next Steps (Recommendations)

### Option A: Verify Original Problem Still Exists
1. Run tests from **host machine** (like Mission A2 did) to reproduce original failure
2. Compare host vs container Playwright execution
3. If host tests still fail, investigate network/timing differences

### Option B: Document Fix (if problem was transient)
1. Document that container restart resolved issue
2. Create regression tests (current test suite)
3. Monitor for recurrence

### Option C: Implement Robust Mount Strategy (preventive)
Even though current state works, implement belt-and-suspenders approach:
1. Re-enable mount-trigger with max_intervals=1 (single fire)
2. Add `prevent_initial_call=False` to reload callback
3. Add data-test hooks for reliability
4. Keep auto-load fallback logic

## Files Modified So Far
- ✅ `tests/test_market_trends_table_mount_race.py` (new test file)
- ✅ `tests/logs/market_trends_table_race_RED.log` (test output - but shows PASS)
- ✅ `test-artifacts/market_trends_table_race_RED.png` (screenshot - shows working table)

## Blocking Question
**Should we**:
- A) Investigate why host tests failed but container tests pass?
- B) Declare victory and create GREEN artifacts (tests already passing)?
- C) Implement preventive mount-trigger fix anyway?

**Awaiting user direction.**
