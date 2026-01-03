#!/usr/bin/env python3
"""
Alpaca Options Lab - Comprehensive E2E Test Suite v2
=====================================================
Fixed tab selectors for Dash tabs rendering
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8053"
SCREENSHOTS_DIR = Path("/home/aarav/Unified-Dashboard/alpaca-options-lab/tests/e2e_screenshots")
REPORTS_DIR = Path("/home/aarav/Unified-Dashboard/alpaca-options-lab/tests/e2e_reports")
TIMEOUT = 15000
NAVIGATION_TIMEOUT = 30000

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Fixed selectors - Dash tabs render as divs with specific classes
TAB_CONFIG = [
    {
        "id": "scanner",
        "name": "Scanner",
        "selector": ".tab-parent:has-text('Scanner'), .tab:has-text('Scanner'), [class*='tab']:has-text('Scanner')",
        "checks": [
            {"type": "visible", "selector": "#scanner-workspace, [id*='scanner']", "name": "Scanner Workspace"},
            {"type": "visible", "selector": "#scanner-hype-gauges, [id*='hype']", "name": "Hype Gauges"},
            {"type": "visible", "selector": "#scanner-tv-chart-container, [id*='tv-chart']", "name": "TV Chart Container"},
            {"type": "snapshot", "name": "scanner"},
        ]
    },
    {
        "id": "strategy",
        "name": "Strategy", 
        "selector": ".tab-parent:has-text('Strategy'), .tab:has-text('Strategy'), [class*='tab']:has-text('Strategy')",
        "checks": [
            {"type": "visible", "selector": "#strategy-workspace, [id*='strategy']", "name": "Strategy Workspace"},
            {"type": "snapshot", "name": "strategy"},
        ]
    },
    {
        "id": "command",
        "name": "Command",
        "selector": ".tab-parent:has-text('Command'), .tab:has-text('Command'), [class*='tab']:has-text('Command')",
        "checks": [
            {"type": "visible", "selector": "#command-workspace, [id*='command']", "name": "Command Workspace"},
            {"type": "snapshot", "name": "command"},
        ]
    },
    {
        "id": "admin",
        "name": "Admin",
        "selector": ".tab-parent:has-text('Admin'), .tab:has-text('Admin'), [class*='tab']:has-text('Admin')",
        "checks": [
            {"type": "visible", "selector": "#admin-workspace, [id*='admin']", "name": "Admin Workspace"},
            {"type": "snapshot", "name": "admin"},
        ]
    },
]


class AlpacaLabTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "tests": [],
            "summary": {"total_tests": 0, "passed": 0, "failed": 0, "errors": []},
            "performance": {"page_load_ms": 0, "total_time_ms": 0},
            "console_logs": [],
            "console_errors": [],
        }
        self.browser = None
        self.page = None
        self.start_time = None

    async def setup(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        self.page.on("console", lambda msg: self._capture_console(msg))
        self.start_time = time.time()
        logger.info("✅ Browser launched")

    def _capture_console(self, msg):
        entry = {"type": msg.type, "text": msg.text}
        if msg.type == "error":
            self.results["console_errors"].append(entry)
        elif any(k in msg.text for k in ["TV Chart", "Render", "Lightweight", "📈"]):
            self.results["console_logs"].append(entry)

    async def teardown(self):
        if self.browser:
            await self.browser.close()
        self.results["performance"]["total_time_ms"] = int((time.time() - self.start_time) * 1000)
        logger.info("✅ Browser closed")

    async def load_dashboard(self):
        start = time.time()
        test_result = {"name": "Dashboard Load", "passed": False, "error": None}
        try:
            await self.page.goto(BASE_URL, timeout=NAVIGATION_TIMEOUT, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(3000)  # Wait for React/Dash to render
            latency = int((time.time() - start) * 1000)
            self.results["performance"]["page_load_ms"] = latency
            test_result["passed"] = True
            test_result["latency_ms"] = latency
            logger.info(f"✅ Dashboard loaded in {latency}ms")
        except Exception as e:
            test_result["error"] = str(e)
            logger.error(f"❌ Dashboard load failed: {e}")
        self.results["tests"].append(test_result)
        self._update_summary(test_result)
        return test_result["passed"]

    async def test_initial_page_elements(self):
        """Test elements visible on initial load (Scanner is default)"""
        test_result = {"name": "Initial Page Elements", "passed": False, "checks": [], "error": None}
        
        try:
            # Check main container
            body = await self.page.query_selector("body")
            test_result["checks"].append({"name": "Body exists", "passed": body is not None})
            
            # Check for key elements on initial load
            elements_to_check = [
                ("#alpaca-ticker-input", "Ticker Input"),
                ("#alpaca-load-button", "Load Chain Button"),
                ("#main-workspace-tabs", "Main Workspace Tabs"),
            ]
            
            for selector, name in elements_to_check:
                try:
                    elem = await self.page.query_selector(selector)
                    passed = elem is not None
                    if passed:
                        visible = await elem.is_visible()
                        passed = visible
                    test_result["checks"].append({"name": name, "passed": passed, "selector": selector})
                    if passed:
                        logger.info(f"  ✅ {name}")
                    else:
                        logger.warning(f"  ⚠️ {name} not found/visible")
                except Exception as e:
                    test_result["checks"].append({"name": name, "passed": False, "error": str(e)})
            
            test_result["passed"] = all(c["passed"] for c in test_result["checks"])
            
        except Exception as e:
            test_result["error"] = str(e)
            logger.error(f"❌ Initial elements test failed: {e}")
        
        self.results["tests"].append(test_result)
        self._update_summary(test_result)
        return test_result

    async def test_scanner_chart(self):
        """Test TradingView chart rendering"""
        test_result = {"name": "TradingView Chart", "passed": False, "details": {}, "error": None}
        
        try:
            # Wait for chart container
            await self.page.wait_for_timeout(2000)
            
            # Look for chart container with multiple possible selectors
            container = None
            for selector in ["#scanner-tv-chart-container", "[id*='tv-chart']", "[id*='chart-container']"]:
                container = await self.page.query_selector(selector)
                if container:
                    test_result["details"]["container_selector"] = selector
                    break
            
            test_result["details"]["container_exists"] = container is not None
            
            if container:
                # Check for canvas (LightweightCharts creates canvas)
                canvas = await container.query_selector("canvas")
                test_result["details"]["canvas_exists"] = canvas is not None
                
                if canvas:
                    box = await canvas.bounding_box()
                    if box:
                        test_result["details"]["canvas_size"] = f"{box['width']}x{box['height']}"
                        test_result["passed"] = box["width"] > 50 and box["height"] > 50
                        logger.info(f"✅ Chart canvas: {box['width']}x{box['height']}")
                    else:
                        test_result["details"]["error"] = "Canvas has no bounding box"
                else:
                    # Maybe chart hasn't rendered yet - capture anyway
                    test_result["details"]["error"] = "No canvas in container (chart may not have rendered)"
                    
                # Screenshot the chart area
                await container.screenshot(path=SCREENSHOTS_DIR / "tv_chart_area.png")
                test_result["details"]["screenshot"] = "tv_chart_area.png"
            else:
                test_result["details"]["error"] = "Chart container not found"
                
        except Exception as e:
            test_result["error"] = str(e)
            logger.error(f"❌ Chart test failed: {e}")
        
        self.results["tests"].append(test_result)
        self._update_summary(test_result)
        return test_result

    async def test_hype_gauges(self):
        """Test sentiment gauges"""
        test_result = {"name": "Hype Gauges", "passed": False, "details": {}, "error": None}
        
        try:
            gauges_container = await self.page.query_selector("#scanner-hype-gauges")
            test_result["details"]["container_exists"] = gauges_container is not None
            
            if gauges_container:
                # Count gauge graphs
                graphs = await gauges_container.query_selector_all(".js-plotly-plot")
                test_result["details"]["gauge_count"] = len(graphs)
                test_result["passed"] = len(graphs) >= 1
                logger.info(f"✅ Found {len(graphs)} Hype Gauges")
                
                await gauges_container.screenshot(path=SCREENSHOTS_DIR / "hype_gauges.png")
            else:
                # Try alternative selectors
                alt_container = await self.page.query_selector("[id*='hype'], [id*='gauge']")
                test_result["details"]["alt_container"] = alt_container is not None
                
        except Exception as e:
            test_result["error"] = str(e)
            logger.error(f"❌ Gauges test failed: {e}")
        
        self.results["tests"].append(test_result)
        self._update_summary(test_result)
        return test_result

    async def test_symbol_buttons(self):
        """Test symbol selection buttons"""
        test_result = {"name": "Symbol Buttons", "passed": False, "details": [], "error": None}
        
        try:
            symbols = ["NVDA", "TSLA", "SPY", "GLD"]
            for symbol in symbols:
                btn = await self.page.query_selector(f"#scanner-sym-btn-{symbol}")
                if btn:
                    test_result["details"].append({"symbol": symbol, "exists": True})
                    logger.info(f"  ✅ {symbol} button found")
                else:
                    test_result["details"].append({"symbol": symbol, "exists": False})
            
            test_result["passed"] = any(d["exists"] for d in test_result["details"])
            
        except Exception as e:
            test_result["error"] = str(e)
        
        self.results["tests"].append(test_result)
        self._update_summary(test_result)
        return test_result

    async def test_tab_navigation(self):
        """Test workspace tab navigation"""
        test_result = {"name": "Tab Navigation", "passed": False, "tabs_tested": [], "error": None}
        
        try:
            # Find all tabs
            tabs = await self.page.query_selector_all(".tab, [class*='Tab'], [role='tab']")
            logger.info(f"Found {len(tabs)} potential tab elements")
            
            # Also try Dash-specific tab class
            dash_tabs = await self.page.query_selector_all(".custom-tab, .tab--selected, .tab--unselected")
            logger.info(f"Found {len(dash_tabs)} Dash tab elements")
            
            # Try clicking tabs by text content
            tab_texts = ["Scanner", "Strategy", "Command", "Admin"]
            for tab_text in tab_texts:
                try:
                    # Multiple selector strategies
                    clicked = False
                    for selector in [
                        f"text='{tab_text}'",
                        f"button:has-text('{tab_text}')",
                        f"div:has-text('{tab_text}'):visible",
                    ]:
                        try:
                            await self.page.click(selector, timeout=3000)
                            clicked = True
                            await self.page.wait_for_timeout(1000)
                            break
                        except:
                            continue
                    
                    test_result["tabs_tested"].append({"tab": tab_text, "clicked": clicked})
                    if clicked:
                        await self.page.screenshot(path=SCREENSHOTS_DIR / f"tab_{tab_text.lower()}.png")
                        logger.info(f"  ✅ Clicked {tab_text} tab")
                    else:
                        logger.warning(f"  ⚠️ Could not click {tab_text} tab")
                        
                except Exception as e:
                    test_result["tabs_tested"].append({"tab": tab_text, "clicked": False, "error": str(e)})
            
            test_result["passed"] = any(t["clicked"] for t in test_result["tabs_tested"])
            
        except Exception as e:
            test_result["error"] = str(e)
            logger.error(f"❌ Tab navigation failed: {e}")
        
        self.results["tests"].append(test_result)
        self._update_summary(test_result)
        return test_result

    async def capture_full_page(self):
        """Capture full page screenshot"""
        try:
            await self.page.screenshot(path=SCREENSHOTS_DIR / "full_page.png", full_page=True)
            logger.info("📸 Full page screenshot captured")
        except Exception as e:
            logger.error(f"❌ Full page screenshot failed: {e}")

    def _update_summary(self, test_result):
        self.results["summary"]["total_tests"] += 1
        if test_result["passed"]:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
            if test_result.get("error"):
                self.results["summary"]["errors"].append({
                    "test": test_result["name"],
                    "error": test_result["error"]
                })

    async def run_all_tests(self):
        logger.info("=" * 60)
        logger.info("🚀 Alpaca Options Lab - E2E Testing Suite v2")
        logger.info("=" * 60)
        
        await self.setup()
        
        # Test 1: Load Dashboard
        if not await self.load_dashboard():
            logger.error("Dashboard failed to load - aborting tests")
            await self.capture_full_page()
            await self.teardown()
            return self.results
        
        # Test 2: Initial Elements
        await self.test_initial_page_elements()
        
        # Test 3: Full Page Screenshot
        await self.capture_full_page()
        
        # Test 4: Hype Gauges
        await self.test_hype_gauges()
        
        # Test 5: TradingView Chart
        await self.test_scanner_chart()
        
        # Test 6: Symbol Buttons
        await self.test_symbol_buttons()
        
        # Test 7: Tab Navigation
        await self.test_tab_navigation()
        
        await self.teardown()
        return self.results

    def save_results(self):
        # JSON
        json_path = REPORTS_DIR / "e2e_results.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Markdown
        md_path = REPORTS_DIR / "e2e_report.md"
        with open(md_path, "w") as f:
            f.write(self._generate_markdown())
        
        logger.info(f"✅ Results saved: {REPORTS_DIR}")
        return json_path, md_path

    def _generate_markdown(self):
        s = self.results["summary"]
        p = self.results["performance"]
        pass_rate = (s["passed"] / max(s["total_tests"], 1)) * 100
        
        md = f"""# Alpaca Options Lab - E2E Test Report

