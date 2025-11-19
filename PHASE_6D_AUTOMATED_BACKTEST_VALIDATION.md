# Phase 6D - Automated Backtest E2E Reliability & Loop Validation

**Status:** IN PROGRESS  
**Date:** 2025-10-23

## Summary

Phase 6D implements a comprehensive automated testing framework for the Market Trends backtest feature, with test mode support, automatic retry logic, and extensive artifact generation.

## Completed Work

### 1. Test Mode Support (`market_trends_dash.py`)

✅ **Added test_mode parameter to `run_full_analysis`**
- Detects `test_mode=True` in kwargs
- Automatically switches to deterministic ticker set: `["AAPL", "MSFT", "GOOGL"]`
- Forces `cache_only=True` to avoid live API calls
- Disables options and news enrichment for speed
- Target runtime: <10s per test

```python
if test_mode:
    logger.info("🧪 TEST MODE ACTIVE - Using deterministic configuration")
    tickers = ["AAPL", "MSFT", "GOOGL"]
    use_cache_only = True
    no_options = True
    no_news = True
```

### 2. Configurable Job Timeout (`_shared.py`)

✅ **Environment variable: `JOB_TIME_LIMIT`**
- Default: 300 seconds (increased from 90s)
- Read from `os.environ.get('JOB_TIME_LIMIT', 300)`
- Applied in `start_background_job` time_limit context manager
- Timeout errors logged with actual limit value

```python
job_timeout = int(os.environ.get('JOB_TIME_LIMIT', 300))
_logger.info(f"⏱️  Starting job execution with {job_timeout}s timeout...")
```

### 3. Enhanced Playwright Loop Validator (`scripts/test_backtest_loop.py`)

✅ **Comprehensive automation framework** with:

**Features:**
- Automatic dashboard restart between runs
- Multiple navigation strategies (wait_for_selector, retry logic)
- Improved tab activation (clicks Market Trends after page load)
- HTTP job status polling via `/_job_status` endpoint
- Extended job ID extraction (3 strategies: dcc.Store, status div, full HTML)
- Per-run artifact generation (screenshots, logs, metrics)
- Structured JSON reporting

**Configuration:**
- `--max-runs N`: Maximum test runs (default: 5)
- `--min-passes N`: Consecutive passes required (default: 3)
- `--timeout N`: Job timeout per run (default: 120s)
- `--debug`: Verbose logging
- `--headless`: Headless browser mode

**Artifacts Generated:**
- `test-artifacts/backtest-automation/report.json` - Full structured report
- `test-artifacts/backtest-automation/metrics.json` - Performance metrics
- `test-artifacts/backtest-automation/VALIDATION_REPORT.md` - Human-readable summary
- `test-artifacts/backtest-automation/runN_*.png` - Screenshots per run
- `test-artifacts/backtest-automation/runN_logs.txt` - Docker logs per run

## Current Status

### ✅ Working Components

1. **Dashboard Loading** - Page loads successfully with domcontentloaded wait
2. **Tab Navigation** - Market Trends tab clicks successfully
3. **Button Interaction** - Backtest button click executes
4. **Artifact Generation** - All screenshots and logs saved correctly
5. **Retry Logic** - Auto-restart and loop validation functioning
6. **Job Runner** - Configurable timeout working

### ⚠️ Known Issues

1. **Job ID Extraction Failing** - Button click succeeds but job ID not appearing in DOM
   - Tried: dcc.Store, status div, full HTML search
   - Issue: Job may not be starting or UI not updating with job ID
   - Need to: Check backend job creation logs

2. **Test Mode Not Activated** - Query parameter `?test_mode=short` not reaching backend
   - Query params don't automatically propagate to Dash callbacks
   - Need to: Add hidden dcc.Store or button to trigger test mode

## Test Results (Latest Run)

```
Configuration:
  Max Runs: 3
  Required Consecutive Passes: 2
  Timeout per run: 180s

Results:
  Total Runs: 3
  Successful: 0
  Failed: 3
  
Error Categories:
  - no_job_id: 3 (100%)
  
Per-Run Status:
  Run #1: button clicked ✅, job ID extracted ❌
  Run #2: button clicked ✅, job ID extracted ❌
  Run #3: button clicked ✅, job ID extracted ❌
```

## Next Steps

### Priority 1: Fix Job ID Extraction

**Approach A: Check Backend Logs**
```bash
docker compose logs dash_app --tail 100 | grep "BACKGROUND JOB"
```
- Verify job is actually being created
- Check for exceptions in start_background_job

**Approach B: Add Debug Logging to Callback**
- Add print statements around `SH.start_background_job` call
- Log the returned job ID
- Check if status div is being updated

**Approach C: Simplify Job ID Display**
- Ensure status div shows full job ID (no ellipsis)
- Add data attribute with job ID to button or container
- Use fixed-position status element that's always visible

### Priority 2: Enable Test Mode

