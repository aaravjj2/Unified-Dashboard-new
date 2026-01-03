"""
Chromium Clicker and Snapshot Testing Framework
For REAL UI validation of the Quant Platform Dashboard
"""

import asyncio
import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import subprocess
import time

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Installing playwright...")
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True

@dataclass
class ClickAction:
    """Represents a click action"""
    selector: str
    description: str
    wait_after: int = 1000
    screenshot_after: bool = True

@dataclass
class TestStep:
    """A single test step"""
    name: str
    action_type: str  # click, input, wait, scroll, screenshot
    selector: Optional[str] = None
    value: Optional[str] = None
    wait_ms: int = 500
    expected_element: Optional[str] = None

@dataclass
class SnapshotResult:
    """Result of a snapshot comparison"""
    test_name: str
    screenshot_path: str
    timestamp: str
    element_found: bool
    visual_hash: str
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class TestResult:
    """Complete test result"""
    test_name: str
    passed: bool
    duration_ms: float
    steps_passed: int
    steps_total: int
    snapshots: List[SnapshotResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    screenshot_paths: List[str] = field(default_factory=list)

class ChromiumClicker:
    """Chromium-based UI clicker for real browser testing"""
    
    def __init__(self, base_url: str = "http://localhost:8053", headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.screenshot_dir = Path("/home/aarav/Unified-Dashboard/test_screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        
    async def start(self):
        """Start browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        
    async def stop(self):
        """Stop browser"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
            
    async def navigate(self, url: str = None) -> bool:
        """Navigate to URL"""
        target = url or self.base_url
        try:
            await self.page.goto(target, wait_until='networkidle', timeout=30000)
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            return False
    
    async def click(self, selector: str, timeout: int = 5000) -> bool:
        """Click an element"""
        try:
            await self.page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            print(f"Click error on {selector}: {e}")
            return False
    
    async def fill(self, selector: str, value: str, timeout: int = 5000) -> bool:
        """Fill an input field"""
        try:
            await self.page.fill(selector, value, timeout=timeout)
            return True
        except Exception as e:
            print(f"Fill error on {selector}: {e}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element to appear"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False
    
    async def screenshot(self, name: str, full_page: bool = False) -> str:
        """Take screenshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = self.screenshot_dir / filename
        await self.page.screenshot(path=str(path), full_page=full_page)
        return str(path)
    
    async def get_element_text(self, selector: str) -> Optional[str]:
        """Get text content of element"""
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.text_content()
            return None
        except Exception:
            return None
    
    async def element_exists(self, selector: str) -> bool:
        """Check if element exists"""
        element = await self.page.query_selector(selector)
        return element is not None
    
    async def get_page_metrics(self) -> Dict[str, Any]:
        """Get page performance metrics"""
        metrics = await self.page.evaluate('''() => {
            const perf = window.performance;
            const timing = perf.timing;
            return {
                loadTime: timing.loadEventEnd - timing.navigationStart,
                domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
                firstPaint: perf.getEntriesByType('paint')[0]?.startTime || 0,
                resourceCount: perf.getEntriesByType('resource').length
            };
        }''')
        return metrics
    
    async def get_console_errors(self) -> List[str]:
        """Capture console errors"""
        errors = []
        self.page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        return errors

class SnapshotTester:
    """Snapshot testing with visual analysis"""
    
    def __init__(self, clicker: ChromiumClicker):
        self.clicker = clicker
        self.baseline_dir = Path("/home/aarav/Unified-Dashboard/test_baselines")
        self.baseline_dir.mkdir(exist_ok=True)
        self.results: List[SnapshotResult] = []
        
    def _hash_image(self, path: str) -> str:
        """Generate hash of image for comparison"""
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    async def capture_snapshot(self, name: str, selector: str = None) -> SnapshotResult:
        """Capture and analyze a snapshot"""
        timestamp = datetime.now().isoformat()
        
        # Check if element exists
        element_found = True
        if selector:
            element_found = await self.clicker.element_exists(selector)
        
        # Take screenshot
        screenshot_path = await self.clicker.screenshot(name)
        
        # Generate visual hash
        visual_hash = self._hash_image(screenshot_path)
        
        # Get page metrics
        metrics = await self.clicker.get_page_metrics()
        
        result = SnapshotResult(
            test_name=name,
            screenshot_path=screenshot_path,
            timestamp=timestamp,
            element_found=element_found,
            visual_hash=visual_hash,
            metrics=metrics
        )
        
        self.results.append(result)
        return result
    
    def compare_to_baseline(self, snapshot: SnapshotResult) -> Tuple[bool, str]:
        """Compare snapshot to baseline"""
        baseline_path = self.baseline_dir / f"{snapshot.test_name}_baseline.png"
        
        if not baseline_path.exists():
            # Save as new baseline
            import shutil
            shutil.copy(snapshot.screenshot_path, baseline_path)
            return True, "New baseline created"
        
        baseline_hash = self._hash_image(str(baseline_path))
        
        if baseline_hash == snapshot.visual_hash:
            return True, "Matches baseline"
        else:
            return False, f"Visual difference detected (baseline: {baseline_hash[:8]}, current: {snapshot.visual_hash[:8]})"
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate snapshot test report"""
        return {
            'total_snapshots': len(self.results),
            'elements_found': sum(1 for r in self.results if r.element_found),
            'elements_missing': sum(1 for r in self.results if not r.element_found),
            'snapshots': [asdict(r) for r in self.results],
            'generated_at': datetime.now().isoformat()
        }

class QuantPlatformTests:
    """Test suite for Quant Platform Dashboard"""
    
    def __init__(self, base_url: str = "http://localhost:8053"):
        self.base_url = base_url
        self.clicker = ChromiumClicker(base_url, headless=True)
        self.snapshot_tester = SnapshotTester(self.clicker)
        self.results: List[TestResult] = []
        
    async def setup(self):
        """Setup test environment"""
        await self.clicker.start()
        
    async def teardown(self):
        """Cleanup"""
        await self.clicker.stop()
    
    async def run_test(self, name: str, steps: List[TestStep]) -> TestResult:
        """Run a single test with multiple steps"""
        start_time = time.time()
        passed_steps = 0
        errors = []
        screenshots = []
        snapshots = []
        
        for step in steps:
            try:
                if step.action_type == 'navigate':
                    success = await self.clicker.navigate(step.value)
                elif step.action_type == 'click':
                    success = await self.clicker.click(step.selector)
                elif step.action_type == 'fill':
                    success = await self.clicker.fill(step.selector, step.value)
                elif step.action_type == 'wait':
                    success = await self.clicker.wait_for_selector(step.selector, step.wait_ms)
                elif step.action_type == 'screenshot':
                    path = await self.clicker.screenshot(step.name)
                    screenshots.append(path)
                    success = True
                elif step.action_type == 'snapshot':
                    snapshot = await self.snapshot_tester.capture_snapshot(step.name, step.selector)
                    snapshots.append(snapshot)
                    success = snapshot.element_found
                else:
                    success = False
                    errors.append(f"Unknown action type: {step.action_type}")
                
                if success:
                    passed_steps += 1
                else:
                    errors.append(f"Step '{step.name}' failed")
                    
                # Wait between steps
                await asyncio.sleep(step.wait_ms / 1000)
                
            except Exception as e:
                errors.append(f"Step '{step.name}' error: {str(e)}")
        
        duration = (time.time() - start_time) * 1000
        
        result = TestResult(
            test_name=name,
            passed=passed_steps == len(steps),
            duration_ms=duration,
            steps_passed=passed_steps,
            steps_total=len(steps),
            snapshots=snapshots,
            errors=errors,
            screenshot_paths=screenshots
        )
        
        self.results.append(result)
        return result
    
    # ===== TEST DEFINITIONS =====
    
    async def test_dashboard_loads(self) -> TestResult:
        """Test that dashboard loads correctly"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Wait for body", action_type="wait", selector="body", wait_ms=3000),
            TestStep(name="Initial screenshot", action_type="screenshot"),
            TestStep(name="Check main container", action_type="snapshot", selector="#quant-platform-container"),
        ]
        return await self.run_test("Dashboard Loads", steps)
    
    async def test_service_status_cards(self) -> TestResult:
        """Test service status cards render"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Wait for cards", action_type="wait", selector="#service-status-row", wait_ms=3000),
            TestStep(name="Snapshot cards", action_type="snapshot", selector="#service-status-row"),
        ]
        return await self.run_test("Service Status Cards", steps)
    
    async def test_market_data_tab(self) -> TestResult:
        """Test Market Data tab functionality"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Wait for tabs", action_type="wait", selector="#quant-tabs", wait_ms=2000),
            TestStep(name="Click Market Data tab", action_type="click", selector='[data-value="tab-market"]'),
            TestStep(name="Wait", action_type="wait", selector="#btn-generate-market", wait_ms=1000),
            TestStep(name="Click Generate Data", action_type="click", selector="#btn-generate-market"),
            TestStep(name="Wait for chart", action_type="wait", selector="#market-price-chart", wait_ms=3000),
            TestStep(name="Snapshot market tab", action_type="snapshot", selector="#market-price-chart"),
        ]
        return await self.run_test("Market Data Tab", steps)
    
    async def test_options_pricing(self) -> TestResult:
        """Test Options pricing functionality"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Wait for tabs", action_type="wait", selector="#quant-tabs", wait_ms=2000),
            TestStep(name="Click Options tab", action_type="click", selector='[data-value="tab-options"]'),
            TestStep(name="Wait for inputs", action_type="wait", selector="#opt-spot", wait_ms=1000),
            TestStep(name="Fill spot", action_type="fill", selector="#opt-spot", value="100"),
            TestStep(name="Fill strike", action_type="fill", selector="#opt-strike", value="100"),
            TestStep(name="Click Price", action_type="click", selector="#btn-price-option"),
            TestStep(name="Wait for output", action_type="wait", selector="#option-price-output", wait_ms=2000),
            TestStep(name="Snapshot options", action_type="snapshot", selector="#greeks-display"),
        ]
        return await self.run_test("Options Pricing", steps)
    
    async def test_vol_surface(self) -> TestResult:
        """Test Volatility Surface generation"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Click Options tab", action_type="click", selector='[data-value="tab-options"]'),
            TestStep(name="Wait", action_type="wait", selector="#btn-build-surface", wait_ms=1000),
            TestStep(name="Build Surface", action_type="click", selector="#btn-build-surface"),
            TestStep(name="Wait for 3D chart", action_type="wait", selector="#vol-surface-chart", wait_ms=5000),
            TestStep(name="Snapshot vol surface", action_type="snapshot", selector="#vol-surface-chart"),
        ]
        return await self.run_test("Volatility Surface", steps)
    
    async def test_portfolio_optimization(self) -> TestResult:
        """Test Portfolio optimization"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Click Portfolio tab", action_type="click", selector='[data-value="tab-portfolio"]'),
            TestStep(name="Wait", action_type="wait", selector="#btn-optimize-portfolio", wait_ms=1000),
            TestStep(name="Optimize", action_type="click", selector="#btn-optimize-portfolio"),
            TestStep(name="Wait for frontier", action_type="wait", selector="#efficient-frontier-chart", wait_ms=5000),
            TestStep(name="Snapshot portfolio", action_type="snapshot", selector="#efficient-frontier-chart"),
            TestStep(name="Snapshot weights", action_type="snapshot", selector="#weights-chart"),
        ]
        return await self.run_test("Portfolio Optimization", steps)
    
    async def test_risk_analytics(self) -> TestResult:
        """Test Risk analytics"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Click Risk tab", action_type="click", selector='[data-value="tab-risk"]'),
            TestStep(name="Wait", action_type="wait", selector="#btn-risk-analysis", wait_ms=1000),
            TestStep(name="Run Analysis", action_type="click", selector="#btn-risk-analysis"),
            TestStep(name="Wait for VaR", action_type="wait", selector="#var-chart", wait_ms=5000),
            TestStep(name="Snapshot VaR", action_type="snapshot", selector="#var-chart"),
            TestStep(name="Snapshot Drawdown", action_type="snapshot", selector="#drawdown-chart"),
        ]
        return await self.run_test("Risk Analytics", steps)
    
    async def test_ml_pipeline(self) -> TestResult:
        """Test ML pipeline"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Click ML tab", action_type="click", selector='[data-value="tab-ml"]'),
            TestStep(name="Wait", action_type="wait", selector="#btn-train-ml", wait_ms=1000),
            TestStep(name="Train Models", action_type="click", selector="#btn-train-ml"),
            TestStep(name="Wait for features", action_type="wait", selector="#feature-importance-chart", wait_ms=8000),
            TestStep(name="Snapshot features", action_type="snapshot", selector="#feature-importance-chart"),
            TestStep(name="Snapshot performance", action_type="snapshot", selector="#model-performance-chart"),
        ]
        return await self.run_test("ML Pipeline", steps)
    
    async def test_execution(self) -> TestResult:
        """Test Execution service"""
        steps = [
            TestStep(name="Navigate", action_type="navigate", value=self.base_url),
            TestStep(name="Click Execution tab", action_type="click", selector='[data-value="tab-execution"]'),
            TestStep(name="Wait", action_type="wait", selector="#btn-submit-order", wait_ms=1000),
            TestStep(name="Fill symbol", action_type="fill", selector="#exec-symbol", value="AAPL"),
            TestStep(name="Fill qty", action_type="fill", selector="#exec-qty", value="1000"),
            TestStep(name="Submit Order", action_type="click", selector="#btn-submit-order"),
            TestStep(name="Wait for TWAP", action_type="wait", selector="#twap-chart", wait_ms=3000),
            TestStep(name="Snapshot TWAP", action_type="snapshot", selector="#twap-chart"),
        ]
        return await self.run_test("Execution Service", steps)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests"""
        await self.setup()
        
        tests = [
            self.test_dashboard_loads,
            self.test_service_status_cards,
            self.test_market_data_tab,
            self.test_options_pricing,
            self.test_vol_surface,
            self.test_portfolio_optimization,
            self.test_risk_analytics,
            self.test_ml_pipeline,
            self.test_execution,
        ]
        
        for test in tests:
            try:
                print(f"Running: {test.__name__}...")
                result = await test()
                status = "✅ PASS" if result.passed else "❌ FAIL"
                print(f"  {status} - {result.steps_passed}/{result.steps_total} steps ({result.duration_ms:.0f}ms)")
                if result.errors:
                    for err in result.errors:
                        print(f"    Error: {err}")
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
        
        await self.teardown()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        total_duration = sum(r.duration_ms for r in self.results)
        total_snapshots = sum(len(r.snapshots) for r in self.results)
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{(passed/len(self.results)*100):.1f}%" if self.results else "0%",
                'total_duration_ms': total_duration,
                'total_snapshots': total_snapshots
            },
            'tests': [
                {
                    'name': r.test_name,
                    'passed': r.passed,
                    'duration_ms': r.duration_ms,
                    'steps_passed': r.steps_passed,
                    'steps_total': r.steps_total,
                    'errors': r.errors,
                    'screenshots': r.screenshot_paths,
                    'snapshots': [asdict(s) for s in r.snapshots]
                }
                for r in self.results
            ],
            'snapshot_report': self.snapshot_tester.generate_report(),
            'generated_at': datetime.now().isoformat()
        }
        
        # Save report
        report_path = Path("/home/aarav/Unified-Dashboard/test_results")
        report_path.mkdir(exist_ok=True)
        report_file = report_path / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Report saved to: {report_file}")
        
        return report


async def main():
    """Main entry point for running tests"""
    print("=" * 60)
    print("🧪 QUANT PLATFORM CHROMIUM CLICKER TESTS")
    print("=" * 60)
    
    tester = QuantPlatformTests()
    report = await tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Pass Rate: {report['summary']['pass_rate']}")
    print(f"Total Duration: {report['summary']['total_duration_ms']:.0f}ms")
    print(f"Total Snapshots: {report['summary']['total_snapshots']}")
    print("=" * 60)
    
    return report


if __name__ == "__main__":
    asyncio.run(main())
