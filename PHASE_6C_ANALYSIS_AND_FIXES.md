# Phase 6C: Portfolio & Forecast Integration - Issue Analysis & Fixes

**Date:** October 24, 2025  
**Status:** Investigation Complete, Fixes Documented

---

## Executive Summary

**Key Findings:**
1. ✅ **Alpaca API is Working** - 40 positions, $93K portfolio value accessible
2. ✅ **SHAP Generation Fixed** - All 40 tickers have SHAP data (Phase 6 complete)
3. ⚠️  **Portfolio Positions Tab** - Data store may not populate on initial tab load
4. ⚠️  **Optimize Portfolio Button** - Callback registered but needs verification
5. ❌ **Market Forecast Tab** - Not yet implemented

---

## Issue 1: Portfolio Positions Table Not Displaying

### Root Cause Analysis

**Diagnostic Results:**
```
✅ Alpaca API Connection: SUCCESS
   Portfolio Value: $93,005.50
   Positions Count: 40
   Sample: AAPL (1.91 shares), AMD (2.11 shares), APH (3.76 shares)...

⚠️  Portfolio Cache: STALE
   Last Updated: 2025-10-15
   Positions: 20 (outdated)
   
✅ Attribution Files: EXISTS
   Path: /app/financial_dashboard/attribution/latest_portfolio.json
   Positions: 0 (empty)
```

**Callback Flow:**
```python
portfolio_tracker_refactored.py:
  update_portfolio_summary() 
    → fetches from Alpaca
    → populates 'portfolio-data-store'
    → triggers: Input('portfolio-refresh-btn')
                Input('portfolio-interval')  
                Input('portfolio-load-trigger')

portfolio_positions.py:
  update_positions_table()
    → reads 'portfolio-data-store'
    → displays table
    → triggers: Input('portfolio-data-store', 'data')
                Input('dashboard-tabs', 'active_tab')
```

**Issue:** The `portfolio-data-store` may not be populated on initial page load because:
1. `portfolio-load-trigger` fires with `data=1` on mount
2. But if Alpaca API is slow or times out, the store remains empty
3. Positions tab callback sees empty store → shows "No positions found"

### Fix 1: Add Fallback Data Loading

**File:** `financial_dashboard/tabs/portfolio_positions.py`

**Change:** Update `update_positions_table()` callback to fetch from Alpaca directly if store is empty:

```python
@app.callback(
    Output('portfolio-positions-table', 'children'),
    [Input('portfolio-data-store', 'data'),
     Input('dashboard-tabs', 'active_tab')],
    prevent_initial_call=False
)
def update_positions_table(portfolio_data, active_tab):
    """Update positions table with fallback to direct Alpaca fetch."""
    logger.info(f"🔥 Positions callback fired! portfolio_data={'present' if portfolio_data else 'None'}, active_tab={active_tab}")
    
    # PHASE 6C FIX: Fallback to direct Alpaca fetch if store is empty
    if not portfolio_data or not portfolio_data.get('positions'):
        logger.warning("⚠️  No positions data in store - attempting direct Alpaca fetch")
        
        try:
            from tabs.portfolio_tracker_refactored import get_alpaca_client
            client = get_alpaca_client()
            
            if client:
                positions = client.get_all_positions()
                
                # Build positions data
                positions_data = []
                for pos in positions:
                    positions_data.append({
                        'symbol': pos.symbol,
                        'qty': float(pos.qty),
                        'avg_entry_price': float(pos.avg_entry_price),
                        'current_price': float(pos.current_price),
                        'cost_basis': float(pos.cost_basis),
                        'market_value': float(pos.market_value),
                        'unrealized_pl': float(pos.market_value) - float(pos.cost_basis),
                        'unrealized_plpc': float(pos.unrealized_plpc) * 100
                    })
                
                # Create temporary portfolio_data structure
                portfolio_data = {'positions': positions_data}
                logger.info(f"✅ Fetched {len(positions_data)} positions directly from Alpaca")
            else:
                # Try loading from cache as last resort
                logger.warning("❌ Alpaca client unavailable - trying cache")
                cache_path = Path(__file__).parent.parent / 'cache' / 'portfolio_data.json'
                
                if cache_path.exists():
                    with open(cache_path, 'r') as f:
                        cached = json.load(f)
                        portfolio_data = cached
                    logger.info(f"✅ Loaded {len(portfolio_data.get('positions', []))} positions from cache")
                else:
                    logger.error("❌ No cache file available")
                    return html.P("No positions found. Click refresh button to load from Alpaca.", 
                                  className="text-muted")
        
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return html.P(f"Error loading positions: {str(e)}", className="text-danger")
    
    # Rest of existing logic continues...
    positions = portfolio_data['positions']
    df = pd.DataFrame(positions)
    # ... (existing table generation code)
```