**Approach A: Add Hidden Control**
```python
html.Div(id='test-mode-flag', style={'display': 'none'}, children=False)
```
- Read `test-mode-flag` value in callback
- Playwright sets via: `page.evaluate("document.getElementById('test-mode-flag').innerText = 'true'")`
- Pass to job_params: `{'test_mode': test_mode_flag}`

**Approach B: URL-based Store**
```python
dcc.Location(id='url'),
dcc.Store(id='url-params'),

@app.callback(Output('url-params', 'data'), Input('url', 'search'))
def parse_url_params(search):
    return {'test_mode': 'test_mode=short' in (search or '')}
```

**Approach C: Environment Variable**
```bash
docker compose down
TEST_MODE=1 docker compose up -d dash_app
```
- Backend reads `os.environ.get('TEST_MODE')`
- Forces test mode for all runs
- Requires restart between test/production

### Priority 3: Full E2E Validation

Once job creation is fixed:

1. Run loop validator with working job ID extraction
2. Verify test mode reduces runtime to <60s
3. Achieve 3 consecutive successful runs
4. Generate final validation report
5. Commit artifacts and documentation

## Usage

### Run Loop Validator

```bash
# Standard validation (3 of 5 runs must pass)
python scripts/test_backtest_loop.py --debug --max-runs 5 --min-passes 3 --timeout 120

# Quick validation (2 of 3 runs must pass)
python scripts/test_backtest_loop.py --debug --max-runs 3 --min-passes 2 --timeout 180

# With visible browser for debugging
python scripts/test_backtest_loop.py --debug --max-runs 3 --min-passes 2 --timeout 180 --no-headless
```

### Inspect Artifacts

```bash
# View summary report
cat test-artifacts/backtest-automation/VALIDATION_REPORT.md

# View JSON metrics
cat test-artifacts/backtest-automation/metrics.json | jq .

# View run logs
tail -100 test-artifacts/backtest-automation/run1_logs.txt

# Open screenshots
open test-artifacts/backtest-automation/run1_*.png
```

### Set Job Timeout

```bash
# Increase timeout to 5 minutes for long-running tests
export JOB_TIME_LIMIT=300
docker compose restart dash_app

# Or set in docker-compose.yml
environment:
  - JOB_TIME_LIMIT=300
```

## Files Modified

1. **`financial_dashboard/market_trends_dash.py`** - Added test_mode support
2. **`financial_dashboard/_shared.py`** - Made job timeout configurable via JOB_TIME_LIMIT
3. **`scripts/test_backtest_loop.py`** - Created comprehensive loop validator

## Files Created

1. **`scripts/test_backtest_loop.py`** - Main validation script
2. **`PHASE_6D_AUTOMATED_BACKTEST_VALIDATION.md`** - This documentation

## Success Criteria

- [ ] Job creation and ID extraction working (0/1)
- [  ] Test mode activated and functioning (0/1)
- [ ] 3 consecutive runs complete successfully (0/3)
- [ ] Each run completes under 60s in test mode (N/A)
- [ ] /_job_status endpoint transitions correctly (0/1)
- [ ] No Playwright errors in any run (3/3) ✅
- [ ] All artifacts generated correctly (3/3) ✅

## Troubleshooting

### Button Clicks But No Job Starts

**Check backend logs:**
```bash
docker compose logs dash_app --tail 50 | grep -E "(BACKGROUND JOB|ATTEMPT|SUCCESS|EXCEPTION)"
```

**Look for:**
- "ATTEMPT: Invoking SH.start_background_job..." - Job creation attempt
- "SUCCESS: SH.start_background_job returned job_id: ..." - Job created
- "EXCEPTION in start_background_job: ..." - Job creation failed

**Common causes:**
- target_fn is None (module not loaded)
- kwargs has wrong format
- Exception in job initialization

### Job ID Not Appearing in DOM

**Check if status div updates:**
```python
# In callback after SH.start_background_job:
return (
    no_update, no_update,
    f"Started job {started_job_id}",  # This should show in status div
    {'display': 'block'},
    no_update
)
```

**Debug extraction:**
```python
page.wait_for_timeout(5000)
html = page.content()
print("Full HTML around status:")
print(html[html.find('id="status"')-100:html.find('id="status"')+500])
```

### Test Mode Not Activating

**Verify query param reaches page:**
```javascript
// In browser console:
console.log(window.location.search);  // Should show "?test_mode=short"
```

**Check if callback receives it:**
```python
# Add to callback:
logger.critical(f"TEST_MODE_DEBUG: analysis_options={analysis_options}, opts={opts}")
```

**Workaround:**
```bash
# Force test mode via environment
echo "TEST_MODE=1" >> doppler.env
docker compose restart dash_app
```

## References

- [Dash Callbacks](https://dash.plotly.com/basic-callbacks)
- [Playwright Python API](https://playwright.dev/python/docs/api/class-page)
- [Job Status Endpoint Implementation](financial_dashboard/index.py:63-77)
- [Test Mode Backend Support](financial_dashboard/market_trends_dash.py:300-325)

---

**Last Updated:** 2025-10-23 20:59 UTC  
**Next Review:** After job ID extraction fix
