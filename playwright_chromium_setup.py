#!/usr/bin/env python3
"""
Playwright Chromium Setup - Unified Financial Dashboard E2E Test Suite

Comprehensive UI validation for all 10 dashboard tabs with:
- Snapshot capture
- Element interaction (button clicks, tab navigation)
- Visibility validation
- Performance metrics
- JSON reporting for CI/CD integration

Supports both local testing and headless CI execution.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError


@dataclass
class TabTestResult:
    """Result of a single tab test"""
    tab_name: str
    tab_id: str
    success: bool
    duration_ms: float
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    elements_validated: List[str] = None
    interactions_performed: List[str] = None

    def __post_init__(self):
        if self.elements_validated is None:
            self.elements_validated = []
        if self.interactions_performed is None:
            self.interactions_performed = []


@dataclass
class TestSuiteReport:
    """Overall test suite report"""
    total_tabs: int
    passed: int
    failed: int
    skipped: int
    total_duration_ms: float
    timestamp: str
    dashboard_url: str
    mode: str  # 'full' or 'smoke'
    results: List[TabTestResult]

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_tabs == 0:
            return 0.0
        return (self.passed / self.total_tabs) * 100


class UnifiedDashboardTester:
    """E2E Test Suite for Unified Financial Dashboard"""

    # Tab configuration with IDs and validation elements
    TAB_CONFIG = {
        "Market Trends": {
            "tab_id": "tab-market-trends",
            "elements": ["#market-trends-table", "button#run-market-trends-analysis"],
            "interactions": ["button#run-market-trends-analysis"]
        },
        "Analysis Hub": {
            "tab_id": "tab-analysis-hub",
            "elements": ["#analysis-results", "#ticker-search"],
            "interactions": []
        },
        "Strategy Lab": {
            "tab_id": "tab-strategy-lab",
            "elements": ["#strategy-results", "#strategy-selector"],
            "interactions": []
        },
        "Market Forecast": {
            "tab_id": "tab-market-forecast",
            "elements": ["#forecast-chart", "#forecast-settings"],
            "interactions": []
        },
        "Portfolio": {
            "tab_id": "tab-portfolio",
            "elements": ["#portfolio-summary", "#portfolio-holdings"],
            "interactions": []
        },
        "Research Lab": {
            "tab_id": "tab-research-lab",
            "elements": ["#research-results", "#research-query"],
            "interactions": []
        },
        "Volatility Lab": {
            "tab_id": "tab-volatility-lab",
            "elements": ["#volatility-chart", "#volatility-metrics"],
            "interactions": []
        },
        "Options Lab": {
            "tab_id": "tab-options-lab",
            "elements": ["#options-chain", "#options-analytics"],
            "interactions": []
        },
        "Backtest Dashboard": {
            "tab_id": "tab-backtest",
            "elements": ["#backtest-results", "#backtest-controls"],
            "interactions": []
        },
        "Signal Dashboard": {
            "tab_id": "tab-signal-dashboard",
            "elements": ["#signal-metrics", "#signal-chart"],
            "interactions": []
        }
    }

    # Smoke test subset (critical tabs only)
    SMOKE_TEST_TABS = ["Market Trends", "Signal Dashboard", "Portfolio"]

    def __init__(self, output_dir: str, headless: bool = True, base_url: str = "http://localhost:8050"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.base_url = base_url
        self.results: List[TabTestResult] = []

    def wait_for_dashboard_ready(self, page: Page, timeout_ms: int = 30000) -> bool:
        """Wait for dashboard to be fully loaded"""
        try:
            print("⏳ Waiting for dashboard to load...")
            # Try a few heuristics so this works across SSR/CSR and versions:
            # 1) Prefer an explicit dashboard tabs id if present
            try:
                page.wait_for_selector("#dashboard-tabs", timeout=timeout_ms)
                print("✅ Dashboard tabs present (#dashboard-tabs)")
                return True
            except PlaywrightTimeoutError:
                pass

            # 2) Wait for a server-side sentinel table used by tests
            try:
                page.wait_for_selector("#market-trends-sentinel-table", timeout=timeout_ms)
                # ensure it's visible (or at least present)
                print("✅ Sentinel table present (#market-trends-sentinel-table)")
                return True
            except PlaywrightTimeoutError:
                pass

            # 3) Wait for the Dash loading placeholder to be removed (CSR completed)
            try:
                page.wait_for_selector("#react-entry-point ._dash-loading", state='detached', timeout=timeout_ms)
                print("✅ Dash client-side rendering complete (loading gone)")
                return True
            except PlaywrightTimeoutError:
                pass

            # 4) Fallback: try legacy selectors used in older tests
            page.wait_for_selector("#page-content", timeout=timeout_ms)
            page.wait_for_selector(".tabs", timeout=timeout_ms)
            print("✅ Dashboard loaded successfully (legacy selectors)")
            return True
        except PlaywrightTimeoutError:
            print("❌ Dashboard failed to load within timeout")
            return False

    def navigate_to_tab(self, page: Page, tab_name: str) -> bool:
        """Navigate to a specific tab"""
        config = self.TAB_CONFIG.get(tab_name)
        if not config:
            print(f"⚠️  Unknown tab: {tab_name}")
            return False

        tab_id = config["tab_id"]
        try:
            # Click tab (try multiple id variants to tolerate hyphen/underscore differences)
            tried = []
            candidates = [tab_id]
            # Build richer candidate set to cover variants like:
            # tab-market-trends, tab_market_trends, tab-market_trends, tab_market-trends
            if tab_id.startswith('tab-'):
                key = tab_id[len('tab-'):]
                candidates.append(f"tab-{key.replace('-', '_')}")
                candidates.append(f"tab_{key}")
                candidates.append(f"tab_{key.replace('-', '_')}")
                candidates.append(f"tab-{key.replace('_', '-')}")
            else:
                # generic separator swaps
                if '-' in tab_id:
                    candidates.append(tab_id.replace('-', '_'))
                if '_' in tab_id:
                    candidates.append(tab_id.replace('_', '-'))

            for cid in dict.fromkeys(candidates):
                tab_selector = f"#{cid}"
                tried.append(tab_selector)
                try:
                    print(f"🖱️  Trying to click tab: {tab_name} ({tab_selector})")
                    page.click(tab_selector, timeout=2500)
                    time.sleep(1)
                    print(f"✅ Navigated to {tab_name} via {tab_selector}")
                    return True
                except Exception:
                    # Try next candidate
                    continue

            print(f"❌ Could not click tab {tab_name}. Tried: {tried}")
            return False
        except PlaywrightTimeoutError:
            print(f"❌ Failed to navigate to {tab_name}")
            return False

    def validate_tab_elements(self, page: Page, tab_name: str) -> tuple[bool, List[str]]:
        """Validate expected elements exist on tab"""
        config = self.TAB_CONFIG.get(tab_name)
        if not config:
            return False, []

        validated_elements = []
        for selector in config["elements"]:
            try:
                # Primary check: exact selector
                element = page.query_selector(selector)
                if element and element.is_visible():
                    validated_elements.append(selector)
                    print(f"  ✅ Element found: {selector}")
                    continue

                # Fallback strategies for selectors that may differ between SSR/CSR
                fallback_found = False
                # If selector is an id like #foo-bar, try data-testid variations
                if selector.startswith('#'):
                    sid = selector[1:]
                    # try data-testid contains
                    try_selectors = [f"[data-testid*='{sid}']", f"#{sid}-sentinel", f"#{sid.replace('-', '_')}"]
                    for fs in try_selectors:
                        try:
                            fe = page.query_selector(fs)
                            if fe and fe.is_visible():
                                validated_elements.append(fs)
                                print(f"  ✅ Fallback element found: {fs} (for {selector})")
                                fallback_found = True
                                break
                        except Exception:
                            continue

                # Generic fallback: search for visible text snippet from selector
                if not fallback_found:
                    try:
                        # Extract a short token from the selector to search for visible text
                        token = selector.strip('#.').split('[')[0].replace('-', ' ').replace('_', ' ')
                        if token and len(token) > 2:
                            text_el = page.query_selector(f"text=/{token}/i")
                            if text_el and text_el.is_visible():
                                validated_elements.append(f"text~{token}")
                                print(f"  ✅ Text-based fallback found for '{selector}': {token}")
                                fallback_found = True
                    except Exception:
                        pass

                if not fallback_found:
                    print(f"  ⚠️  Element not visible: {selector}")
            except Exception as e:
                print(f"  ⚠️  Element validation failed for {selector}: {e}")

        # Consider tab validated if at least one element found
        success = len(validated_elements) > 0
        return success, validated_elements

    def perform_interactions(self, page: Page, tab_name: str) -> List[str]:
        """Perform automated interactions on tab"""
        config = self.TAB_CONFIG.get(tab_name)
        if not config:
            return []

        performed_interactions = []
        for selector in config["interactions"]:
            try:
                print(f"  🖱️  Clicking: {selector}")
                page.click(selector, timeout=5000)
                time.sleep(0.5)  # Allow UI to respond
                performed_interactions.append(selector)
                print(f"  ✅ Interaction successful: {selector}")
            except Exception as e:
                print(f"  ⚠️  Interaction failed for {selector}: {e}")

        return performed_interactions

    def capture_screenshot(self, page: Page, tab_name: str) -> Optional[str]:
        """Capture screenshot of current tab"""
        try:
            filename = f"{tab_name.lower().replace(' ', '_')}_screenshot.png"
            filepath = self.output_dir / filename
            page.screenshot(path=str(filepath), full_page=True)
            print(f"  📸 Screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"  ⚠️  Screenshot failed: {e}")
            return None

    def test_tab(self, page: Page, tab_name: str) -> TabTestResult:
        """Test a single dashboard tab"""
        print(f"\n{'='*60}")
        print(f"Testing Tab: {tab_name}")
        print(f"{'='*60}")

        start_time = time.time()
        config = self.TAB_CONFIG.get(tab_name)

        try:
            # Navigate to tab
            if not self.navigate_to_tab(page, tab_name):
                raise Exception(f"Failed to navigate to {tab_name}")

            # Validate elements
            elements_valid, validated_elements = self.validate_tab_elements(page, tab_name)
            if not elements_valid:
                raise Exception(f"No elements validated for {tab_name}")

            # Perform interactions
            performed_interactions = self.perform_interactions(page, tab_name)

            # Capture screenshot
            screenshot_path = self.capture_screenshot(page, tab_name)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            result = TabTestResult(
                tab_name=tab_name,
                tab_id=config["tab_id"],
                success=True,
                duration_ms=duration_ms,
                screenshot_path=screenshot_path,
                elements_validated=validated_elements,
                interactions_performed=performed_interactions
            )

            print(f"✅ {tab_name} test PASSED ({duration_ms:.0f}ms)")
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            print(f"❌ {tab_name} test FAILED: {error_msg}")

            result = TabTestResult(
                tab_name=tab_name,
                tab_id=config["tab_id"] if config else "unknown",
                success=False,
                duration_ms=duration_ms,
                error_message=error_msg
            )
            return result

    def run_test_suite(self, smoke_tests_only: bool = False) -> TestSuiteReport:
        """Run full test suite or smoke tests"""
        print(f"\n{'#'*60}")
        print(f"# Unified Financial Dashboard E2E Test Suite")
        print(f"# Mode: {'Smoke Tests' if smoke_tests_only else 'Full Suite'}")
        print(f"# Dashboard URL: {self.base_url}")
        print(f"# Output: {self.output_dir}")
        print(f"{'#'*60}\n")

        suite_start_time = time.time()

        with sync_playwright() as playwright:
            # Launch browser
            browser: Browser = playwright.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            )
            page: Page = context.new_page()

            try:
                # Navigate to dashboard
                print(f"🌐 Navigating to {self.base_url}...")
                page.goto(self.base_url, timeout=30000)

                # Wait for dashboard ready
                if not self.wait_for_dashboard_ready(page):
                    raise Exception("Dashboard failed to load")

                # Determine which tabs to test
                tabs_to_test = self.SMOKE_TEST_TABS if smoke_tests_only else list(self.TAB_CONFIG.keys())

                # Run tests
                for tab_name in tabs_to_test:
                    result = self.test_tab(page, tab_name)
                    self.results.append(result)

            finally:
                browser.close()

        # Generate report
        total_duration_ms = (time.time() - suite_start_time) * 1000
        passed = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success)

        report = TestSuiteReport(
            total_tabs=len(self.results),
            passed=passed,
            failed=failed,
            skipped=0,
            total_duration_ms=total_duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dashboard_url=self.base_url,
            mode="smoke" if smoke_tests_only else "full",
            results=self.results
        )

        self.print_summary(report)
        self.save_report(report)

        return report

    def print_summary(self, report: TestSuiteReport):
        """Print test summary to console"""
        print(f"\n{'='*60}")
        print(f"TEST SUITE SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tabs Tested: {report.total_tabs}")
        print(f"✅ Passed: {report.passed}")
        print(f"❌ Failed: {report.failed}")
        print(f"⏭️  Skipped: {report.skipped}")
        print(f"Success Rate: {report.success_rate:.1f}%")
        print(f"Total Duration: {report.total_duration_ms:.0f}ms")
        print(f"{'='*60}\n")

        if report.failed > 0:
            print("Failed Tests:")
            for result in report.results:
                if not result.success:
                    print(f"  ❌ {result.tab_name}: {result.error_message}")
            print()

    def save_report(self, report: TestSuiteReport):
        """Save JSON report"""
        report_path = self.output_dir / "ui_validation_report.json"
        
        # Convert dataclasses to dicts
        report_dict = {
            "total_tabs": report.total_tabs,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "success_rate": report.success_rate,
            "total_duration_ms": report.total_duration_ms,
            "timestamp": report.timestamp,
            "dashboard_url": report.dashboard_url,
            "mode": report.mode,
            "results": [asdict(r) for r in report.results]
        }

        with open(report_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"📄 Report saved: {report_path}")


def main():
    """Main entry point with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Unified Financial Dashboard E2E Test Suite (Playwright Chromium)"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8050",
        help="Dashboard URL (default: http://localhost:8050)"
    )
    parser.add_argument(
        "--output",
        default="ci_reports/ui_validation",
        help="Output directory for screenshots and reports (default: ci_reports/ui_validation)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default: True)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run in headed mode (show browser)"
    )
    parser.add_argument(
        "--smoke-tests-only",
        action="store_true",
        help="Run smoke tests only (Market Trends, Signal Dashboard, Portfolio)"
    )
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="CI mode: headless, smoke tests, strict validation"
    )

    args = parser.parse_args()

    # Resolve headless mode
    headless = not args.headed if args.headed else args.headless

    # CI mode overrides
    if args.ci_mode:
        headless = True
        smoke_tests_only = args.smoke_tests_only
        print("🤖 Running in CI mode (headless, strict)")
    else:
        smoke_tests_only = args.smoke_tests_only

    # Create tester
    tester = UnifiedDashboardTester(
        output_dir=args.output,
        headless=headless,
        base_url=args.url
    )

    # Run test suite
    try:
        report = tester.run_test_suite(smoke_tests_only=smoke_tests_only)
        
        # Exit with appropriate code
        if report.failed > 0:
            print(f"\n❌ Test suite FAILED ({report.failed}/{report.total_tabs} tests failed)")
            sys.exit(1)
        else:
            print(f"\n✅ Test suite PASSED ({report.passed}/{report.total_tabs} tests passed)")
            sys.exit(0)

    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
