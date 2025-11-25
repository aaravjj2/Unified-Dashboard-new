# Test Selector Fix Guide

**Guide for updating E2E test selectors to match actual dashboard components**

---

## 🎯 Overview

Phase 2 testing identified 5 tabs with selector mismatches. This guide provides systematic steps to fix each selector and validate the fixes.

---

## 📋 Failed Selectors Summary

| Tab | Current Selector | Issue | Confidence |
|-----|------------------|-------|------------|
| Home Lab | `a:has-text('Home')` | Text mismatch | High - likely has icon |
| Volatility Lab | `#vl-ticker-input` | ID not found | Medium - may use different namespace |
| Research Lab | `button:has-text('Historical Price')` | Element hidden | High - accordion/collapse |
| Attribution Lab | `button:has-text('Factor Exposure')` | Element hidden | High - accordion/collapse |
| Options Lab | `#ol-ticker-input` | ID not found | Medium - may use different namespace |

---

## 🔧 Fixing Process (Step-by-Step)

### Step 1: Inspect Actual Elements

1. **Start Dashboard:**
   ```bash
   docker-compose up -d
   # Wait for health check
   curl http://localhost:8050
   ```

2. **Open in Browser:**
   ```
   http://localhost:8050
   ```

3. **Open DevTools:**
   - Press `F12` or `Ctrl+Shift+I`
   - Go to "Elements" or "Inspector" tab

4. **Locate Target Elements:**
   - Click "Select Element" tool (top-left corner icon)
   - Click on the element you want to test
   - Note the actual ID, class, and text content

### Step 2: Test Selectors in Console

**Console Testing Pattern:**
```javascript
// Test selector (returns element if found)
document.querySelector('a:has-text("Home")')

// Alternative: query by ID
document.querySelector('#vl-ticker-input')

// Check all matching elements
document.querySelectorAll('button')
```

**Pro Tip:** Use Playwright's selector tester:
```python
# In Python console
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('http://localhost:8050')
    
    # Test selector
    element = page.locator('a:has-text("Home")')
    print(element.count())  # Should be > 0 if found
```

### Step 3: Update Test Configuration

**File to Edit:** `tests/phase2_comprehensive_e2e.py`

**Location:** Lines 25-180 (TAB_CONFIG array)

**Example Fix:**

```python
# BEFORE:
{
    'name': 'Home Lab',
    'selector': 'a:has-text("Home")',  # ❌ FAILING
    'checks': [
        {'type': 'visible', 'selector': '.portfolio-snapshot'}
    ]
}

# AFTER:
{
    'name': 'Home Lab',
    'selector': 'a:has-text("🏠 Home")',  # ✅ FIXED (added icon)
    'checks': [
        {'type': 'visible', 'selector': '.portfolio-snapshot'}
    ]
}
```

---

## 🔍 Tab-Specific Fixes

### Fix #1: Home Lab

**Issue:** Tab text likely includes icon or different casing

**Investigation Steps:**
1. Open dashboard in browser
2. Inspect the navigation tabs at top
3. Find the "Home" tab element
4. Check exact text content (may be "🏠 Home" or "HOME LAB")

**Possible Fixes:**
```python
# Option A: Include icon
'selector': 'a:has-text("🏠 Home")'

# Option B: Case-insensitive match
'selector': 'a[href="#/home"]'

# Option C: Data attribute (if available)
'selector': '[data-tab="home"]'

# Option D: Partial text match
'selector': 'a:has-text("Home")'  # May already work if icon removed
```

**Test Command:**
```python
page.locator('a:has-text("🏠 Home")').click()
```

---

### Fix #2: Volatility Lab Ticker Input

**Issue:** Input ID `#vl-ticker-input` not found

**Investigation Steps:**
1. Navigate to Volatility Lab tab
2. Inspect the ticker input field
3. Check actual ID attribute (may be different namespace)

**Possible Fixes:**
```python
# Option A: Correct ID
'selector': '#volatility-ticker-input'

# Option B: Placeholder attribute
'selector': 'input[placeholder*="ticker"]'

# Option C: Label association
'selector': 'label:has-text("Ticker") + input'

# Option D: Class-based
'selector': 'input.ticker-input'
```

**Test Command:**
```python
page.locator('#volatility-ticker-input').fill('AAPL')
```

---

### Fix #3: Research Lab Subtabs

**Issue:** Subtab buttons not clickable (hidden in accordion)

**Investigation Steps:**
1. Navigate to Research Lab
2. Check if subtabs are in collapsed accordion
3. Find parent container selector

**Root Cause:** Buttons may be hidden until parent tab activates

**Fix Strategy:**
```python
# BEFORE:
{
    'name': 'Historical Price',
    'selector': 'button:has-text("Historical Price")',
    'parent_tab': 'Research Lab'
}

# AFTER: Add wait or expand parent first
{
    'name': 'Historical Price',
    'selector': 'button:has-text("Historical Price")',
    'parent_tab': 'Research Lab',
    'wait_for': 'visible',  # Wait for visibility
    'expand_parent': True   # New flag to expand accordion
}
```

**Code Implementation:**
```python
# In test_subtab() method, add:
if subtab_config.get('expand_parent'):
    # Find and click accordion header
    accordion = page.locator('.accordion-header')
    accordion.click()
    page.wait_for_timeout(1000)  # Wait for expansion
```

