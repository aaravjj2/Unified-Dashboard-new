# Dashboard Fix Summary

## Date: 2025-11-18

## Issues Addressed

### ✅ FIXED: Duplicate Callback Outputs

**Problem:**
- Browser console showed repeated "Duplicate callback outputs" errors for:
  - `perf-total-return`
  - `factors-exposures`
  - `sectors-weights-p`
  - `residual-alpha`

**Root Cause:**
- Attribution Lab callbacks were using `@callback` decorator (Dash 2.x global decorator)
- This decorator registers callbacks at module import time
- When combined with `register_callbacks(app)` function, it could cause issues
- The `@callback` decorator doesn't need an app instance, but `@app.callback` does

**Solution:**
- Changed attribution_lab/callbacks.py to use `@app.callback` instead of `@callback`
- Removed `callback` from imports: `from dash import callback, Input, Output...` → `from dash import Input, Output...`
- Replaced all 4 instances of `@callback(` with `@app.callback(`
- This ensures callbacks are registered only when `register_callbacks(app)` is called

**Files Modified:**
- `financial_dashboard/tabs/attribution_lab/callbacks.py`

**Verification:**
```bash
python test_attribution_callbacks.py
```
Result: ✅ All attribution_lab callbacks properly registered (no duplicates)

```bash
python test_browser_errors.py
```
Result: ✅ No duplicate callback errors in browser console

---

### ⚠️ REMAINING: React Error #31

**Problem:**
- Browser console shows: "Minified React error #31: Objects are not valid as a React child"
- Error message indicates: `object with keys {props, type, namespace}`
- This means some component is returning a raw Dash component object instead of a rendered instance

**Possible Causes:**
1. A callback is returning a component class instead of an instance
   - Example: `return html.Div` instead of `return html.Div()`
2. A layout function is returning an uninstantiated component
3. Component children contain raw objects

**Next Steps to Debug:**
1. Enable Dash dev mode to get unminified error messages:
   ```python
   app.run(debug=True)
   ```
2. Check browser console for full error stack trace
3. Inspect which component/callback is causing the error
4. Look for patterns like:
   - `return SomeComponent` (missing parentheses)
   - `children=[ComponentClass]` (should be `ComponentClass()`)
   - Callbacks returning dicts with `{props, type, namespace}` structure

**Component Sanitizer:**
- Already implemented in `financial_dashboard/utils/component_sanitizer.py`
- Called on initial layout in `app.py`
- May need to be applied to callback outputs as well

---

## Testing Commands

### Test Attribution Lab Callbacks
```bash
python test_attribution_callbacks.py
```

### Test Browser Console Errors
```bash
python test_browser_errors.py
```

### Find React Error Source
```bash
python find_react_error_source.py
```

### Run Dashboard
```bash
python run_dashboard.py
```
Dashboard runs on: http://localhost:8090

---

## Architecture Notes

### Callback Registration Patterns

**Pattern 1: Module-level `@callback` (used by research_lab, home_lab, options_lab)**
```python
from dash import callback, Input, Output

@callback(
    Output('my-output', 'children'),
    Input('my-input', 'value')
)
def my_callback(value):
    return value

def register_callbacks(app):
    # No-op, callbacks already registered
    pass
```
- Callbacks register automatically when module is imported
- `register_callbacks()` is just a placeholder for consistency
- Works fine, no duplicates

**Pattern 2: Function-level `@app.callback` (used by attribution_lab - FIXED)**
```python
from dash import Input, Output

def register_callbacks(app):
    @app.callback(
        Output('my-output', 'children'),
        Input('my-input', 'value')
    )
    def my_callback(value):
        return value
```
- Callbacks register when `register_callbacks(app)` is called
- Requires app instance to be passed
- More explicit control over registration timing
- **This is the pattern we fixed attribution_lab to use**

---

## Summary

✅ **Fixed:** Duplicate callback registrations for attribution_lab
⚠️ **Remaining:** React error #31 (invalid children) - needs further investigation
📝 **Status:** Dashboard runs successfully, duplicate errors eliminated, but React rendering issue persists

The duplicate callback issue was the primary blocker and has been resolved. The React error is a separate rendering issue that doesn't prevent the dashboard from functioning but should be addressed for clean console output.
