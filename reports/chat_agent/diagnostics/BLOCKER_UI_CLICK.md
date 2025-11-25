# BLOCKER: Chat Toggle Button Click Intercepted

## Issue
Playwright cannot click `#chatbot-toggle-btn` - it's being intercepted by another element (likely the `#chatbot-mini-bar` or overlapping FAB).

## Error
```
<button id="chatbot-toggle-btn" aria-label="chat toggle">…</button> intercepts pointer events
```

## Impact
Cannot test chat widget opening via standard Playwright click().

## Workaround Attempted for PHASE 0
- Used JavaScript evaluation to directly check color of diagnostic element
- Validated CSS is loaded and color rules are in effect
- Screenshot captured showing chat widget in DOM

## Root Cause
Duplicate `#chatbot-toggle-btn` elements or z-index/positioning conflict between:
1. Floating action button (FAB)
2. Mini chat bar
3. Assets-level early toggle button

## Required Fix for PHASE 6 (Headful Tests)
Before Playwright HEADFUL validation can proceed:
1. Remove duplicate `#chatbot-toggle-btn` IDs or
2. Use `force: true` option in Playwright click or
3. Use JavaScript click: `page.evaluate("document.querySelector('#chatbot-toggle-btn').click()")`
4. Or revise UI to have non-overlapping clickable area

## Current Status
PHASE 0 proceeding with alternative validation method (direct color evaluation without click).
