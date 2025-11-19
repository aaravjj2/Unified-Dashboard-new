#!/usr/bin/env python3
"""
Phase 16B - Dashboard Functional Callback Repair & Output Validation
======================================================================

Mission: Validate ALL button callbacks produce actual rendered output
Port: 8051 only
Browser: Chromium only
Standard: Zero tolerance for hallucinated success

Targets:
1. Strategy Lab - Backtest Button (must show results)
2. Options Forecast - Fetch Forecast Button (must populate output)
3. Azure ML Lab - Run Prediction Button (must render result)

Execution: 3-loop auto-retest until 100% success or explicit failure
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DASHBOARD_URL = "http://localhost:8051"
OUTPUTS_DIR = Path("outputs/phase16b_final")
SCREENSHOTS_DIR = OUTPUTS_DIR / "screenshots"
DOM_DUMPS_DIR = OUTPUTS_DIR / "dom_dumps"
TELEMETRY_DB = OUTPUTS_DIR / "telemetry_phase16b.db"

# Timeouts (increased for slow operations)
ACTION_TIMEOUT = 30000  # 30s for button clicks
NAVIGATION_TIMEOUT = 45000  # 45s for navigation
WAIT_AFTER_CLICK = 8000  # 8 seconds wait after clicking button (increased for callback processing)
RETRY_COUNT = 3
MAX_LOOPS = 3  # 3-loop validation sequence

# Feature targets with strict validation criteria
FEATURE_TARGETS = {
    "strategy_lab_backtest": {
        "tab": "⚡ Strategy Lab",
        "subtab": "▶️ Execute",
        "button_text": "Run Backtest",
        "button_selectors": [
            "button:has-text('Run Backtest')",
            "#sl-run-backtest-btn",
            "button[id*='backtest']:has-text('Run')",
            "[id*='sl'][id*='run']"
        ],
        "output_selectors": [
            "#sl-backtest-progress",  # ✅ CORRECT: This is where callback outputs
            "#sl-backtest-results",   # Data store (secondary)
            "[id*='backtest'][id*='progress']",
            ".backtest-results-container",
            "#sl-equity-curve",
            ".strategy-lab-results"
        ],
        "validation_criteria": {
            "min_content_length": 50,  # Must have substantial content
            "required_elements": ["div", "p", "h6"],  # Alert/success message elements
            "forbidden_text": ["validate your strategy first", "Please validate", "No backtest running"]  # Can't be empty state or error
        },
        "prerequisite_steps": [  # ✅ NEW: Required setup before main button click
            {
                "action": "navigate_subtab",
                "subtab": "📋 Setup",  # ✅ CORRECT: Actual subtab label
                "description": "Navigate to Setup tab to validate strategy"
            },
            {
                "action": "click_button",
                "button_text": "Validate Strategy",
                "button_selectors": ["button:has-text('Validate Strategy')", "#sl-validate-btn"],
                "wait_after_click": 2.0,
                "description": "Click Validate Strategy button (prerequisite for backtest)"
            },
            {
                "action": "navigate_subtab",
                "subtab": "▶️ Execute",
                "description": "Navigate back to Execute tab"
            }
        ]
    },
    "options_forecast": {
        "tab": "Market Forecast",
        "subtab": None,
        "button_text": "Generate Forecast",
        "button_selectors": [
            "button:has-text('Generate Forecast')",
            "#mf-generate-btn",  # ✅ CORRECT: Actual button ID
            "button[id*='forecast']:has-text('Generate')",
            "[id*='generate-btn']"
        ],
        "output_selectors": [
            "#mf-summary-cards",      # ✅ CORRECT: Primary output container
            "#mf-returns-chart",      # ✅ CORRECT: Returns chart
            "#mf-volatility-chart",   # ✅ CORRECT: Volatility chart
            "#mf-details-table",      # ✅ CORRECT: Details table
            "#mf-loading-output",     # Loading/status output
            "[id*='mf'][id*='chart']"
        ],
        "validation_criteria": {
            "min_content_length": 30,
            "required_elements": ["div", "svg"],  # Cards and charts
            "forbidden_text": ["No tickers provided", "Select or enter", "No forecasts generated"]  # Error states
        }
    },
    "azure_ml_prediction": {
        "tab": "🤖 Azure ML Lab",
        "subtab": "📊 Predictions",
        "button_text": "Run Prediction",
        "button_selectors": [
            "button:has-text('Run Prediction')",
            "#azure-ml-run-prediction-btn",  # ✅ CORRECT: Actual button ID
            "button[id*='prediction']:has-text('Run')",
            "[id*='ml'][id*='run']"
        ],
        "output_selectors": [
            "#azure-ml-prediction-results",  # ✅ CORRECT: Primary output container
            "#azure-ml-predictions-table",   # ✅ Secondary: Predictions table
            "[id*='prediction'][id*='result']",
            ".azure-ml-output",
            "#azure-ml-status",
            "[id*='ml'][id*='prediction']"
        ],
        "validation_criteria": {
            "min_content_length": 40,
            "required_elements": ["div", "span"],  # Alert contains divs and spans
            "forbidden_text": ["Click 'Run Prediction' above", "No portfolio data"]  # Empty/error states
        }
    }
}


class TelemetryDB:
    """SQLite telemetry logging"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self._init_schema()
    
    def _init_schema(self):
        """Create telemetry table"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS callback_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                loop_iteration INTEGER NOT NULL,
                feature TEXT NOT NULL,
                tab TEXT NOT NULL,
                subtab TEXT,
                button_text TEXT NOT NULL,
                action TEXT NOT NULL,
                duration_ms INTEGER,
                button_found INTEGER NOT NULL,
                button_clicked INTEGER NOT NULL,
                output_detected INTEGER NOT NULL,
                output_length INTEGER,
                validation_passed INTEGER NOT NULL,
                console_errors INTEGER DEFAULT 0,
                network_errors INTEGER DEFAULT 0,
                failure_reason TEXT,
                details TEXT
            )
        """)
        self.conn.commit()
    
    def log_test(
        self,
        loop_iteration: int,
        feature: str,
        tab: str,
        subtab: Optional[str],
        button_text: str,
        action: str,
        duration_ms: int,
        button_found: bool,
        button_clicked: bool,
        output_detected: bool,
        output_length: int,
        validation_passed: bool,
        console_errors: int = 0,
        network_errors: int = 0,
        failure_reason: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log callback test event"""
        self.conn.execute("""
            INSERT INTO callback_tests (
                timestamp, loop_iteration, feature, tab, subtab, button_text,
                action, duration_ms, button_found, button_clicked,
                output_detected, output_length, validation_passed,
                console_errors, network_errors, failure_reason, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(), loop_iteration, feature, tab, subtab, button_text,
            action, duration_ms, int(button_found), int(button_clicked),
            int(output_detected), output_length, int(validation_passed),
            console_errors, network_errors, failure_reason, details
        ))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


