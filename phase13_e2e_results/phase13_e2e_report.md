
====================================================================================================
PHASE 13 - END-TO-END CHROMIUM CLICKER TEST REPORT
====================================================================================================
Timestamp: 2025-10-30 12:59:11
Dashboard URL: http://localhost:8051

📊 SUMMARY:
   Total Tests:     8
   ✅ Passed:       3 (37.5%)
   ❌ Failed:       5 (62.5%)
   💥 Errors:       0 (0.0%)

====================================================================================================
TEST RESULTS BY TAB:
====================================================================================================

▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
TAB: Azure ML Lab
▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

✅ Verify Scaffold Mode Banner
   Status: PASS
   Steps: 4 total
      ✓ Step 1: wait
      ✓ Step 2: screenshot
      ✓ Step 3: check_element
      ✓ Step 4: check_text

▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
TAB: Home / Command Center
▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

❌ Run Full Diagnostic Button
   Status: FAIL
   Errors (1):
      • Expected has_content=True, got has_content=False
   Steps: 7 total
      ✓ Step 1: wait
      ✓ Step 2: screenshot
      ✓ Step 3: click
      ✓ Step 4: wait
      ✓ Step 5: screenshot
      ✓ Step 6: check_element
      ✗ Step 7: check_content

▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
TAB: Options Lab
▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

✅ Inventory All Buttons
   Status: PASS
   Steps: 3 total
      ✓ Step 1: wait
      ✓ Step 2: screenshot
      ✓ Step 3: count_buttons

▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
TAB: Strategy Lab
▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

✅ Setup - Validate Strategy Button
   Status: PASS
   Steps: 6 total
      ✓ Step 1: wait
      ✓ Step 2: screenshot
      ✓ Step 3: click
      ✓ Step 4: wait
      ✓ Step 5: screenshot
      ✓ Step 6: check_element

❌ Backtest - Date Pickers
   Status: FAIL
   Errors (6):
      • Element not found: button#backtest-tab
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
   Steps: 8 total
      ✗ Step 1: click
      ✓ Step 2: wait
      ✓ Step 3: screenshot
      ✗ Step 4: check_element
      ✗ Step 5: check_element
      ✗ Step 6: check_element
      ✗ Step 7: check_element
      ✗ Step 8: check_element

❌ Execute - Run Backtest Button
   Status: FAIL
   Errors (1):
      • Element not found: button#execute-tab
   Steps: 4 total
      ✗ Step 1: click
      ✓ Step 2: wait
      ✓ Step 3: screenshot
      ✓ Step 4: check_element

❌ Results - Metric Components
   Status: FAIL
   Errors (5):
      • Element not found: button#results-tab
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
   Steps: 7 total
      ✗ Step 1: click
      ✓ Step 2: wait
      ✓ Step 3: screenshot
      ✗ Step 4: check_element
      ✗ Step 5: check_element
      ✗ Step 6: check_element
      ✗ Step 7: check_element

❌ Benchmark - Charts
   Status: FAIL
   Errors (4):
      • Element not found: button#benchmark-tab
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
      • Expected exists=True, got exists=False
   Steps: 6 total
      ✗ Step 1: click
      ✓ Step 2: wait
      ✓ Step 3: screenshot
      ✗ Step 4: check_element
      ✗ Step 5: check_element
      ✗ Step 6: check_element

====================================================================================================
CONSOLE ERRORS (0):
====================================================================================================
   ✅ No console errors detected!

====================================================================================================
Screenshots saved to: phase13_e2e_results/screenshots
====================================================================================================
