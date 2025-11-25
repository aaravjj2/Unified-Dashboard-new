#!/usr/bin/env python3
"""
PHASE 14B FINAL FIX & VALIDATION - Port 8051
Corrects subtab IDs and validates all known issues
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Configuration
DASHBOARD_URL = "http://localhost:8051"
OUTPUTS_DIR = Path("outputs/phase14b_final")
ACTION_TIMEOUT = 15000
SUBTAB_TIMEOUT = 5000
NAVIGATION_TIMEOUT = 30000
RETRY_COUNT = 3

# CORRECTED Tab structure based on actual layout files
TAB_STRUCTURE = {
    "home_lab": {
        "name": "🏠 Command Center",
        "selector": "#tab-home_lab",
        "subtabs": {},
        "known_issues": ["portfolio_snapshot_widget"]  # Widget, not subtab
    },
    "research_lab": {
        "name": "🔬 Research Lab",
        "selector": "#tab-research_lab",
        "subtabs": {
            "market-scan": "📊 Market Scan",
            "factor-analysis": "📈 Factor Analysis",
            "correlation-explorer": "🔗 Correlation Explorer",
            "strategy-backtest": "⚙️ Strategy Backtest",
            "research-notes": "📝 Research Notes"
        }
    },
    "attribution_lab": {
        "name": "📊 Attribution Lab",
        "selector": "#tab-attribution_lab",
        "subtabs": {
            "performance": "📈 Performance Overview"
        }
    },
    "strategy_lab": {
        "name": "⚡ Strategy Lab",
        "selector": "#tab-strategy_lab",
        "subtabs": {
            "setup-tab": "📋 Setup",
            "backtest-tab": "📊 Backtest",
            "execute-tab": "▶️ Execute",
            "results-tab": "📈 Results",
            "benchmark-tab": "🎯 Benchmark",
            "risk-tab": "⚠️ Risk"
        },
        "known_issues": ["tradingview_signals_preview"]
    },
    "azure_ml_lab": {
        "name": "🤖 Azure ML Lab",
        "selector": "#tab-azure_ml_lab",
        "subtabs": {
            "predictions": "📊 Predictions",
            "performance": "Performance"  # FIXED: Use exact visible text "Performance" (no emoji to avoid "Performance Overview")
        },
        "known_issues": ["buttons_not_responding", "options_forecast_no_output"]
    },
    "weekly_picks": {
        "name": "Weekly Picks",
        "selector": "#tab-weekly_picks",
        "subtabs": {}
    },
    "monthly_picks": {
        "name": "Monthly Picks",
        "selector": "#tab-monthly_picks",
        "subtabs": {}
    },
    "market_trends": {
        "name": "Market Trends",
        "selector": "#tab-market_trends",
        "subtabs": {}
    },
    "market_forecast": {
        "name": "Market Forecast",
        "selector": "#tab-market_forecast",
        "subtabs": {}
    },
    "volatility_lab": {
        "name": "⚡ Volatility Lab",
        "selector": "#tab-volatility_lab",
        "subtabs": {
            "hv": "Historical HV",
            "iv": "IV Surface",
            "corr": "Correlation",  # Actual display name, not "🔗 Correlation Explorer"
            "factor": "Factors",  # FIXED: Actually "Factors", not "Factor Analytics"
            "advanced": "Charts",  # FIXED: Actually "Charts", not "Advanced Charts"
            "metrics": "Metrics",  # FIXED: Actually "Metrics", not "Metrics Table"
            "scenarios": "Scenarios",  # FIXED: Actually "Scenarios", not "Custom Scenarios"
            "alerts": "Alerts"
        }
    },
    "portfolio": {
        "name": "Portfolio",
        "selector": "#tab-portfolio",
        "subtabs": {
            "positions": "Positions",  # CORRECT: tab_id='positions'
            "orders": "Order History",  # CORRECT: tab_id='orders'
            "analytics": "Analytics",  # CORRECT: tab_id='analytics'
            "factors": "Factor Exposure",  # CORRECT: tab_id='factors'
            "optimization": "Optimization"  # CORRECT: tab_id='optimization'
        }
    },
    "options_lab": {
        "name": "💹 Options Lab",
        "selector": "#tab-options_lab",
        "subtabs": {
            "chain-viewer": "📊 Chain Viewer",
            "volatility": "Volatility Lab"
        }
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
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tab TEXT NOT NULL,
                subtab TEXT,
                action TEXT NOT NULL,
                duration_ms INTEGER,
                success INTEGER NOT NULL,
                details TEXT
            )
        """)
        self.conn.commit()
    
    def log_event(self, tab: str, subtab: str, action: str, duration_ms: int, 
                  success: bool, details: str = ""):
        self.cursor.execute("""
            INSERT INTO events (timestamp, tab, subtab, action, duration_ms, success, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            tab,
            subtab or "",
            action,
            duration_ms,
            1 if success else 0,
            details
        ))
        self.conn.commit()
    
    def close(self):
        self.conn.close()


class Phase14BFinalValidator:
    def __init__(self):
        self.playwright_context = None
        self.browser = None
        self.page = None
        self.console_errors = []
        self.network_errors = []
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "FAIL",
            "pass_rate": 0.0,
            "tabs_tested": 0,
            "tabs_passed": 0,
            "subtabs_tested": 0,
            "subtabs_passed": 0,
            "failures": [],
            "remediation_tickets": [],
            "known_issues_resolved": []
        }
    
    async def setup(self):
        print("🚀 Initializing Playwright...")
        self.playwright_context = await async_playwright().start()
        self.browser = await self.playwright_context.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Event listeners
        self.page.on("console", lambda msg: self.console_errors.append(f"[{msg.type.upper()}] {msg.text}") if msg.type in ("error", "warning") else None)
        self.page.on("pageerror", lambda err: self.console_errors.append(f"[PAGE ERROR] {str(err)}"))
        self.page.on("requestfailed", lambda req: self.network_errors.append(f"[NETWORK FAIL] {req.url}"))
        
        await self.page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)
        await self.page.wait_for_selector("#dashboard-tabs", state="visible", timeout=10000)
        print(f"✅ Dashboard loaded: {await self.page.title()}")
    
    async def teardown(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright_context:
            await self.playwright_context.stop()
    
    async def navigate_to_tab(self, tab_id: str, selector: str) -> bool:
        for attempt in range(RETRY_COUNT):
            try:
                await self.page.click(selector, timeout=ACTION_TIMEOUT)
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(2)
                return True
            except:
                if attempt == RETRY_COUNT - 1:
                    return False
                await asyncio.sleep(1)
        return False
    
    async def navigate_to_subtab(self, subtab_name: str) -> bool:
        """Navigate to subtab using text-based selector (Bootstrap DBC tabs use <a> tags)"""
        # Find all VISIBLE subtab links (filter out hidden tabs from other sections)
        try:
            all_tabs = await self.page.query_selector_all("a[role='tab']")
            for tab in all_tabs:
                is_visible = await tab.is_visible()
                if not is_visible:
                    continue
                
                text = await tab.text_content()
                if text and subtab_name in text:
                    await tab.click(timeout=SUBTAB_TIMEOUT)
                    await asyncio.sleep(1.5)  # Wait for content load
                    return True
            
            return False
        except:
            return False
    
    async def capture_screenshot(self, tab_id: str, subtab_id: str = None) -> bool:
        try:
            folder = OUTPUTS_DIR / "snapshots" / tab_id
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"{subtab_id}.png" if subtab_id else "main.png"
            await self.page.screenshot(path=str(folder / filename), full_page=True)
            return True
        except Exception as e:
            print(f"❌ Screenshot error: {e}")
            return False
    
    async def test_known_issue_tradingview_signals(self) -> Dict:
        """Test TradingView Signals Preview in Strategy Lab"""
        print("\n  🔍 Testing TradingView Signals Preview...")
        result = {"issue": "tradingview_signals_preview", "resolved": False, "details": ""}
        
        try:
            # Look for the preview container
            error_selector = "text=/Error fetching preview/i"
            preview_selector = ".tradingview-signals-preview, #tradingview-preview"
            
            # Check if error message exists
            error_elem = await self.page.query_selector(error_selector)
            if error_elem:
                result["details"] = "Error message found: 'Error fetching preview'"
                result["resolved"] = False
            else:
                # Check if preview container exists
                preview_elem = await self.page.query_selector(preview_selector)
                if preview_elem:
                    content = await preview_elem.text_content()
                    result["details"] = f"Preview found with content length: {len(content)}"
                    result["resolved"] = len(content) > 10
                else:
                    result["details"] = "Preview container not found"
                    result["resolved"] = False
        except Exception as e:
            result["details"] = f"Test error: {str(e)}"
        
        return result
    
    async def test_known_issue_options_forecast(self) -> Dict:
        """Test Options Forecast rendering in Azure ML Lab"""
        print("\n  🔍 Testing Options Forecast...")
        result = {"issue": "options_forecast", "resolved": False, "details": ""}
        
        try:
            # Look for forecast output
            forecast_selector = "#options-forecast-output, .forecast-result, #azure-ml-forecast"
            
            elem = await self.page.query_selector(forecast_selector)
            if elem:
                text = await elem.text_content()
                result["details"] = f"Forecast element exists, content length: {len(text)}"
                result["resolved"] = len(text) > 20
            else:
                result["details"] = "Forecast output container not found"
                result["resolved"] = False
        except Exception as e:
            result["details"] = f"Test error: {str(e)}"
        
        return result
    
    async def test_known_issue_azure_ml_buttons(self) -> Dict:
        """Test Azure ML Lab button responsiveness"""
        print("\n  🔍 Testing Azure ML Lab Buttons...")
        result = {"issue": "azure_ml_buttons", "resolved": False, "details": "", "buttons_found": 0, "buttons_working": 0}
        
        try:
            # Find all buttons in Azure ML Lab
            button_selectors = [
                "#azure-ml-lab button",
                ".azure-ml-controls button",
                "[id*='azure'] button"
            ]
            
            for sel in button_selectors:
                buttons = await self.page.query_selector_all(sel)
                if buttons:
                    result["buttons_found"] = len(buttons)
                    
                    # Test first 3 buttons
                    for idx, btn in enumerate(buttons[:3]):
                        try:
                            is_visible = await btn.is_visible()
                            if is_visible:
                                await btn.click(timeout=3000)
                                result["buttons_working"] += 1
                        except:
                            pass
                    
                    break
            
            result["resolved"] = result["buttons_working"] > 0
            result["details"] = f"Found {result['buttons_found']} buttons, {result['buttons_working']} working"
        except Exception as e:
            result["details"] = f"Test error: {str(e)}"
        
        return result
    
    async def test_known_issue_portfolio_snapshot_widget(self) -> Dict:
        """Test Portfolio Snapshot widget in Command Center"""
        print("\n  🔍 Testing Portfolio Snapshot Widget...")
        result = {"issue": "portfolio_snapshot_widget", "resolved": False, "details": ""}
        
        try:
            # Look for portfolio snapshot widget
            widget_selectors = [
                "#portfolio-snapshot-widget",
                ".portfolio-snapshot",
                ".portfolio-summary-card",
                "#pa-summary-card"
            ]
            
            for sel in widget_selectors:
                elem = await self.page.query_selector(sel)
                if elem:
                    html = await elem.inner_html()
                    
                    # Check for key data fields
                    has_sector = "sector" in html.lower()
                    has_price = "price" in html.lower() or "$" in html
                    has_change = "%" in html or "change" in html.lower()
                    
                    result["resolved"] = has_sector and has_price and has_change
                    result["details"] = f"Widget found: sector={has_sector}, price={has_price}, change={has_change}"
                    return result
            
            result["details"] = "Portfolio snapshot widget not found"
        except Exception as e:
            result["details"] = f"Test error: {str(e)}"
        
        return result
    
    async def validate_tab(self, tab_id: str, config: Dict, telemetry: TelemetryDB) -> Dict:
        """Complete validation of a single tab"""
        start_time = datetime.utcnow()
        tab_name = config["name"]
        
        print(f"\n{'='*60}")
        print(f"📍 Testing Tab: {tab_name} ({tab_id})")
        print(f"{'='*60}")
        
        result = {
            "tab_id": tab_id,
            "tab_name": tab_name,
            "status": "PASS",
            "subtabs": [],
            "errors": [],
            "known_issues_tested": []
        }
        
        # Navigate to tab
        selector = config.get("selector", f"#tab-{tab_id}")
        if not await self.navigate_to_tab(tab_id, selector):
            result["status"] = "FAIL"
            result["errors"].append(f"Could not navigate to tab: {tab_name}")
            telemetry.log_event(tab_id, None, "navigate", 0, False, "Navigation failed")
            return result
        
        # Capture main tab
        await self.capture_screenshot(tab_id)
        telemetry.log_event(tab_id, None, "screenshot", 0, True, "Main tab captured")
        
        # Test known issues for this tab
        known_issues = config.get("known_issues", [])
        for issue in known_issues:
            if issue == "tradingview_signals_preview":
                issue_result = await self.test_known_issue_tradingview_signals()
                result["known_issues_tested"].append(issue_result)
                if issue_result["resolved"]:
                    self.results["known_issues_resolved"].append(issue)
            elif issue == "options_forecast_no_output":
                issue_result = await self.test_known_issue_options_forecast()
                result["known_issues_tested"].append(issue_result)
                if issue_result["resolved"]:
                    self.results["known_issues_resolved"].append(issue)
            elif issue == "buttons_not_responding":
                issue_result = await self.test_known_issue_azure_ml_buttons()
                result["known_issues_tested"].append(issue_result)
                if issue_result["resolved"]:
                    self.results["known_issues_resolved"].append(issue)
            elif issue == "portfolio_snapshot_widget":
                issue_result = await self.test_known_issue_portfolio_snapshot_widget()
                result["known_issues_tested"].append(issue_result)
                if issue_result["resolved"]:
                    self.results["known_issues_resolved"].append(issue)
        
        # Test subtabs
        subtabs = config.get("subtabs", {})
        self.results["subtabs_tested"] += len(subtabs)
        
        for subtab_id, subtab_name in subtabs.items():
            print(f"\n  📂 Subtab: {subtab_name}")
            
            subtab_result = {
                "subtab_id": subtab_id,
                "subtab_name": subtab_name,
                "status": "PASS",
                "errors": []
            }
            
            # Use subtab_name for navigation (text-based selector)
            if await self.navigate_to_subtab(subtab_name):
                await self.capture_screenshot(tab_id, subtab_id)
                telemetry.log_event(tab_id, subtab_id, "navigate", 0, True, "Subtab validated")
                self.results["subtabs_passed"] += 1
                print(f"    ✅ {subtab_name} - PASSED")
            else:
                subtab_result["status"] = "FAIL"
                subtab_result["errors"].append(f"Could not navigate to subtab: {subtab_name}")
                result["status"] = "FAIL"
                telemetry.log_event(tab_id, subtab_id, "navigate", 0, False, "Navigation timeout")
                print(f"    ❌ {subtab_name} - FAILED")
            
            result["subtabs"].append(subtab_result)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        print(f"\n✅ Tab {tab_name} completed in {duration:.2f}s - Status: {result['status']}")
        
        return result
    
    async def run_full_validation(self) -> Dict:
        """Run complete validation"""
        print("🚀 Starting Phase 14B Final Validation")
        print(f"🌐 Dashboard URL: {DASHBOARD_URL}")
        print(f"🗂️  Outputs: {OUTPUTS_DIR}\n")
        
        telemetry = TelemetryDB(OUTPUTS_DIR / "telemetry_final.db")
        
        await self.setup()
        
        all_results = []
        for tab_id, config in TAB_STRUCTURE.items():
            result = await self.validate_tab(tab_id, config, telemetry)
            all_results.append(result)
            
            if result["status"] == "PASS":
                self.results["tabs_passed"] += 1
            else:
                self.results["failures"].append({
                    "tab": tab_id,
                    "errors": result["errors"]
                })
            
            self.results["tabs_tested"] += 1
        
        # Calculate pass rate
        total_items = self.results["tabs_tested"] + self.results["subtabs_tested"]
        total_passed = self.results["tabs_passed"] + self.results["subtabs_passed"]
        
        if total_items > 0:
            self.results["pass_rate"] = (total_passed / total_items) * 100
        
        if self.results["pass_rate"] == 100.0:
            self.results["overall_status"] = "PASS"
        
        self.results["detailed_results"] = all_results
        
        telemetry.close()
        await self.teardown()
        
        return self.results


async def main():
    # Create output directories
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "snapshots").mkdir(exist_ok=True)
    (OUTPUTS_DIR / "remediation").mkdir(exist_ok=True)
    
    validator = Phase14BFinalValidator()
    results = await validator.run_full_validation()
    
    # Save results
    results_file = OUTPUTS_DIR / "phase14b_final_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"📊 PHASE 14B FINAL VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Overall Status: {results['overall_status']}")
    print(f"Pass Rate: {results['pass_rate']:.1f}%")
    print(f"Tabs: {results['tabs_passed']}/{results['tabs_tested']} passed")
    print(f"Subtabs: {results['subtabs_passed']}/{results['subtabs_tested']} passed")
    print(f"Known Issues Resolved: {len(results['known_issues_resolved'])}/4")
    print(f"  - {', '.join(results['known_issues_resolved']) if results['known_issues_resolved'] else 'None resolved'}")
    
    # Generate remediation tickets for remaining failures
    if results['failures']:
        print(f"\n⚠️  Generating remediation tickets for {len(results['failures'])} failures...")
        ticket_file = OUTPUTS_DIR / "remediation" / "CONSOLIDATED_REMEDIATION_TICKET.md"
        
        with open(ticket_file, 'w') as f:
            f.write("# Phase 14B Final Remediation Ticket\n\n")
            f.write(f"**Timestamp:** {datetime.utcnow().isoformat()}\n")
            f.write(f"**Pass Rate:** {results['pass_rate']:.1f}%\n\n")
            
            for failure in results['failures']:
                f.write(f"## ❌ {failure['tab']}\n\n")
                f.write("**Errors:**\n")
                for error in failure['errors']:
                    f.write(f"- {error}\n")
                f.write("\n")
            
            f.write("## Suggested Fixes\n\n")
            f.write("1. Verify all subtab IDs match actual layout definitions\n")
            f.write("2. Check if subtabs are dynamically loaded\n")
            f.write("3. Increase timeout if network latency is high\n")
            f.write("4. Review console errors for JavaScript issues\n")
        
        print(f"📋 Remediation ticket: {ticket_file}")
    
    return 0 if results["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