**Benefits:**
- ✅ Handles empty store gracefully
- ✅ Auto-fetches from Alpaca if store not populated
- ✅ Fallback to cache if Alpaca unavailable
- ✅ User sees positions immediately on tab load

---

## Issue 2: Optimize Portfolio Button Not Working

### Root Cause Analysis

**Button Location:** `financial_dashboard/tabs/portfolio_optimization.py:77`

**Callback:** `run_optimization()` on line 100
- ✅ Callback is registered
- ✅ Button ID matches: `opt-run-btn`
- ⚠️  Uses synchronous optimization (blocks UI)
- ❌ Does NOT use `start_background_job()` from job queue

**Expected Behavior:**
1. User clicks "Optimize Portfolio"
2. Job queued via `start_background_job()`
3. Polling callback checks job status
4. UI updates when complete

**Actual Behavior:**
1. User clicks "Optimize Portfolio"
2. Optimization runs synchronously in callback
3. Browser waits 10-30 seconds (appears frozen)
4. Results appear all at once

### Fix 2: Implement Background Job for Optimization

**File:** `financial_dashboard/tabs/portfolio_optimization.py`

**Changes Required:**

1. **Import job queue utilities:**
```python
from utils.job_queue import start_background_job, get_job_status, get_job_result
```

2. **Split callback into two parts:**

```python
@app.callback(
    [Output('opt-job-status', 'data'),
     Output('opt-run-btn', 'disabled')],
    [Input('opt-run-btn', 'n_clicks')],
    [State('opt-tickers-input', 'value'),
     State('opt-strategy', 'value'),
     State('opt-period-slider', 'value'),
     State('portfolio-data-store', 'data')]
)
def start_optimization_job(n_clicks, tickers_input, strategy, period_days, portfolio_data):
    """Start optimization as background job."""
    if not n_clicks or n_clicks == 0:
        raise PreventUpdate
    
    # Parse tickers
    if not tickers_input:
        if portfolio_data and portfolio_data.get('positions'):
            tickers = [pos['symbol'] for pos in portfolio_data['positions']]
        else:
            raise PreventUpdate
    else:
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    
    if len(tickers) < 2:
        raise PreventUpdate
    
    # Queue optimization job
    job_id = start_background_job(
        'optimize_portfolio',
        tickers=tickers,
        strategy=strategy,
        period_days=period_days,
        risk_free_rate=0.04
    )
    
    logger.info(f"🚀 Started optimization job: {job_id}")
    
    return {'job_id': job_id, 'status': 'running'}, True  # Disable button


@app.callback(
    [Output('opt-results-container', 'children'),
     Output('opt-run-btn', 'disabled', allow_duplicate=True)],
    [Input('opt-poll-interval', 'n_intervals')],
    [State('opt-job-status', 'data')],
    prevent_initial_call=True
)
def poll_optimization_results(n_intervals, job_status):
    """Poll for optimization job completion."""
    if not job_status or job_status.get('status') == 'completed':
        raise PreventUpdate
    
    job_id = job_status['job_id']
    status = get_job_status(job_id)
    
    if status == 'running':
        return html.Div([
            dbc.Spinner(color="primary"),
            html.P(f"Optimizing portfolio... (Job: {job_id})", className="text-muted mt-2")
        ]), True  # Keep button disabled
    
    elif status == 'completed':
        result = get_job_result(job_id)
        
        if result and 'weights' in result:
            # Generate results visualization (existing code)
            return _build_optimization_results(result), False  # Re-enable button
        else:
            return dbc.Alert("Optimization failed. Check logs.", color="danger"), False
    
    elif status == 'failed':
        return dbc.Alert("Optimization job failed.", color="danger"), False
    
    raise PreventUpdate
```

