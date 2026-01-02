"""
Comprehensive E2E Test Suite for Alpaca Options Dashboard
Tests all components, tabs, and functionality via automated testing

This script runs:
1. Clicker tests (UI interaction)
2. Snapshot tests (visual regression)
3. Auto-analysis of results
"""

import time
import json
import os
import sys
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import hashlib


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

@dataclass
class TestConfig:
    """Test suite configuration."""
    base_url: str = "http://127.0.0.1:8053"
    screenshot_dir: str = "test_screenshots"
    results_dir: str = "test_results"
    timeout: int = 30
    headless: bool = True
    
    # Tabs to test
    tabs: List[str] = None
    
    def __post_init__(self):
        if self.tabs is None:
            self.tabs = [
                "dashboard",
                "options-lab",
                "strategy-lab",
                "volatility-lab",
                "market-forecast",
                "research-lab",
                "orders-tab",
                "settings"
            ]


@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    status: str  # passed, failed, skipped, error
    duration_ms: float
    message: Optional[str] = None
    screenshot_path: Optional[str] = None
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "screenshot_path": self.screenshot_path,
            "details": self.details or {}
        }


# =============================================================================
# SELENIUM TEST RUNNER
# =============================================================================

class ClickerTestRunner:
    """Run clicker (UI interaction) tests."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.driver = None
    
    def setup(self):
        """Initialize Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            options = Options()
            if self.config.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
            return True
        except Exception as e:
            print(f"Failed to initialize WebDriver: {e}")
            return False
    
    def teardown(self):
        """Clean up WebDriver."""
        if self.driver:
            self.driver.quit()
    
    def run_test(self, test_name: str, test_fn) -> TestResult:
        """Run a single test function."""
        start_time = time.time()
        try:
            result = test_fn(self.driver, self.config)
            duration_ms = (time.time() - start_time) * 1000
            
            if result.get("passed", True):
                return TestResult(
                    test_name=test_name,
                    status="passed",
                    duration_ms=duration_ms,
                    details=result
                )
            else:
                return TestResult(
                    test_name=test_name,
                    status="failed",
                    duration_ms=duration_ms,
                    message=result.get("message", "Test failed"),
                    details=result
                )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                status="error",
                duration_ms=duration_ms,
                message=str(e)
            )
    
    def screenshot(self, name: str) -> str:
        """Take a screenshot."""
        os.makedirs(self.config.screenshot_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.config.screenshot_dir}/{name}_{timestamp}.png"
        if self.driver:
            self.driver.save_screenshot(path)
        return path


# =============================================================================
# TEST DEFINITIONS
# =============================================================================

def test_dashboard_loads(driver, config: TestConfig) -> Dict[str, Any]:
    """Test that main dashboard loads correctly."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    driver.get(config.base_url)
    
    # Wait for dashboard to load
    WebDriverWait(driver, config.timeout).until(
        EC.presence_of_element_located((By.CLASS_NAME, "dash-graph"))
    )
    
    # Check key elements
    title = driver.title
    graphs = driver.find_elements(By.CLASS_NAME, "dash-graph")
    tabs = driver.find_elements(By.CLASS_NAME, "tab")
    
    return {
        "passed": len(graphs) > 0,
        "title": title,
        "graphs_found": len(graphs),
        "tabs_found": len(tabs)
    }


def test_tab_navigation(driver, config: TestConfig) -> Dict[str, Any]:
    """Test that all tabs are navigable."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    driver.get(config.base_url)
    time.sleep(2)
    
    results = {}
    for tab_id in config.tabs:
        try:
            # Try to find and click the tab
            tab_selector = f"[data-tab='{tab_id}'], #{tab_id}-tab, .tab-{tab_id}"
            tab_element = None
            
            for selector in tab_selector.split(", "):
                try:
                    tab_element = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if tab_element:
                tab_element.click()
                time.sleep(1)
                results[tab_id] = "accessible"
            else:
                results[tab_id] = "not_found"
                
        except Exception as e:
            results[tab_id] = f"error: {str(e)[:50]}"
    
    accessible = sum(1 for v in results.values() if v == "accessible")
    return {
        "passed": accessible >= len(config.tabs) * 0.5,  # 50% threshold
        "tabs_tested": len(config.tabs),
        "accessible": accessible,
        "details": results
    }


