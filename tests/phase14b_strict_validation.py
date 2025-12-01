#!/usr/bin/env python3
"""
PHASE 14B: STRICT DASHBOARD UI & SUBTAB VALIDATION (PORT 8051)

Requirements:
- 100% tab/subtab coverage or documented remediation tickets
- Full-page screenshots (1920x1080)
- DOM JSON dumps
- Console + Network HAR logs
- Telemetry database logging
- Known issue inspection (TradingView, Options Forecast, Azure ML, Portfolio Snapshot)
- 5s timeout for subtabs, 3 retry attempts
- Max 8 iterations for auto-fix loop
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import async_playwright, Browser, Page, TimeoutError

# Configuration
DASHBOARD_URL = "http://localhost:8050"  # NOTE: Dashboard currently running on 8050, not 8051 as in spec
OUTPUTS_DIR = Path("outputs/phase14b")
ACTION_TIMEOUT = 15000  # 15s for tabs
SUBTAB_TIMEOUT = 5000   # 5s for subtabs (strict per user requirement)
NAVIGATION_TIMEOUT = 30000
RETRY_COUNT = 3
MAX_ITERATIONS = 8

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(OUTPUTS_DIR / "execution.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Tab structure based on ENABLED_TABS from Phase 13B + user-specified subtabs
TAB_STRUCTURE = {
    "home_lab": {
        "name": "🏠 Command Center",
        "selector": "#tab-home_lab",
        "subtabs": {},  # Single-page, but must verify Portfolio Snapshot widget
        "known_issues": ["portfolio_snapshot_missing_data"]
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
        "known_issues": ["tradingview_signals_preview_error"]
    },
    "azure_ml_lab": {
        "name": "🤖 Azure ML Lab",
        "selector": "#tab-azure_ml_lab",
        "subtabs": {
            "predictions": "📊 Predictions",
            "performance": "📈 Performance"
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
            "corr": "Correlation",
            "factors": "Factors",
            "charts": "Charts",
            "metrics": "Metrics",
            "scenarios": "Scenarios",
            "alerts": "Alerts"
        }
    },
    "portfolio": {
        "name": "Portfolio",
        "selector": "#tab-portfolio",
        "subtabs": {
            "positions": "Positions",
            "orders": "Order History",
            "snapshot": "Snapshot"  # User-specified
        }
    },
    "options_lab": {
        "name": "💹 Options Lab",
        "selector": "#tab-options_lab",
        "subtabs": {
            "chain-viewer": "📊 Chain Viewer",
            "volatility": "Volatility Lab"  # User-specified
        }
    }
}


class TelemetryDB:
    """SQLite telemetry database for event logging"""
    
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
                details TEXT,
                console_errors INTEGER DEFAULT 0,
                network_errors INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()
    
    def log_event(self, tab: str, subtab: str, action: str, duration_ms: int, 
                  success: bool, details: str = "", console_errors: int = 0, 
                  network_errors: int = 0):
        self.cursor.execute("""
            INSERT INTO events (timestamp, tab, subtab, action, duration_ms, success, 
                              details, console_errors, network_errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            tab,
            subtab or "",
            action,
            duration_ms,
            1 if success else 0,
            details,
            console_errors,
            network_errors
        ))
        self.conn.commit()
    
    def close(self):
        self.conn.close()


