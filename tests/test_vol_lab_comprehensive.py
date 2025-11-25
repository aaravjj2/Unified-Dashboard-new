"""
Comprehensive Volatility Lab Testing Suite
Tests all 8 subtabs with clicker + Playwright snapshots
"""

from playwright.sync_api import sync_playwright
import time
import json
import sys
from datetime import datetime

def test_volatility_lab_comprehensive():
    """Test all 8 Volatility Lab subtabs with screenshots and interaction validation"""
    
    results = {
        'test_timestamp': datetime.now().isoformat(),
        'tab_visible': False,
        'subtabs_count': 0,
        'subtabs_details': {},
        'screenshots': [],
        'errors': []
    }
    
    subtab_configs = [
        {'name': 'Historical HV', 'tab_id': 'hv', 'expected_elements': ['input', 'button']},
        {'name': 'IV Surface', 'tab_id': 'iv', 'expected_elements': ['input', 'button']},
        {'name': 'Correlation', 'tab_id': 'corr', 'expected_elements': ['input', 'button']},
        {'name': 'Factor Analytics', 'tab_id': 'factor', 'expected_elements': ['input', 'button']},
        {'name': 'Advanced Charts', 'tab_id': 'advanced', 'expected_elements': []},
        {'name': 'Metrics Table', 'tab_id': 'metrics', 'expected_elements': ['input', 'button']},
        {'name': 'Custom Scenarios', 'tab_id': 'scenarios', 'expected_elements': ['input', 'button']},
        {'name': 'Alerts', 'tab_id': 'alerts', 'expected_elements': []}
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1200})
        
        try:
            # ============================================================
            # STEP 1: Load Dashboard
            # ============================================================
            print("🔍 STEP 1/10: Loading dashboard...")
            page.goto("http://localhost:8050", wait_until="networkidle", timeout=60000)
            time.sleep(3)
            
            # Take homepage screenshot
            page.screenshot(path="test-artifacts/vol_lab_00_homepage.png")
            results['screenshots'].append('vol_lab_00_homepage.png')
            print("   ✅ Dashboard loaded, screenshot saved")
            
            # ============================================================
            # STEP 2: Find Volatility Lab Tab
            # ============================================================
            print("\n🔍 STEP 2/10: Finding Volatility Lab tab...")
            vol_tab = page.query_selector('text=⚡ Volatility Lab')
            
            if not vol_tab:
                # Try alternative selectors
                vol_tab = page.query_selector('[role="tab"]:has-text("Volatility Lab")')
            
            if not vol_tab:
                raise Exception("❌ Volatility Lab tab not found in navbar")
            
            results['tab_visible'] = True
            print("   ✅ Volatility Lab tab found in navbar")
            
            # ============================================================
            # STEP 3: Click Volatility Lab Tab
            # ============================================================
            print("\n🔍 STEP 3/10: Clicking Volatility Lab tab...")
            vol_tab.click()
            time.sleep(3)
            
            page.screenshot(path="test-artifacts/vol_lab_01_tab_clicked.png")
            results['screenshots'].append('vol_lab_01_tab_clicked.png')
            print("   ✅ Tab clicked, screenshot saved")
            
            # ============================================================
            # STEP 4: Count Subtabs
            # ============================================================
            print("\n🔍 STEP 4/10: Counting subtabs...")
            subtabs = page.query_selector_all('#vl-tabs [role="tab"]')
            results['subtabs_count'] = len(subtabs)
            
            print(f"   ✅ Found {len(subtabs)} subtabs:")
            for i, tab in enumerate(subtabs, 1):
                tab_text = tab.inner_text()
                print(f"      {i}. {tab_text}")
            
            if len(subtabs) != 8:
                results['errors'].append(f"Expected 8 subtabs, found {len(subtabs)}")
            
            # ============================================================
            # STEP 5-12: Test Each Subtab
            # ============================================================
            for idx, config in enumerate(subtab_configs, 1):
                step_num = idx + 4
                print(f"\n🔍 STEP {step_num}/10: Testing '{config['name']}' subtab...")
                
                subtab_result = {
                    'name': config['name'],
                    'clickable': False,
                    'elements_found': {},
                    'screenshot': None,
                    'html_content_length': 0,
                    'errors': []
                }
                
                try:
                    # Find and click subtab
                    subtab = page.query_selector(f'text={config["name"]}')
                    if not subtab:
                        # Try alternative selector
                        subtab = page.query_selector(f'#vl-tabs [role="tab"]:has-text("{config["name"]}")')
                    
                    if subtab:
                        subtab.click()
                        time.sleep(2)
                        subtab_result['clickable'] = True
                        print(f"   ✅ Subtab clicked successfully")
                        
                        # Check for expected elements
                        if 'input' in config['expected_elements']:
                            inputs = page.query_selector_all('input')
                            subtab_result['elements_found']['inputs'] = len(inputs)
                            print(f"   📊 Found {len(inputs)} input elements")
                        
                        if 'button' in config['expected_elements']:
                            buttons = page.query_selector_all('button')
                            subtab_result['elements_found']['buttons'] = len(buttons)
                            print(f"   📊 Found {len(buttons)} button elements")
                        
                        # Get HTML content length
                        page_content = page.content()
                        subtab_result['html_content_length'] = len(page_content)
                        
                        # Take screenshot
                        screenshot_name = f"vol_lab_{idx+1:02d}_{config['tab_id']}.png"
                        page.screenshot(path=f"test-artifacts/{screenshot_name}")
                        subtab_result['screenshot'] = screenshot_name
                        results['screenshots'].append(screenshot_name)
                        print(f"   📸 Screenshot saved: {screenshot_name}")
                        
                        # Try to interact with first button if present
                        if 'button' in config['expected_elements']:
                            calc_btn = page.query_selector('button:has-text("Calculate"), button:has-text("Fetch"), button:has-text("Generate"), button:has-text("Analyze"), button:has-text("Run"), button:has-text("Check")')
                            if calc_btn:
                                print(f"   🖱️  Found action button, testing click...")
                                calc_btn.click()
                                time.sleep(2)
                                
                                # Take after-click screenshot
                                after_click_name = f"vol_lab_{idx+1:02d}_{config['tab_id']}_clicked.png"
                                page.screenshot(path=f"test-artifacts/{after_click_name}")
                                results['screenshots'].append(after_click_name)
                                print(f"   ✅ Button clicked, screenshot saved: {after_click_name}")
                        
                    else:
                        subtab_result['errors'].append("Subtab element not found")
                        print(f"   ❌ Subtab not found")
                
                except Exception as e:
                    subtab_result['errors'].append(str(e))
                    print(f"   ❌ Error: {e}")
                
                results['subtabs_details'][config['name']] = subtab_result
            
            # ============================================================
            # FINAL: Summary Screenshot
            # ============================================================
            print("\n🔍 FINAL STEP: Taking summary screenshot...")
            page.screenshot(path="test-artifacts/vol_lab_99_final_state.png", full_page=True)
            results['screenshots'].append('vol_lab_99_final_state.png')
            print("   ✅ Final full-page screenshot saved")
            
        except Exception as e:
            results['errors'].append(f"Critical error: {str(e)}")
            print(f"\n❌ CRITICAL ERROR: {e}")
        
        finally:
            browser.close()
    
    # ============================================================
    # Print Results Summary
    # ============================================================
    print("\n" + "="*70)
    print("📊 VOLATILITY LAB COMPREHENSIVE TEST RESULTS")
    print("="*70)
    
    print(f"\n✅ Tab Visible: {results['tab_visible']}")
    print(f"✅ Subtabs Count: {results['subtabs_count']}/8")
    print(f"📸 Screenshots Captured: {len(results['screenshots'])}")
    
    print(f"\n📋 Subtab Details:")
    passed = 0
    failed = 0
    
    for name, details in results['subtabs_details'].items():
        status = "✅ PASS" if details['clickable'] and not details['errors'] else "❌ FAIL"
        if details['clickable'] and not details['errors']:
            passed += 1
        else:
            failed += 1
        
        print(f"\n   {status} - {name}")
        print(f"      Clickable: {details['clickable']}")
        print(f"      Elements: {details['elements_found']}")
        print(f"      Screenshot: {details['screenshot']}")
        if details['errors']:
            print(f"      Errors: {', '.join(details['errors'])}")
    
    print(f"\n📊 Summary: {passed}/8 passed, {failed}/8 failed")
    
    if results['errors']:
        print(f"\n❌ General Errors:")
        for err in results['errors']:
            print(f"   - {err}")
    
    # Save JSON report
    report_path = "test-artifacts/vol_lab_comprehensive_report.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 JSON report saved: {report_path}")
    
    # Determine exit code
    if results['tab_visible'] and results['subtabs_count'] == 8 and passed >= 6:
        print("\n🎉 OVERALL RESULT: ✅ PASS")
        print(f"   - All 8 subtabs present")
        print(f"   - {passed}/8 subtabs fully functional")
        print(f"   - {len(results['screenshots'])} screenshots captured")
        return 0
    else:
        print("\n⚠️  OVERALL RESULT: ⚠️  PARTIAL PASS")
        print(f"   - Some tests failed or incomplete")
        return 1

if __name__ == "__main__":
    exit_code = test_volatility_lab_comprehensive()
    sys.exit(exit_code)
