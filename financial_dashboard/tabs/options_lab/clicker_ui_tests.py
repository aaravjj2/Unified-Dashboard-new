"""
Alpaca Options Lab - Chromium Clicker & Screenshot Tests
Automated UI validation with auto-analysis of results
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import base64


# Try to import playwright
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright not installed. Run: pip install playwright && playwright install chromium")


@dataclass
class ClickerTestResult:
    """Result from a clicker test."""
    test_name: str
    status: str  # 'pass', 'fail', 'error', 'skip'
    duration_ms: float
    screenshot_path: Optional[str] = None
    console_errors: List[str] = None
    network_errors: List[str] = None
    element_found: bool = False
    message: str = ""


@dataclass
class ScreenshotAnalysis:
    """Analysis of a screenshot."""
    path: str
    has_content: bool
    has_errors_visible: bool
    tab_loaded: bool
    components_visible: List[str]
    issues: List[str]


class AlpacaOptionsLabTester:
    """Automated UI tester for Alpaca Options Lab."""
    
    def __init__(self, base_url: str = "http://localhost:8053"):
        self.base_url = base_url
        self.results: List[ClickerTestResult] = []
        self.screenshots: List[str] = []
        self.console_messages: List[Dict] = []
        self.network_errors: List[str] = []
        self.browser: Browser = None
        self.page: Page = None
        
        # Output directory
        self.output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'test_screenshots',
            datetime.now().strftime('%Y%m%d_%H%M%S')
        )
    
    async def setup(self):
        """Initialize browser and page."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Capture console messages
        self.page.on('console', lambda msg: self.console_messages.append({
            'type': msg.type,
            'text': msg.text,
            'timestamp': datetime.now().isoformat()
        }))
        
        # Capture network errors
        self.page.on('requestfailed', lambda req: self.network_errors.append(
            f"{req.method} {req.url}: {req.failure}"
        ))
        
        return True
    
    async def teardown(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
    
    async def take_screenshot(self, name: str) -> str:
        """Take and save screenshot."""
        path = os.path.join(self.output_dir, f"{name}.png")
        await self.page.screenshot(path=path, full_page=True)
        self.screenshots.append(path)
        return path
    
    async def wait_for_dash_loaded(self, timeout: int = 30000):
        """Wait for Dash app to fully load."""
        try:
            # Wait for main container - try class if ID fails
            await self.page.wait_for_selector('[class*="tab"]', timeout=timeout)
            # Wait for loading spinners to disappear
            await self.page.wait_for_function(
                "document.querySelectorAll('.dash-loading').length === 0",
                timeout=timeout
            )
            await asyncio.sleep(0.5)  # Extra stability
            return True
        except Exception as e:
            print(f"⚠️ Wait for load failed: {e}")
            content = await self.page.content()
            print(f"HTML Content Preview: {content[:500]}...")
            return False
    
    async def click_and_wait(self, selector: str, timeout: int = 5000) -> bool:
        """Click an element and wait for response."""
        try:
            await self.page.click(selector, timeout=timeout)
            await asyncio.sleep(0.3)  # Allow callback to trigger
            return True
        except Exception as e:
            print(f"⚠️ Click failed on {selector}: {e}")
            return False
    
    async def run_test(self, name: str, test_func) -> ClickerTestResult:
        """Run a single test with timing."""
        start = datetime.now()
        console_before = len(self.console_messages)
        network_before = len(self.network_errors)
        
        try:
            result = await test_func()
            status = 'pass' if result else 'fail'
            message = 'Test passed' if result else 'Test failed'
        except Exception as e:
            status = 'error'
            message = str(e)
        
        duration = (datetime.now() - start).total_seconds() * 1000
        
        # Capture new errors
        console_errors = [
            m['text'] for m in self.console_messages[console_before:]
            if m['type'] == 'error'
        ]
        network_errs = self.network_errors[network_before:]
        
        # Take screenshot
        screenshot_path = await self.take_screenshot(f"test_{name}")
        
        test_result = ClickerTestResult(
            test_name=name,
            status=status,
            duration_ms=duration,
            screenshot_path=screenshot_path,
            console_errors=console_errors,
            network_errors=network_errs,
            message=message
        )
        
        self.results.append(test_result)
        
        icon = {'pass': '✅', 'fail': '❌', 'error': '⚠️', 'skip': '⏭️'}[status]
        print(f"{icon} {name}: {message} ({duration:.0f}ms)")
        
        return test_result
    
    # ============================================================
    # Test Cases
    # ============================================================
    
    async def test_load_main_page(self) -> bool:
        """Test main page loads."""
        await self.page.goto(self.base_url, wait_until='networkidle')
        return await self.wait_for_dash_loaded()
    
    async def test_options_lab_tab_exists(self) -> bool:
        """Check if Options Lab tab exists."""
        # Look for options-related tabs
        tabs = await self.page.query_selector_all('[class*="tab"], [role="tab"], a[href*="option"]')
        return len(tabs) > 0
    
    async def test_navigate_to_options_lab(self) -> bool:
        """Navigate to Options Lab."""
        # Try multiple selectors for the tab
        selectors = [
            '#tab-options_lab', # ID if available
            'text=Options Lab',
            'text=💹 Options Lab',
            'a[href*="alpaca"]',
            'a[href*="options"]', 
            '[data-tab="alpaca"]',
            'text=Options',
            'text=Alpaca'
        ]
        
        for selector in selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    print(f"Found tab with selector: {selector}")
                    await element.click()
                    await asyncio.sleep(1)
                    return True
            except Exception as e:
                print(f"Failed to click {selector}: {e}")
                continue
        
        print("❌ Could not find Options Lab tab to click")
        return False
    
    async def test_symbol_input_exists(self) -> bool:
        """Check for symbol input field."""
        selectors = [
            '#symbol-input',
            '#alpaca-symbol-input',
            'input[placeholder*="symbol"]',
            'input[placeholder*="ticker"]'
        ]
        
        for selector in selectors:
            element = await self.page.query_selector(selector)
            if element:
                return True
        
        return False
    
    async def test_enter_symbol(self) -> bool:
        """Test entering a symbol."""
        selectors = [
            '#symbol-input',
            '#alpaca-symbol-input',
            'input[placeholder*="symbol"]',
            'input[placeholder*="ticker"]'
        ]
        
        for selector in selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    await element.fill('SPY')
                    await asyncio.sleep(0.5)
                    return True
            except:
                continue
        
        return False
    
    async def test_chain_viewer_loads(self) -> bool:
        """Check if chain viewer loads data."""
        # Look for chain table or data
        selectors = [
            '[id*="chain"]',
            '[class*="chain"]',
            'table',
            '[class*="datatable"]'
        ]
        
        await asyncio.sleep(2)  # Wait for data
        
        for selector in selectors:
            elements = await self.page.query_selector_all(selector)
            if elements:
                return True
        
        return False
    
    async def test_greeks_display(self) -> bool:
        """Check if Greeks are displayed."""
        # Look for Greek letters
        content = await self.page.content()
        greeks = ['delta', 'gamma', 'theta', 'vega', 'Δ', 'Γ', 'Θ', 'ν']
        
        for greek in greeks:
            if greek.lower() in content.lower():
                return True
        
        return False
    
    async def test_expiration_selector(self) -> bool:
        """Check for expiration date selector."""
        selectors = [
            '#expiration-dropdown',
            '[id*="expir"]',
            'select[id*="exp"]',
            '[class*="DatePicker"]'
        ]
        
        for selector in selectors:
            element = await self.page.query_selector(selector)
            if element:
                return True
        
        return False
    
    async def test_no_console_errors(self) -> bool:
        """Check for absence of console errors."""
        errors = [m for m in self.console_messages if m['type'] == 'error']
        # Allow some minor errors, fail on critical ones
        critical = [e for e in errors if 'TypeError' in e['text'] or 'undefined' in e['text']]
        return len(critical) == 0
    
    async def test_page_responsive(self) -> bool:
        """Test page is responsive."""
        # Resize viewport
        await self.page.set_viewport_size({'width': 1024, 'height': 768})
        await asyncio.sleep(0.5)
        
        # Check content still visible
        content_visible = await self.page.query_selector('[class*="tab"]')
        
        # Reset viewport
        await self.page.set_viewport_size({'width': 1920, 'height': 1080})
        
        return content_visible is not None
    
    # ============================================================
    # Analysis
    # ============================================================
    
    def analyze_screenshot(self, path: str) -> ScreenshotAnalysis:
        """Analyze a screenshot for issues."""
        # In production, would use image analysis
        # For now, return basic analysis based on file existence
        
        has_content = os.path.exists(path) and os.path.getsize(path) > 10000
        
        return ScreenshotAnalysis(
            path=path,
            has_content=has_content,
            has_errors_visible=False,  # Would analyze image
            tab_loaded=has_content,
            components_visible=['chain_viewer', 'greeks'],  # Placeholder
            issues=[]
        )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        passed = sum(1 for r in self.results if r.status == 'pass')
        failed = sum(1 for r in self.results if r.status == 'fail')
        errors = sum(1 for r in self.results if r.status == 'error')
        total = len(self.results)
        
        # Analyze screenshots
        screenshot_analyses = [
            asdict(self.analyze_screenshot(s)) for s in self.screenshots
        ]
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'summary': {
                'total_tests': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "N/A"
            },
            'results': [asdict(r) for r in self.results],
            'screenshots': screenshot_analyses,
            'console_messages': self.console_messages[-50:],  # Last 50
            'network_errors': self.network_errors[-20:],  # Last 20
            'analysis': {
                'critical_issues': [],
                'warnings': [],
                'recommendations': []
            }
        }
        
        # Add analysis
        if failed > 0:
            report['analysis']['critical_issues'].append(f"{failed} tests failed")
        
        error_msgs = [r.console_errors for r in self.results if r.console_errors]
        if error_msgs:
            report['analysis']['warnings'].append("Console errors detected")
        
        return report
    
    # ============================================================
    # Main Runner
    # ============================================================
    
    async def run_all_tests(self):
        """Run all UI tests."""
        print("=" * 60)
        print("ALPACA OPTIONS LAB - UI CLICKER TESTS")
        print("=" * 60)
        
        if not await self.setup():
            print("❌ Failed to initialize browser. Skipping UI tests.")
            return {'error': 'Playwright not available'}
        
        try:
            tests = [
                ('load_main_page', self.test_load_main_page),
                ('options_lab_tab_exists', self.test_options_lab_tab_exists),
                ('navigate_to_options_lab', self.test_navigate_to_options_lab),
                ('symbol_input_exists', self.test_symbol_input_exists),
                ('enter_symbol', self.test_enter_symbol),
                ('chain_viewer_loads', self.test_chain_viewer_loads),
                ('greeks_display', self.test_greeks_display),
                ('expiration_selector', self.test_expiration_selector),
                ('no_console_errors', self.test_no_console_errors),
                ('page_responsive', self.test_page_responsive),
            ]
            
            for name, test_func in tests:
                await self.run_test(name, test_func)
            
            # Generate report
            report = self.generate_report()
            
            # Save report
            report_path = os.path.join(self.output_dir, 'test_report.json')
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            print(f"Total: {report['summary']['total_tests']}")
            print(f"✅ Passed: {report['summary']['passed']}")
            print(f"❌ Failed: {report['summary']['failed']}")
            print(f"⚠️  Errors: {report['summary']['errors']}")
            print(f"Pass Rate: {report['summary']['pass_rate']}")
            print(f"\n📁 Screenshots: {self.output_dir}")
            print(f"📄 Report: {report_path}")
            print("=" * 60)
            
            return report
            
        finally:
            await self.teardown()


async def main():
    """Main entry point."""
    tester = AlpacaOptionsLabTester()
    report = await tester.run_all_tests()
    
    # Return exit code
    if 'error' in report:
        return 1
    
    passed = report.get('summary', {}).get('passed', 0)
    total = report.get('summary', {}).get('total_tests', 1)
    return 0 if passed == total else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
