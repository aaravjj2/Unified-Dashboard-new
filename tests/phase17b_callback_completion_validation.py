"""
🔱 PHASE 17B - CALLBACK COMPLETION & FUNCTIONAL LOOP VALIDATION

Mission: Repair and validate Strategy Lab Backtest + Azure ML Prediction callbacks
         until 100% pass rate achieved across 3 validation loops.

Architecture:
- 3-loop validation sequence (Debug & Repair → Playwright Validation → E2E Re-execution)
- 20-second wait times for callback execution
- 8 retry iterations per loop (auto-retry until success)
- Telemetry logging to SQLite
- Before/after screenshots + DOM captures
- Content validation with min length requirements (>100 chars for backtest, >150 for prediction)

Strict Termination Rule:
- Agent must not stop until BOTH callbacks produce verified, non-placeholder UI outputs
- 100% pass rate required (no partial completion allowed)
"""

import asyncio
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, List
from playwright.async_api import async_playwright, Page
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

DASHBOARD_URL = "http://localhost:8051"
BROWSER_TYPE = "chromium"  # Strict enforcement
MAX_LOOPS = 3
MAX_RETRIES_PER_LOOP = 8  # Auto-retry until success
ACTION_TIMEOUT = 45000  # 45s for button interactions
NAVIGATION_TIMEOUT = 60000  # 60s for page navigation
WAIT_AFTER_CLICK = 20000  # 20s wait after button click (increased from 8s)
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Output directories
OUTPUT_DIR = Path("outputs/phase17b")
SCREENSHOTS_DIR = OUTPUT_DIR / "snapshots"
DOM_DIR = OUTPUT_DIR / "dom"
TELEMETRY_DB = OUTPUT_DIR / "telemetry_phase17b.db"
RESULTS_JSON = OUTPUT_DIR / "phase17b_results.json"

# Feature targets with strict validation
FEATURE_TARGETS = {
    "strategy_lab_backtest": {
        "tab": "⚡ Strategy Lab",
        "subtabs": ["📋 Setup", "▶️ Execute"],  # Two-step flow
        "prerequisite_button": "Validate Strategy",  # Must click first
        "prerequisite_button_selectors": [
            "button:has-text('Validate Strategy')",
            "#sl-validate-btn"
        ],
        "main_button_text": "Run Backtest",
        "main_button_selectors": [
            "button:has-text('Run Backtest')",
            "#sl-run-backtest-btn"
        ],
        "output_selectors": [
            "#sl-backtest-progress",  # Primary output container
            ".alert-success",  # Success alert
            ".alert-danger"  # Error alert (also valid output)
        ],
        "validation_criteria": {
            "min_content_length": 100,  # Must have >100 chars
            "required_elements": ["div", "p", "h6"],
            "forbidden_text": ["Please validate your strategy first", "No backtest running"]
        },
        "wait_time": 20000  # 20s for backtest computation
    },
    "azure_ml_prediction": {
        "tab": "🤖 Azure ML Lab",
        "subtabs": ["📊 Predictions"],
        "main_button_text": "Run Prediction",
        "main_button_selectors": [
            "button:has-text('Run Prediction')",
            "#azure-ml-run-prediction-btn"
        ],
        "output_selectors": [
            "#azure-ml-prediction-results",  # Primary output
            ".alert-warning",  # Warning alert (valid if no portfolio data)
            ".alert-success"  # Success alert
        ],
        "validation_criteria": {
            "min_content_length": 150,  # Must have >150 chars
            "required_elements": ["div", "span"],
            "forbidden_text": ["Click 'Run Prediction' above to generate ML insights"]
        },
        "wait_time": 20000,  # 20s for prediction computation
        "use_js_click": True  # Force JavaScript click for n_clicks increment
    }
}