class Phase16BCallbackValidator:
    """Main validation orchestrator with 3-loop retry logic"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.telemetry_db: Optional[TelemetryDB] = None
        self.results: Dict[str, Any] = {}
        self.console_errors: List[str] = []
        self.network_errors: List[str] = []
        
        # Create output directories
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        DOM_DUMPS_DIR.mkdir(parents=True, exist_ok=True)
    
    async def setup(self):
        """Initialize browser and navigate to dashboard"""
        print("🚀 Setting up Chromium browser...")
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        
        # Set timeouts
        self.context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        self.context.set_default_timeout(ACTION_TIMEOUT)
        
        self.page = await self.context.new_page()
        
        # Attach console/network listeners
        self.page.on("console", lambda msg: self._on_console(msg))
        self.page.on("pageerror", lambda err: self._on_page_error(err))
        self.page.on("requestfailed", lambda req: self._on_request_failed(req))
        
        # Navigate to dashboard
        print(f"📍 Navigating to {DASHBOARD_URL}...")
        await self.page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)
        await asyncio.sleep(2)  # Let dashboard initialize
        
        print("✅ Browser setup complete")
    
    def _on_console(self, msg):
        """Capture console messages"""
        if msg.type in ["error", "warning"]:
            self.console_errors.append(f"[{msg.type}] {msg.text}")
    
    def _on_page_error(self, error):
        """Capture page errors"""
        self.console_errors.append(f"[page_error] {error}")
    
    def _on_request_failed(self, request):
        """Capture failed network requests"""
        self.network_errors.append(f"{request.method} {request.url}")
    
    async def teardown(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        print("🛑 Browser closed")
    
    async def navigate_to_tab(self, tab_name: str, retry: int = 0) -> bool:
        """Navigate to specific tab"""
        if retry >= RETRY_COUNT:
            return False
        
        try:
            print(f"  📑 Navigating to tab: {tab_name}")
            
            # Try multiple selector strategies
            selectors = [
                f"a.nav-link:has-text('{tab_name}')",
                f"[role='tab']:has-text('{tab_name}')",
                f".nav-item:has-text('{tab_name}') a",
                f"a[href*='{tab_name.lower().replace(' ', '-')}']"
            ]
            
            for selector in selectors:
                tab_link = self.page.locator(selector).first
                if await tab_link.count() > 0 and await tab_link.is_visible():
                    await tab_link.click()
                    await asyncio.sleep(2)  # Wait for tab content to load
                    print(f"  ✅ Tab navigation successful")
                    return True
            
            print(f"  ⚠️  Tab not found, retrying...")
            return await self.navigate_to_tab(tab_name, retry + 1)
            
        except Exception as e:
            print(f"  ❌ Tab navigation error: {e}")
            return await self.navigate_to_tab(tab_name, retry + 1)
    
    async def navigate_to_subtab(self, subtab_name: str) -> bool:
        """Navigate to specific subtab"""
        try:
            print(f"  📑 Navigating to subtab: {subtab_name}")
            
            selectors = [
                f"button:has-text('{subtab_name}')",
                f"a:has-text('{subtab_name}')",
                f"[role='tab']:has-text('{subtab_name}')",
                f".nav-link:has-text('{subtab_name}')"
            ]
            
            for selector in selectors:
                subtab_link = self.page.locator(selector).first
                if await subtab_link.count() > 0 and await subtab_link.is_visible():
                    await subtab_link.click()
                    await asyncio.sleep(1)
                    print(f"  ✅ Subtab navigation successful")
                    return True
            
            print(f"  ⚠️  Subtab not found")
            return False
            
        except Exception as e:
            print(f"  ❌ Subtab navigation error: {e}")
            return False
    
    async def capture_screenshot(self, feature: str, suffix: str):
        """Capture full-page screenshot"""
        screenshot_path = SCREENSHOTS_DIR / feature / f"{suffix}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  📸 Screenshot saved: {screenshot_path}")
    
    async def dump_dom(self, feature: str, suffix: str):
        """Dump HTML + metadata to JSON"""
        html_content = await self.page.content()
        
        dom_data = {
            "timestamp": datetime.now().isoformat(),
            "url": self.page.url,
            "title": await self.page.title(),
            "html_length": len(html_content),
            "html": html_content[:100000]  # Limit size (first 100KB)
        }
        
        dom_path = DOM_DUMPS_DIR / feature / f"{suffix}.json"
        dom_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dom_path, 'w') as f:
            json.dump(dom_data, f, indent=2)
        
        print(f"  🗂️  DOM dump saved: {dom_path}")
    
    async def find_button(self, selectors: List[str], button_text: str) -> Optional[Any]:
        """Find button using multiple selector strategies"""
        for selector in selectors:
            try:
                button = self.page.locator(selector).first
                if await button.count() > 0:
                    # Check if visible
                    if await button.is_visible(timeout=2000):
                        print(f"  ✅ Button found: {selector}")
                        return button
            except Exception:
                continue
        
        print(f"  ❌ Button not found: {button_text}")
        return None
    
    async def validate_output(
        self,
        output_selectors: List[str],
        validation_criteria: Dict[str, Any]
    ) -> tuple[bool, int, str]:
        """
        Strict output validation - checks actual rendered content.
        
        Returns: (is_valid, content_length, failure_reason)
        """
        print("  🔍 Validating output...")
        
        # Find output container
        output_element = None
        for selector in output_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    print(f"    ✅ Output container found: {selector}")
                    output_element = element
                    break
            except Exception:
                continue
        
        if not output_element:
            return False, 0, "Output container not found"
        
        # Extract content
        try:
            content_text = await output_element.inner_text()
            content_html = await output_element.inner_html()
        except Exception as e:
            return False, 0, f"Failed to extract content: {e}"
        
        content_length = len(content_text)
        print(f"    📏 Content length: {content_length} chars")
        
        # Validation 1: Minimum content length
        min_length = validation_criteria.get("min_content_length", 30)
        if content_length < min_length:
            return False, content_length, f"Content too short ({content_length} < {min_length})"
        
        # Validation 2: Required elements present
        required_elements = validation_criteria.get("required_elements", [])
        for elem_type in required_elements:
            elem_count = await output_element.locator(elem_type).count()
            if elem_count > 0:
                print(f"    ✅ Found required element: {elem_type} (count: {elem_count})")
                break  # At least one required element type found
        else:
            if required_elements:
                return False, content_length, f"No required elements found: {required_elements}"
        
        # Validation 3: Forbidden text (empty states)
        forbidden_text = validation_criteria.get("forbidden_text", [])
        for forbidden in forbidden_text:
            if forbidden.lower() in content_text.lower():
                print(f"    ❌ Forbidden text found: '{forbidden}'")
                return False, content_length, f"Empty state detected: '{forbidden}'"
        
        print(f"  ✅ Output validation PASSED")
        return True, content_length, ""
    
    async def test_button_callback(
        self,
        loop_iteration: int,
        feature: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test single button callback with strict validation.
        
        Returns detailed result with actual evidence.
        """
        print(f"\n{'='*80}")
        print(f"🎯 TESTING: {feature} (Loop {loop_iteration})")
        print(f"{'='*80}")
        
        result = {
            "feature": feature,
            "loop_iteration": loop_iteration,
            "tab": config["tab"],
            "subtab": config.get("subtab"),
            "button_text": config["button_text"],
            "button_found": False,
            "button_clicked": False,
            "output_detected": False,
            "output_length": 0,
            "validation_passed": False,
            "failure_reason": None,
            "details": []
        }
        
        start_time = datetime.now()
        
        # Clear error logs
        self.console_errors = []
        self.network_errors = []
        
        # Step 1: Navigate to tab
        nav_success = await self.navigate_to_tab(config["tab"])
        if not nav_success:
            result["failure_reason"] = f"Failed to navigate to tab: {config['tab']}"
            return result
        
        # Step 2: Navigate to subtab (if applicable)
        if config.get("subtab"):
            subtab_success = await self.navigate_to_subtab(config["subtab"])
            if not subtab_success:
                result["failure_reason"] = f"Failed to navigate to subtab: {config['subtab']}"
                return result
        
        # Step 2.5: Execute prerequisite steps (if any)
        if config.get("prerequisite_steps"):
            print(f"  🔧 Executing {len(config['prerequisite_steps'])} prerequisite steps...")
            for i, step in enumerate(config["prerequisite_steps"], 1):
                print(f"    Step {i}: {step.get('description', step['action'])}")
                
                if step["action"] == "navigate_subtab":
                    subtab_success = await self.navigate_to_subtab(step["subtab"])
                    if not subtab_success:
                        result["failure_reason"] = f"Prerequisite failed: Navigate to {step['subtab']}"
                        return result
                
                elif step["action"] == "click_button":
                    prereq_button = await self.find_button(step["button_selectors"], step["button_text"])
                    if not prereq_button:
                        result["failure_reason"] = f"Prerequisite failed: Button '{step['button_text']}' not found"
                        return result
                    
                    await prereq_button.click()
                    print(f"      ✅ Clicked: {step['button_text']}")
                    
                    wait_time = step.get("wait_after_click", 2.0)
                    await self.page.wait_for_timeout(int(wait_time * 1000))
        
        # Step 3: Capture BEFORE screenshot
        await self.capture_screenshot(feature, f"loop{loop_iteration}_before_click")
        await self.dump_dom(feature, f"loop{loop_iteration}_before_click")
        
        # Step 4: Find button
        button = await self.find_button(config["button_selectors"], config["button_text"])
        if not button:
            result["failure_reason"] = f"Button not found: {config['button_text']}"
            return result
        
        result["button_found"] = True
        result["details"].append("Button found")
        
        # Step 5: Click button (with double-click for stubborn callbacks)
        try:
            print(f"  🖱️  Clicking button: {config['button_text']}")
            await button.click()
            result["button_clicked"] = True
            result["details"].append("Button clicked")
            
            # Step 5.5: Double-click for Azure ML to ensure n_clicks increments
            if "azure" in feature.lower() or "prediction" in config["button_text"].lower():
                await asyncio.sleep(0.5)  # Small delay between clicks
                await button.click()  # Second click
                print(f"    🔄 Double-clicked for reliable n_clicks trigger")
            
            # Wait for async operations
            print(f"  ⏳ Waiting {WAIT_AFTER_CLICK/1000}s for callback execution...")
            await asyncio.sleep(WAIT_AFTER_CLICK / 1000)
            
        except Exception as e:
            result["failure_reason"] = f"Button click failed: {e}"
            return result
        
        # Step 6: Capture AFTER screenshot
        await self.capture_screenshot(feature, f"loop{loop_iteration}_after_click")
        await self.dump_dom(feature, f"loop{loop_iteration}_after_click")
        
        # Step 7: Validate output (STRICT)
        is_valid, output_length, failure_reason = await self.validate_output(
            config["output_selectors"],
            config["validation_criteria"]
        )
        
        result["output_detected"] = output_length > 0
        result["output_length"] = output_length
        result["validation_passed"] = is_valid
        
        if not is_valid:
            result["failure_reason"] = failure_reason
            result["details"].append(f"Validation failed: {failure_reason}")
        else:
            result["details"].append(f"Validation passed: {output_length} chars")
        
        # Calculate duration
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log to telemetry
        if self.telemetry_db:
            self.telemetry_db.log_test(
                loop_iteration=loop_iteration,
                feature=feature,
                tab=config["tab"],
                subtab=config.get("subtab"),
                button_text=config["button_text"],
                action="click_and_validate",
                duration_ms=duration_ms,
                button_found=result["button_found"],
                button_clicked=result["button_clicked"],
                output_detected=result["output_detected"],
                output_length=result["output_length"],
                validation_passed=result["validation_passed"],
                console_errors=len(self.console_errors),
                network_errors=len(self.network_errors),
                failure_reason=result.get("failure_reason"),
                details="; ".join(result["details"])
            )
        
        # Print summary
        status = "✅ PASS" if result["validation_passed"] else "❌ FAIL"
        print(f"\n{status}: {feature}")
        print(f"  Button Found: {result['button_found']}")
        print(f"  Button Clicked: {result['button_clicked']}")
        print(f"  Output Detected: {result['output_detected']} ({result['output_length']} chars)")
        print(f"  Validation Passed: {result['validation_passed']}")
        if result.get("failure_reason"):
            print(f"  Failure Reason: {result['failure_reason']}")
        print(f"  Console Errors: {len(self.console_errors)}")
        print(f"  Network Errors: {len(self.network_errors)}")
        
        return result
    
    async def run_validation_loop(self, loop_iteration: int) -> Dict[str, Any]:
        """Run full validation for all features in single loop"""
        print(f"\n{'#'*80}")
        print(f"🔁 VALIDATION LOOP {loop_iteration}/{MAX_LOOPS}")
        print(f"{'#'*80}")
        
        loop_results = {
            "loop_iteration": loop_iteration,
            "timestamp": datetime.now().isoformat(),
            "features_tested": 0,
            "features_passed": 0,
            "feature_results": []
        }
        
        for feature, config in FEATURE_TARGETS.items():
            result = await self.test_button_callback(loop_iteration, feature, config)
            loop_results["feature_results"].append(result)
            loop_results["features_tested"] += 1
            if result["validation_passed"]:
                loop_results["features_passed"] += 1
        
        loop_results["pass_rate"] = (
            loop_results["features_passed"] / loop_results["features_tested"] * 100
            if loop_results["features_tested"] > 0 else 0
        )
        
        print(f"\n{'='*80}")
        print(f"📊 LOOP {loop_iteration} SUMMARY")
        print(f"{'='*80}")
        print(f"Features Tested: {loop_results['features_tested']}")
        print(f"Features Passed: {loop_results['features_passed']}")
        print(f"Pass Rate: {loop_results['pass_rate']:.1f}%")
        
        return loop_results
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Execute 3-loop validation sequence"""
        print(f"\n{'#'*80}")
        print(f"🚀 PHASE 16B - CALLBACK REPAIR & VALIDATION")
        print(f"{'#'*80}")
        print(f"Dashboard: {DASHBOARD_URL}")
        print(f"Browser: Chromium (headless)")
        print(f"Max Loops: {MAX_LOOPS}")
        print(f"Features: {len(FEATURE_TARGETS)}")
        
        # Setup telemetry
        self.telemetry_db = TelemetryDB(TELEMETRY_DB)
        
        # Setup browser
        await self.setup()
        
        all_results = {
            "mission": "Phase 16B - Callback Repair & Validation",
            "timestamp": datetime.now().isoformat(),
            "dashboard_url": DASHBOARD_URL,
            "max_loops": MAX_LOOPS,
            "features_targeted": len(FEATURE_TARGETS),
            "loops": [],
            "final_status": "PENDING"
        }
        
        # Execute validation loops
        for loop_num in range(1, MAX_LOOPS + 1):
            loop_results = await self.run_validation_loop(loop_num)
            all_results["loops"].append(loop_results)
            
            # Check if all passed
            if loop_results["pass_rate"] == 100.0:
                print(f"\n✅ 100% pass rate achieved in loop {loop_num}!")
                all_results["final_status"] = "PASS"
                break
        else:
            # All loops exhausted without 100% pass
            print(f"\n❌ Failed to achieve 100% pass rate after {MAX_LOOPS} loops")
            all_results["final_status"] = "FAIL"
        
        # Calculate final statistics
        final_loop = all_results["loops"][-1]
        all_results["final_pass_rate"] = final_loop["pass_rate"]
        all_results["features_passed"] = final_loop["features_passed"]
        all_results["features_failed"] = final_loop["features_tested"] - final_loop["features_passed"]
        
        # Cleanup
        await self.teardown()
        self.telemetry_db.close()
        
        return all_results


async def main():
    """Main execution"""
    validator = Phase16BCallbackValidator()
    
    try:
        results = await validator.run_full_validation()
        
        # Save results
        results_path = OUTPUTS_DIR / "phase16b_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"📊 PHASE 16B FINAL RESULTS")
        print(f"{'='*80}")
        print(f"Status: {results['final_status']}")
        print(f"Loops Executed: {len(results['loops'])}")
        print(f"Final Pass Rate: {results['final_pass_rate']:.1f}%")
        print(f"Features Passed: {results['features_passed']}/{results['features_targeted']}")
        print(f"\n📁 Results saved to: {results_path}")
        
        # Return exit code
        return 0 if results['final_status'] == "PASS" else 1
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
