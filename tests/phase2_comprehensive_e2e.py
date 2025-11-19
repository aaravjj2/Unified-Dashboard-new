"""
Playwright Chromium E2E Test Suite - Phase 1 Dashboard Validation
=================================================================

Comprehensive automated testing for all tabs and subtabs with:
- Snapshot capture
- Clicker interactions
- Performance metrics
- Regression validation

Designed for 3-iteration reproducibility testing.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8050"
SCREENSHOTS_DIR = Path("outputs/phase2_e2e/screenshots")
REPORTS_DIR = Path("outputs/phase2_e2e/reports")
TIMEOUT = 10000  # 10 seconds per interaction
NAVIGATION_TIMEOUT = 15000  # 15 seconds for tab loads

# Create output directories
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Test Configuration: Tabs and subtabs
TAB_CONFIG = [
    {
        "id": "home_lab",
        "name": "Home Lab",
        "selector": "a:has-text('Home')",
        "checks": [
            {"type": "visible", "selector": "#home-system-summary", "name": "System Summary"},
            {"type": "visible", "selector": "#portfolio-total-value", "name": "Portfolio Snapshot"},
            {"type": "click", "selector": "#home-refresh-portfolio-btn", "name": "Refresh Portfolio Button"},
        ]
    },
    {
        "id": "market_trends",
        "name": "Market Trends",
        "selector": "a:has-text('Market Trends')",
        "checks": [
            {"type": "visible", "selector": "[data-testid='market-trends-table']", "name": "Market Trends Table"},
            {"type": "snapshot", "name": "market_trends_main"},
        ]
    },
    {
        "id": "market_forecast",
        "name": "Market Forecast",
        "selector": "a:has-text('Market Forecast')",
        "checks": [
            {"type": "visible", "selector": "#mf-ticker-input", "name": "Ticker Input"},
            {"type": "visible", "selector": "#mf-generate-btn", "name": "Generate Button"},
            {"type": "snapshot", "name": "market_forecast_main"},
        ]
    },
    {
        "id": "volatility_lab",
        "name": "Volatility Lab",
        "selector": "a:has-text('Volatility Lab')",
        "checks": [
            {"type": "visible", "selector": "#vl-ticker-input", "name": "Volatility Ticker Input"},
            {"type": "snapshot", "name": "volatility_lab_main"},
        ]
    },
    {
        "id": "research_lab",
        "name": "Research Lab",
        "selector": "a:has-text('Research Lab')",
        "subtabs": [
            {"name": "Market Scan", "selector": "button:has-text('Market Scan')"},
            {"name": "Factor Analysis", "selector": "button:has-text('Factor Analysis')"},
            {"name": "Correlation Explorer", "selector": "button:has-text('Correlation Explorer')"},
            {"name": "Sector Trends", "selector": "button:has-text('Sector Trends')"},
            {"name": "Historical Patterns", "selector": "button:has-text('Historical Patterns')"},
        ],
        "checks": [
            {"type": "snapshot", "name": "research_lab_overview"},
        ]
    },
    {
        "id": "attribution_lab",
        "name": "Attribution Lab",
        "selector": "a:has-text('Attribution Lab')",
        "subtabs": [
            {"name": "Factor Attribution", "selector": "button:has-text('Factor Attribution')"},
            {"name": "Sector Attribution", "selector": "button:has-text('Sector Attribution')"},
            {"name": "Residual Analysis", "selector": "button:has-text('Residual Analysis')"},
        ],
        "checks": [
            {"type": "snapshot", "name": "attribution_lab_overview"},
        ]
    },
    {
        "id": "options_lab",
        "name": "Options Lab",
        "selector": "a:has-text('Options Lab')",
        "checks": [
            {"type": "visible", "selector": "#ol-ticker-input", "name": "Options Ticker Input"},
            {"type": "snapshot", "name": "options_lab_main"},
        ]
    },
    {
        "id": "strategy_lab",
        "name": "Strategy Lab",
        "selector": "a:has-text('Strategy Lab')",
        "checks": [
            {"type": "visible", "selector": "#sl-strategy-type", "name": "Strategy Type Dropdown"},
            {"type": "visible", "selector": "#sl-run-backtest-btn", "name": "Run Backtest Button"},
            {"type": "snapshot", "name": "strategy_lab_main"},
        ]
    },
]

class DashboardTester:
    def __init__(self, iteration: int):
        self.iteration = iteration
        self.results = {
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "tabs": [],
            "summary": {
                "total_tabs": 0,
                "passed_tabs": 0,
                "failed_tabs": 0,
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "total_latency_ms": 0,
            }
        }
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def setup(self):
        """Initialize browser and page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        logger.info(f"✅ Browser launched for iteration {self.iteration}")

    async def teardown(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        logger.info(f"✅ Browser closed for iteration {self.iteration}")

    async def navigate_to_dashboard(self):
        """Navigate to dashboard home"""
        start = time.time()
        try:
            await self.page.goto(BASE_URL, timeout=NAVIGATION_TIMEOUT)
            await self.page.wait_for_load_state("networkidle", timeout=NAVIGATION_TIMEOUT)
            latency = int((time.time() - start) * 1000)
            logger.info(f"✅ Dashboard loaded in {latency}ms")
            return latency, None
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"❌ Dashboard load failed: {e}")
            return latency, str(e)

    async def test_tab(self, tab_config: dict):
        """Test a single tab with all its checks"""
        tab_result = {
            "id": tab_config["id"],
            "name": tab_config["name"],
            "checks": [],
            "subtabs": [],
            "passed": False,
            "error": None,
            "latency_ms": 0
        }

        start = time.time()
        
        try:
            # Navigate to tab
            logger.info(f"\n🔍 Testing {tab_config['name']}...")
            await self.page.click(tab_config["selector"], timeout=TIMEOUT)
            await self.page.wait_for_timeout(1000)  # Wait for tab content to load
            
            # Run checks
            for check in tab_config.get("checks", []):
                check_result = await self.run_check(check, tab_config["id"])
                tab_result["checks"].append(check_result)
            
            # Test subtabs if they exist
            if "subtabs" in tab_config:
                for subtab in tab_config["subtabs"]:
                    subtab_result = await self.test_subtab(subtab, tab_config["id"])
                    tab_result["subtabs"].append(subtab_result)
            
            # Overall tab pass/fail
            tab_result["passed"] = all(
                c["passed"] for c in tab_result["checks"]
            ) and all(
                s["passed"] for s in tab_result["subtabs"]
            )
            
        except Exception as e:
            logger.error(f"❌ Tab {tab_config['name']} failed: {e}")
            tab_result["error"] = str(e)
            tab_result["passed"] = False
        
        tab_result["latency_ms"] = int((time.time() - start) * 1000)
        return tab_result

    async def test_subtab(self, subtab_config: dict, parent_tab_id: str):
        """Test a subtab"""
        subtab_result = {
            "name": subtab_config["name"],
            "passed": False,
            "error": None,
            "screenshot": None
        }
        
        try:
            logger.info(f"  ↳ Subtab: {subtab_config['name']}")
            await self.page.click(subtab_config["selector"], timeout=TIMEOUT)
            await self.page.wait_for_timeout(800)
            
            # Capture screenshot
            screenshot_name = f"iter{self.iteration}_{parent_tab_id}_{subtab_config['name'].replace(' ', '_').lower()}.png"
            screenshot_path = SCREENSHOTS_DIR / screenshot_name
            await self.page.screenshot(path=screenshot_path, full_page=False)
            subtab_result["screenshot"] = str(screenshot_path)
            subtab_result["passed"] = True
            
        except Exception as e:
            logger.error(f"    ❌ Subtab {subtab_config['name']} failed: {e}")
            subtab_result["error"] = str(e)
        
        return subtab_result

    async def run_check(self, check: dict, tab_id: str):
        """Run a single check (visible, click, snapshot)"""
        check_result = {
            "type": check["type"],
            "name": check.get("name", check.get("selector", "Unknown")),
            "passed": False,
            "error": None,
            "screenshot": None
        }
        
        try:
            if check["type"] == "visible":
                element = await self.page.wait_for_selector(check["selector"], timeout=TIMEOUT)
                is_visible = await element.is_visible()
                check_result["passed"] = is_visible
                if is_visible:
                    logger.info(f"  ✅ {check['name']} visible")
                else:
                    logger.warning(f"  ⚠️ {check['name']} not visible")
            
            elif check["type"] == "click":
                await self.page.click(check["selector"], timeout=TIMEOUT)
                await self.page.wait_for_timeout(500)
                check_result["passed"] = True
                logger.info(f"  ✅ {check['name']} clicked")
            
            elif check["type"] == "snapshot":
                screenshot_name = f"iter{self.iteration}_{check['name']}.png"
                screenshot_path = SCREENSHOTS_DIR / screenshot_name
                await self.page.screenshot(path=screenshot_path, full_page=False)
                check_result["screenshot"] = str(screenshot_path)
                check_result["passed"] = True
                logger.info(f"  📸 Snapshot: {screenshot_name}")
        
        except Exception as e:
            logger.error(f"  ❌ Check {check['name']} failed: {e}")
            check_result["error"] = str(e)
        
        return check_result

    async def run_all_tests(self):
        """Execute full test suite"""
        await self.setup()
        
        # Navigate to dashboard
        nav_latency, nav_error = await self.navigate_to_dashboard()
        if nav_error:
            self.results["dashboard_load_error"] = nav_error
            await self.teardown()
            return self.results
        
        # Test each tab
        for tab_config in TAB_CONFIG:
            tab_result = await self.test_tab(tab_config)
            self.results["tabs"].append(tab_result)
            
            # Update summary
            self.results["summary"]["total_tabs"] += 1
            if tab_result["passed"]:
                self.results["summary"]["passed_tabs"] += 1
            else:
                self.results["summary"]["failed_tabs"] += 1
            
            self.results["summary"]["total_checks"] += len(tab_result["checks"])
            self.results["summary"]["passed_checks"] += sum(1 for c in tab_result["checks"] if c["passed"])
            self.results["summary"]["failed_checks"] += sum(1 for c in tab_result["checks"] if not c["passed"])
            self.results["summary"]["total_latency_ms"] += tab_result["latency_ms"]
        
        await self.teardown()
        return self.results

    def save_results(self):
        """Save results to JSON and generate Markdown report"""
        # Save JSON
        json_path = REPORTS_DIR / f"iteration_{self.iteration}_results.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"✅ JSON report saved: {json_path}")
        
        # Generate Markdown
        md_path = REPORTS_DIR / f"iteration_{self.iteration}_report.md"
        with open(md_path, "w") as f:
            f.write(self.generate_markdown_report())
        logger.info(f"✅ Markdown report saved: {md_path}")

    def generate_markdown_report(self):
        """Generate human-readable Markdown report"""
        md = f"""# Phase 1 E2E Test Report - Iteration {self.iteration}

**Timestamp:** {self.results['timestamp']}

## Summary

| Metric | Value |
|--------|-------|
| Total Tabs Tested | {self.results['summary']['total_tabs']} |
| ✅ Passed Tabs | {self.results['summary']['passed_tabs']} |
| ❌ Failed Tabs | {self.results['summary']['failed_tabs']} |
| Total Checks | {self.results['summary']['total_checks']} |
| ✅ Passed Checks | {self.results['summary']['passed_checks']} |
| ❌ Failed Checks | {self.results['summary']['failed_checks']} |
| Total Latency | {self.results['summary']['total_latency_ms']}ms |
| Avg Latency/Tab | {self.results['summary']['total_latency_ms'] // self.results['summary']['total_tabs'] if self.results['summary']['total_tabs'] > 0 else 0}ms |

## Tab Results

"""
        for tab in self.results["tabs"]:
            status = "✅ PASS" if tab["passed"] else "❌ FAIL"
            md += f"### {tab['name']} - {status} ({tab['latency_ms']}ms)\n\n"
            
            if tab["error"]:
                md += f"**Error:** {tab['error']}\n\n"
            
            if tab["checks"]:
                md += "**Checks:**\n"
                for check in tab["checks"]:
                    check_status = "✅" if check["passed"] else "❌"
                    md += f"- {check_status} {check['name']} ({check['type']})\n"
                    if check["error"]:
                        md += f"  - Error: {check['error']}\n"
                md += "\n"
            
            if tab["subtabs"]:
                md += "**Subtabs:**\n"
                for subtab in tab["subtabs"]:
                    subtab_status = "✅" if subtab["passed"] else "❌"
                    md += f"- {subtab_status} {subtab['name']}\n"
                    if subtab["error"]:
                        md += f"  - Error: {subtab['error']}\n"
                md += "\n"
        
        return md