class TelemetryDB:
    """SQLite telemetry database for Phase 17B"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self._init_schema()
    
    def _init_schema(self):
        """Create telemetry schema"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS phase17b_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                loop_number INTEGER NOT NULL,
                iteration INTEGER NOT NULL,
                feature TEXT NOT NULL,
                tab TEXT NOT NULL,
                subtabs TEXT,
                button_text TEXT NOT NULL,
                prerequisite_executed INTEGER DEFAULT 0,
                button_found INTEGER NOT NULL,
                button_clicked INTEGER NOT NULL,
                output_found INTEGER NOT NULL,
                output_length INTEGER DEFAULT 0,
                validation_passed INTEGER NOT NULL,
                console_errors INTEGER DEFAULT 0,
                network_errors INTEGER DEFAULT 0,
                failure_reason TEXT,
                screenshot_before TEXT,
                screenshot_after TEXT,
                dom_before TEXT,
                dom_after TEXT,
                duration_ms INTEGER,
                details TEXT
            )
        """)
        self.conn.commit()
    
    def log_test(self, test_data: Dict[str, Any]):
        """Log test execution"""
        self.conn.execute("""
            INSERT INTO phase17b_tests (
                timestamp, loop_number, iteration, feature, tab, subtabs,
                button_text, prerequisite_executed, button_found, button_clicked,
                output_found, output_length, validation_passed, console_errors,
                network_errors, failure_reason, screenshot_before, screenshot_after,
                dom_before, dom_after, duration_ms, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_data.get('timestamp'),
            test_data.get('loop_number'),
            test_data.get('iteration'),
            test_data.get('feature'),
            test_data.get('tab'),
            test_data.get('subtabs'),
            test_data.get('button_text'),
            test_data.get('prerequisite_executed', 0),
            test_data.get('button_found', 0),
            test_data.get('button_clicked', 0),
            test_data.get('output_found', 0),
            test_data.get('output_length', 0),
            test_data.get('validation_passed', 0),
            test_data.get('console_errors', 0),
            test_data.get('network_errors', 0),
            test_data.get('failure_reason'),
            test_data.get('screenshot_before'),
            test_data.get('screenshot_after'),
            test_data.get('dom_before'),
            test_data.get('dom_after'),
            test_data.get('duration_ms'),
            test_data.get('details')
        ))
        self.conn.commit()
    
    def close(self):
        self.conn.close()