3. **Add polling interval to layout:**
```python
def layout():
    return dbc.Container([
        # ... existing layout ...
        
        # Hidden stores for job status
        dcc.Store(id='opt-job-status', data=None),
        dcc.Interval(id='opt-poll-interval', interval=1000, n_intervals=0)  # Poll every 1s
    ], fluid=True)
```

**Benefits:**
- ✅ Non-blocking optimization (UI remains responsive)
- ✅ Progress indicator shown to user
- ✅ Button disabled during optimization
- ✅ Consistent with other dashboard async patterns

---

## Issue 3: Market Forecast Tab Missing

### Current State

**Status:** NOT IMPLEMENTED

**Required:** New file `financial_dashboard/tabs/market_forecast.py`

### Implementation Checklist

**Layout Components:**
- [ ] Ticker selector (dropdown, multi-select)
- [ ] Horizon selector (1-week, 1-month, 3-month)
- [ ] Forecast chart (expected return + confidence intervals)
- [ ] Probability chart (probability of positive return)
- [ ] Summary table (ticker, forecast, confidence)

**Backend Integration:**
- [ ] Connect to forecast module (utils/forecast.py or similar)
- [ ] Fetch forecast data for selected tickers
- [ ] Calculate confidence intervals
- [ ] Link to SHAP data for feature importance

**Stub Implementation:**

```python
"""
Market Forecast Tab - Predictive Analytics
Displays forecast returns, volatility, and confidence intervals for portfolio tickers
"""

import logging
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def layout():
    """Build forecast tab layout."""
    return dbc.Container([
        html.H5("Market Forecast", className="mt-3 mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Select Tickers:"),
                dcc.Dropdown(
                    id='forecast-ticker-selector',
                    multi=True,
                    placeholder="Select tickers to forecast..."
                )
            ], width=6),
            dbc.Col([
                html.Label("Forecast Horizon:"),
                dcc.Dropdown(
                    id='forecast-horizon',
                    options=[
                        {'label': '1 Week', 'value': 7},
                        {'label': '1 Month', 'value': 30},
                        {'label': '3 Months', 'value': 90}
                    ],
                    value=30
                )
            ], width=6)
        ], className="mb-4"),
        
        html.Div(id='forecast-charts-container'),
        html.Div(id='forecast-table-container')
        
    ], fluid=True)


def register_callbacks(app):
    """Register forecast tab callbacks."""
    
    @app.callback(
        Output('forecast-ticker-selector', 'options'),
        Input('portfolio-data-store', 'data')
    )
    def populate_ticker_options(portfolio_data):
        """Populate ticker dropdown from portfolio."""
        if not portfolio_data or not portfolio_data.get('positions'):
            return []
        
        tickers = [pos['symbol'] for pos in portfolio_data['positions']]
        return [{'label': t, 'value': t} for t in sorted(tickers)]
    
    @app.callback(
        [Output('forecast-charts-container', 'children'),
         Output('forecast-table-container', 'children')],
        [Input('forecast-ticker-selector', 'value'),
         Input('forecast-horizon', 'value')]
    )
    def update_forecast(selected_tickers, horizon):
        """Generate forecast charts and table."""
        if not selected_tickers:
            return html.P("Select tickers to view forecast", className="text-muted"), None
        
        # TODO: Connect to forecast backend
        # For now, return placeholder
        return (
            dbc.Alert("Forecast module integration pending", color="info"),
            None
        )
```

**Integration Steps:**
1. Add to `financial_dashboard/tabs/__init__.py`
2. Import in `index.py`
3. Add tab to dashboard layout
4. Register callbacks

---

## Issue 4: SHAP Coverage for 40 Tickers

### Status: ✅ COMPLETE (Phase 6)

**Validation:**
```bash
$ docker compose exec -T dash_app python3 /app/scripts/generate_full_portfolio_shap.py

✅ Generated: 40 / 40 tickers
   Features: 8 per ticker
   File: /app/financial_dashboard/explain/picks_explain_20251023.json
   Size: 85 KB
```