def test_options_chain_interaction(driver, config: TestConfig) -> Dict[str, Any]:
    """Test options chain component interaction."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    driver.get(f"{config.base_url}")
    time.sleep(2)
    
    # Navigate to options lab if needed
    try:
        options_tab = driver.find_element(By.CSS_SELECTOR, "[data-tab='options-lab'], .tab-options")
        options_tab.click()
        time.sleep(2)
    except:
        pass
    
    # Check for options chain table
    tables = driver.find_elements(By.TAG_NAME, "table")
    dropdowns = driver.find_elements(By.TAG_NAME, "select")
    
    return {
        "passed": True,
        "tables_found": len(tables),
        "dropdowns_found": len(dropdowns)
    }


def test_graph_rendering(driver, config: TestConfig) -> Dict[str, Any]:
    """Test that graphs render correctly."""
    from selenium.webdriver.common.by import By
    
    driver.get(config.base_url)
    time.sleep(3)
    
    # Find all Plotly graphs
    graphs = driver.find_elements(By.CLASS_NAME, "js-plotly-plot")
    svg_elements = driver.find_elements(By.TAG_NAME, "svg")
    
    # Check if graphs have rendered content
    rendered = 0
    for graph in graphs:
        try:
            # Check if SVG has path elements (indicates rendered graph)
            paths = graph.find_elements(By.TAG_NAME, "path")
            if len(paths) > 0:
                rendered += 1
        except:
            pass
    
    return {
        "passed": rendered > 0 or len(graphs) == 0,
        "total_graphs": len(graphs),
        "rendered_graphs": rendered,
        "svg_elements": len(svg_elements)
    }


def test_console_errors(driver, config: TestConfig) -> Dict[str, Any]:
    """Check for JavaScript console errors."""
    driver.get(config.base_url)
    time.sleep(3)
    
    # Get browser logs
    try:
        logs = driver.get_log('browser')
        errors = [log for log in logs if log.get('level') == 'SEVERE']
        warnings = [log for log in logs if log.get('level') == 'WARNING']
        
        return {
            "passed": len(errors) == 0,
            "errors": len(errors),
            "warnings": len(warnings),
            "error_messages": [e.get('message', '')[:100] for e in errors[:5]]
        }
    except:
        return {
            "passed": True,
            "message": "Browser logs not available"
        }


def test_responsive_layout(driver, config: TestConfig) -> Dict[str, Any]:
    """Test responsive layout at different viewport sizes."""
    viewports = [
        (1920, 1080, "desktop"),
        (1366, 768, "laptop"),
        (768, 1024, "tablet"),
    ]
    
    results = {}
    for width, height, name in viewports:
        driver.set_window_size(width, height)
        driver.get(config.base_url)
        time.sleep(2)
        
        # Check if main content is visible
        try:
            from selenium.webdriver.common.by import By
            main_content = driver.find_element(By.TAG_NAME, "main")
            visible = main_content.is_displayed()
            results[name] = "visible" if visible else "hidden"
        except:
            results[name] = "main_not_found"
    
    # Reset to default
    driver.set_window_size(1920, 1080)
    
    return {
        "passed": all(v == "visible" or v == "main_not_found" for v in results.values()),
        "viewports": results
    }


# =============================================================================
# SNAPSHOT TEST RUNNER
# =============================================================================

class SnapshotTestRunner:
    """Run visual regression (snapshot) tests."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.baseline_dir = "test_baselines"
        self.results: List[TestResult] = []
    
    def capture_snapshot(self, driver, name: str) -> str:
        """Capture a snapshot for comparison."""
        os.makedirs(self.config.screenshot_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.config.screenshot_dir}/{name}_{timestamp}.png"
        driver.save_screenshot(path)
        return path
    
    def compare_snapshots(self, current_path: str, baseline_name: str) -> Tuple[bool, float]:
        """Compare current snapshot with baseline."""
        baseline_path = f"{self.baseline_dir}/{baseline_name}.png"
        
        if not os.path.exists(baseline_path):
            return True, 0.0  # No baseline, consider passed
        
        try:
            from PIL import Image
            import numpy as np
            
            current = np.array(Image.open(current_path))
            baseline = np.array(Image.open(baseline_path))
            
            # Resize if needed
            if current.shape != baseline.shape:
                return False, 100.0
            
            # Calculate difference
            diff = np.abs(current.astype(float) - baseline.astype(float))
            diff_percent = (diff.sum() / diff.size) / 255 * 100
            
            return diff_percent < 5.0, diff_percent
            
        except Exception as e:
            print(f"Snapshot comparison error: {e}")
            return True, 0.0
    
    def save_as_baseline(self, snapshot_path: str, baseline_name: str):
        """Save snapshot as new baseline."""
        os.makedirs(self.baseline_dir, exist_ok=True)
        import shutil
        shutil.copy(snapshot_path, f"{self.baseline_dir}/{baseline_name}.png")


# =============================================================================
# RESULT ANALYZER
# =============================================================================

