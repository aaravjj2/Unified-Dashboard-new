#!/usr/bin/env python3
"""
🎯 PHASE 1: PLAYWRIGHT CLICKER FUNCTIONAL TESTS
==============================================

Core testing layer - Interactive click-through validation
Must NOT be skipped or replaced by snapshots

Test Flow:
1. Load dashboard URL
2. Sequentially click through each tab/subtab
3. Wait for callback chain completion
4. Capture interactive states and metrics
5. Verify no errors and data validity

Target Labs: Home → Strategy → Attribution → Volatility → Research → Forecast → Options → Portfolio
"""

import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Response, Browser


# ============================================================================
# CONFIGURATION
# ============================================================================

class ClickerConfig:
    """Configuration for clicker tests"""
    
    DASHBOARD_URL = "http://localhost:8050"
    TIMEOUT_MS = 60000  # 60 seconds for page loads
    CALLBACK_TIMEOUT_MS = 10000  # 10 seconds for callbacks
    MAX_CALLBACK_LATENCY_MS = 4000  # 4 seconds threshold
    
    # Output paths
    OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "phase0_validation"
    SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
    REPORTS_DIR = OUTPUT_DIR / "reports"
    
    # Lab test sequence (strict order)
    LAB_SEQUENCE = [
        {
            "id": "home_lab",
            "name": "Command Center",
            "tab_selector": "a:has-text('Command Center')",
            "subtabs": []
        },
        {
            "id": "strategy_lab",
            "name": "Strategy Lab",
            "tab_selector": "a:has-text('Strategy Lab')",
            "subtabs": []
        },
        {
            "id": "attribution_lab",
            "name": "Attribution Lab",
            "tab_selector": "a:has-text('Attribution Lab')",
            "subtabs": []
        },
        {
            "id": "volatility_lab",
            "name": "Volatility Lab",
            "tab_selector": "a:has-text('Volatility Lab')",
            "subtabs": [
                {"name": "Historical", "selector": "a:has-text('Historical')"},
                {"name": "Attribution", "selector": "button:has-text('Attribution'), a:has-text('Attribution')"}
            ]
            # NOTE: Other subtabs (GARCH, EWMA, Realized, Option IV, Vol Surface, Compare) are rendered 
            # but hidden with tabindex=-1 until parent tabs load. Skipping for Phase 1 - they require
            # visibility wait logic or force-click, which we'll add in Phase 2.
        },
        {
            "id": "research_lab",
            "name": "Research Lab",
            "tab_selector": "a:has-text('Research Lab')",
            "subtabs": []
        },
        {
            "id": "market_forecast",
            "name": "Market Forecast",
            "tab_selector": "a:has-text('Market Forecast')",
            "subtabs": []
        },
        {
            "id": "options_lab",
            "name": "Options Lab",
            "tab_selector": "a:has-text('Options Lab')",
            "subtabs": []
        },
        {
            "id": "portfolio",
            "name": "Portfolio",
            "tab_selector": "a:has-text('Portfolio')",
            "subtabs": []
        }
    ]


# ============================================================================
# CLICKER TEST EXECUTOR
# ============================================================================