class Phase14BValidator:
    """Strict Playwright validator for Phase 14B"""
    
    def __init__(self):
        self.playwright_context = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.telemetry = TelemetryDB(OUTPUTS_DIR / "telemetry.db")
        self.console_errors: List[str] = []
        self.network_errors: List[str] = []
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "FAIL",
            "pass_rate": 0.0,
            "tabs_tested": 0,
            "tabs_passed": 0,
            "tabs_failed": 0,
            "subtabs_tested": 0,
            "subtabs_passed": 0,
            "subtabs_failed": 0,
            "failures": [],
            "remediation_tickets": []
        }
    
    async def setup(self):
        """Initialize browser and page"""
        try:
            self.playwright_context = await async_playwright().start()
            logger.info("  → Playwright context started")
            
            self.browser = await self.playwright_context.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            logger.info("  → Chromium browser launched")
            
            self.page = await self.browser.new_page(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            )
            logger.info("  → New page created")
            
            # Setup console/network listeners
            self.page.on("console", self._handle_console)
            self.page.on("pageerror", self._handle_page_error)
            self.page.on("requestfailed", self._handle_request_failed)
            logger.info("  → Event listeners registered")
            
            # Navigate to dashboard
            logger.info(f"  → Navigating to {DASHBOARD_URL}...")
            await self.page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)
            await self.page.wait_for_selector("#dashboard-tabs", state="visible", timeout=10000)
            
            page_title = await self.page.title()
            logger.info(f"✅ Dashboard loaded: {page_title}")
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise
    
    def _handle_console(self, msg):
        if msg.type in ("error", "warning"):
            error_text = f"[{msg.type.upper()}] {msg.text}"
            self.console_errors.append(error_text)
            logger.warning(f"Console: {error_text}")
    
    def _handle_page_error(self, error):
        error_text = f"[PAGE ERROR] {str(error)}"
        self.console_errors.append(error_text)
        logger.error(error_text)
    
    def _handle_request_failed(self, request):
        error_text = f"[NETWORK FAIL] {request.url} - {request.failure}"
        self.network_errors.append(error_text)
        logger.warning(error_text)
    
    async def teardown(self):
        """Cleanup resources"""
        try:
            if self.page:
                await self.page.close()
                logger.info("  → Page closed")
            if self.browser:
                await self.browser.close()
                logger.info("  → Browser closed")
            if self.playwright_context:
                await self.playwright_context.stop()
                logger.info("  → Playwright context stopped")
            self.telemetry.close()
            logger.info("  → Telemetry DB closed")
        except Exception as e:
            logger.error(f"❌ Teardown error: {e}")
    
    async def navigate_to_tab(self, tab_id: str, tab_name: str, selector: str) -> bool:
        """Navigate to main tab with retry logic"""
        for attempt in range(RETRY_COUNT):
            try:
                await self.page.wait_for_selector("#dashboard-tabs", state="visible", timeout=10000)
                
                selectors = [
                    selector if selector.startswith('#') else f"#{selector}",
                    f"a{selector}" if selector.startswith('#') else f"a#{selector}",
                    f".nav-link:has-text('{tab_name}')"
                ]
                
                for sel in selectors:
                    try:
                        await self.page.click(sel, timeout=ACTION_TIMEOUT)
                        await self.page.wait_for_load_state('domcontentloaded')
                        await asyncio.sleep(2)  # Stabilization
                        logger.info(f"✅ Navigated to tab: {tab_name} (attempt {attempt + 1})")
                        return True
                    except:
                        continue
            except Exception as e:
                if attempt == RETRY_COUNT - 1:
                    logger.error(f"❌ Tab navigation failed after {RETRY_COUNT} attempts: {tab_name}")
                    return False
                await asyncio.sleep(1)
        return False
    
    async def navigate_to_subtab(self, subtab_id: str, subtab_name: str) -> bool:
        """Navigate to subtab with 5s timeout"""
        selectors = [
            f"#{subtab_id}",
            f"button#{subtab_id}",
            f"a#{subtab_id}",
            f"[data-tab-id='{subtab_id}']",
            f".nav-link:has-text('{subtab_name}')"
        ]
        
        for sel in selectors:
            try:
                await self.page.click(sel, timeout=SUBTAB_TIMEOUT)
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(1)
                logger.info(f"  ✅ Navigated to subtab: {subtab_name}")
                return True
            except:
                continue
        
        logger.warning(f"  ⚠️ Could not navigate to subtab: {subtab_name}")
        return False
    
    async def capture_screenshot(self, tab_id: str, subtab_id: Optional[str] = None) -> bool:
        """Capture full-page screenshot"""
        try:
            folder = OUTPUTS_DIR / "snapshots" / tab_id
            folder.mkdir(parents=True, exist_ok=True)
            
            filename = f"{subtab_id}.png" if subtab_id else "main.png"
            filepath = folder / filename
            
            await self.page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"  📸 Screenshot saved: {filename}")
            return True
        except Exception as e:
            logger.error(f"  ❌ Screenshot failed: {e}")
            return False
    
    async def dump_dom(self, tab_id: str, subtab_id: Optional[str] = None) -> bool:
        """Dump DOM to JSON"""
        try:
            folder = OUTPUTS_DIR / "dom" / tab_id
            folder.mkdir(parents=True, exist_ok=True)
            
            filename = f"{subtab_id}.json" if subtab_id else "main.json"
            filepath = folder / filename
            
            dom_content = await self.page.content()
            element_count = await self.page.evaluate("document.querySelectorAll('*').length")
            
            dom_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "tab_id": tab_id,
                "subtab_id": subtab_id,
                "element_count": element_count,
                "html_length": len(dom_content),
                "url": self.page.url
            }
            
            with open(filepath, 'w') as f:
                json.dump(dom_data, f, indent=2)
            
            logger.info(f"  📋 DOM dumped: {filename}")
            return True
        except Exception as e:
            logger.error(f"  ❌ DOM dump failed: {e}")
            return False
    
    async def capture_logs(self, tab_id: str, subtab_id: Optional[str] = None):
        """Save console + network logs"""
        try:
            folder = OUTPUTS_DIR / "logs"
            folder.mkdir(parents=True, exist_ok=True)
            
            name = f"{tab_id}_{subtab_id}" if subtab_id else tab_id
            
            # Console logs
            console_file = folder / f"{name}_console.log"
            with open(console_file, 'w') as f:
                f.write("\n".join(self.console_errors))
            
            # Network errors (HAR would require CDP, using simple log)
            network_file = folder / f"{name}_network.log"
            with open(network_file, 'w') as f:
                f.write("\n".join(self.network_errors))
            
            logger.info(f"  📝 Logs saved for {name}")
        except Exception as e:
            logger.error(f"  ❌ Log capture failed: {e}")
    
    async def test_interactive_elements(self, tab_id: str, subtab_id: Optional[str] = None) -> Dict:
        """Test clickable elements with 3 retries"""
        result = {
            "tested": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # Find all buttons, links, inputs
            elements = await self.page.query_selector_all("button, a.btn, input[type='submit'], .clickable")
            result["tested"] = len(elements)
            
            for idx, elem in enumerate(elements[:10]):  # Test first 10 interactive elements
                for attempt in range(RETRY_COUNT):
                    try:
                        is_visible = await elem.is_visible()
                        if not is_visible:
                            break
                        
                        await elem.click(timeout=3000)
                        await asyncio.sleep(0.5)
                        result["passed"] += 1
                        logger.info(f"    ✅ Clicked element {idx + 1}")
                        break
                    except Exception as e:
                        if attempt == RETRY_COUNT - 1:
                            result["failed"] += 1
                            result["errors"].append(f"Element {idx + 1}: {str(e)}")
        except Exception as e:
            result["errors"].append(f"Interactive test error: {str(e)}")
        
        return result
    
    async def inspect_known_issue(self, tab_id: str, issue_type: str) -> Dict:
        """Inspect specific known issues per user requirements"""
        logger.info(f"  🔍 Inspecting known issue: {issue_type}")
        
        issue_data = {
            "type": issue_type,
            "found": False,
            "details": "",
            "console_errors": [],
            "network_errors": [],
            "dom_snapshot": ""
        }
        
        try:
            if issue_type == "portfolio_snapshot_missing_data":
                # Check Command Center portfolio snapshot widget
                snapshot_selector = "#portfolio-snapshot-widget, .portfolio-snapshot"
                if await self.page.query_selector(snapshot_selector):
                    content = await self.page.text_content(snapshot_selector)
                    issue_data["found"] = True
                    issue_data["details"] = f"Widget found, content length: {len(content)}"
                    issue_data["dom_snapshot"] = content[:500]
            
            elif issue_type == "tradingview_signals_preview_error":
                # Check TradingView signals preview error
                error_selector = "text=/Error fetching preview/i"
                if await self.page.query_selector(error_selector):
                    issue_data["found"] = True
                    issue_data["details"] = "TradingView preview error detected"
            
            elif issue_type == "options_forecast_no_output":
                # Check options forecast rendering
                forecast_selector = "#options-forecast, .options-forecast-output"
                elem = await self.page.query_selector(forecast_selector)
                if elem:
                    text = await elem.text_content()
                    issue_data["found"] = True
                    issue_data["details"] = f"Forecast element exists, text length: {len(text)}"
            
            elif issue_type == "buttons_not_responding":
                # Test Azure ML Lab buttons
                button_selector = "#azure-ml-lab button"
                buttons = await self.page.query_selector_all(button_selector)
                issue_data["found"] = len(buttons) > 0
                issue_data["details"] = f"Found {len(buttons)} buttons in Azure ML Lab"
            
            issue_data["console_errors"] = self.console_errors.copy()
            issue_data["network_errors"] = self.network_errors.copy()
            
        except Exception as e:
            issue_data["details"] = f"Inspection error: {str(e)}"
        
        return issue_data
    
    async def generate_remediation_ticket(self, tab_id: str, subtab_id: Optional[str], 
                                         failure_reason: str, issue_data: Optional[Dict] = None):
        """Generate detailed remediation ticket"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        name = f"{tab_id}_{subtab_id}" if subtab_id else tab_id
        ticket_file = OUTPUTS_DIR / "remediation" / f"{name}_{timestamp}.md"
        
        ticket_content = f"""# Remediation Ticket: {name}

**Timestamp:** {datetime.utcnow().isoformat()}  
**Tab:** {tab_id}  
**Subtab:** {subtab_id or "N/A"}  
**Failure Reason:** {failure_reason}

## Console Errors
```
{chr(10).join(self.console_errors[-10:]) if self.console_errors else "None"}
```

## Network Errors
```
{chr(10).join(self.network_errors[-10:]) if self.network_errors else "None"}
```

## Issue Data
```json
{json.dumps(issue_data, indent=2) if issue_data else "{}"}
```

## Screenshots
- Full-page: `outputs/phase14b/snapshots/{tab_id}/{subtab_id or 'main'}.png`
- DOM JSON: `outputs/phase14b/dom/{tab_id}/{subtab_id or 'main'}.json`

## Suggested Fix
1. Review console errors for JavaScript exceptions
2. Check network logs for failed API calls
3. Verify component IDs match expected selectors
4. Test interactive elements manually in browser

## Telemetry Query
```sql
SELECT * FROM events 
WHERE tab = '{tab_id}' AND subtab = '{subtab_id or ""}'
ORDER BY timestamp DESC LIMIT 10;
```
"""
        
        with open(ticket_file, 'w') as f:
            f.write(ticket_content)
        
        logger.info(f"  📋 Remediation ticket created: {ticket_file.name}")
        self.results["remediation_tickets"].append(str(ticket_file))
    
    async def validate_tab(self, tab_id: str, config: Dict) -> Dict:
        """Complete validation of a single tab"""
        start_time = datetime.utcnow()
        tab_name = config["name"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📍 Testing Tab: {tab_name} ({tab_id})")
        logger.info(f"{'='*60}")
        
        result = {
            "tab_id": tab_id,
            "tab_name": tab_name,
            "status": "PASS",
            "subtabs": [],
            "errors": [],
            "known_issues_inspected": []
        }
        
        # Clear error buffers
        self.console_errors = []
        self.network_errors = []
        
        # Navigate to tab
        selector = config.get("selector", f"#tab-{tab_id}")
        if not await self.navigate_to_tab(tab_id, tab_name, selector):
            result["status"] = "FAIL"
            result["errors"].append(f"Could not navigate to tab: {tab_name}")
            await self.generate_remediation_ticket(tab_id, None, "Tab navigation failed")
            return result
        
        # Main tab validations
        await self.capture_screenshot(tab_id)
        await self.dump_dom(tab_id)
        await self.capture_logs(tab_id)
        
        interactive_result = await self.test_interactive_elements(tab_id)
        if interactive_result["failed"] > 0:
            result["errors"].append(f"Interactive elements failed: {interactive_result['failed']}")
        
        # Inspect known issues
        known_issues = config.get("known_issues", [])
        for issue_type in known_issues:
            issue_data = await self.inspect_known_issue(tab_id, issue_type)
            result["known_issues_inspected"].append(issue_data)
            if issue_data["found"]:
                await self.generate_remediation_ticket(tab_id, None, f"Known issue: {issue_type}", issue_data)
        
        # Test subtabs
        subtabs = config.get("subtabs", {})
        self.results["subtabs_tested"] += len(subtabs)
        
        for subtab_id, subtab_name in subtabs.items():
            logger.info(f"\n  📂 Subtab: {subtab_name}")
            
            subtab_result = {
                "subtab_id": subtab_id,
                "subtab_name": subtab_name,
                "status": "PASS",
                "errors": []
            }
            
            # Navigate to subtab
            if await self.navigate_to_subtab(subtab_id, subtab_name):
                await self.capture_screenshot(tab_id, subtab_id)
                await self.dump_dom(tab_id, subtab_id)
                await self.capture_logs(tab_id, subtab_id)
                
                interactive_result = await self.test_interactive_elements(tab_id, subtab_id)
                if interactive_result["failed"] > 0:
                    subtab_result["status"] = "FAIL"
                    subtab_result["errors"].append(f"Interactive test failures: {interactive_result['failed']}")
                    result["status"] = "FAIL"
                    self.results["subtabs_failed"] += 1
                    await self.generate_remediation_ticket(tab_id, subtab_id, "Interactive element failures", interactive_result)
                else:
                    self.results["subtabs_passed"] += 1
                
                # Log telemetry
                self.telemetry.log_event(
                    tab_id, subtab_id, "validate", 
                    (datetime.utcnow() - start_time).seconds * 1000,
                    subtab_result["status"] == "PASS",
                    json.dumps(subtab_result),
                    len(self.console_errors),
                    len(self.network_errors)
                )
            else:
                subtab_result["status"] = "FAIL"
                subtab_result["errors"].append(f"Could not navigate to subtab: {subtab_name}")
                result["status"] = "FAIL"
                self.results["subtabs_failed"] += 1
                await self.generate_remediation_ticket(tab_id, subtab_id, "Subtab navigation failed")
            
            result["subtabs"].append(subtab_result)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"\n✅ Tab {tab_name} completed in {duration:.2f}s - Status: {result['status']}")
        
        return result
    
    async def run_full_validation(self) -> Dict:
        """Run complete validation of all tabs"""
        logger.info("🚀 Starting Phase 14B Strict Validation")
        logger.info(f"🌐 Dashboard URL: {DASHBOARD_URL}")
        logger.info(f"🗂️  Outputs: {OUTPUTS_DIR}\n")
        
        await self.setup()
        
        all_results = []
        for tab_id, config in TAB_STRUCTURE.items():
            result = await self.validate_tab(tab_id, config)
            all_results.append(result)
            
            if result["status"] == "PASS":
                self.results["tabs_passed"] += 1
            else:
                self.results["tabs_failed"] += 1
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
        
        # Determine overall status
        if self.results["pass_rate"] == 100.0:
            self.results["overall_status"] = "PASS"
        elif len(self.results["remediation_tickets"]) >= self.results["tabs_failed"] + self.results["subtabs_failed"]:
            self.results["overall_status"] = "PASS_WITH_TICKETS"
        else:
            self.results["overall_status"] = "FAIL"
        
        self.results["detailed_results"] = all_results
        
        await self.teardown()
        
        return self.results


async def main():
    """Main execution with auto-retry loop"""
    validator = Phase14BValidator()
    
    iteration = 1
    max_iterations = MAX_ITERATIONS
    
    while iteration <= max_iterations:
        logger.info(f"\n{'#'*70}")
        logger.info(f"# ITERATION {iteration}/{max_iterations}")
        logger.info(f"{'#'*70}\n")
        
        results = await validator.run_full_validation()
        
        # Save results
        results_file = OUTPUTS_DIR / "results" / f"phase14b_results_iter{iteration}.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 ITERATION {iteration} SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Overall Status: {results['overall_status']}")
        logger.info(f"Pass Rate: {results['pass_rate']:.1f}%")
        logger.info(f"Tabs: {results['tabs_passed']}/{results['tabs_tested']} passed")
        logger.info(f"Subtabs: {results['subtabs_passed']}/{results['subtabs_tested']} passed")
        logger.info(f"Remediation Tickets: {len(results['remediation_tickets'])}")
        
        # Check if we achieved success
        if results["overall_status"] in ("PASS", "PASS_WITH_TICKETS"):
            logger.info(f"\n✅ Phase 14B validation SUCCESSFUL after {iteration} iteration(s)!")
            
            # Generate final report
            report_file = OUTPUTS_DIR / "reports" / f"PHASE14B_UI_VALIDATION_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_file, 'w') as f:
                f.write(f"""# Phase 14B UI Validation Report

**Timestamp:** {datetime.utcnow().isoformat()}  
**Iteration:** {iteration}/{max_iterations}  
**Overall Status:** {results['overall_status']}  
**Pass Rate:** {results['pass_rate']:.1f}%

## Summary
- **Tabs Tested:** {results['tabs_tested']}
- **Tabs Passed:** {results['tabs_passed']}
- **Subtabs Tested:** {results['subtabs_tested']}
- **Subtabs Passed:** {results['subtabs_passed']}
- **Remediation Tickets:** {len(results['remediation_tickets'])}

## Artifacts
- Screenshots: `outputs/phase14b/snapshots/`
- DOM Dumps: `outputs/phase14b/dom/`
- Logs: `outputs/phase14b/logs/`
- Telemetry: `outputs/phase14b/telemetry.db`
- Remediation: `outputs/phase14b/remediation/`

## Failures
{chr(10).join([f"- {f['tab']}: {', '.join(f['errors'])}" for f in results['failures']])}

## Next Steps
{'All validations passed!' if results['overall_status'] == 'PASS' else 'Review remediation tickets for persistent failures.'}
""")
            
            logger.info(f"📄 Final report: {report_file}")
            break
        
        if iteration == max_iterations:
            logger.error(f"\n❌ Phase 14B validation did not achieve 100% pass after {max_iterations} iterations")
            logger.error(f"Final pass rate: {results['pass_rate']:.1f}%")
            
            # Generate escalation report
            escalation_file = OUTPUTS_DIR / "reports" / f"ESCALATION_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
            with open(escalation_file, 'w') as f:
                f.write(f"""# Phase 14B Escalation Report

**Status:** FAILED TO ACHIEVE 100% PASS  
**Final Pass Rate:** {results['pass_rate']:.1f}%  
**Iterations Attempted:** {max_iterations}

## Failures ({len(results['failures'])})

{chr(10).join([f"### {f['tab']}{chr(10)}```{chr(10)}{chr(10).join(f['errors'])}{chr(10)}```{chr(10)}" for f in results['failures']])}

## Remediation Tickets
{chr(10).join([f"- {ticket}" for ticket in results['remediation_tickets']])}

## Recommended Actions
1. Review all remediation tickets
2. Fix server-side component issues
3. Verify API endpoints are functional
4. Re-run validation after fixes applied
""")
            
            logger.error(f"📄 Escalation report: {escalation_file}")
            break
        
        logger.warning(f"\n⚠️ Iteration {iteration} incomplete - retrying...")
        iteration += 1
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
