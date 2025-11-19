#!/bin/bash
#
# Comprehensive Dashboard Tab Verification Script
# Run this to verify all tabs are working correctly
#

echo "======================================================================"
echo "COMPREHENSIVE DASHBOARD TAB VERIFICATION"
echo "======================================================================"
echo ""

# Check if dashboard is running
echo "1. Checking dashboard status..."
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "   ✓ Dashboard is running on port 8000"
else
    echo "   ✗ Dashboard is NOT running on port 8000"
    echo "   Please start the dashboard first:"
    echo "   cd /mnt/c/Aarav/fin_env/Dash && python3 integrated_dashboard.py"
    exit 1
fi
echo ""

# Run Playwright test
echo "2. Running automated browser tests..."
echo ""

python3 << 'PYTEST'
from playwright.sync_api import sync_playwright
import time

results = {
    'analysis_hub': False,
    'research_lab': False,
    'portfolio_holdings': False,
    'portfolio_orders': False,
    'portfolio_analytics': False
}

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Load dashboard
        page.goto('http://localhost:8000', wait_until='networkidle', timeout=60000)
        page.wait_for_selector('a[role="tab"]', timeout=10000)
        time.sleep(2)
        
        tabs = page.locator('a[id^="react-aria"][id*="-1-tab-"][role="tab"]').all()
        
        # Test Analysis Hub
        tabs[4].click()
        time.sleep(2)
        if page.locator('text=Analysis Configuration').count() > 0:
            if page.locator('text=/Internal Server Error/i').count() == 0:
                results['analysis_hub'] = True
        
        # Test Research Lab
        tabs[6].click()
        time.sleep(2)
        if page.locator('text=Scenario Analysis').count() > 0:
            if page.locator('text=/Internal Server Error/i').count() == 0:
                results['research_lab'] = True
        
        # Test Portfolio
        tabs[5].click()
        time.sleep(2)
        
        subtabs = page.locator('a[id^="react-aria"][id*="-3-tab-"][role="tab"]').all()
        
        # Holdings
        if len(subtabs) > 0:
            subtabs[0].click()
            time.sleep(1)
            if page.locator('table').count() > 0:
                if page.locator('text=/Error:/').count() == 0:
                    results['portfolio_holdings'] = True
        
        # Orders
        if len(subtabs) > 1:
            subtabs[1].click()
            time.sleep(1)
            if page.locator('text=/Error:/').count() == 0:
                results['portfolio_orders'] = True
        
        # Analytics
        if len(subtabs) > 2:
            subtabs[2].click()
            time.sleep(1)
            if page.locator('.js-plotly-plot').count() > 0:
                if page.locator('text=/Error:/').count() == 0:
                    results['portfolio_analytics'] = True
        
        browser.close()
    
    # Print results
    print("   Test Results:")
    print("   " + "-" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"   {status}  {name.replace('_', ' ').title()}")
        if not passed:
            all_passed = False
    
    print("   " + "-" * 60)
    
    if all_passed:
        print("\n   🎉 ALL TESTS PASSED! Dashboard is fully functional.")
        exit(0)
    else:
        print("\n   ⚠ Some tests failed. Please check the errors above.")
        exit(1)
        
except Exception as e:
    print(f"\n   ✗ Test execution failed: {e}")
    exit(1)
PYTEST

TEST_EXIT_CODE=$?

echo ""
echo "======================================================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "VERIFICATION COMPLETE: ALL TABS WORKING ✓"
else
    echo "VERIFICATION FAILED: Some tabs have errors ✗"
fi
echo "======================================================================"

exit $TEST_EXIT_CODE
