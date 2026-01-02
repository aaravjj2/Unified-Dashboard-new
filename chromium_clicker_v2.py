"""
Chromium Clicker and Snapshot Testing Framework V2
Uses correct selectors for DBC Tabs
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

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeout

@dataclass
class SnapshotResult:
    """Result of a snapshot"""
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

class QuantPlatformClickerV2:
    """Clicker tests v2 with correct selectors"""
    
    def __init__(self, base_url: str = "http://localhost:8053"):
        self.base_url = base_url
        self.browser = None
        self.page = None
        self.screenshot_dir = Path("/home/aarav/Unified-Dashboard/test_screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        self.results: List[TestResult] = []
        
    async def start(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = await context.new_page()
        
    async def stop(self):
        if self.browser:
            await self.browser.close()
    
    async def screenshot(self, name: str, full_page: bool = False) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{name}_{ts}.png"
        path = self.screenshot_dir / filename
        await self.page.screenshot(path=str(path), full_page=full_page)
        return str(path)
    
    async def click_tab_by_text(self, text: str) -> bool:
        """Click a tab by its visible text"""
        try:
            await self.page.click(f'.nav-link:has-text("{text}")', timeout=5000)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            print(f"  Click tab error: {e}")
            return False
    
    async def run_test(self, name: str, test_fn) -> TestResult:
        """Run a test function and record results"""
        start = time.time()
        errors = []
        screenshots = []
        passed_steps = 0
        total_steps = 0
        
        try:
            # Navigate to base URL
            await self.page.goto(self.base_url, wait_until='networkidle', timeout=15000)
            await asyncio.sleep(1)
            
            # Run the test
            result = await test_fn(self, screenshots, errors)
            passed_steps = result.get('passed', 0)
            total_steps = result.get('total', 0)
        except Exception as e:
            errors.append(f"Test error: {str(e)}")
        
        duration = (time.time() - start) * 1000
        passed = len(errors) == 0 and passed_steps == total_steps
        
        test_result = TestResult(
            test_name=name,
            passed=passed,
            duration_ms=duration,
            steps_passed=passed_steps,
            steps_total=total_steps,
            errors=errors,
            screenshot_paths=screenshots
        )
        self.results.append(test_result)
        return test_result
    
    async def run_all_tests(self):
        """Run all tests"""
        await self.start()
        
        tests = [
            ("Dashboard Loads", self._test_dashboard_loads),
            ("Service Cards", self._test_service_cards),
            ("Market Data Tab", self._test_market_data),
            ("Factors Tab", self._test_factors),
            ("Options Tab", self._test_options),
            ("Portfolio Tab", self._test_portfolio),
            ("Risk Tab", self._test_risk),
            ("ML Tab", self._test_ml),
            ("Execution Tab", self._test_execution),
        ]
        
        print("=" * 60)
        print("🧪 QUANT PLATFORM CLICKER TESTS V2")
        print("=" * 60)
        
        for name, test_fn in tests:
            print(f"\nRunning: {name}...")
            result = await self.run_test(name, test_fn)
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  {status} ({result.steps_passed}/{result.steps_total} steps, {result.duration_ms:.0f}ms)")
            if result.errors:
                for e in result.errors[:3]:
                    print(f"    Error: {e}")
        
        await self.stop()
        return self._generate_report()
    
    # ===== TEST IMPLEMENTATIONS =====
    
    async def _test_dashboard_loads(self, tester, screenshots, errors):
        """Test dashboard loads"""
        steps = {'passed': 0, 'total': 3}
        
        # Check page loaded
        title = await tester.page.title()
        if title:
            steps['passed'] += 1
        else:
            errors.append("Page title not found")
        
        # Check body exists
        body = await tester.page.query_selector('body')
        if body:
            steps['passed'] += 1
        else:
            errors.append("Body element missing")
        
        # Take screenshot
        path = await tester.screenshot("dashboard_load")
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_service_cards(self, tester, screenshots, errors):
        """Test service status cards"""
        steps = {'passed': 0, 'total': 3}
        
        # Check for cards
        cards = await tester.page.query_selector_all('.card')
        if len(cards) >= 6:
            steps['passed'] += 1
        else:
            errors.append(f"Expected 6+ cards, found {len(cards)}")
        
        # Check for badges
        badges = await tester.page.query_selector_all('.badge')
        if len(badges) >= 6:
            steps['passed'] += 1
        else:
            errors.append(f"Expected 6+ badges, found {len(badges)}")
        
        # Screenshot
        path = await tester.screenshot("service_cards")
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_market_data(self, tester, screenshots, errors):
        """Test Market Data tab"""
        steps = {'passed': 0, 'total': 4}
        
        # Click Market Data tab
        if await tester.click_tab_by_text("Market Data"):
            steps['passed'] += 1
        else:
            errors.append("Failed to click Market Data tab")
        
        await asyncio.sleep(0.5)
        
        # Check for Generate button
        btn = await tester.page.query_selector('#btn-generate-market')
        if btn:
            steps['passed'] += 1
            await btn.click()
            await asyncio.sleep(2)
        else:
            errors.append("Generate button not found")
        
        # Check for chart
        chart = await tester.page.query_selector('#market-price-chart')
        if chart:
            steps['passed'] += 1
        else:
            errors.append("Market price chart not found")
        
        # Screenshot
        path = await tester.screenshot("market_data", full_page=True)
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_factors(self, tester, screenshots, errors):
        """Test Factors tab"""
        steps = {'passed': 0, 'total': 4}
        
        if await tester.click_tab_by_text("Factors"):
            steps['passed'] += 1
        else:
            errors.append("Failed to click Factors tab")
        
        await asyncio.sleep(0.5)
        
        btn = await tester.page.query_selector('#btn-factor-analysis')
        if btn:
            steps['passed'] += 1
            await btn.click()
            await asyncio.sleep(2)
        else:
            errors.append("Factor analysis button not found")
        
        chart = await tester.page.query_selector('#factor-chart')
        if chart:
            steps['passed'] += 1
        else:
            errors.append("Factor chart not found")
        
        path = await tester.screenshot("factors", full_page=True)
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_options(self, tester, screenshots, errors):
        """Test Options tab"""
        steps = {'passed': 0, 'total': 5}
        
        if await tester.click_tab_by_text("Options"):
            steps['passed'] += 1
        else:
            errors.append("Failed to click Options tab")
        
        await asyncio.sleep(0.5)
        
        # Fill inputs
        spot = await tester.page.query_selector('#opt-spot')
        if spot:
            await spot.fill("100")
            steps['passed'] += 1
        else:
            errors.append("Spot input not found")
        
        # Click price button
        btn = await tester.page.query_selector('#btn-price-option')
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            steps['passed'] += 1
        else:
            errors.append("Price button not found")
        
        # Click build surface
        surf_btn = await tester.page.query_selector('#btn-build-surface')
        if surf_btn:
            await surf_btn.click()
            await asyncio.sleep(3)
            steps['passed'] += 1
        else:
            errors.append("Build surface button not found")
        
        path = await tester.screenshot("options", full_page=True)
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_portfolio(self, tester, screenshots, errors):
        """Test Portfolio tab"""
        steps = {'passed': 0, 'total': 4}
        
        if await tester.click_tab_by_text("Portfolio"):
            steps['passed'] += 1
        else:
            errors.append("Failed to click Portfolio tab")
        
        await asyncio.sleep(0.5)
        
        btn = await tester.page.query_selector('#btn-optimize-portfolio')
        if btn:
            steps['passed'] += 1
            await btn.click()
            await asyncio.sleep(3)
        else:
            errors.append("Optimize button not found")
        
        chart = await tester.page.query_selector('#efficient-frontier-chart')
        if chart:
            steps['passed'] += 1
        else:
            errors.append("Efficient frontier chart not found")
        
        path = await tester.screenshot("portfolio", full_page=True)
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_risk(self, tester, screenshots, errors):
        """Test Risk tab"""
        steps = {'passed': 0, 'total': 4}
        
        if await tester.click_tab_by_text("Risk"):
            steps['passed'] += 1
        else:
            errors.append("Failed to click Risk tab")
        
        await asyncio.sleep(0.5)
        
        btn = await tester.page.query_selector('#btn-risk-analysis')
        if btn:
            steps['passed'] += 1
            await btn.click()
            await asyncio.sleep(3)
        else:
            errors.append("Risk analysis button not found")
        
        chart = await tester.page.query_selector('#var-chart')
        if chart:
            steps['passed'] += 1
        else:
            errors.append("VaR chart not found")
        
        path = await tester.screenshot("risk", full_page=True)
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_ml(self, tester, screenshots, errors):
        """Test ML tab"""
        steps = {'passed': 0, 'total': 4}
        
        if await tester.click_tab_by_text("ML"):
            steps['passed'] += 1
        else:
            errors.append("Failed to click ML tab")
        
        await asyncio.sleep(0.5)
        
        btn = await tester.page.query_selector('#btn-train-ml')
        if btn:
            steps['passed'] += 1
            await btn.click()
            await asyncio.sleep(5)  # ML training takes longer
        else:
            errors.append("Train button not found")
        
        chart = await tester.page.query_selector('#feature-importance-chart')
        if chart:
            steps['passed'] += 1
        else:
            errors.append("Feature importance chart not found")
        
        path = await tester.screenshot("ml", full_page=True)
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    async def _test_execution(self, tester, screenshots, errors):
        """Test Execution tab"""
        steps = {'passed': 0, 'total': 5}
        
        if await tester.click_tab_by_text("Execution"):
            steps['passed'] += 1
        else:
            errors.append("Failed to click Execution tab")
        
        await asyncio.sleep(0.5)
        
        # Fill symbol
        symbol = await tester.page.query_selector('#exec-symbol')
        if symbol:
            await symbol.fill("AAPL")
            steps['passed'] += 1
        else:
            errors.append("Symbol input not found")
        
        # Fill qty
        qty = await tester.page.query_selector('#exec-qty')
        if qty:
            await qty.fill("1000")
            steps['passed'] += 1
        else:
            errors.append("Qty input not found")
        
        # Submit order
        btn = await tester.page.query_selector('#btn-submit-order')
        if btn:
            await btn.click()
            await asyncio.sleep(2)
            steps['passed'] += 1
        else:
            errors.append("Submit order button not found")
        
        path = await tester.screenshot("execution", full_page=True)
        screenshots.append(path)
        steps['passed'] += 1
        
        return steps
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate test report"""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        total_duration = sum(r.duration_ms for r in self.results)
        total_screenshots = sum(len(r.screenshot_paths) for r in self.results)
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{(passed/len(self.results)*100):.1f}%" if self.results else "0%",
                'total_duration_ms': total_duration,
                'total_screenshots': total_screenshots
            },
            'tests': [
                {
                    'name': r.test_name,
                    'passed': r.passed,
                    'duration_ms': r.duration_ms,
                    'steps_passed': r.steps_passed,
                    'steps_total': r.steps_total,
                    'errors': r.errors,
                    'screenshots': r.screenshot_paths
                }
                for r in self.results
            ],
            'generated_at': datetime.now().isoformat()
        }
        
        # Save report
        report_path = Path("/home/aarav/Unified-Dashboard/test_results")
        report_path.mkdir(exist_ok=True)
        report_file = report_path / f"clicker_test_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Report saved to: {report_file}")
        
        return report


async def main():
    tester = QuantPlatformClickerV2()
    report = await tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Pass Rate: {report['summary']['pass_rate']}")
    print(f"Duration: {report['summary']['total_duration_ms']:.0f}ms")
    print(f"Screenshots: {report['summary']['total_screenshots']}")
    print("=" * 60)
    
    return report


if __name__ == "__main__":
    asyncio.run(main())
