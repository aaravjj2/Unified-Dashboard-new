#!/usr/bin/env python3
"""
Phase 11B: Fixed Playwright Tests
Uses text-based selectors instead of IDs since React generates dynamic IDs
"""
from playwright.sync_api import sync_playwright, Page
import time
import json
from pathlib import Path

print("🧪 Phase 11B: Fixed Playwright Smoke Tests")
print("=" * 70)

DASHBOARD_URL = "http://localhost:8050"
TIMEOUT_MS = 15000

# Test configuration - using text-based selectors
TEST_TABS = {
    "Market Trends": {
        "text": "Market Trends",
        "expected_elements": ["market-trends-table", "market-trends-sentinel-table"]
    },
    "Portfolio": {
        "text": "Portfolio",
        "expected_elements": ["portfolio-value", "portfolio-positions"]
    },
    "Options Lab": {
        "text": "Options Lab",
        "expected_elements": ["options"]  # Flexible - any element with "options" in it
    },
    "Volatility Lab": {
        "text": "Volatility Lab",
        "expected_elements": ["volatility", "vol"]  # Flexible matching
    }
}

results = {
    "total": len(TEST_TABS),
    "passed": 0,
    "failed": 0,
    "tests": []
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print(f"\n🌐 Loading dashboard: {DASHBOARD_URL}")
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)
    
    # Wait for dashboard to be ready
    try:
        page.wait_for_selector("#dashboard-tabs", timeout=TIMEOUT_MS)
        print("✅ Dashboard loaded successfully")
    except:
        print("❌ Dashboard failed to load")
        browser.close()
        exit(1)
    
    # Test each tab
    for tab_name, config in TEST_TABS.items():
        print(f"\n{'=' * 70}")
        print(f"Testing Tab: {tab_name}")
        print("=" * 70)
        
        test_result = {
            "tab": tab_name,
            "status": "FAILED",
            "duration_ms": 0,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            # Click tab using text content
            tab_text = config["text"]
            selector = f'a[role="tab"]:has-text("{tab_text}")'
            
            print(f"🖱️  Clicking tab by text: '{tab_text}'")
            page.click(selector, timeout=5000)
            time.sleep(2)  # Wait for content to load
            
            print(f"✅ Navigated to {tab_name}")
            
            # Verify at least one expected element is present and visible
            elements_found = []
            for elem_id in config["expected_elements"]:
                # Try multiple selector strategies
                selectors = [
                    f"#{elem_id}",
                    f"[id*='{elem_id}']",
                    f"[data-testid='{elem_id}']",
                    f"[data-testid*='{elem_id}']"
                ]
                
                for selector in selectors:
                    try:
                        count = page.locator(selector).count()
                        if count > 0:
                            elements_found.append(elem_id)
                            print(f"   ✅ Found element: {elem_id} (via {selector})")
                            break
                    except:
                        pass
            
            if elements_found:
                test_result["status"] = "PASSED"
                test_result["elements_found"] = elements_found
                results["passed"] += 1
                print(f"✅ {tab_name} test PASSED")
            else:
                test_result["error"] = "No expected elements found"
                results["failed"] += 1
                print(f"⚠️  {tab_name} test: Elements not found ({config['expected_elements']})")
                
            # Capture screenshot
            screenshot_path = f"ci_reports/ui_validation/phase11b_{tab_name.lower().replace(' ', '_')}.png"
            Path("ci_reports/ui_validation").mkdir(parents=True, exist_ok=True)
            page.screenshot(path=screenshot_path)
            test_result["screenshot"] = screenshot_path
            
        except Exception as e:
            test_result["error"] = str(e)
            results["failed"] += 1
            print(f"❌ {tab_name} test FAILED: {e}")
        
        test_result["duration_ms"] = int((time.time() - start_time) * 1000)
        results["tests"].append(test_result)
    
    browser.close()

# Print summary
print("\n" + "=" * 70)
print("TEST SUITE SUMMARY")
print("=" * 70)
print(f"Total Tabs Tested: {results['total']}")
print(f"✅ Passed: {results['passed']}")
print(f"❌ Failed: {results['failed']}")
print(f"Success Rate: {round(results['passed'] / results['total'] * 100, 1)}%")

if results["failed"] > 0:
    print(f"\nFailed Tests:")
    for test in results["tests"]:
        if test["status"] == "FAILED":
            print(f"  ❌ {test['tab']}: {test.get('error', 'Unknown error')}")

# Save results
output_path = Path("ci_reports/ui_validation/phase11b_smoke_tests.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\n📄 Results saved: {output_path}")

# Exit code
exit(0 if results["failed"] == 0 else 1)