**Timestamp:** {self.results['timestamp']}
**URL:** {self.results['base_url']}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {s['total_tests']} |
| ✅ Passed | {s['passed']} |
| ❌ Failed | {s['failed']} |
| Pass Rate | {pass_rate:.1f}% |
| Page Load | {p['page_load_ms']}ms |
| Total Time | {p['total_time_ms']}ms |

## Test Results

"""
        for test in self.results["tests"]:
            status = "✅" if test["passed"] else "❌"
            md += f"### {status} {test['name']}\n\n"
            
            if test.get("error"):
                md += f"**Error:** `{test['error']}`\n\n"
            
            if test.get("details"):
                md += f"**Details:**\n```json\n{json.dumps(test['details'], indent=2)}\n```\n\n"
            
            if test.get("checks"):
                md += "**Checks:**\n"
                for check in test["checks"]:
                    c_status = "✅" if check.get("passed") else "❌"
                    md += f"- {c_status} {check.get('name', 'Unknown')}\n"
                md += "\n"
            
            if test.get("tabs_tested"):
                md += "**Tabs:**\n"
                for tab in test["tabs_tested"]:
                    t_status = "✅" if tab.get("clicked") else "❌"
                    md += f"- {t_status} {tab['tab']}\n"
                md += "\n"
        
        if self.results["console_errors"]:
            md += "## Console Errors\n\n"
            for err in self.results["console_errors"][:5]:
                md += f"- `{err['text'][:200]}`\n"
            md += "\n"
        
        if self.results["console_logs"]:
            md += "## Chart-Related Console Logs\n\n"
            for log in self.results["console_logs"][:10]:
                md += f"- `{log['text']}`\n"
        
        return md


async def main():
    tester = AlpacaLabTester()
    results = await tester.run_all_tests()
    json_path, md_path = tester.save_results()
    
    print("\n" + "=" * 60)
    print("📊 E2E TEST SUMMARY")
    print("=" * 60)
    s = results["summary"]
    print(f"  Total: {s['total_tests']} | Passed: {s['passed']} | Failed: {s['failed']}")
    print(f"  Pass Rate: {(s['passed']/max(s['total_tests'],1)*100):.1f}%")
    print(f"\n  📄 Report: {md_path}")
    print(f"  📸 Screenshots: {SCREENSHOTS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
