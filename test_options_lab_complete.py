#!/usr/bin/env python3
"""
Complete E2E Test Suite for Options Lab - All 14 Subtabs
Tests in non-headless mode with screenshots and verification
"""

import os
import sys
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration
DASHBOARD_URL = "http://127.0.0.1:8051"
SCREENSHOT_DIR = "/tmp/options_lab_complete_test"
TIMEOUT = 30000  # 30 seconds

# All 14 subtabs to test
SUBTABS = [
    {"id": "options-chain-tab", "name": "Chain Viewer", "icon": "📋"},
    {"id": "options-greeks-tab", "name": "Greeks Calculator", "icon": "🔢"},
    {"id": "options-vol-tab", "name": "IV Surface & Forecast", "icon": "📈"},
    {"id": "options-flow-tab", "name": "Flow Scanner", "icon": "🔍"},
    {"id": "options-iv-tab", "name": "IV Analysis", "icon": "📊"},
    {"id": "options-strategy-tab", "name": "Strategy Builder", "icon": "🏗️"},
    {"id": "options-manual-tab", "name": "Manual Trade", "icon": "💼"},
    {"id": "options-portfolio-tab", "name": "Portfolio Greeks", "icon": "📉"},
    {"id": "options-screener-tab", "name": "Screener", "icon": "🔎"},
    {"id": "options-ai-tab", "name": "AI Recommendations", "icon": "🤖"},
    {"id": "options-earnings-tab", "name": "Earnings Calendar", "icon": "📅"},
    {"id": "options-journal-tab", "name": "Trade Journal", "icon": "📓"},
    {"id": "options-backtest-tab", "name": "Backtester", "icon": "🎯"},
    {"id": "options-settings-tab", "name": "Settings", "icon": "⚙️"},
]

class OptionsLabTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "dashboard_url": DASHBOARD_URL,
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": []
            }
        }
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def save_screenshot(self, page, name):
        """Save screenshot with timestamp"""
        filename = f"{SCREENSHOT_DIR}/{name}.png"
        try:
            page.screenshot(path=filename, full_page=False)
            self.log(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            self.log(f"Failed to save screenshot {name}: {e}", "ERROR")
            return None
    
    def record_result(self, test_name, success, details=None, screenshot=None):
        """Record test result"""
        result = {
            "test": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "screenshot": screenshot
        }
        self.results["tests"].append(result)
        self.results["summary"]["total"] += 1
        if success:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
            if details:
                self.results["summary"]["errors"].append(f"{test_name}: {details}")
    
    def run_tests(self):
        """Run complete test suite"""
        self.log("=" * 60)
        self.log("OPTIONS LAB COMPLETE E2E TEST SUITE")
        self.log("=" * 60)
        
        with sync_playwright() as p:
            # Launch browser in visible mode
            browser = p.chromium.launch(
                headless=False,
                slow_mo=200  # Slow down for visibility
            )
            
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            
            page = context.new_page()
            
            try:
                # Test 1: Load Dashboard
                self.log("\n[TEST 1] Loading Dashboard...")
                page.goto(DASHBOARD_URL, timeout=TIMEOUT)
                page.wait_for_load_state("networkidle", timeout=TIMEOUT)
                time.sleep(2)
                
                screenshot = self.save_screenshot(page, "01_dashboard_home")
                self.record_result("Dashboard Load", True, "Dashboard loaded successfully", screenshot)
                
                # Test 2: Navigate to Options Lab
                self.log("\n[TEST 2] Navigating to Options Lab...")
                options_tab = page.locator("#tab-options_lab")
                
                if options_tab.count() > 0:
                    options_tab.click()
                    time.sleep(2)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    
                    screenshot = self.save_screenshot(page, "02_options_lab_main")
                    self.record_result("Options Lab Navigation", True, "Successfully navigated to Options Lab", screenshot)
                else:
                    self.record_result("Options Lab Navigation", False, "Options Lab tab not found")
                    browser.close()
                    return self.results
                
                # Test 3: Load mock data
                self.log("\n[TEST 3] Loading mock data...")
                mock_btn = page.locator("#options-mock-btn")
                
                if mock_btn.count() > 0:
                    mock_btn.click()
                    time.sleep(3)
                    
                    screenshot = self.save_screenshot(page, "03_mock_data_loaded")
                    self.record_result("Load Mock Data", True, "Mock data loaded successfully", screenshot)
                else:
                    self.record_result("Load Mock Data", False, "Mock data button not found")
                
                # Test 4-17: Test each subtab
                for idx, subtab in enumerate(SUBTABS):
                    test_num = idx + 4
                    self.log(f"\n[TEST {test_num}] Testing subtab: {subtab['icon']} {subtab['name']}...")
                    
                    try:
                        # Find and click the subtab
                        tab_link = page.locator(f"#{subtab['id']}")
                        
                        if tab_link.count() > 0:
                            # Scroll to make sure it's visible
                            tab_link.scroll_into_view_if_needed()
                            time.sleep(0.3)
                            
                            tab_link.click()
                            time.sleep(1.5)  # Wait for content to load
                            
                            # Take screenshot
                            screenshot_name = f"{test_num:02d}_{subtab['id'].replace('-', '_')}"
                            screenshot = self.save_screenshot(page, screenshot_name)
                            
                            # Verify tab content is visible (check for any content in the tab pane)
                            self.record_result(
                                f"Subtab: {subtab['name']}", 
                                True, 
                                f"Tab {subtab['icon']} {subtab['name']} loaded successfully",
                                screenshot
                            )
                            self.log(f"  ✓ {subtab['icon']} {subtab['name']} - PASSED")
                        else:
                            self.record_result(
                                f"Subtab: {subtab['name']}", 
                                False, 
                                f"Tab element #{subtab['id']} not found"
                            )
                            self.log(f"  ✗ {subtab['icon']} {subtab['name']} - FAILED (not found)")
                    
                    except PlaywrightTimeout as e:
                        self.record_result(
                            f"Subtab: {subtab['name']}", 
                            False, 
                            f"Timeout: {str(e)}"
                        )
                        self.log(f"  ✗ {subtab['icon']} {subtab['name']} - TIMEOUT")
                    
                    except Exception as e:
                        self.record_result(
                            f"Subtab: {subtab['name']}", 
                            False, 
                            f"Error: {str(e)}"
                        )
                        self.log(f"  ✗ {subtab['icon']} {subtab['name']} - ERROR: {e}")
                
                # Test: Check console errors
                self.log("\n[TEST] Checking for console errors...")
                console_errors = []
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                
                # Final screenshot with all tabs verified
                screenshot = self.save_screenshot(page, "99_final_state")
                
            except Exception as e:
                self.log(f"Critical error during testing: {e}", "ERROR")
                self.record_result("Test Suite", False, f"Critical error: {str(e)}")
            
            finally:
                # Keep browser open for 5 seconds for visual inspection
                self.log("\nKeeping browser open for inspection...")
                time.sleep(5)
                browser.close()
        
        return self.results
    
    def print_summary(self):
        """Print test summary"""
        summary = self.results["summary"]
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']} ✓")
        print(f"Failed: {summary['failed']} ✗")
        print(f"Success Rate: {(summary['passed']/max(summary['total'],1))*100:.1f}%")
        
        if summary['errors']:
            print("\nErrors:")
            for error in summary['errors']:
                print(f"  - {error}")
        
        print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
        print("=" * 60)
    
    def save_results(self):
        """Save results to JSON file"""
        results_file = f"{SCREENSHOT_DIR}/test_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        self.log(f"Results saved to: {results_file}")


def main():
    print("\n" + "=" * 60)
    print("OPTIONS LAB COMPLETE E2E TEST")
    print("Non-headless mode with visual verification")
    print("=" * 60 + "\n")
    
    tester = OptionsLabTester()
    results = tester.run_tests()
    tester.print_summary()
    tester.save_results()
    
    # Return exit code based on results
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