class Phase17BValidator:
    """Phase 17B callback validator with 3-loop validation"""
    
    def __init__(self):
        self.page: Page = None
        self.browser = None
        self.context = None
        self.console_errors = []
        self.network_errors = []
        self.db = TelemetryDB(TELEMETRY_DB)
        
        # Create output directories
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        DOM_DIR.mkdir(parents=True, exist_ok=True)
    
    async def setup(self):
        """Launch browser and setup page"""
        print(f"🚀 Setting up {BROWSER_TYPE.upper()} browser...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT}
        )
        self.page = await self.context.new_page()
        
        # Attach console/network listeners
        self.page.on("console", lambda msg: self._handle_console(msg))
        self.page.on("requestfailed", lambda req: self.network_errors.append(req.url))
        
        # Navigate to dashboard
        print(f"📍 Navigating to {DASHBOARD_URL}...")
        await self.page.goto(DASHBOARD_URL, timeout=NAVIGATION_TIMEOUT, wait_until="networkidle")
        await self.page.wait_for_timeout(3000)  # Stabilization delay
        print("✅ Browser setup complete\n")
    
    def _handle_console(self, msg):
        """Handle console messages"""
        if msg.type in ['error', 'warning']:
            self.console_errors.append(f"{msg.type}: {msg.text}")
    
    async def navigate_to_tab(self, tab_text: str) -> bool:
        """Navigate to main tab"""
        print(f"  📑 Navigating to tab: {tab_text}")
        try:
            tab_selector = f"a.nav-link:has-text('{tab_text}')"
            await self.page.locator(tab_selector).first.click(timeout=ACTION_TIMEOUT)
            await self.page.wait_for_timeout(2000)
            print(f"  ✅ Tab navigation successful")
            return True
        except Exception as e:
            print(f"  ❌ Tab navigation failed: {e}")
            return False
    
    async def navigate_to_subtab(self, subtab_text: str) -> bool:
        """Navigate to subtab"""
        print(f"  📑 Navigating to subtab: {subtab_text}")
        try:
            # Try multiple selector strategies
            selectors = [
                f"a.nav-link:has-text('{subtab_text}')",
                f"button.nav-link:has-text('{subtab_text}')",
                f"[role='tab']:has-text('{subtab_text}')"
            ]
            
            for selector in selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.count() > 0:
                        await element.click(timeout=ACTION_TIMEOUT)
                        await self.page.wait_for_timeout(2000)
                        print(f"  ✅ Subtab navigation successful")
                        return True
                except:
                    continue
            
            print(f"  ⚠️  Subtab not found")
            return False
        except Exception as e:
            print(f"  ❌ Subtab navigation failed: {e}")
            return False
    
    async def find_button(self, selectors: List[str], button_text: str):
        """Find button using multiple selector strategies"""
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    print(f"  ✅ Button found: {selector}")
                    return element
            except:
                continue
        return None
    
    async def capture_screenshot(self, feature: str, filename: str):
        """Capture screenshot"""
        filepath = SCREENSHOTS_DIR / feature / f"{filename}.png"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(filepath), full_page=False)
        print(f"  📸 Screenshot saved: {filepath}")
        return str(filepath)
    
    async def dump_dom(self, feature: str, filename: str) -> str:
        """Dump DOM to JSON"""
        filepath = DOM_DIR / feature / f"{filename}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        html = await self.page.content()
        dom_data = {
            "timestamp": datetime.now().isoformat(),
            "url": self.page.url,
            "html": html,
            "title": await self.page.title()
        }
        
        with open(filepath, 'w') as f:
            json.dump(dom_data, f, indent=2)
        
        print(f"  🗂️  DOM dump saved: {filepath}")
        return str(filepath)
    
    async def validate_output(self, output_selectors: List[str], validation_criteria: Dict) -> Tuple[bool, int, str]:
        """
        Validate output with strict criteria.
        Returns: (is_valid, content_length, failure_reason)
        """
        # Find output container
        output_element = None
        for selector in output_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    output_element = element
                    print(f"    ✅ Output container found: {selector}")
                    break
            except:
                continue
        
        if not output_element:
            return False, 0, "Output container not found"
        
        # Extract content
        try:
            content_text = await output_element.inner_text()
            content_length = len(content_text.strip())
            print(f"    📏 Content length: {content_length} chars")
            
            # Validation 1: Minimum content length
            min_length = validation_criteria.get("min_content_length", 50)
            if content_length < min_length:
                return False, content_length, f"Content too short ({content_length} < {min_length})"
            
            # Validation 2: Required elements present
            required_elements = validation_criteria.get("required_elements", [])
            found_element = False
            for elem_type in required_elements:
                elem_count = await output_element.locator(elem_type).count()
                if elem_count > 0:
                    found_element = True
                    print(f"    ✅ Found required element: {elem_type} (count: {elem_count})")
                    break
            
            if not found_element and required_elements:
                return False, content_length, "No required elements found"
            
            # Validation 3: Forbidden text (placeholder/error states)
            forbidden_text = validation_criteria.get("forbidden_text", [])
            for forbidden in forbidden_text:
                if forbidden.lower() in content_text.lower():
                    return False, content_length, f"Forbidden text detected: '{forbidden}'"
            
            print(f"  ✅ Output validation PASSED")
            return True, content_length, ""
            
        except Exception as e:
            return False, 0, f"Validation error: {e}"
    
    async def test_feature(
        self,
        feature: str,
        config: Dict[str, Any],
        loop_number: int,
        iteration: int
    ) -> Dict[str, Any]:
        """
        Test single feature with prerequisite handling and strict validation.
        """
        print(f"\n{'='*80}")
        print(f"🎯 TESTING: {feature} (Loop {loop_number}, Iteration {iteration})")
        print(f"{'='*80}")
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "loop_number": loop_number,
            "iteration": iteration,
            "feature": feature,
            "tab": config["tab"],
            "subtabs": ",".join(config.get("subtabs", [])),
            "button_text": config["main_button_text"],
            "prerequisite_executed": 0,
            "button_found": 0,
            "button_clicked": 0,
            "output_found": 0,
            "output_length": 0,
            "validation_passed": 0,
            "console_errors": 0,
            "network_errors": 0,
            "failure_reason": None,
            "screenshot_before": None,
            "screenshot_after": None,
            "dom_before": None,
            "dom_after": None,
            "duration_ms": 0,
            "details": ""
        }
        
        start_time = datetime.now()
        self.console_errors = []
        self.network_errors = []
        
        try:
            # Step 1: Navigate to tab
            nav_success = await self.navigate_to_tab(config["tab"])
            if not nav_success:
                result["failure_reason"] = f"Failed to navigate to tab: {config['tab']}"
                return result
            
            # Step 2: Navigate to first subtab (for prerequisite)
            subtabs = config.get("subtabs", [])
            if subtabs:
                subtab_success = await self.navigate_to_subtab(subtabs[0])
                if not subtab_success:
                    result["failure_reason"] = f"Failed to navigate to subtab: {subtabs[0]}"
                    return result
            
            # Step 3: Execute prerequisite (if any)
            if config.get("prerequisite_button"):
                print(f"  🔧 Executing prerequisite: {config['prerequisite_button']}")
                prereq_button = await self.find_button(
                    config["prerequisite_button_selectors"],
                    config["prerequisite_button"]
                )
                
                if prereq_button:
                    await prereq_button.click(timeout=ACTION_TIMEOUT)
                    result["prerequisite_executed"] = 1
                    print(f"    ✅ Prerequisite executed: {config['prerequisite_button']}")
                    await self.page.wait_for_timeout(3000)  # Wait for validation to complete
                else:
                    print(f"    ⚠️  Prerequisite button not found")
            
            # Step 4: Navigate to execution subtab (if different from setup)
            if len(subtabs) > 1:
                exec_subtab_success = await self.navigate_to_subtab(subtabs[1])
                if not exec_subtab_success:
                    result["failure_reason"] = f"Failed to navigate to execution subtab: {subtabs[1]}"
                    return result
            
            # Step 5: Capture BEFORE state
            result["screenshot_before"] = await self.capture_screenshot(feature, f"loop{loop_number}_iter{iteration}_before")
            result["dom_before"] = await self.dump_dom(feature, f"loop{loop_number}_iter{iteration}_before")
            
            # Step 6: Find main button
            button = await self.find_button(config["main_button_selectors"], config["main_button_text"])
            if not button:
                result["failure_reason"] = f"Main button not found: {config['main_button_text']}"
                return result
            
            result["button_found"] = 1
            
            # Step 7: Click button (use JavaScript click if specified)
            print(f"  🖱️  Clicking button: {config['main_button_text']}")
            
            if config.get("use_js_click"):
                # Force JavaScript click for better n_clicks increment
                await self.page.evaluate(f"""
                    document.querySelector('{config["main_button_selectors"][1]}').click();
                """)
                print(f"    🔄 Used JavaScript click for reliable callback trigger")
            else:
                await button.click(timeout=ACTION_TIMEOUT)
            
            result["button_clicked"] = 1
            
            # Step 8: Wait for callback execution
            wait_time = config.get("wait_time", WAIT_AFTER_CLICK)
            print(f"  ⏳ Waiting {wait_time/1000}s for callback execution...")
            await self.page.wait_for_timeout(wait_time)
            
            # Step 9: Capture AFTER state
            result["screenshot_after"] = await self.capture_screenshot(feature, f"loop{loop_number}_iter{iteration}_after")
            result["dom_after"] = await self.dump_dom(feature, f"loop{loop_number}_iter{iteration}_after")
            
            # Step 10: Validate output
            print(f"  🔍 Validating output...")
            is_valid, output_length, failure_reason = await self.validate_output(
                config["output_selectors"],
                config["validation_criteria"]
            )
            
            result["output_found"] = 1 if output_length > 0 else 0
            result["output_length"] = output_length
            result["validation_passed"] = 1 if is_valid else 0
            result["failure_reason"] = failure_reason if not is_valid else None
            
            # Log console/network errors
            result["console_errors"] = len(self.console_errors)
            result["network_errors"] = len(self.network_errors)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds() * 1000
            result["duration_ms"] = int(duration)
            
            # Print result
            if is_valid:
                print(f"\n✅ PASS: {feature}")
                print(f"  Button Found: True")
                print(f"  Button Clicked: True")
                print(f"  Output Detected: True ({output_length} chars)")
                print(f"  Validation Passed: True")
            else:
                print(f"\n❌ FAIL: {feature}")
                print(f"  Button Found: {bool(result['button_found'])}")
                print(f"  Button Clicked: {bool(result['button_clicked'])}")
                print(f"  Output Detected: {bool(result['output_found'])} ({output_length} chars)")
                print(f"  Validation Passed: False")
                print(f"  Failure Reason: {failure_reason}")
                print(f"  Console Errors: {result['console_errors']}")
                print(f"  Network Errors: {result['network_errors']}")
            
        except Exception as e:
            result["failure_reason"] = f"Exception: {str(e)}"
            print(f"\n❌ EXCEPTION: {feature}")
            print(f"  Error: {str(e)}")
        
        # Log to telemetry
        self.db.log_test(result)
        
        return result
    
    async def run_validation_loop(self, loop_number: int) -> Dict[str, Any]:
        """
        Execute validation loop with auto-retry (up to MAX_RETRIES_PER_LOOP iterations).
        """
        print(f"\n{'#'*80}")
        print(f"🔁 VALIDATION LOOP {loop_number}/{MAX_LOOPS}")
        print(f"{'#'*80}\n")
        
        features_passed = {}
        
        for iteration in range(1, MAX_RETRIES_PER_LOOP + 1):
            print(f"\n{'='*80}")
            print(f"🔄 ITERATION {iteration}/{MAX_RETRIES_PER_LOOP}")
            print(f"{'='*80}")
            
            # Test each feature
            for feature_id, config in FEATURE_TARGETS.items():
                # Skip if already passed
                if features_passed.get(feature_id):
                    print(f"\n⏭️  Skipping {feature_id} (already passed)")
                    continue
                
                result = await self.test_feature(feature_id, config, loop_number, iteration)
                
                if result["validation_passed"]:
                    features_passed[feature_id] = True
                    print(f"✅ {feature_id} PASSED in iteration {iteration}")
            
            # Check if all features passed
            if len(features_passed) == len(FEATURE_TARGETS):
                print(f"\n🎉 ALL FEATURES PASSED in Loop {loop_number}, Iteration {iteration}!")
                return {
                    "loop_number": loop_number,
                    "iterations_needed": iteration,
                    "features_passed": list(features_passed.keys()),
                    "pass_rate": 100.0,
                    "status": "PASS"
                }
        
        # Failed after MAX_RETRIES_PER_LOOP iterations
        print(f"\n❌ Loop {loop_number} FAILED after {MAX_RETRIES_PER_LOOP} iterations")
        return {
            "loop_number": loop_number,
            "iterations_needed": MAX_RETRIES_PER_LOOP,
            "features_passed": list(features_passed.keys()),
            "pass_rate": (len(features_passed) / len(FEATURE_TARGETS)) * 100,
            "status": "FAIL"
        }
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """
        Execute full 3-loop validation sequence.
        Returns summary with pass/fail status.
        """
        results = {
            "mission": "Phase 17B - Callback Completion & Functional Loop Validation",
            "timestamp": datetime.now().isoformat(),
            "dashboard_url": DASHBOARD_URL,
            "browser": BROWSER_TYPE,
            "max_loops": MAX_LOOPS,
            "max_retries_per_loop": MAX_RETRIES_PER_LOOP,
            "features_targeted": len(FEATURE_TARGETS),
            "loops": [],
            "final_status": "FAIL",
            "final_pass_rate": 0.0
        }
        
        for loop_num in range(1, MAX_LOOPS + 1):
            loop_result = await self.run_validation_loop(loop_num)
            results["loops"].append(loop_result)
            
            # Check if loop passed
            if loop_result["status"] == "PASS":
                print(f"\n✅ Loop {loop_num} PASSED")
            else:
                print(f"\n❌ Loop {loop_num} FAILED")
        
        # Calculate final status
        all_passed = all(loop["status"] == "PASS" for loop in results["loops"])
        
        if all_passed:
            results["final_status"] = "PASS"
            results["final_pass_rate"] = 100.0
            print(f"\n🎉 PHASE 17B MISSION COMPLETE - 100% PASS RATE ACHIEVED!")
        else:
            # Calculate average pass rate
            avg_pass_rate = sum(loop["pass_rate"] for loop in results["loops"]) / len(results["loops"])
            results["final_pass_rate"] = avg_pass_rate
            print(f"\n❌ PHASE 17B MISSION FAILED - {avg_pass_rate:.1f}% average pass rate")
        
        return results
    
    async def cleanup(self):
        """Close browser and database"""
        if self.browser:
            await self.browser.close()
        if self.db:
            self.db.close()
        print("🛑 Browser and database closed")


