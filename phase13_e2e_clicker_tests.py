#!/usr/bin/env python3
"""
Phase 13 - End-to-End Chromium Clicker Tests
Comprehensive button and callback testing with visual verification.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DASHBOARD_URL = "http://localhost:8051"
OUTPUT_DIR = Path("phase13_e2e_results")
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
TIMEOUT = 15000

# Test scenarios for each problematic tab
TEST_SCENARIOS = {
    "Strategy Lab": {
        "tab_selector": "a.nav-link:has-text('Strategy Lab')",
        "tests": [
            {
                "name": "Setup - Validate Strategy Button",
                "steps": [
                    {"action": "wait", "ms": 2000},
                    {"action": "screenshot", "name": "strategy_lab_setup_before"},
                    {"action": "click", "selector": "button#sl-validate-btn"},
                    {"action": "wait", "ms": 3000},
                    {"action": "screenshot", "name": "strategy_lab_setup_after"},
                    {"action": "check_element", "selector": "#sl-validation-result", "should_exist": True}
                ]
            },
            {
                "name": "Backtest - Date Pickers",
                "steps": [
                    {"action": "click", "selector": "button#backtest-tab"},
                    {"action": "wait", "ms": 1000},
                    {"action": "screenshot", "name": "strategy_lab_backtest"},
                    {"action": "check_element", "selector": "#sl-start-date", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-end-date", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-transaction-cost", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-position-size", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-max-positions", "should_exist": True}
                ]
            },
            {
                "name": "Execute - Run Backtest Button",
                "steps": [
                    {"action": "click", "selector": "button#execute-tab"},
                    {"action": "wait", "ms": 1000},
                    {"action": "screenshot", "name": "strategy_lab_execute"},
                    {"action": "check_element", "selector": "#sl-run-backtest-btn", "should_exist": True}
                ]
            },
            {
                "name": "Results - Metric Components",
                "steps": [
                    {"action": "click", "selector": "button#results-tab"},
                    {"action": "wait", "ms": 1000},
                    {"action": "screenshot", "name": "strategy_lab_results"},
                    {"action": "check_element", "selector": "#sl-metric-cagr", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-metric-sharpe", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-metric-maxdd", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-metric-winrate", "should_exist": True}
                ]
            },
            {
                "name": "Benchmark - Charts",
                "steps": [
                    {"action": "click", "selector": "button#benchmark-tab"},
                    {"action": "wait", "ms": 1000},
                    {"action": "screenshot", "name": "strategy_lab_benchmark"},
                    {"action": "check_element", "selector": "#sl-vs-benchmark", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-factor-attribution", "should_exist": True},
                    {"action": "check_element", "selector": "#sl-exposure-breakdown", "should_exist": True}
                ]
            }
        ]
    },
    "Home / Command Center": {
        "tab_selector": "a.nav-link:has-text('Command Center'), a.nav-link:has-text('Home')",
        "tests": [
            {
                "name": "Run Full Diagnostic Button",
                "steps": [
                    {"action": "wait", "ms": 2000},
                    {"action": "screenshot", "name": "home_before_diagnostic"},
                    {"action": "click", "selector": "button#home-run-diagnostic-btn"},
                    {"action": "wait", "ms": 5000},
                    {"action": "screenshot", "name": "home_after_diagnostic"},
                    {"action": "check_element", "selector": "#home-diagnostic-result", "should_exist": True},
                    {"action": "check_content", "selector": "#home-diagnostic-result", "should_have_content": True}
                ]
            }
        ]
    },
    "Azure ML Lab": {
        "tab_selector": "a.nav-link:has-text('Azure ML Lab')",
        "tests": [
            {
                "name": "Verify Scaffold Mode Banner",
                "steps": [
                    {"action": "wait", "ms": 2000},
                    {"action": "screenshot", "name": "azure_ml_lab_overview"},
                    {"action": "check_element", "selector": "#azure-ml-status-badge", "should_exist": True},
                    {"action": "check_text", "selector": "#azure-ml-status-badge", "expected_text": "Scaffold Mode"}
                ]
            }
        ]
    },
    "Options Lab": {
        "tab_selector": "a.nav-link:has-text('Options Lab')",
        "tests": [
            {
                "name": "Inventory All Buttons",
                "steps": [
                    {"action": "wait", "ms": 2000},
                    {"action": "screenshot", "name": "options_lab_overview"},
                    {"action": "count_buttons", "min_expected": 1}
                ]
            }
        ]
    }
}

class E2ETestRunner:
    def __init__(self):
        self.results = []
        self.console_errors = []
        OUTPUT_DIR.mkdir(exist_ok=True)
        SCREENSHOTS_DIR.mkdir(exist_ok=True)
    
    async def execute_step(self, page, step, test_name):
        """Execute a single test step."""
        action = step["action"]
        
        try:
            if action == "wait":
                await page.wait_for_timeout(step["ms"])
                return {"status": "success", "action": action}
            
            elif action == "click":
                selector = step["selector"]
                elem = await page.query_selector(selector)
                if not elem:
                    return {"status": "fail", "action": action, "error": f"Element not found: {selector}"}
                await elem.click()
                return {"status": "success", "action": action, "selector": selector}
            
            elif action == "screenshot":
                name = step["name"]
                screenshot_path = SCREENSHOTS_DIR / f"{name}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                return {"status": "success", "action": action, "path": str(screenshot_path)}
            
            elif action == "check_element":
                selector = step["selector"]
                should_exist = step.get("should_exist", True)
                elem = await page.query_selector(selector)
                exists = elem is not None
                
                if exists == should_exist:
                    return {"status": "success", "action": action, "selector": selector, "exists": exists}
                else:
                    return {
                        "status": "fail", 
                        "action": action, 
                        "selector": selector,
                        "error": f"Expected exists={should_exist}, got exists={exists}"
                    }
            
            elif action == "check_content":
                selector = step["selector"]
                should_have_content = step.get("should_have_content", True)
                elem = await page.query_selector(selector)
                if not elem:
                    return {"status": "fail", "action": action, "error": f"Element not found: {selector}"}
                
                text = await elem.inner_text()
                has_content = len(text.strip()) > 0
                
                if has_content == should_have_content:
                    return {
                        "status": "success", 
                        "action": action, 
                        "selector": selector,
                        "content_preview": text[:100]
                    }
                else:
                    return {
                        "status": "fail",
                        "action": action,
                        "selector": selector,
                        "error": f"Expected has_content={should_have_content}, got has_content={has_content}"
                    }
            
            elif action == "check_text":
                selector = step["selector"]
                expected_text = step["expected_text"]
                elem = await page.query_selector(selector)
                if not elem:
                    return {"status": "fail", "action": action, "error": f"Element not found: {selector}"}
                
                actual_text = await elem.inner_text()
                if expected_text.lower() in actual_text.lower():
                    return {"status": "success", "action": action, "selector": selector, "text": actual_text}
                else:
                    return {
                        "status": "fail",
                        "action": action,
                        "selector": selector,
                        "error": f"Expected '{expected_text}' in '{actual_text}'"
                    }
            
            elif action == "count_buttons":
                buttons = await page.query_selector_all("button")
                count = len(buttons)
                min_expected = step.get("min_expected", 0)
                
                if count >= min_expected:
                    return {"status": "success", "action": action, "button_count": count}
                else:
                    return {
                        "status": "fail",
                        "action": action,
                        "error": f"Expected >= {min_expected} buttons, found {count}"
                    }
            
            else:
                return {"status": "fail", "action": action, "error": f"Unknown action: {action}"}
        
        except Exception as e:
            return {"status": "error", "action": action, "error": str(e)}
    
    async def run_test(self, page, tab_name, test_config):
        """Run a single test scenario."""
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {tab_name} - {test_config['name']}")
        logger.info(f"{'='*80}")
        
        test_result = {
            "tab": tab_name,
            "test": test_config["name"],
            "steps": [],
            "status": "unknown",
            "errors": []
        }
        
        for i, step in enumerate(test_config["steps"], 1):
            logger.info(f"  Step {i}/{len(test_config['steps'])}: {step['action']}")
            step_result = await self.execute_step(page, step, test_config['name'])
            test_result["steps"].append(step_result)
            
            if step_result["status"] == "fail":
                logger.error(f"    ❌ FAILED: {step_result.get('error', 'Unknown error')}")
                test_result["errors"].append(step_result.get('error'))
            elif step_result["status"] == "error":
                logger.error(f"    💥 ERROR: {step_result.get('error', 'Unknown error')}")
                test_result["errors"].append(step_result.get('error'))
            else:
                logger.info(f"    ✅ {step['action']} succeeded")
        
        # Determine overall test status
        if any(s["status"] in ["fail", "error"] for s in test_result["steps"]):
            test_result["status"] = "FAIL"
        else:
            test_result["status"] = "PASS"
        
        logger.info(f"  Result: {test_result['status']}")
        return test_result
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        logger.info("🚀 Starting Phase 13 E2E Chromium Clicker Tests")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            
            # Capture console errors
            page.on("console", lambda msg: 
                self.console_errors.append(f"[{msg.type}] {msg.text}") 
                if msg.type == "error" else None
            )
            
            try:
                # Load dashboard
                logger.info(f"\n📡 Loading dashboard: {DASHBOARD_URL}")
                await page.goto(DASHBOARD_URL, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                
                # Run tests for each tab
                for tab_name, tab_config in TEST_SCENARIOS.items():
                    logger.info(f"\n{'#'*80}")
                    logger.info(f"TAB: {tab_name}")
                    logger.info(f"{'#'*80}")
                    
                    # Navigate to tab
                    try:
                        tab_selector = tab_config["tab_selector"]
                        logger.info(f"Clicking tab: {tab_selector}")
                        await page.click(tab_selector, timeout=TIMEOUT)
                        await page.wait_for_timeout(2000)
                    except Exception as e:
                        logger.error(f"❌ Failed to click tab: {str(e)}")
                        self.results.append({
                            "tab": tab_name,
                            "test": "Tab Navigation",
                            "status": "FAIL",
                            "error": str(e)
                        })
                        continue
                    
                    # Run all tests for this tab
                    for test_config in tab_config["tests"]:
                        test_result = await self.run_test(page, tab_name, test_config)
                        self.results.append(test_result)
                
            except Exception as e:
                logger.error(f"❌ Fatal error: {str(e)}")
                self.results.append({
                    "tab": "Global",
                    "test": "Test Suite",
                    "status": "FATAL",
                    "error": str(e)
                })
            finally:
                await browser.close()
    
    def generate_report(self):
        """Generate comprehensive test report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate statistics
        total_tests = len(self.results)
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        errors = len([r for r in self.results if r["status"] in ["FATAL", "ERROR"]])
        
        # Generate report
        report = f"""
{'='*100}
PHASE 13 - END-TO-END CHROMIUM CLICKER TEST REPORT
{'='*100}
Timestamp: {timestamp}
Dashboard URL: {DASHBOARD_URL}

📊 SUMMARY:
   Total Tests:     {total_tests}
   ✅ Passed:       {passed} ({passed/total_tests*100:.1f}%)
   ❌ Failed:       {failed} ({failed/total_tests*100:.1f}%)
   💥 Errors:       {errors} ({errors/total_tests*100:.1f}%)

{'='*100}
TEST RESULTS BY TAB:
{'='*100}
"""
        
        # Group by tab
        tabs = {}
        for result in self.results:
            tab = result["tab"]
            if tab not in tabs:
                tabs[tab] = []
            tabs[tab].append(result)
        
        for tab_name, tab_results in sorted(tabs.items()):
            report += f"\n{'▼'*100}\n"
            report += f"TAB: {tab_name}\n"
            report += f"{'▼'*100}\n"
            
            for result in tab_results:
                status_icon = {"PASS": "✅", "FAIL": "❌", "FATAL": "💥"}.get(result["status"], "❓")
                report += f"\n{status_icon} {result['test']}\n"
                report += f"   Status: {result['status']}\n"
                
                if result.get("errors"):
                    report += f"   Errors ({len(result['errors'])}):\n"
                    for err in result['errors']:
                        report += f"      • {err}\n"
                
                # Step-by-step results
                if "steps" in result:
                    report += f"   Steps: {len(result['steps'])} total\n"
                    for i, step in enumerate(result['steps'], 1):
                        step_icon = {"success": "✓", "fail": "✗", "error": "💥"}.get(step["status"], "?")
                        report += f"      {step_icon} Step {i}: {step['action']}\n"
        
        # Console errors
        report += f"\n{'='*100}\n"
        report += f"CONSOLE ERRORS ({len(self.console_errors)}):\n"
        report += f"{'='*100}\n"
        if self.console_errors:
            for err in self.console_errors[:20]:  # Limit to 20
                report += f"   • {err}\n"
        else:
            report += "   ✅ No console errors detected!\n"
        
        report += f"\n{'='*100}\n"
        report += f"Screenshots saved to: {SCREENSHOTS_DIR}\n"
        report += f"{'='*100}\n"
        
        return report
    
    def save_results(self):
        """Save results to JSON and text files."""
        # Save JSON
        json_file = OUTPUT_DIR / "phase13_e2e_results.json"
        with open(json_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "dashboard_url": DASHBOARD_URL,
                "results": self.results,
                "console_errors": self.console_errors
            }, f, indent=2)
        logger.info(f"✅ JSON results saved to: {json_file}")
        
        # Save report
        report = self.generate_report()
        report_file = OUTPUT_DIR / "phase13_e2e_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        logger.info(f"✅ Report saved to: {report_file}")
        
        return report

async def main():
    """Main test execution."""
    runner = E2ETestRunner()
    
    try:
        await runner.run_all_tests()
        report = runner.save_results()
        print(report)
    except Exception as e:
        logger.error(f"❌ Test suite failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
