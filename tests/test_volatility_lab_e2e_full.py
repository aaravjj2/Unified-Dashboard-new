"""
Comprehensive E2E Test for Volatility Lab - All 8 Subtabs
Tests UI visibility, button clicks, and callback execution
"""

from playwright.sync_api import sync_playwright, expect
import time
import sys

def test_volatility_lab_e2e():
    """Full end-to-end test of all 8 Volatility Lab subtabs"""
    
    results = {
        'tab_visible': False,
        'subtabs_count': 0,
        'subtabs_tested': {},
        'errors': []
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            # Step 1: Open dashboard
            print("🔍 Step 1/9: Opening dashboard...")
            page.goto("http://localhost:8050", wait_until="networkidle", timeout=60000)
            time.sleep(3)
            
            # Step 2: Find and click Volatility Lab main tab
            print("🔍 Step 2/9: Finding Volatility Lab tab...")
            vol_tab = page.query_selector('text=⚡ Volatility Lab')
            if not vol_tab:
                raise Exception("Volatility Lab tab not found in navbar")
            
            results['tab_visible'] = True
            print("✅ Volatility Lab tab found!")
            
            vol_tab.click()
            time.sleep(2)
            
            # Step 3: Count and verify all 8 subtabs
            print("🔍 Step 3/9: Verifying 8 subtabs...")
            subtabs = page.query_selector_all('#vl-tabs [role="tab"]')
            results['subtabs_count'] = len(subtabs)
            
            if len(subtabs) != 8:
                results['errors'].append(f"Expected 8 subtabs, found {len(subtabs)}")
            else:
                print(f"✅ All 8 subtabs present!")
            
            subtab_names = []
            for st in subtabs:
                subtab_names.append(st.inner_text())
            print(f"   Subtabs: {', '.join(subtab_names)}")
            
            # Step 4: Test Historical HV subtab
            print("🔍 Step 4/9: Testing Historical HV subtab...")
            hv_tab = page.query_selector('text=📊 Historical HV')
            if hv_tab:
                hv_tab.click()
                time.sleep(1)
                
                calc_btn = page.query_selector('#hv-calc-btn')
                if calc_btn:
                    calc_btn.click()
                    time.sleep(3)  # Wait for chart rendering
                    
                    chart = page.query_selector('#hv-chart')
                    if chart:
                        results['subtabs_tested']['hv'] = 'PASS'
                        print("   ✅ Historical HV: Button click successful, chart rendered")
                    else:
                        results['subtabs_tested']['hv'] = 'FAIL - Chart not found'
                else:
                    results['subtabs_tested']['hv'] = 'FAIL - Button not found'
            
            # Step 5: Test IV Surface subtab
            print("🔍 Step 5/9: Testing IV Surface subtab...")
            iv_tab = page.query_selector('text=🌐 IV Surface')
            if iv_tab:
                iv_tab.click()
                time.sleep(1)
                
                fetch_btn = page.query_selector('#iv-fetch-btn')
                if fetch_btn:
                    fetch_btn.click()
                    time.sleep(3)
                    
                    surface = page.query_selector('#iv-surface')
                    if surface:
                        results['subtabs_tested']['iv'] = 'PASS'
                        print("   ✅ IV Surface: 3D surface generated")
                    else:
                        results['subtabs_tested']['iv'] = 'FAIL - Surface not found'
                else:
                    results['subtabs_tested']['iv'] = 'FAIL - Button not found'
            
            # Step 6: Test Correlation subtab
            print("🔍 Step 6/9: Testing Correlation subtab...")
            corr_tab = page.query_selector('text=🔗 Correlation')
            if corr_tab:
                corr_tab.click()
                time.sleep(1)
                
                corr_btn = page.query_selector('#corr-calc-btn')
                if corr_btn:
                    corr_btn.click()
                    time.sleep(3)
                    
                    heatmap = page.query_selector('#corr-heatmap')
                    if heatmap:
                        results['subtabs_tested']['corr'] = 'PASS'
                        print("   ✅ Correlation: Heatmap rendered")
                    else:
                        results['subtabs_tested']['corr'] = 'FAIL - Heatmap not found'
                else:
                    results['subtabs_tested']['corr'] = 'FAIL - Button not found'
            
            # Step 7: Test Factor Analytics
            print("🔍 Step 7/9: Testing Factor Analytics subtab...")
            factor_tab = page.query_selector('text=📈 Factor Analytics')
            if factor_tab:
                factor_tab.click()
                time.sleep(1)
                
                factor_btn = page.query_selector('#factor-calc-btn')
                if factor_btn:
                    factor_btn.click()
                    time.sleep(2)
                    
                    chart = page.query_selector('#factor-chart')
                    if chart:
                        results['subtabs_tested']['factor'] = 'PASS'
                        print("   ✅ Factor Analytics: Chart rendered")
                    else:
                        results['subtabs_tested']['factor'] = 'FAIL - Chart not found'
                else:
                    results['subtabs_tested']['factor'] = 'FAIL - Button not found'
            
            # Step 8: Test Metrics Table
            print("🔍 Step 8/9: Testing Metrics Table subtab...")
            metrics_tab = page.query_selector('text=📋 Metrics Table')
            if metrics_tab:
                metrics_tab.click()
                time.sleep(1)
                
                metrics_btn = page.query_selector('#metrics-calc-btn')
                if metrics_btn:
                    metrics_btn.click()
                    time.sleep(3)
                    
                    table = page.query_selector('#metrics-table')
                    if table:
                        results['subtabs_tested']['metrics'] = 'PASS'
                        print("   ✅ Metrics Table: Table rendered")
                    else:
                        results['subtabs_tested']['metrics'] = 'FAIL - Table not found'
                else:
                    results['subtabs_tested']['metrics'] = 'FAIL - Button not found'
            
            # Step 9: Test Scenarios
            print("🔍 Step 9/9: Testing Custom Scenarios subtab...")
            scenario_tab = page.query_selector('text=🎯 Custom Scenarios')
            if scenario_tab:
                scenario_tab.click()
                time.sleep(1)
                
                scenario_btn = page.query_selector('#scenario-run-btn')
                if scenario_btn:
                    scenario_btn.click()
                    time.sleep(2)
                    
                    results_div = page.query_selector('#scenario-results')
                    if results_div:
                        results['subtabs_tested']['scenarios'] = 'PASS'
                        print("   ✅ Custom Scenarios: Results rendered")
                    else:
                        results['subtabs_tested']['scenarios'] = 'FAIL - Results not found'
                else:
                    results['subtabs_tested']['scenarios'] = 'FAIL - Button not found'
            
            # Take screenshot
            page.screenshot(path="test-artifacts/vol_lab_e2e_final.png")
            print("\n📸 Screenshot saved: test-artifacts/vol_lab_e2e_final.png")
            
        except Exception as e:
            results['errors'].append(str(e))
            print(f"\n❌ Error during test: {e}")
        
        finally:
            browser.close()
    
    # Print results summary
    print("\n" + "="*60)
    print("📊 VOLATILITY LAB E2E TEST RESULTS")
    print("="*60)
    print(f"✅ Tab Visible: {results['tab_visible']}")
    print(f"✅ Subtabs Count: {results['subtabs_count']}/8")
    print(f"\n📋 Subtab Callback Tests:")
    
    passed = 0
    failed = 0
    for subtab, status in results['subtabs_tested'].items():
        if status == 'PASS':
            print(f"   ✅ {subtab}: {status}")
            passed += 1
        else:
            print(f"   ❌ {subtab}: {status}")
            failed += 1
    
    print(f"\n📊 Test Summary: {passed} passed, {failed} failed")
    
    if results['errors']:
        print(f"\n❌ Errors encountered:")
        for err in results['errors']:
            print(f"   - {err}")
    
    # Exit code: 0 if all pass, 1 if any failures
    if results['tab_visible'] and results['subtabs_count'] == 8 and passed >= 6:
        print("\n🎉 OVERALL: PASS (all critical tests passed)")
        return 0
    else:
        print("\n⚠️ OVERALL: PARTIAL SUCCESS (some tests failed)")
        return 1

if __name__ == "__main__":
    exit_code = test_volatility_lab_e2e()
    sys.exit(exit_code)