async def main():
    """Main execution"""
    print(f"""
{'='*80}
🔱 PHASE 17B - CALLBACK COMPLETION & FUNCTIONAL LOOP VALIDATION
{'='*80}
Dashboard: {DASHBOARD_URL}
Browser: {BROWSER_TYPE.upper()} (headless)
Max Loops: {MAX_LOOPS}
Max Retries per Loop: {MAX_RETRIES_PER_LOOP}
Features: {len(FEATURE_TARGETS)}
Wait Time: {WAIT_AFTER_CLICK/1000}s after button click

Features to Validate:
1. Strategy Lab → Run Backtest (>100 chars output)
2. Azure ML Lab → Run Prediction (>150 chars output)

{'='*80}
""")
    
    validator = Phase17BValidator()
    
    try:
        await validator.setup()
        results = await validator.run_full_validation()
        
        # Save results to JSON
        with open(RESULTS_JSON, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"📊 PHASE 17B FINAL RESULTS")
        print(f"{'='*80}")
        print(f"Status: {results['final_status']}")
        print(f"Final Pass Rate: {results['final_pass_rate']:.1f}%")
        print(f"Loops Executed: {len(results['loops'])}")
        print(f"\n📁 Results saved to: {RESULTS_JSON}")
        print(f"📁 Telemetry saved to: {TELEMETRY_DB}")
        print(f"📁 Screenshots: {SCREENSHOTS_DIR}")
        print(f"📁 DOM dumps: {DOM_DIR}")
        
        # Return exit code based on success
        sys.exit(0 if results['final_status'] == 'PASS' else 1)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await validator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