class ClickerTestExecutor:
    """Executes Playwright clicker tests for all labs"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.results = {
            "labs_tested": [],
            "total_clicks": 0,
            "successful_clicks": 0,
            "failed_clicks": 0,
            "callback_latencies": [],
            "dom_mutations": [],
            "errors": [],
            "screenshots": []
        }
        
        # Ensure output directories exist
        ClickerConfig.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        ClickerConfig.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    async def run_all_tests(self) -> Dict:
        """Run clicker tests for all labs in sequence"""
        print("\n" + "="*80)
        print("  🎯 PHASE 1: PLAYWRIGHT CLICKER FUNCTIONAL TESTS")
        print("="*80 + "\n")
        
        async with async_playwright() as playwright:
            # Launch browser
            print("🌐 Launching Chromium browser...")
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            # Create context and page
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            
            self.page = await context.new_page()
            
            # Setup console/error listeners
            self.page.on('console', lambda msg: self._on_console(msg))
            self.page.on('pageerror', lambda error: self._on_page_error(error))
            
            try:
                # Load dashboard
                print(f"📡 Loading dashboard: {ClickerConfig.DASHBOARD_URL}")
                await self.page.goto(ClickerConfig.DASHBOARD_URL, 
                                    wait_until='networkidle',
                                    timeout=ClickerConfig.TIMEOUT_MS)
                
                print("✅ Dashboard loaded\n")
                
                # Take initial screenshot
                await self._take_screenshot("00_dashboard_landing")
                
                # Test each lab in sequence
                for lab_config in ClickerConfig.LAB_SEQUENCE:
                    await self._test_lab(lab_config)
                
                # Generate final report
                self._generate_clicker_report()
                
                print("\n✅ All clicker tests completed!")
                return self.results
                
            except Exception as e:
                print(f"\n❌ Clicker tests failed: {e}")
                self.results["errors"].append({
                    "type": "fatal_exception",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                return self.results
            
            finally:
                if self.browser:
                    await self.browser.close()
    
    async def _test_lab(self, lab_config: Dict):
        """Test a single lab with all its subtabs"""
        lab_id = lab_config["id"]
        lab_name = lab_config["name"]
        
        print(f"\n{'─'*80}")
        print(f"🧪 Testing Lab: {lab_name}")
        print(f"{'─'*80}\n")
        
        lab_results = {
            "lab_id": lab_id,
            "lab_name": lab_name,
            "timestamp": datetime.now().isoformat(),
            "main_tab_click": {},
            "subtab_clicks": [],
            "metrics": {},
            "errors": []
        }
        
        try:
            # Click main tab
            print(f"📍 Clicking main tab: {lab_name}")
            
            main_tab_result = await self._click_and_validate(
                lab_config["tab_selector"],
                f"{lab_id}_main_tab"
            )
            
            lab_results["main_tab_click"] = main_tab_result
            
            if not main_tab_result["success"]:
                print(f"❌ Failed to click main tab: {main_tab_result.get('error', 'Unknown error')}")
                lab_results["errors"].append(f"Main tab click failed: {main_tab_result.get('error')}")
                self.results["failed_clicks"] += 1
            else:
                print(f"✅ Main tab clicked successfully (Latency: {main_tab_result['latency_ms']}ms)")
                self.results["successful_clicks"] += 1
                
                # Capture state after main tab load
                lab_results["metrics"]["main_tab_state"] = await self._capture_page_state()
                
                # Test subtabs if any
                if lab_config.get("subtabs"):
                    print(f"\n  Testing {len(lab_config['subtabs'])} subtabs...")
                    
                    for i, subtab_config in enumerate(lab_config["subtabs"], 1):
                        subtab_name = subtab_config["name"]
                        print(f"  📌 {i}/{len(lab_config['subtabs'])}: {subtab_name}")
                        
                        subtab_result = await self._click_and_validate(
                            subtab_config["selector"],
                            f"{lab_id}_subtab_{i}_{subtab_name.lower().replace(' ', '_')}"
                        )
                        
                        subtab_result["subtab_name"] = subtab_name
                        lab_results["subtab_clicks"].append(subtab_result)
                        
                        if subtab_result["success"]:
                            print(f"     ✅ {subtab_name} (Latency: {subtab_result['latency_ms']}ms)")
                            self.results["successful_clicks"] += 1
                        else:
                            print(f"     ❌ {subtab_name} failed: {subtab_result.get('error', 'Unknown')}")
                            self.results["failed_clicks"] += 1
                        
                        self.results["total_clicks"] += 1
                        
                        # Small delay between subtabs
                        await asyncio.sleep(0.5)
            
            self.results["total_clicks"] += 1
            
        except Exception as e:
            print(f"❌ Lab test exception: {e}")
            lab_results["errors"].append(f"Lab test exception: {str(e)}")
            self.results["errors"].append({
                "lab": lab_name,
                "type": "lab_test_exception",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        # Store lab results
        self.results["labs_tested"].append(lab_results)
    
    async def _click_and_validate(self, selector: str, screenshot_id: str) -> Dict:
        """
        Click element, wait for callbacks, and validate state
        
        Returns:
            Dict with success status, latency, DOM changes, and errors
        """
        result = {
            "selector": selector,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "latency_ms": 0,
            "dom_mutations": 0,
            "chart_count_before": 0,
            "chart_count_after": 0,
            "metric_cards_before": 0,
            "metric_cards_after": 0,
            "error": None
        }
        
        try:
            # Capture state before click
            state_before = await self._capture_page_state()
            result["chart_count_before"] = state_before["chart_count"]
            result["metric_cards_before"] = state_before["metric_card_count"]
            
            # Wait for element to be visible
            await self.page.wait_for_selector(selector, timeout=ClickerConfig.CALLBACK_TIMEOUT_MS)
            
            # Click and measure latency
            start_time = time.time()
            
            # Setup response listener for callbacks
            response_received = asyncio.Event()
            response_count = 0
            
            def on_response(response: Response):
                nonlocal response_count
                # Track Dash callback responses
                if '/_dash-update-component' in response.url or '/_dash-layout' in response.url:
                    response_count += 1
                    response_received.set()
            
            self.page.on('response', on_response)
            
            # Perform click
            await self.page.click(selector)
            
            # Wait for at least one callback response (or timeout)
            try:
                await asyncio.wait_for(response_received.wait(), timeout=ClickerConfig.CALLBACK_TIMEOUT_MS / 1000)
            except asyncio.TimeoutError:
                print(f"     ⚠️  No callback detected within {ClickerConfig.CALLBACK_TIMEOUT_MS}ms (might be cached)")
            
            # Additional wait for DOM to settle
            await self.page.wait_for_timeout(1000)
            
            # Measure latency
            latency_ms = int((time.time() - start_time) * 1000)
            result["latency_ms"] = latency_ms
            
            self.results["callback_latencies"].append(latency_ms)
            
            # Capture state after click
            state_after = await self._capture_page_state()
            result["chart_count_after"] = state_after["chart_count"]
            result["metric_cards_after"] = state_after["metric_card_count"]
            
            # Calculate DOM mutations
            dom_mutations = abs(state_after["chart_count"] - state_before["chart_count"]) + \
                          abs(state_after["metric_card_count"] - state_before["metric_card_count"])
            
            result["dom_mutations"] = dom_mutations
            self.results["dom_mutations"].append(dom_mutations)
            
            # Take screenshot
            await self._take_screenshot(screenshot_id)
            
            # Validation checks
            if latency_ms > ClickerConfig.MAX_CALLBACK_LATENCY_MS:
                result["error"] = f"Callback latency ({latency_ms}ms) exceeds threshold ({ClickerConfig.MAX_CALLBACK_LATENCY_MS}ms)"
            elif response_count == 0 and dom_mutations == 0:
                result["error"] = "No callback response and no DOM changes detected (possibly cached or broken)"
            else:
                result["success"] = True
            
        except Exception as e:
            result["error"] = f"Click exception: {str(e)}"
        
        return result
    
    async def _capture_page_state(self) -> Dict:
        """Capture current page state metrics"""
        try:
            # Count charts (Plotly graphs)
            chart_count = await self.page.evaluate("""
                () => document.querySelectorAll('.js-plotly-plot, .plotly').length
            """)
            
            # Count metric cards (bootstrap cards with numeric values)
            metric_card_count = await self.page.evaluate("""
                () => document.querySelectorAll('.card-body h3, .card-body h4').length
            """)
            
            # Count table rows
            table_row_count = await self.page.evaluate("""
                () => document.querySelectorAll('table tbody tr').length
            """)
            
            # Check for NaN or empty values
            nan_count = await self.page.evaluate("""
                () => {
                    const text = document.body.innerText;
                    const nanMatches = text.match(/NaN|undefined|null/gi);
                    return nanMatches ? nanMatches.length : 0;
                }
            """)
            
            return {
                "chart_count": chart_count,
                "metric_card_count": metric_card_count,
                "table_row_count": table_row_count,
                "nan_count": nan_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️  Failed to capture page state: {e}")
            return {
                "chart_count": 0,
                "metric_card_count": 0,
                "table_row_count": 0,
                "nan_count": 0,
                "error": str(e)
            }
    
    async def _take_screenshot(self, filename: str):
        """Take screenshot of current page state"""
        try:
            screenshot_path = ClickerConfig.SCREENSHOTS_DIR / f"{filename}.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=False)
            self.results["screenshots"].append(str(screenshot_path))
            print(f"     📸 Screenshot: {screenshot_path.name}")
        except Exception as e:
            print(f"⚠️  Screenshot failed: {e}")
    
    def _on_console(self, msg):
        """Handle browser console messages"""
        # Only log errors and warnings
        if msg.type in ['error', 'warning']:
            print(f"     🔴 Console {msg.type.upper()}: {msg.text}")
            self.results["errors"].append({
                "type": f"console_{msg.type}",
                "message": msg.text,
                "timestamp": datetime.now().isoformat()
            })
    
    def _on_page_error(self, error):
        """Handle page errors"""
        error_msg = str(error)
        print(f"     ❌ Page Error: {error_msg}")
        self.results["errors"].append({
            "type": "page_error",
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        })
    
    def _generate_clicker_report(self):
        """Generate Phase 1 clicker test report"""
        # Calculate metrics
        avg_latency = sum(self.results["callback_latencies"]) / len(self.results["callback_latencies"]) \
                     if self.results["callback_latencies"] else 0
        
        max_latency = max(self.results["callback_latencies"]) if self.results["callback_latencies"] else 0
        
        total_dom_mutations = sum(self.results["dom_mutations"])
        avg_dom_mutations = total_dom_mutations / len(self.results["dom_mutations"]) \
                           if self.results["dom_mutations"] else 0
        
        success_rate = (self.results["successful_clicks"] / self.results["total_clicks"] * 100) \
                      if self.results["total_clicks"] > 0 else 0
        
        report = {
            "phase": "Phase 1: Playwright Clicker Functional Tests",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_labs_tested": len(self.results["labs_tested"]),
                "total_clicks": self.results["total_clicks"],
                "successful_clicks": self.results["successful_clicks"],
                "failed_clicks": self.results["failed_clicks"],
                "success_rate_pct": round(success_rate, 2)
            },
            "performance_metrics": {
                "avg_callback_latency_ms": round(avg_latency, 2),
                "max_callback_latency_ms": max_latency,
                "avg_dom_mutations_per_click": round(avg_dom_mutations, 2),
                "total_dom_mutations": total_dom_mutations,
                "callback_latency_threshold_ms": ClickerConfig.MAX_CALLBACK_LATENCY_MS
            },
            "labs_tested": self.results["labs_tested"],
            "errors": self.results["errors"],
            "screenshots": self.results["screenshots"],
            "pass_criteria": {
                "all_clicks_successful": self.results["failed_clicks"] == 0,
                "avg_latency_under_threshold": avg_latency < ClickerConfig.MAX_CALLBACK_LATENCY_MS,
                "no_critical_errors": len([e for e in self.results["errors"] if e["type"] == "page_error"]) == 0
            }
        }
        
        # Calculate overall pass
        report["overall_pass"] = all(report["pass_criteria"].values())
        
        # Save JSON report
        report_path = ClickerConfig.REPORTS_DIR / "phase1_clicker_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Clicker report saved to: {report_path}")
        
        # Print summary
        print("\n" + "="*80)
        print("  CLICKER TEST SUMMARY")
        print("="*80)
        print(f"  Total Clicks:        {self.results['total_clicks']}")
        print(f"  Successful:          {self.results['successful_clicks']} ({success_rate:.1f}%)")
        print(f"  Failed:              {self.results['failed_clicks']}")
        print(f"  Avg Latency:         {avg_latency:.0f}ms (Threshold: {ClickerConfig.MAX_CALLBACK_LATENCY_MS}ms)")
        print(f"  Max Latency:         {max_latency}ms")
        print(f"  Total DOM Mutations: {total_dom_mutations}")
        print(f"  Console Errors:      {len([e for e in self.results['errors'] if 'console' in e['type']])}")
        print(f"  Overall Pass:        {'✅ YES' if report['overall_pass'] else '❌ NO'}")
        print("="*80 + "\n")


# ============================================================================
# ENTRY POINT
# ============================================================================

async def main():
    """Main entry point for clicker tests"""
    executor = ClickerTestExecutor()
    results = await executor.run_all_tests()
    
    return results["failed_clicks"] == 0


if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
