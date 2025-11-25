# Playwright Analysis Heuristics Documentation

**Phase 31 Agent 1A - STEP 6**  
**File:** `tests/playwright/options_button_audit.py`  
**Purpose:** Immediate per-element analysis rules for Options Lab validation

---

## Analysis Rules (Evaluated in Order)

### RULE 1: Action Success
**Criterion:** `action_result['success'] == True`  
**Verdict:** If False → FAIL with "Action failed: {error}"  
**Rationale:** Cannot validate side effects if action didn't execute

### RULE 2: Console Errors
**Criterion:** `console_errors` list contains errors during test  
**Verdict:** If errors present → FAIL with "Console errors detected: N errors"  
**Artifacts:** `analysis['metrics']['console_errors']` contains full log  
**Rationale:** JavaScript errors indicate broken functionality

### RULE 3: Graph Data Validation (for `type == 'graph'`)
**Criterion:** 
- Pre and post Plotly data captured via `page.evaluate()`
- Data structure valid (no NaN, expected shape)
- Trace count comparison

**Verdicts:**
- Invalid data → FAIL with "Graph data invalid: {reason}"
- Data changed → PASS with "Graph data changed: {change_type}"

**Metrics:**
- `analysis['metrics']['graph']['valid']`: Boolean
- `analysis['metrics']['graph']['changed']`: Boolean
- `analysis['metrics']['graph']['change_type']`: Description

**Future Enhancement:** L2 norm for numeric data arrays

### RULE 4: Table Row Count (for `type == 'table'`)
**Criterion:** Count `<tr` tags in pre vs post DOM  
**Verdict:** If row_diff > 0 → PASS with "Table rows changed: A → B"  
**Metrics:** `analysis['metrics']['table_row_diff']`  
**Rationale:** Table updates indicate data loading/filtering worked

### RULE 5: Input Value Change (for `type == 'input'`)
**Criterion:** `action_result['value']` contains filled value  
**Verdict:** If value present → PASS with "Input filled with: {value}"  
**Rationale:** Input fill is the expected side effect

### RULE 6: General DOM Change Detection
**Criterion:** `abs(len(post_dom) - len(pre_dom)) > 100` bytes  
**Verdicts:**
- dom_diff > 100 → PASS with "Action triggered DOM change (N bytes)"
- dom_diff ≤ 100 → PASS with "Action performed, minimal DOM change (N bytes)"

**Metrics:** `analysis['metrics']['dom_diff_bytes']`  
**Rationale:** Even minimal changes pass if action succeeded

---

## Console Monitoring

**Implementation:**
- `context.on('console', self._on_console)` captures all browser messages
- `self.console_errors` list cleared before each element test
- Entries stored with timestamp, type, text

**Error Types:**
- `error`: JavaScript exceptions, uncaught errors → FAIL
- `warning`: Network failures, deprecations → logged but don't fail

---

## Graph Data Capture

**Method:** `_capture_plotly_data(elem_id)`  
**JavaScript:**
```javascript
() => {
  const elem = document.querySelector('#<elem_id>');
  if (!elem || !elem.data) return null;
  return JSON.stringify(elem.data);
}
```

**Returns:** Plotly `data` array (traces) or `null`  
**Stored in:** `result['artifacts']['graph_data_pre']`, `result['artifacts']['graph_data_post']`

---

## Expected Side Effects by Element Type

| Element Type | Expected Side Effect | Pass Criteria |
|--------------|---------------------|---------------|
| `button` | DOM change, network call, or graph update | dom_diff > 100 OR graph changed |
| `input` | Value populated | action_result contains value |
| `dropdown` | Options visible, selection changes table/graph | dom_diff > 100 OR graph/table changed |
| `graph` | Plotly data updated | Graph trace count changed OR data values differ |
| `table` | Row count change | `<tr` count differs pre→post |

---

## Artifact Storage

**Per Element:**
- `screenshots/`: `<id>_pre.png`, `<id>_post.png`
- `dom/`: `<id>_pre.html`, `<id>_post.html`
- `playwright/element_results.json`: Aggregated verdicts

**Full Run:**
- `playwright/full_audit.har`: Network traces for all elements
- `playwright/videos/`: Screen recordings (if enabled)

---

## Pass/Fail Thresholds

| Metric | Pass Threshold | Fail Threshold |
|--------|---------------|----------------|
| Action success | True | False |
| Console errors | 0 errors | ≥1 error |
| DOM diff | ≥0 bytes (permissive) | N/A (action success is primary) |
| Graph trace count | Any change detected | Invalid data structure |
| Table rows | Any change detected | N/A |

**Philosophy:** Prefer false positives (passing broken elements) over false negatives (failing working elements). Repair loop (STEP 7) will catch real failures via manual validation.

---

## Next: STEP 7 - Automated Repair Loop

Elements that fail analysis will trigger:
1. **Attempt 1:** WAIT & RETRY (90s timeout)
2. **Attempt 2:** CSS VISIBILITY FIX (force display/opacity)
3. **Attempt 3:** CALLBACK WIRING (add error handling)

Each attempt re-runs `--single-id <id>` and updates `element_results.json`.