async def run_iteration(iteration: int):
    """Run a single test iteration"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Starting Iteration {iteration}")
    logger.info(f"{'='*60}")
    
    tester = DashboardTester(iteration)
    results = await tester.run_all_tests()
    tester.save_results()
    
    logger.info(f"\n✅ Iteration {iteration} complete!")
    logger.info(f"  Tabs: {results['summary']['passed_tabs']}/{results['summary']['total_tabs']} passed")
    logger.info(f"  Checks: {results['summary']['passed_checks']}/{results['summary']['total_checks']} passed")
    
    return results


async def main():
    """Run 3-iteration test loop"""
    logger.info("="*60)
    logger.info("Phase 1 Dashboard E2E Testing - 3 Iterations")
    logger.info("="*60)
    
    all_results = []
    
    for i in range(1, 4):
        results = await run_iteration(i)
        all_results.append(results)
        
        # Wait between iterations
        if i < 3:
            logger.info(f"\n⏳ Waiting 5 seconds before iteration {i+1}...")
            await asyncio.sleep(5)
    
    # Generate aggregate report
    logger.info("\n" + "="*60)
    logger.info("📊 Generating Aggregate Report...")
    logger.info("="*60)
    
    aggregate_path = REPORTS_DIR / "aggregate_report.md"
    with open(aggregate_path, "w") as f:
        f.write(generate_aggregate_report(all_results))
    
    logger.info(f"✅ Aggregate report saved: {aggregate_path}")
    logger.info("\n🎉 All 3 iterations complete!")


def generate_aggregate_report(all_results):
    """Generate cross-iteration aggregate report"""
    md = f"""# Phase 1 E2E Testing - Aggregate Report (3 Iterations)