**Tickers Covered:**
```
AAPL, AMD, APH, ARWR, ASTS, AVAV, AVGO, BE, BEAM, CAT,
CGON, CIFR, DIS, EA, ETSY, GEV, GLW, HOOD, HUT, INOD,
INTC, JNJ, KLAC, LRCX, MU, NEM, ORCL, PL, PLUG, QS,
RGTI, SMCI, SNDK, STX, SYM, TPR, TSLA, UNH, WBD, WDC
```

**No action required** - SHAP generation is working correctly.

---

## Issue 5: Debug Logs Panel Missing

### Requirement

**Functionality:**
- Real-time log viewer showing backtest, SHAP, optimizer, forecast events
- Filterable by module/severity
- Timestamp and error capture
- Accessible via button in Portfolio tab

### Implementation Approach

**Option 1: WebSocket Log Streaming**
- Stream logs from Python logging to frontend via WebSocket
- Real-time updates
- Complex implementation

**Option 2: Polling Log File**
- Write logs to file, poll periodically
- Simple implementation
- Slight delay (acceptable for debugging)

**Recommended: Option 2**

```python
# In portfolio_positions.py or shared location

def layout():
    return dbc.Container([
        # ... existing layout ...
        
        dbc.Button(
            [html.I(className="fas fa-bug me-2"), "Debug Logs"],
            id='show-debug-logs-btn',
            color='secondary',
            size='sm',
            className='mb-2'
        ),
        
        dbc.Modal([
            dbc.ModalHeader("Live Debug Logs"),
            dbc.ModalBody(id='debug-logs-content', style={'maxHeight': '500px', 'overflowY': 'scroll'}),
            dbc.ModalFooter(
                dbc.Button("Close", id='close-debug-logs-btn')
            )
        ], id='debug-logs-modal', size='xl', is_open=False)
    ])


@app.callback(
    [Output('debug-logs-modal', 'is_open'),
     Output('debug-logs-content', 'children')],
    [Input('show-debug-logs-btn', 'n_clicks'),
     Input('close-debug-logs-btn', 'n_clicks'),
     Input('debug-logs-refresh-interval', 'n_intervals')],
    [State('debug-logs-modal', 'is_open')]
)
def toggle_debug_logs(show_clicks, close_clicks, n_intervals, is_open):
    """Show/hide debug logs modal with live updates."""
    ctx = callback_context
    
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'show-debug-logs-btn':
        return True, _load_recent_logs()
    elif trigger_id == 'close-debug-logs-btn':
        return False, None
    elif trigger_id == 'debug-logs-refresh-interval' and is_open:
        return is_open, _load_recent_logs()
    
    raise PreventUpdate


def _load_recent_logs():
    """Load last 100 lines from log file."""
    import subprocess
    
    try:
        # Read last 100 lines from Docker logs
        result = subprocess.run(
            ['docker', 'compose', 'logs', '--tail=100', 'dash_app'],
            capture_output=True,
            text=True
        )
        
        log_lines = result.stdout.split('\n')[-100:]
        
        # Format as HTML
        log_elements = []
        for line in log_lines:
            if 'ERROR' in line:
                color = 'danger'
            elif 'WARNING' in line:
                color = 'warning'
            elif 'INFO' in line:
                color = 'info'
            else:
                color = 'secondary'
            
            log_elements.append(
                html.Pre(line, className=f'text-{color} mb-1', style={'fontSize': '0.85rem'})
            )
        
        return html.Div(log_elements)
    
    except Exception as e:
        return html.P(f"Error loading logs: {e}", className="text-danger")
```

---

## Quick Win Fixes Summary

### Priority 1: Portfolio Positions Display (CRITICAL)

**File:** `financial_dashboard/tabs/portfolio_positions.py`

**Action:** Add fallback Alpaca fetch in `update_positions_table()` callback

**Impact:** ✅ Positions visible on first tab load

**Effort:** 30 minutes

---

### Priority 2: Optimize Portfolio Async (HIGH)

**File:** `financial_dashboard/tabs/portfolio_optimization.py`

**Action:** Convert to background job with polling callback