---

### Fix #4: Attribution Lab Subtabs

**Issue:** Same as Research Lab (accordion hidden)

**Fix:** Apply same strategy as Fix #3

```python
# Update all Attribution Lab subtabs
for subtab in ['Factor Exposure', 'Return Attribution', 'Risk Attribution']:
    {
        'name': subtab,
        'selector': f'button:has-text("{subtab}")',
        'parent_tab': 'Attribution Lab',
        'expand_parent': True
    }
```

---

### Fix #5: Options Lab Ticker Input

**Issue:** Input ID `#ol-ticker-input` not found

**Investigation:** Same process as Fix #2

**Possible Fixes:**
```python
# Option A: Correct ID
'selector': '#options-ticker-input'

# Option B: Unique attribute
'selector': 'input[id*="options"][id*="ticker"]'

# Option C: Position-based (last resort)
'selector': '#options-lab input[type="text"]:first'
```

---

## 🧪 Validation Process

### Quick Single-Tab Test

**File:** `test_single_tab.py` (create new file)

```python
import asyncio
from playwright.async_api import async_playwright

async def test_single_selector():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('http://localhost:8050')
        
        # TEST YOUR SELECTOR HERE
        selector = 'a:has-text("🏠 Home")'
        
        try:
            element = page.locator(selector)
            count = await element.count()
            print(f"✅ Found {count} element(s) matching: {selector}")
            
            # Try clicking
            await element.click()
            await page.wait_for_timeout(2000)
            print("✅ Click successful")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await browser.close()

asyncio.run(test_single_selector())
```

**Run:**
```bash
python3 test_single_tab.py
```

### Full Test Re-run

**After fixing selectors:**

1. **Edit Phase 2 Test Suite:**
   ```bash
   nano tests/phase2_comprehensive_e2e.py
   # Update TAB_CONFIG with new selectors
   ```

2. **Run Single Iteration:**
   ```python
   # In phase2_comprehensive_e2e.py
   TOTAL_ITERATIONS = 1  # Change from 3 to 1
   ```

3. **Execute:**
   ```bash
   python3 tests/phase2_comprehensive_e2e.py
   ```

4. **Check Results:**
   ```bash
   cat outputs/phase2_e2e/reports/iteration_1_report.md | grep "Status:"
   ```

---

## 📊 Expected Outcomes

### After Fixes

**Target Success Rate:**
- Tabs: 8/8 (100%) ← currently 3/8
- Checks: 14/14 (100%) ← currently 12/14

**Validation:**
- All tabs should navigate successfully
- All screenshots should capture correct content
- No timeout errors in reports

---

## 🚨 Common Pitfalls

### 1. Dynamic Content Loading
**Problem:** Element exists but loads after navigation  
**Fix:** Add explicit wait
```python
await page.wait_for_selector(selector, state='visible', timeout=15000)
```

### 2. Shadow DOM Elements
**Problem:** Element inside shadow root  
**Fix:** Use pierce selector
```python
'selector': 'pierce/#vl-ticker-input'
```

### 3. iFrames
**Problem:** Element inside iframe  
**Fix:** Navigate into frame first
```python
frame = page.frame_locator('iframe[title="Dashboard"]')
await frame.locator(selector).click()
```

### 4. Overlapping Elements
**Problem:** Element blocked by another element  
**Fix:** Force click or scroll into view
```python
await page.locator(selector).click(force=True)
# OR
await page.locator(selector).scroll_into_view_if_needed()
```

---

## 📝 Checklist Template

**Use this for each selector fix:**

- [ ] Identified actual element in browser DevTools
- [ ] Tested selector in browser console
- [ ] Updated TAB_CONFIG in test suite
- [ ] Ran single-tab test to verify
- [ ] Documented fix in comments
- [ ] Re-ran full iteration to confirm
- [ ] Checked screenshot for correct content
- [ ] Verified no regressions in passing tabs

---

## 🎓 Selector Best Practices

### Priority Order (use in this sequence):

1. **data-testid attributes** (best - stable across refactors)
   ```python
   '[data-testid="home-tab"]'
   ```

2. **Unique IDs** (good - but may change)
   ```python
   '#home-tab'
   ```

3. **ARIA labels** (good - semantic)
   ```python
   'button[aria-label="Home Tab"]'
   ```

4. **Text content** (moderate - i18n issues)
   ```python
   'a:has-text("Home")'
   ```

5. **Class names** (weak - may change)
   ```python
   '.nav-tab.home'
   ```

6. **Position-based** (last resort - fragile)
   ```python
   'nav > a:nth-child(1)'
   ```

---

## 📞 Quick Reference

### Playwright Selector Documentation
https://playwright.dev/python/docs/selectors

### Test Selector
```bash
# In Playwright interactive mode
playwright codegen http://localhost:8050
```

### Debugging
```python
# Add to test code for visual debugging
await page.pause()  # Opens inspector
```

---

**Next Steps After Fixing:**
1. Run full 3-iteration test to verify stability
2. Update Phase 2 completion report with new success rates
3. Commit fixes with descriptive messages
4. Archive old test results for comparison

**Estimated Time:** 30-60 minutes for all 5 fixes

---

*Created: October 28, 2025*  
*For: Phase 2 E2E Test Suite Maintenance*