**Generated:** {datetime.now().isoformat()}

## Cross-Iteration Summary

| Iteration | Total Tabs | Passed Tabs | Failed Tabs | Total Checks | Passed Checks | Failed Checks | Avg Latency |
|-----------|------------|-------------|-------------|--------------|---------------|---------------|-------------|
"""
    
    for i, results in enumerate(all_results, 1):
        s = results["summary"]
        avg_latency = s["total_latency_ms"] // s["total_tabs"] if s["total_tabs"] > 0 else 0
        md += f"| {i} | {s['total_tabs']} | {s['passed_tabs']} | {s['failed_tabs']} | {s['total_checks']} | {s['passed_checks']} | {s['failed_checks']} | {avg_latency}ms |\n"
    
    md += "\n## Reproducibility Analysis\n\n"
    
    # Check consistency across iterations
    tab_consistency = {}
    for results in all_results:
        for tab in results["tabs"]:
            if tab["id"] not in tab_consistency:
                tab_consistency[tab["id"]] = {"name": tab["name"], "results": []}
            tab_consistency[tab["id"]]["results"].append(tab["passed"])
    
    md += "| Tab | Iter 1 | Iter 2 | Iter 3 | Stable? |\n"
    md += "|-----|--------|--------|--------|------|\n"
    
    for tab_id, data in tab_consistency.items():
        iter1 = "✅" if data["results"][0] else "❌"
        iter2 = "✅" if data["results"][1] else "❌"
        iter3 = "✅" if data["results"][2] else "❌"
        stable = "🟢" if all(data["results"]) or not any(data["results"]) else "🔴"
        md += f"| {data['name']} | {iter1} | {iter2} | {iter3} | {stable} |\n"
    
    return md


if __name__ == "__main__":
    asyncio.run(main())