**Impact:** ✅ UI remains responsive during optimization

**Effort:** 1-2 hours

---

### Priority 3: Market Forecast Tab (MEDIUM)

**File:** NEW - `financial_dashboard/tabs/market_forecast.py`

**Action:** Create stub layout + placeholder callbacks

**Impact:** ✅ Tab exists, backend integration TBD

**Effort:** 2-3 hours

---

### Priority 4: Debug Logs Panel (LOW)

**File:** `financial_dashboard/tabs/portfolio_positions.py`

**Action:** Add modal with log polling

**Impact:** ✅ Developer debugging improved

**Effort:** 1-2 hours

---

## E2E Testing Plan

### Test Scenario 1: Portfolio Positions Load

**Steps:**
1. Open dashboard at http://localhost:8050
2. Navigate to Portfolio tab
3. Click Positions sub-tab
4. **Expected:** Table shows 40 positions within 5 seconds
5. **Verify:** Tickers match Alpaca positions
6. **Verify:** Market Trends columns populated

### Test Scenario 2: SHAP Inspect Modal

**Steps:**
1. In Positions tab, click 🔍 Inspect on any ticker
2. **Expected:** Modal opens within 2 seconds
3. **Verify:** Model score displayed
4. **Verify:** Top 3 SHAP features shown
5. **Verify:** Recent news loaded

### Test Scenario 3: Optimize Portfolio

**Steps:**
1. Navigate to Portfolio → Optimization tab
2. Verify tickers pre-populated from portfolio
3. Select strategy: "Maximize Sharpe Ratio"
4. Click "Optimize Portfolio"
5. **Expected:** Button disables, spinner shows
6. **Expected:** Results appear within 30 seconds
7. **Verify:** Weights chart displays
8. **Verify:** Efficient frontier chart shows

### Test Scenario 4: SHAP Regeneration

**Steps:**
1. In Positions tab, click "Regenerate SHAP Data"
2. **Expected:** Button shows loading state
3. **Expected:** Success alert shows "40/40 tickers"
4. **Verify:** Inspect modal SHAP data updated

---

## Reproducibility Artifacts

### Diagnostic Script

**Location:** `/app/scripts/diagnose_portfolio_data.py`

**Usage:**
```bash
docker compose exec -T dash_app python3 /app/scripts/diagnose_portfolio_data.py
```

**Output:** Shows Alpaca connection, cache status, attribution files

---

### Portfolio Data Snapshot

**Location:** `/app/financial_dashboard/cache/portfolio_data.json`

**Generated:** 2025-10-24

**Contains:** 40 positions from live Alpaca account

---

### SHAP Data Files

**Location:** `/app/financial_dashboard/explain/picks_explain_20251023.json`

**Generated:** Phase 6

**Coverage:** 40/40 tickers, 8 features each

---

## Known Limitations

1. **Alpaca Data Subscription:** Some tickers show "subscription does not permit querying recent SIP data" warnings
   - **Impact:** Historical data fetch may fail for certain tickers
   - **Workaround:** Use yfinance as fallback

2. **Cache Staleness:** Portfolio cache not auto-refreshed
   - **Impact:** May show outdated positions if Alpaca unavailable
   - **Workaround:** Manual refresh button

3. **Market Forecast:** Backend not implemented
   - **Impact:** Tab shows placeholder
   - **Workaround:** Stub layout prevents UI errors

4. **Debug Logs:** No persistent log storage
   - **Impact:** Logs lost on container restart
   - **Workaround:** Use `docker compose logs` for history

---

## Next Steps

1. **Implement Priority 1 Fix** (Portfolio Positions fallback) - CRITICAL
2. **Test E2E Scenario 1 & 2** - Validate positions and SHAP
3. **Implement Priority 2 Fix** (Optimize Portfolio async) - HIGH
4. **Create Market Forecast stub** - MEDIUM
5. **Run full E2E test suite** - Capture screenshots + artifacts
6. **Document final results** - Update PHASE_6C_PORTFOLIO_FORECAST.md

---

**Status:** Ready for implementation  
**Estimated Completion:** Priority 1-2 fixes = 2-3 hours  
**Full Phase 6C:** 6-8 hours with testing + documentation
