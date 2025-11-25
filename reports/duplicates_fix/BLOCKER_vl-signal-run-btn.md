# BLOCKER REPORT: Run Signals

**Button ID:** vl-signal-run-btn  
**Tab:** volatility_lab  
**Expected Effect:** network_call  
**Attempts:** 3  
**Status:** ❌ FAILED

## Verdict

❌ FAIL: Button not visible

## Error

```
Button not visible
```

## Artifacts

- Pre-screenshot: `N/A`
- Post-screenshot: `N/A`
- DOM snapshot: `N/A`
- Console log: `N/A`
- Network log: `N/A`

## Analysis

- DOM Changed: False
- Network Activity: False
- Console Errors: False

## Recommended Next Steps

1. Inspect screenshots for visual differences
2. Review DOM snapshot for structural changes
3. Check console log for JavaScript errors
4. Verify callback is registered and firing
5. Check network log for failed API calls

## Manual Verification

Open the dashboard and:
1. Navigate to **volatility_lab** tab
2. Click **Run Signals** button
3. Observe expected behavior: **network_call**