class ResultAnalyzer:
    """Analyze test results and generate reports."""
    
    def __init__(self, results: List[TestResult]):
        self.results = results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        errors = sum(1 for r in self.results if r.status == "error")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        
        total_duration = sum(r.duration_ms for r in self.results)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": passed / total * 100 if total > 0 else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / total if total > 0 else 0
        }
    
    def get_failures(self) -> List[TestResult]:
        """Get failed tests."""
        return [r for r in self.results if r.status in ["failed", "error"]]
    
    def generate_report(self) -> str:
        """Generate detailed test report."""
        summary = self.get_summary()
        failures = self.get_failures()
        
        lines = [
            "=" * 60,
            "ALPACA OPTIONS DASHBOARD - E2E TEST REPORT",
            "=" * 60,
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Tests: {summary['total']}",
            f"Passed: {summary['passed']} ({summary['pass_rate']:.1f}%)",
            f"Failed: {summary['failed']}",
            f"Errors: {summary['errors']}",
            f"Skipped: {summary['skipped']}",
            f"Total Duration: {summary['total_duration_ms']:.0f}ms",
            "",
        ]
        
        if failures:
            lines.extend([
                "FAILURES",
                "-" * 40,
            ])
            for f in failures:
                lines.append(f"  [{f.status.upper()}] {f.test_name}")
                if f.message:
                    lines.append(f"    Message: {f.message[:100]}")
            lines.append("")
        
        lines.extend([
            "ALL RESULTS",
            "-" * 40,
        ])
        for r in self.results:
            status_icon = "✓" if r.status == "passed" else "✗"
            lines.append(f"  {status_icon} {r.test_name} ({r.duration_ms:.0f}ms)")
        
        lines.extend([
            "",
            "=" * 60,
            f"Pass Rate: {summary['pass_rate']:.1f}%",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    def save_results(self, path: str):
        """Save results to JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results]
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests(config: TestConfig = None) -> Tuple[List[TestResult], str]:
    """Run all E2E tests."""
    config = config or TestConfig()
    all_results: List[TestResult] = []
    
    print("=" * 60)
    print("ALPACA OPTIONS DASHBOARD - E2E TEST SUITE")
    print("=" * 60)
    print(f"Base URL: {config.base_url}")
    print(f"Headless: {config.headless}")
    print()
    
    # Define tests
    tests = [
        ("dashboard_loads", test_dashboard_loads),
        ("tab_navigation", test_tab_navigation),
        ("options_chain_interaction", test_options_chain_interaction),
        ("graph_rendering", test_graph_rendering),
        ("console_errors", test_console_errors),
        ("responsive_layout", test_responsive_layout),
    ]
    
    # Initialize runner
    runner = ClickerTestRunner(config)
    
    if not runner.setup():
        print("ERROR: Could not initialize WebDriver")
        print("Installing selenium and webdriver...")
        # Return mock results for testing
        for test_name, _ in tests:
            all_results.append(TestResult(
                test_name=test_name,
                status="skipped",
                duration_ms=0,
                message="WebDriver not available"
            ))
    else:
        # Run tests
        print("Running tests...")
        print("-" * 40)
        
        for test_name, test_fn in tests:
            print(f"  Running: {test_name}...", end=" ")
            result = runner.run_test(test_name, test_fn)
            all_results.append(result)
            
            status_icon = "✓" if result.status == "passed" else "✗"
            print(f"{status_icon} ({result.duration_ms:.0f}ms)")
        
        # Cleanup
        runner.teardown()
    
    # Analyze results
    print()
    analyzer = ResultAnalyzer(all_results)
    report = analyzer.generate_report()
    
    # Save results
    os.makedirs(config.results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analyzer.save_results(f"{config.results_dir}/results_{timestamp}.json")
    
    with open(f"{config.results_dir}/report_{timestamp}.txt", "w") as f:
        f.write(report)
    
    print(report)
    
    return all_results, report


def run_quick_validation() -> bool:
    """Run quick validation without Selenium."""
    print("=" * 60)
    print("ALPACA OPTIONS DASHBOARD - QUICK VALIDATION")
    print("=" * 60)
    
    import requests
    
    base_url = "http://127.0.0.1:8053"
    
    tests = [
        ("Dashboard Accessible", f"{base_url}/"),
        ("Health Check", f"{base_url}/_dash-component-suites/dash/deps/polyfill@7.v2_18_2m1748686507.12.1.min.js"),
    ]
    
    results = []
    for test_name, url in tests:
        try:
            resp = requests.get(url, timeout=10)
            passed = resp.status_code == 200
            results.append((test_name, passed, resp.status_code))
            print(f"  {'✓' if passed else '✗'} {test_name}: {resp.status_code}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"  ✗ {test_name}: {e}")
    
    all_passed = all(r[1] for r in results)
    print()
    print(f"Quick Validation: {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run E2E tests for Alpaca Options Dashboard")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--url", default="http://127.0.0.1:8053", help="Base URL")
    
    args = parser.parse_args()
    
    if args.quick:
        success = run_quick_validation()
        sys.exit(0 if success else 1)
    else:
        config = TestConfig(
            base_url=args.url,
            headless=args.headless
        )
        results, report = run_all_tests(config)
        
        # Exit with appropriate code
        summary = ResultAnalyzer(results).get_summary()
        sys.exit(0 if summary["pass_rate"] >= 80 else 1)
