#!/usr/bin/env python3
"""
Options Lab Button Test - Click each button and capture results
"""

import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://127.0.0.1:8051"
SCREENSHOT_DIR = "/tmp/options_lab_button_tests"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Buttons to test per subtab (discovered from actual DOM)
TESTS = [
    {
        "subtab": "options-chain-tab",
        "name": "Chain Viewer",
        "buttons": [
            ("options-forecast-btn", "Generate Forecast"),
            ("chain-export-btn", "Export Chain Data"),
        ]
    },
    {
        "subtab": "options-flow-tab",
        "name": "Flow Scanner",
        "buttons": [
            ("ol-flow-scan-btn", "Scan Flow"),
        ]
    },
    {
        "subtab": "options-iv-tab",
        "name": "IV Analysis",
        "buttons": [
            ("ol-iv-analyze-btn", "Analyze IV"),
        ]
    },
    {
        "subtab": "options-strategy-tab",
        "name": "Strategy Builder",
        "buttons": [
            ("ol-strategy-build-btn", "Build Strategy"),
        ]
    },
    {
        "subtab": "options-manual-tab",
        "name": "Manual Trade",
        "buttons": [
            ("sim-calculate-btn", "Calculate P&L"),
            ("sim-order-submit-btn", "Submit Paper Order"),
        ]
    },
    {
        "subtab": "options-portfolio-tab",
        "name": "Portfolio Greeks",
        "buttons": [
            ("ol-portfolio-refresh-btn", "Refresh Portfolio"),
        ]
    },
    {
        "subtab": "options-screener-tab",
        "name": "Screener",
        "buttons": [
            ("ol-screener-run-btn", "Run Screen"),
        ]
    },
    {
        "subtab": "options-ai-tab",
        "name": "AI Recommendations",
        "buttons": [
            ("ol-ai-generate-btn", "Generate Recommendations"),
        ]
    },
    {
        "subtab": "options-earnings-tab",
        "name": "Earnings Calendar",
        "buttons": [
            ("ol-earnings-load-btn", "Load Calendar"),
            ("ol-earnings-high-iv-btn", "High IV Opportunities"),
        ]
    },
    {
        "subtab": "options-backtest-tab",
        "name": "Backtester",
        "buttons": [
            ("ol-backtest-run-btn", "Run Backtest"),
        ]
    },
]

def run_button_tests():
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        print("=" * 70)
        print("OPTIONS LAB BUTTON CLICK TESTS")
        print("=" * 70)
        
        # Load dashboard
        page.goto(DASHBOARD_URL, timeout=60000)
        time.sleep(5)  # Simple wait instead of networkidle
        
        # Navigate to Options Lab
        page.locator("#tab-options_lab").click()
        time.sleep(2)
        
        # Load mock data first
        page.locator("#options-mock-btn").click()
        time.sleep(3)
        page.screenshot(path=f"{SCREENSHOT_DIR}/00_initial_state.png")
        print("✓ Mock data loaded\n")
        
        test_num = 0
        for test_group in TESTS:
            subtab_id = test_group["subtab"]
            subtab_name = test_group["name"]
            
            print(f"\n{'='*60}")
            print(f"SUBTAB: {subtab_name}")
            print("="*60)
            
            # Click on subtab
            try:
                page.locator(f"#{subtab_id}").click()
                time.sleep(1.5)
            except Exception as e:
                print(f"  ✗ Failed to open subtab: {e}")
                continue
            
            # Test each button
            for btn_id, btn_name in test_group["buttons"]:
                test_num += 1
                print(f"\n  [{test_num}] Testing: #{btn_id} ({btn_name})")
                
                # Clear console errors before click
                console_errors.clear()
                
                try:
                    btn = page.locator(f"#{btn_id}")
                    
                    if btn.count() == 0:
                        print(f"      ✗ Button NOT FOUND")
                        results.append({"test": f"{subtab_name}: {btn_name}", "status": "NOT_FOUND", "error": "Button not found"})
                        continue
                    
                    if not btn.is_visible():
                        print(f"      ✗ Button NOT VISIBLE")
                        results.append({"test": f"{subtab_name}: {btn_name}", "status": "NOT_VISIBLE", "error": "Button not visible"})
                        continue
                    
                    # Click button
                    btn.click()
                    time.sleep(2)
                    
                    # Take screenshot after click
                    screenshot_path = f"{SCREENSHOT_DIR}/{test_num:02d}_{btn_id}_after.png"
                    page.screenshot(path=screenshot_path)
                    
                    # Check for errors
                    page_content = page.content()
                    has_callback_error = "Callback error" in page_content or "callback error" in page_content.lower()
                    has_exception = "Exception" in page_content and "Traceback" in page_content
                    
                    if console_errors:
                        print(f"      ⚠️ Console errors: {len(console_errors)}")
                        for err in console_errors[:3]:
                            print(f"         - {err[:80]}")
                    
                    if has_callback_error:
                        print(f"      ✗ CALLBACK ERROR detected")
                        results.append({"test": f"{subtab_name}: {btn_name}", "status": "CALLBACK_ERROR", "screenshot": screenshot_path})
                    elif has_exception:
                        print(f"      ✗ EXCEPTION detected")
                        results.append({"test": f"{subtab_name}: {btn_name}", "status": "EXCEPTION", "screenshot": screenshot_path})
                    else:
                        print(f"      ✓ PASSED - No errors")
                        results.append({"test": f"{subtab_name}: {btn_name}", "status": "PASSED", "screenshot": screenshot_path})
                        
                except Exception as e:
                    print(f"      ✗ Error clicking: {e}")
                    results.append({"test": f"{subtab_name}: {btn_name}", "status": "CLICK_ERROR", "error": str(e)})
        
        # Final screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/99_final_state.png")
        
        print("\n\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        passed = [r for r in results if r["status"] == "PASSED"]
        failed = [r for r in results if r["status"] != "PASSED"]
        
        print(f"\nTotal: {len(results)} | Passed: {len(passed)} | Failed: {len(failed)}")
        
        if failed:
            print("\nFAILED TESTS:")
            for f in failed:
                print(f"  ✗ {f['test']}: {f['status']}")
        
        print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
        
        time.sleep(3)
        browser.close()
        
    return results

if __name__ == "__main__":
    run_button_tests()
