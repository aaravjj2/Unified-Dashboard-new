# BLOCKER: STEP 4 - Playwright Browser Crash on Options Lab Load

**Status:** BLOCKED  
**Severity:** CRITICAL  
**Timestamp:** 2025-01-20T21:21:00Z

---

## Summary

Full headed Playwright audit of Options Lab cannot proceed due to browser instability. Both initial run and Repair Attempt 1 show systematic failure:

- **Initial Run:** 4/45 passed (8.9%), browser crashed after element 6
- **Repair Attempt 1:** 0/45 passed (0.0%), browser closed immediately

---

## Root Cause

Subtab navigation logic attempts to click containers by `[tab_id="..."]` selector, which are NOT clickable elements. This causes:
1. Timeout warnings on every subtab switch attempt
2. Browser becomes unresponsive
3. "Target page, context or browser has been closed" errors

**Evidence:**
```
Could not switch to subtab chain-viewer: Timeout 5000ms exceeded
Could not switch to subtab greeks-dashboard: Target page, context or browser has been closed
```

---

## Repair Attempts

**Attempt 1:** Extended timeouts (5s→15s, 45s→90s)  
**Result:** FAILED - 0/45 passed (worse than initial 4/45)  
**Conclusion:** Timeouts not the issue - subtab navigation logic fundamentally broken

---

## Recommended Fix (Not Implemented)

Skip subtab navigation entirely:
```python
# Comment out lines 177-179 in options_button_audit.py
# subtab = self._get_subtab_for_element(elem_id)
# if subtab:
#     await self._ensure_subtab_active(subtab)
```

---

## Decision Required

1. **Fix subtab navigation** (requires identifying correct tab button selectors)
2. **Skip subtab logic** (accept partial results - only visible elements tested)
3. **Manual testing** (screenshot each subtab manually for evidence)

