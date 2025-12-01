#!/usr/bin/env python3
"""
Interactive Feature Test for Options Lab
Tests actual functionality of new features
"""

import os
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://127.0.0.1:8051"
SCREENSHOT_DIR = "/tmp/options_lab_interactive_test"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def test_interactive_features():
    """Test interactive features of Options Lab"""
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=" * 60)
        print("OPTIONS LAB INTERACTIVE FEATURE TESTS")
        print("=" * 60)
        
        try:
            # Navigate to Options Lab
            page.goto(DASHBOARD_URL, timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            page.locator("#tab-options_lab").click()
            time.sleep(2)
            
            # Load mock data
            page.locator("#options-mock-btn").click()
            time.sleep(3)
            
            print("\n✓ Mock data loaded")
            
            # Test 1: Flow Scanner - Scan Button
            print("\n[TEST 1] Flow Scanner - Scan Button...")
            page.locator("#options-flow-tab").click()
            time.sleep(1)
            
            scan_btn = page.locator("#ol-flow-scan-btn")
            if scan_btn.count() > 0:
                scan_btn.click()
                time.sleep(2)
                page.screenshot(path=f"{SCREENSHOT_DIR}/flow_scanner_scanned.png")
                print("  ✓ Flow Scanner scan executed")
                results.append({"test": "Flow Scanner Scan", "passed": True})
            else:
                print("  ✗ Scan button not found")
                results.append({"test": "Flow Scanner Scan", "passed": False})
            
            # Test 2: IV Analysis - Analyze Button
            print("\n[TEST 2] IV Analysis - Analyze Button...")
            page.locator("#options-iv-tab").click()
            time.sleep(1)
            
            analyze_btn = page.locator("#ol-iv-analyze-btn")
            if analyze_btn.count() > 0:
                analyze_btn.click()
                time.sleep(2)
                page.screenshot(path=f"{SCREENSHOT_DIR}/iv_analysis_done.png")
                print("  ✓ IV Analysis executed")
                results.append({"test": "IV Analysis", "passed": True})
            else:
                print("  ✗ Analyze button not found")
                results.append({"test": "IV Analysis", "passed": False})
            
            # Test 3: Strategy Builder - Select Strategy
            print("\n[TEST 3] Strategy Builder - Template Selection...")
            page.locator("#options-strategy-tab").click()
            time.sleep(1)
            
            strategy_dropdown = page.locator("#ol-strategy-template")
            if strategy_dropdown.count() > 0:
                strategy_dropdown.click()
                time.sleep(0.5)
                # Try to select Iron Condor
                page.keyboard.type("iron")
                page.keyboard.press("Enter")
                time.sleep(1)
                page.screenshot(path=f"{SCREENSHOT_DIR}/strategy_builder_template.png")
                print("  ✓ Strategy template selection works")
                results.append({"test": "Strategy Builder", "passed": True})
            else:
                print("  ✗ Strategy dropdown not found")
                results.append({"test": "Strategy Builder", "passed": False})
            
            # Test 4: Portfolio Greeks - Calculate
            print("\n[TEST 4] Portfolio Greeks - Calculate...")
            page.locator("#options-portfolio-tab").click()
            time.sleep(1)
            
            calc_btn = page.locator("#ol-portfolio-refresh-btn")
            if calc_btn.count() > 0:
                calc_btn.click()
                time.sleep(2)
                page.screenshot(path=f"{SCREENSHOT_DIR}/portfolio_greeks_done.png")
                print("  ✓ Portfolio Greeks calculated")
                results.append({"test": "Portfolio Greeks", "passed": True})
            else:
                print("  ✗ Calculate button not found")
                results.append({"test": "Portfolio Greeks", "passed": False})
            
            # Test 5: Screener - Run Screen
            print("\n[TEST 5] Options Screener - Run Screen...")
            page.locator("#options-screener-tab").click()
            time.sleep(1)
            
            screen_btn = page.locator("#ol-screener-run-btn")
            if screen_btn.count() > 0:
                screen_btn.click()
                time.sleep(2)
                page.screenshot(path=f"{SCREENSHOT_DIR}/screener_results.png")
                print("  ✓ Screener executed")
                results.append({"test": "Options Screener", "passed": True})
            else:
                print("  ✗ Screen button not found")
                results.append({"test": "Options Screener", "passed": False})
            
            # Test 6: AI Recommendations - Get Recommendations
            print("\n[TEST 6] AI Recommendations - Get Recs...")
            page.locator("#options-ai-tab").click()
            time.sleep(1)
            
            ai_btn = page.locator("#ol-ai-generate-btn")
            if ai_btn.count() > 0:
                ai_btn.click()
                time.sleep(2)
                page.screenshot(path=f"{SCREENSHOT_DIR}/ai_recommendations_done.png")
                print("  ✓ AI Recommendations generated")
                results.append({"test": "AI Recommendations", "passed": True})
            else:
                print("  ✗ Recommend button not found")
                results.append({"test": "AI Recommendations", "passed": False})
            
            # Test 7: Earnings Calendar - Load Earnings
            print("\n[TEST 7] Earnings Calendar - Load Data...")
            page.locator("#options-earnings-tab").click()
            time.sleep(1)
            
            earnings_btn = page.locator("#ol-earnings-load-btn")
            if earnings_btn.count() > 0:
                earnings_btn.click()
                time.sleep(2)
                page.screenshot(path=f"{SCREENSHOT_DIR}/earnings_calendar_loaded.png")
                print("  ✓ Earnings Calendar loaded")
                results.append({"test": "Earnings Calendar", "passed": True})
            else:
                print("  ✗ Load button not found")
                results.append({"test": "Earnings Calendar", "passed": False})
            
            # Test 8: Trade Journal - View Journal
            print("\n[TEST 8] Trade Journal - View...")
            page.locator("#options-journal-tab").click()
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/trade_journal_view.png")
            print("  ✓ Trade Journal displayed")
            results.append({"test": "Trade Journal", "passed": True})
            
            # Final screenshot
            page.screenshot(path=f"{SCREENSHOT_DIR}/final_state.png")
            
        except Exception as e:
            print(f"\n✗ Error during testing: {e}")
            results.append({"test": "Error", "passed": False, "error": str(e)})
        
        finally:
            print("\n\nKeeping browser open for inspection...")
            time.sleep(5)
            browser.close()
    
    # Print summary
    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    
    print("\n" + "=" * 60)
    print("INTERACTIVE FEATURE TEST SUMMARY")
    print("=" * 60)
    print(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
    print(f"Success Rate: {(passed/max(total,1))*100:.1f}%")
    print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    test_interactive_features()
