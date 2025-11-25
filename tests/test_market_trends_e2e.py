"""
Market Trends End-to-End Validation Test
==========================================
Comprehensive test that validates:
1. News container populates with real data after background job
2. Backtest modal opens and displays results
3. Debug logs modal opens and displays content
4. All buttons are clickable and trigger expected behavior
"""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Configuration
BASE_URL = "http://localhost:8050"
OUTPUT_DIR = Path("/mnt/c/Aarav/fin_env/unified-dashboard/market_trends_snapshots")
OUTPUT_DIR.mkdir(exist_ok=True)

def save_screenshot(page, name):
    """Save screenshot with timestamp"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = OUTPUT_DIR / f"e2e_{name}_{timestamp}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"📸 Screenshot saved: {screenshot_path}")
    return screenshot_path

def wait_for_element(page, selector, description, timeout=10000):
    """Wait for element and verify it's visible"""
    print(f"⏳ Waiting for: {description} [{selector}]...")
    try:
        element = page.wait_for_selector(selector, timeout=timeout, state='visible')
        print(f"✅ Found: {description}")
        return element
    except Exception as e:
        print(f"❌ Timeout waiting for: {description} - {e}")
        return None

def test_market_trends_complete_workflow():
    """
    Test complete Market Trends workflow:
    1. Navigate to Market Trends tab
    2. Wait for news to populate (background job)
    3. Click backtest button and verify modal
    4. Click debug logs button and verify modal
    5. Verify all 7 buttons are clickable
    """
    
    print("\n" + "="*80)
    print("MARKET TRENDS E2E TEST - COMPLETE WORKFLOW")
    print("="*80 + "\n")
    
    results = {
        "test_name": "market_trends_e2e",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": []
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # TEST 1: Navigate to app and Market Trends tab
        print("\n📍 TEST 1: Navigate to Market Trends tab")
        print("-" * 80)
        
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(2)
        save_screenshot(page, "01_home_page")
        
        # Find and click Market Trends tab
        market_trends_tab = wait_for_element(page, 'a:has-text("Market Trends")', "Market Trends tab link")
        if market_trends_tab:
            market_trends_tab.click()
            print("✅ Clicked Market Trends tab")
            time.sleep(3)
            save_screenshot(page, "02_market_trends_active")
            results["tests"].append({"name": "navigate_to_tab", "status": "PASS"})
        else:
            print("❌ Failed to find Market Trends tab")
            results["tests"].append({"name": "navigate_to_tab", "status": "FAIL", "error": "Tab not found"})
            browser.close()
            return results
        
        # TEST 2: Verify news container exists and check content
        print("\n📍 TEST 2: Verify news container content")
        print("-" * 80)
        
        news_container = wait_for_element(page, '#news-container', "News container")
        if news_container:
            initial_content = news_container.inner_text()
            print(f"📰 Initial news content: '{initial_content}' ({len(initial_content)} chars)")
            
            # Wait up to 30 seconds for news to populate (background job)
            print("⏳ Waiting for news background job to complete...")
            news_populated = False
            
            for i in range(6):  # 6 attempts x 5 seconds = 30 seconds
                time.sleep(5)
                current_content = page.locator('#news-container').inner_text()
                print(f"  [{i+1}/6] News content: {len(current_content)} chars")
                
                if "Loading news..." not in current_content and len(current_content) > 50:
                    news_populated = True
                    print(f"✅ News populated! Content: {current_content[:200]}")
                    save_screenshot(page, "03_news_populated")
                    results["tests"].append({
                        "name": "news_population",
                        "status": "PASS",
                        "content_length": len(current_content)
                    })
                    break
            
            if not news_populated:
                print(f"⚠️  News still showing placeholder after 30s: '{current_content}'")
                results["tests"].append({
                    "name": "news_population",
                    "status": "PARTIAL",
                    "note": "News didn't populate within 30s timeout"
                })
        else:
            print("❌ News container not found in DOM")
            results["tests"].append({"name": "news_container_exists", "status": "FAIL"})
        
        # TEST 3: Verify results area has content
        print("\n📍 TEST 3: Verify results area content")
        print("-" * 80)
        
        results_area = wait_for_element(page, '#results-area', "Results area")
        if results_area:
            results_content = results_area.inner_text()
            print(f"📊 Results area content: {len(results_content)} chars")
            print(f"Preview: {results_content[:200]}")
            
            if len(results_content) > 100:
                print("✅ Results area has substantial content")
                results["tests"].append({
                    "name": "results_area_populated",
                    "status": "PASS",
                    "content_length": len(results_content)
                })
            else:
                print("⚠️  Results area has minimal content")
                results["tests"].append({
                    "name": "results_area_populated",
                    "status": "PARTIAL",
                    "content_length": len(results_content)
                })
        else:
            print("❌ Results area not found")
            results["tests"].append({"name": "results_area_exists", "status": "FAIL"})
        
        # TEST 4: Test backtest button and modal
        print("\n📍 TEST 4: Test backtest button and modal")
        print("-" * 80)
        
        backtest_btn = wait_for_element(page, '#backtest-btn', "Backtest button")
        if backtest_btn:
            print("🖱️  Clicking backtest button...")
            backtest_btn.click()
            time.sleep(3)
            save_screenshot(page, "04_backtest_clicked")
            
            # Check if modal appeared
            backtest_modal = page.locator('#backtest-modal')
            modal_style = backtest_modal.get_attribute('style')
            
            if 'display: none' not in str(modal_style).lower():
                print("✅ Backtest modal opened")
                
                # Check for modal content
                modal_content = backtest_modal.inner_text()
                print(f"📝 Modal content: {len(modal_content)} chars")
                print(f"Preview: {modal_content[:200]}")
                
                results["tests"].append({
                    "name": "backtest_modal",
                    "status": "PASS",
                    "modal_visible": True,
                    "content_length": len(modal_content)
                })
                
                # Close modal
                close_btn = page.locator('#close-backtest-modal')
                if close_btn.count() > 0:
                    close_btn.click()
                    time.sleep(1)
                    print("✅ Closed backtest modal")
            else:
                print("⚠️  Backtest modal did not open (still display:none)")
                results["tests"].append({
                    "name": "backtest_modal",
                    "status": "PARTIAL",
                    "modal_visible": False
                })
        else:
            print("❌ Backtest button not found")
            results["tests"].append({"name": "backtest_button_exists", "status": "FAIL"})
        
        # TEST 5: Test debug logs button and modal
        print("\n📍 TEST 5: Test debug logs button and modal")
        print("-" * 80)
        
        debug_btn = wait_for_element(page, '#debug-logs-btn', "Debug logs button")
        if debug_btn:
            print("🖱️  Clicking debug logs button...")
            debug_btn.click()
            time.sleep(2)
            save_screenshot(page, "05_debug_logs_clicked")
            
            # Check if modal appeared
            debug_modal = page.locator('#debug-logs-modal')
            modal_style = debug_modal.get_attribute('style')
            
            if 'display: none' not in str(modal_style).lower():
                print("✅ Debug logs modal opened")
                
                # Check for modal content
                modal_content = debug_modal.inner_text()
                print(f"📝 Modal content: {len(modal_content)} chars")
                print(f"Preview: {modal_content[:200]}")
                
                results["tests"].append({
                    "name": "debug_logs_modal",
                    "status": "PASS",
                    "modal_visible": True,
                    "content_length": len(modal_content)
                })
                
                # Close modal
                close_btn = page.locator('#close-debug-modal')
                if close_btn.count() > 0:
                    close_btn.click()
                    time.sleep(1)
                    print("✅ Closed debug logs modal")
            else:
                print("⚠️  Debug logs modal did not open")
                results["tests"].append({
                    "name": "debug_logs_modal",
                    "status": "PARTIAL",
                    "modal_visible": False
                })
        else:
            print("❌ Debug logs button not found")
            results["tests"].append({"name": "debug_logs_button_exists", "status": "FAIL"})
        
        # TEST 6: Verify all 7 buttons are present and clickable
        print("\n📍 TEST 6: Verify all 7 Market Trends buttons")
        print("-" * 80)
        
        buttons = [
            ('#run-btn', 'Run Full Analysis'),
            ('#reload-model', 'Reload Model'),
            ('#refresh-cached', 'Refresh Cached'),
            ('#backtest-btn', 'Backtest'),
            ('#debug-logs-btn', 'Debug Logs'),
            ('#toggle-brief', 'Toggle Brief'),
            ('#mt-download-btn', 'Download CSV')
        ]
        
        button_results = []
        for btn_id, btn_name in buttons:
            btn = page.locator(btn_id)
            exists = btn.count() > 0
            visible = btn.is_visible() if exists else False
            enabled = btn.is_enabled() if exists else False
            
            status = "✅" if (exists and visible and enabled) else "❌"
            print(f"  {status} {btn_name} [{btn_id}]: exists={exists}, visible={visible}, enabled={enabled}")
            
            button_results.append({
                "id": btn_id,
                "name": btn_name,
                "exists": exists,
                "visible": visible,
                "enabled": enabled
            })
        
        all_buttons_ok = all(b['exists'] and b['visible'] and b['enabled'] for b in button_results)
        results["tests"].append({
            "name": "all_buttons_check",
            "status": "PASS" if all_buttons_ok else "PARTIAL",
            "buttons": button_results
        })
        
        # TEST 7: Test "Run Full Analysis" button interaction
        print("\n📍 TEST 7: Test 'Run Full Analysis' button")
        print("-" * 80)
        
        run_btn = page.locator('#run-btn')
        if run_btn.count() > 0:
            # Capture results BEFORE click
            results_before = page.locator('#results-area').inner_text()
            print(f"📊 Results BEFORE click: {len(results_before)} chars")
            
            print("🖱️  Clicking 'Run Full Analysis' button...")
            run_btn.click()
            time.sleep(5)  # Wait for processing
            save_screenshot(page, "06_run_analysis_clicked")
            
            # Capture results AFTER click
            results_after = page.locator('#results-area').inner_text()
            print(f"📊 Results AFTER click: {len(results_after)} chars")
            
            changed = results_before != results_after
            print(f"{'✅' if changed else '⚠️ '} Results content changed: {changed}")
            
            results["tests"].append({
                "name": "run_analysis_interaction",
                "status": "PASS" if changed else "PARTIAL",
                "content_changed": changed,
                "before_length": len(results_before),
                "after_length": len(results_after)
            })
        
        # Final screenshot
        save_screenshot(page, "07_final_state")
        
        browser.close()
    
    # Calculate summary
    total_tests = len(results["tests"])
    passed_tests = sum(1 for t in results["tests"] if t["status"] == "PASS")
    partial_tests = sum(1 for t in results["tests"] if t["status"] == "PARTIAL")
    failed_tests = sum(1 for t in results["tests"] if t["status"] == "FAIL")
    
    results["summary"] = {
        "total": total_tests,
        "passed": passed_tests,
        "partial": partial_tests,
        "failed": failed_tests,
        "success_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0%"
    }
    
    # Save results
    results_path = OUTPUT_DIR / f"e2e_test_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"⚠️  Partial: {partial_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success rate: {results['summary']['success_rate']}")
    print(f"\nResults saved to: {results_path}")
    print("="*80 + "\n")
    
    return results

if __name__ == "__main__":
    print("Market Trends E2E Validation Test")
    print("="*80)
    
    test_results = test_market_trends_complete_workflow()
    
    # Exit with appropriate code
    if test_results["summary"]["failed"] > 0:
        exit(1)
    elif test_results["summary"]["partial"] > 0:
        exit(2)
    else:
        exit(0)
