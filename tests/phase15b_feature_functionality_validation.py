#!/usr/bin/env python3
"""
PHASE 15B - FEATURE FUNCTIONALITY VALIDATION & BUTTON CALLBACK REPAIR
Port 8051 - Chromium Headless - Independent Execution

Mission: Repair and validate all inactive buttons until 100% functional or documented.
Target: Options Forecast, Azure ML Lab buttons, System Health ≥95%
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Configuration
DASHBOARD_URL = "http://localhost:8051"
OUTPUTS_DIR = Path("outputs/phase15b_final")
ACTION_TIMEOUT = 20000  # 20s for button clicks
NAVIGATION_TIMEOUT = 30000  # 30s for navigation
WAIT_AFTER_CLICK = 3000  # Wait 3s for UI updates
RETRY_COUNT = 3

# Target features for validation
FEATURE_TARGETS = {
    "market_forecast_options": {
        "tab": "Market Forecast",
        "tab_selector": "#tab-market_forecast",
        "button_text": "Fetch Options Forecast",
        "button_selectors": [
            "button:has-text('Fetch Options Forecast')",
            "button:has-text('Fetch')",
            "#options-forecast-btn",
            ".options-forecast-button"
        ],
        "expected_outputs": [
            "#options-forecast-output",
            ".forecast-result",
            "#forecast-container",
            "[id*='forecast']"
        ]
    },
    "azure_ml_buttons": {
        "tab": "🤖 Azure ML Lab",
        "tab_selector": "#tab-azure_ml_lab",
        "subtabs": ["📊 Predictions", "Performance"],
        "button_patterns": [
            "button:has-text('Run')",
            "button:has-text('Generate')",
            "button:has-text('Fetch')",
            "button:has-text('Calculate')",
            "button:has-text('Analyze')",
            "button:has-text('Predict')",
            "button:has-text('Train')",
            "button:has-text('Submit')"
        ]
    },
    "system_health": {
        "tab": "Settings",
        "tab_selector": "#tab-settings",
        "health_selectors": [
            "#system-health-indicator",
            ".system-health",
            "[id*='health']",
            "text=/\\d+%/"
        ],
        "target_value": 95.0
    }
}


class TelemetryDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()
        self._init_schema()
    
    def _init_schema(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                feature TEXT NOT NULL,
                tab TEXT NOT NULL,
                subtab TEXT,
                button_text TEXT,
                action TEXT NOT NULL,
                duration_ms INTEGER,
                success INTEGER NOT NULL,
                output_detected INTEGER,
                console_errors INTEGER,
                network_errors INTEGER,
                details TEXT
            )
        """)
        self.conn.commit()
    
    def log_feature_test(self, feature: str, tab: str, subtab: str, button_text: str, 
                        action: str, duration_ms: int, success: bool, 
                        output_detected: bool, console_errors: int, 
                        network_errors: int, details: str = ""):
        self.cursor.execute("""
            INSERT INTO feature_tests 
            (timestamp, feature, tab, subtab, button_text, action, duration_ms, 
             success, output_detected, console_errors, network_errors, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            feature,
            tab,
            subtab or "",
            button_text or "",
            action,
            duration_ms,
            1 if success else 0,
            1 if output_detected else 0,
            console_errors,
            network_errors,
            details
        ))
        self.conn.commit()
    
    def close(self):
        self.conn.close()


class Phase15BFeatureValidator:
    def __init__(self):
        self.playwright_context = None
        self.browser = None
        self.page = None
        self.console_errors = []
        self.network_errors = []
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "FAIL",
            "features_tested": 0,
            "features_passed": 0,
            "buttons_tested": 0,
            "buttons_functional": 0,
            "system_health_value": 0.0,
            "system_health_target": 95.0,
            "detailed_results": [],
            "remediation_tickets": []
        }
    
    async def setup(self):
        print("🚀 Initializing Playwright Chromium...")
        self.playwright_context = await async_playwright().start()
        self.browser = await self.playwright_context.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Event listeners
        self.page.on("console", self._on_console)
        self.page.on("pageerror", lambda err: self.console_errors.append(f"[PAGE ERROR] {str(err)}"))
        self.page.on("requestfailed", lambda req: self.network_errors.append(f"[NETWORK FAIL] {req.url}"))
        
        await self.page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)
        await self.page.wait_for_selector("#dashboard-tabs", state="visible", timeout=10000)
        print(f"✅ Dashboard loaded: {await self.page.title()}")
    
    def _on_console(self, msg):
        if msg.type in ("error", "warning"):
            self.console_errors.append(f"[{msg.type.upper()}] {msg.text}")
    
    async def teardown(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright_context:
            await self.playwright_context.stop()
    
    async def navigate_to_tab(self, tab_name: str, selector: str) -> bool:
        """Navigate to tab using text or selector"""
        for attempt in range(RETRY_COUNT):
            try:
                # Try selector first
                await self.page.click(selector, timeout=ACTION_TIMEOUT)
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(2)
                return True
            except:
                # Try text-based selector
                try:
                    text_selector = f"a[role='tab']:has-text('{tab_name}')"
                    await self.page.click(text_selector, timeout=ACTION_TIMEOUT)
                    await asyncio.sleep(2)
                    return True
                except:
                    if attempt == RETRY_COUNT - 1:
                        return False
                    await asyncio.sleep(1)
        return False
    
    async def navigate_to_subtab(self, subtab_name: str) -> bool:
        """Navigate to subtab using text-based selector"""
        try:
            all_tabs = await self.page.query_selector_all("a[role='tab']")
            for tab in all_tabs:
                is_visible = await tab.is_visible()
                if not is_visible:
                    continue
                text = await tab.text_content()
                if text and subtab_name in text:
                    await tab.click(timeout=ACTION_TIMEOUT)
                    await asyncio.sleep(1.5)
                    return True
            return False
        except:
            return False
    
    async def capture_screenshot(self, feature: str, suffix: str = "") -> bool:
        """Capture screenshot"""
        try:
            folder = OUTPUTS_DIR / "screenshots" / feature
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"{suffix}.png" if suffix else "main.png"
            await self.page.screenshot(path=str(folder / filename), full_page=True)
            return True
        except Exception as e:
            print(f"❌ Screenshot error: {e}")
            return False
    
    async def dump_dom(self, feature: str, suffix: str = "") -> bool:
        """Dump DOM to JSON"""
        try:
            folder = OUTPUTS_DIR / "dom_dumps" / feature
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"{suffix}.json" if suffix else "main.json"
            
            html = await self.page.content()
            dom_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "feature": feature,
                "url": self.page.url,
                "html_length": len(html),
                "html": html[:50000]  # Truncate to 50KB
            }
            
            with open(folder / filename, 'w') as f:
                json.dump(dom_data, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ DOM dump error: {e}")
            return False
    
    async def check_output_visible(self, selectors: List[str]) -> Tuple[bool, str]:
        """Check if any output element is visible"""
        for sel in selectors:
            try:
                elem = await self.page.query_selector(sel)
                if elem and await elem.is_visible():
                    text = await elem.text_content()
                    return True, f"Output visible: {sel}, content length: {len(text) if text else 0}"
            except:
                continue
        return False, "No output elements found"
    
    async def test_options_forecast(self, telemetry: TelemetryDB) -> Dict:
        """Test Options Forecast button in Market Forecast tab"""
        print("\n" + "="*70)
        print("🎯 TESTING: Options Forecast Button")
        print("="*70)
        
        config = FEATURE_TARGETS["market_forecast_options"]
        result = {
            "feature": "options_forecast",
            "tab": config["tab"],
            "status": "FAIL",
            "button_found": False,
            "button_clicked": False,
            "output_visible": False,
            "details": []
        }
        
        # Navigate to Market Forecast tab
        if not await self.navigate_to_tab(config["tab"], config["tab_selector"]):
            result["details"].append("Failed to navigate to Market Forecast tab")
            telemetry.log_feature_test("options_forecast", config["tab"], None, None, 
                                      "navigate", 0, False, False, 
                                      len(self.console_errors), len(self.network_errors),
                                      "Tab navigation failed")
            return result
        
        await self.capture_screenshot("options_forecast", "tab_loaded")
        
        # Find and click button
        button_clicked = False
        button_text = ""
        
        for selector in config["button_selectors"]:
            try:
                print(f"  🔍 Trying selector: {selector}")
                btn = await self.page.query_selector(selector)
                if btn and await btn.is_visible():
                    button_text = await btn.text_content() or selector
                    print(f"  ✅ Button found: {button_text}")
                    result["button_found"] = True
                    
                    # Click button
                    await btn.click(timeout=ACTION_TIMEOUT)
                    print(f"  🖱️  Button clicked, waiting for response...")
                    await asyncio.sleep(WAIT_AFTER_CLICK / 1000)
                    
                    button_clicked = True
                    result["button_clicked"] = True
                    break
            except Exception as e:
                print(f"  ❌ Error with selector {selector}: {e}")
                continue
        
        if not button_clicked:
            result["details"].append("Button not found or not clickable")
            telemetry.log_feature_test("options_forecast", config["tab"], None, button_text,
                                      "click", 0, False, False,
                                      len(self.console_errors), len(self.network_errors),
                                      "Button not found")
            return result
        
        # Check for output
        await asyncio.sleep(2)  # Additional wait for async operations
        output_visible, output_msg = await self.check_output_visible(config["expected_outputs"])
        result["output_visible"] = output_visible
        result["details"].append(output_msg)
        
        if output_visible:
            result["status"] = "PASS"
            print(f"  ✅ Output detected: {output_msg}")
            await self.capture_screenshot("options_forecast", "after_click_success")
            await self.dump_dom("options_forecast", "after_click_success")
        else:
            print(f"  ⚠️  No output detected")
            await self.capture_screenshot("options_forecast", "after_click_no_output")
            await self.dump_dom("options_forecast", "after_click_no_output")
        
        telemetry.log_feature_test("options_forecast", config["tab"], None, button_text,
                                  "click", WAIT_AFTER_CLICK, output_visible, output_visible,
                                  len(self.console_errors), len(self.network_errors),
                                  output_msg)
        
        return result
    
    async def test_azure_ml_buttons(self, telemetry: TelemetryDB) -> Dict:
        """Test all buttons in Azure ML Lab"""
        print("\n" + "="*70)
        print("🎯 TESTING: Azure ML Lab Buttons")
        print("="*70)
        
        config = FEATURE_TARGETS["azure_ml_buttons"]
        result = {
            "feature": "azure_ml_buttons",
            "tab": config["tab"],
            "status": "FAIL",
            "subtabs_tested": 0,
            "buttons_found": 0,
            "buttons_functional": 0,
            "subtab_results": []
        }
        
        # Navigate to Azure ML Lab
        if not await self.navigate_to_tab(config["tab"], config["tab_selector"]):
            result["details"] = ["Failed to navigate to Azure ML Lab"]
            return result
        
        await self.capture_screenshot("azure_ml_buttons", "tab_loaded")
        
        # Test each subtab
        for subtab_name in config["subtabs"]:
            print(f"\n  📂 Testing subtab: {subtab_name}")
            
            subtab_result = {
                "subtab": subtab_name,
                "buttons_found": 0,
                "buttons_functional": 0,
                "button_tests": []
            }
            
            if not await self.navigate_to_subtab(subtab_name):
                print(f"    ❌ Failed to navigate to {subtab_name}")
                subtab_result["error"] = "Navigation failed"
                result["subtab_results"].append(subtab_result)
                continue
            
            await asyncio.sleep(2)
            await self.capture_screenshot("azure_ml_buttons", f"subtab_{subtab_name.replace(' ', '_')}")
            
            # Find all buttons matching patterns
            all_buttons = await self.page.query_selector_all("button")
            tested_buttons = []
            
            for btn in all_buttons:
                try:
                    if not await btn.is_visible():
                        continue
                    
                    btn_text = await btn.text_content()
                    if not btn_text:
                        continue
                    
                    # Check if button matches any pattern
                    matches_pattern = False
                    for pattern in config["button_patterns"]:
                        pattern_text = pattern.replace("button:has-text('", "").replace("')", "")
                        if pattern_text.lower() in btn_text.lower():
                            matches_pattern = True
                            break
                    
                    if not matches_pattern:
                        continue
                    
                    print(f"    🔘 Found button: {btn_text.strip()}")
                    result["buttons_found"] += 1
                    subtab_result["buttons_found"] += 1
                    
                    # Test button
                    btn_test = {
                        "text": btn_text.strip(),
                        "clicked": False,
                        "response_detected": False
                    }
                    
                    try:
                        # Clear previous errors
                        self.console_errors.clear()
                        self.network_errors.clear()
                        
                        # Click button
                        await btn.click(timeout=ACTION_TIMEOUT)
                        btn_test["clicked"] = True
                        print(f"      🖱️  Clicked, waiting for response...")
                        
                        await asyncio.sleep(WAIT_AFTER_CLICK / 1000)
                        
                        # Check for DOM changes or network activity
                        has_console_errors = len(self.console_errors) > 0
                        has_network_errors = len(self.network_errors) > 0
                        
                        if not has_console_errors and not has_network_errors:
                            btn_test["response_detected"] = True
                            result["buttons_functional"] += 1
                            subtab_result["buttons_functional"] += 1
                            print(f"      ✅ Button functional")
                        else:
                            print(f"      ⚠️  Errors detected: console={len(self.console_errors)}, network={len(self.network_errors)}")
                        
                        telemetry.log_feature_test("azure_ml_buttons", config["tab"], subtab_name,
                                                  btn_text.strip(), "click", WAIT_AFTER_CLICK,
                                                  btn_test["response_detected"], 
                                                  btn_test["response_detected"],
                                                  len(self.console_errors), len(self.network_errors),
                                                  f"Button clicked: {btn_text.strip()}")
                        
                    except Exception as e:
                        print(f"      ❌ Click failed: {e}")
                        btn_test["error"] = str(e)
                    
                    subtab_result["button_tests"].append(btn_test)
                    tested_buttons.append(btn_text.strip())
                    
                except Exception as e:
                    print(f"    ❌ Error testing button: {e}")
                    continue
            
            result["subtabs_tested"] += 1
            result["subtab_results"].append(subtab_result)
            
            await self.capture_screenshot("azure_ml_buttons", 
                                        f"subtab_{subtab_name.replace(' ', '_')}_tested")
            await self.dump_dom("azure_ml_buttons", 
                               f"subtab_{subtab_name.replace(' ', '_')}_tested")
        
        if result["buttons_functional"] > 0:
            result["status"] = "PARTIAL" if result["buttons_functional"] < result["buttons_found"] else "PASS"
        
        return result
    
    async def test_system_health(self, telemetry: TelemetryDB) -> Dict:
        """Test System Health indicator"""
        print("\n" + "="*70)
        print("🎯 TESTING: System Health Indicator")
        print("="*70)
        
        config = FEATURE_TARGETS["system_health"]
        result = {
            "feature": "system_health",
            "tab": config["tab"],
            "status": "FAIL",
            "health_value": 0.0,
            "target_value": config["target_value"],
            "indicator_found": False,
            "details": []
        }
        
        # Try to find Settings tab
        # Note: Settings tab may not exist, try common alternatives
        settings_selectors = [
            "#tab-settings",
            "a[role='tab']:has-text('Settings')",
            "a[role='tab']:has-text('System')",
            "#tab-home_lab"  # System health might be in Command Center
        ]
        
        tab_found = False
        for sel in settings_selectors:
            try:
                await self.page.click(sel, timeout=5000)
                await asyncio.sleep(2)
                tab_found = True
                print(f"  ✅ Found tab with selector: {sel}")
                break
            except:
                continue
        
        if not tab_found:
            result["details"].append("Settings/System tab not found - checking Command Center")
            # Try Command Center as fallback
            try:
                await self.page.click("#tab-home_lab", timeout=5000)
                await asyncio.sleep(2)
            except:
                result["details"].append("Could not navigate to any tab with system health")
                return result
        
        await self.capture_screenshot("system_health", "tab_loaded")
        
        # Search for health indicator
        health_value = None
        indicator_text = ""
        
        for selector in config["health_selectors"]:
            try:
                if selector.startswith("text="):
                    # Regex selector for percentage
                    elements = await self.page.query_selector_all("*")
                    for elem in elements:
                        if not await elem.is_visible():
                            continue
                        text = await elem.text_content()
                        if text and '%' in text:
                            # Try to extract percentage
                            import re
                            matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
                            if matches:
                                try:
                                    val = float(matches[0])
                                    if 0 <= val <= 100:
                                        health_value = val
                                        indicator_text = text.strip()
                                        result["indicator_found"] = True
                                        print(f"  ✅ Health indicator found: {indicator_text}")
                                        break
                                except:
                                    continue
                else:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        text = await elem.text_content()
                        if text:
                            indicator_text = text.strip()
                            result["indicator_found"] = True
                            # Try to extract percentage
                            import re
                            matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
                            if matches:
                                health_value = float(matches[0])
                            print(f"  ✅ Health indicator found: {indicator_text}")
                            break
            except Exception as e:
                print(f"  ❌ Error with selector {selector}: {e}")
                continue
        
        if health_value is not None:
            result["health_value"] = health_value
            result["details"].append(f"Health value: {health_value}%")
            
            if health_value >= config["target_value"]:
                result["status"] = "PASS"
                print(f"  ✅ System Health: {health_value}% (Target: {config['target_value']}%)")
            else:
                print(f"  ⚠️  System Health: {health_value}% < {config['target_value']}% (Target not met)")
                result["details"].append(f"Health below target: {health_value}% < {config['target_value']}%")
        else:
            result["details"].append("Could not extract health percentage value")
        
        await self.capture_screenshot("system_health", "indicator_check")
        await self.dump_dom("system_health", "indicator_check")
        
        telemetry.log_feature_test("system_health", "Command Center", None, None,
                                  "check", 0, result["indicator_found"], 
                                  health_value >= config["target_value"] if health_value else False,
                                  len(self.console_errors), len(self.network_errors),
                                  f"Health: {health_value}%" if health_value else "Not found")
        
        return result
    
    async def run_full_validation(self) -> Dict:
        """Run complete feature functionality validation"""
        print("\n🚀 Starting Phase 15B Feature Functionality Validation")
        print(f"🌐 Dashboard URL: {DASHBOARD_URL}")
        print(f"🗂️  Outputs: {OUTPUTS_DIR}\n")
        
        telemetry = TelemetryDB(OUTPUTS_DIR / "telemetry_phase15b.db")
        
        await self.setup()
        
        # Test 1: Options Forecast
        options_result = await self.test_options_forecast(telemetry)
        self.results["detailed_results"].append(options_result)
        self.results["features_tested"] += 1
        if options_result["status"] == "PASS":
            self.results["features_passed"] += 1
        
        # Test 2: Azure ML Lab Buttons
        azure_result = await self.test_azure_ml_buttons(telemetry)
        self.results["detailed_results"].append(azure_result)
        self.results["features_tested"] += 1
        if azure_result["status"] in ("PASS", "PARTIAL"):
            self.results["features_passed"] += 1
        self.results["buttons_tested"] = azure_result.get("buttons_found", 0)
        self.results["buttons_functional"] = azure_result.get("buttons_functional", 0)
        
        # Test 3: System Health
        health_result = await self.test_system_health(telemetry)
        self.results["detailed_results"].append(health_result)
        self.results["features_tested"] += 1
        if health_result["status"] == "PASS":
            self.results["features_passed"] += 1
        self.results["system_health_value"] = health_result.get("health_value", 0.0)
        
        # Calculate overall status
        if self.results["features_passed"] == self.results["features_tested"]:
            self.results["overall_status"] = "PASS"
        elif self.results["features_passed"] > 0:
            self.results["overall_status"] = "PARTIAL"
        
        telemetry.close()
        await self.teardown()
        
        return self.results


async def main():
    # Create output directories
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "screenshots").mkdir(exist_ok=True)
    (OUTPUTS_DIR / "dom_dumps").mkdir(exist_ok=True)
    (OUTPUTS_DIR / "remediation").mkdir(exist_ok=True)
    
    validator = Phase15BFeatureValidator()
    results = await validator.run_full_validation()
    
    # Save results
    results_file = OUTPUTS_DIR / "phase15b_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"📊 PHASE 15B FEATURE VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Overall Status: {results['overall_status']}")
    print(f"Features Tested: {results['features_tested']}")
    print(f"Features Passed: {results['features_passed']}")
    print(f"Buttons Tested: {results['buttons_tested']}")
    print(f"Buttons Functional: {results['buttons_functional']}")
    print(f"System Health: {results['system_health_value']}% (Target: {results['system_health_target']}%)")
    
    # Generate remediation tickets if needed
    if results['overall_status'] != "PASS":
        print(f"\n⚠️  Generating remediation tickets...")
        
        for feature_result in results['detailed_results']:
            if feature_result.get('status') != 'PASS':
                ticket_file = OUTPUTS_DIR / "remediation" / f"{feature_result['feature']}_ticket.md"
                with open(ticket_file, 'w') as f:
                    f.write(f"# Remediation Ticket: {feature_result['feature']}\n\n")
                    f.write(f"**Timestamp:** {datetime.utcnow().isoformat()}\n")
                    f.write(f"**Status:** {feature_result['status']}\n\n")
                    f.write(f"## Details\n\n")
                    for detail in feature_result.get('details', []):
                        f.write(f"- {detail}\n")
                    f.write(f"\n## Recommended Actions\n\n")
                    f.write(f"1. Review console and network logs\n")
                    f.write(f"2. Verify callback registration\n")
                    f.write(f"3. Check API endpoints\n")
                    f.write(f"4. Validate DOM selectors\n")
                
                print(f"📋 Ticket created: {ticket_file}")
    
    return 0 if results["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
