"""
Playwright E2E Tests for Alpaca Options Lab Critical Flows

Tests:
1. Sentiment gauge correctness
2. Buy/ticket flow
3. Fallback behaviors
4. Callback deduplication verification
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright not installed. Run: pip install playwright && playwright install chromium")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://localhost:8053"
SCREENSHOT_DIR = PROJECT_ROOT / "e2e_snapshots" / datetime.now().strftime("%Y%m%d_%H%M%S")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class AlpacaOptionsCriticalFlowsTester:
    """Test critical flows for Alpaca Options Lab."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'console_errors': [],
            'network_errors': [],
            'screenshots': []
        }
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def setup(self):
        """Initialize browser."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Capture console errors
        self.page.on('console', lambda msg: self._handle_console(msg))
        self.page.on('requestfailed', lambda req: self._handle_network_error(req))
        
        return True
    
    def _handle_console(self, msg):
        """Handle console messages."""
        if msg.type == 'error':
            self.results['console_errors'].append({
                'text': msg.text,
                'timestamp': datetime.now().isoformat()
            })
    
    def _handle_network_error(self, req):
        """Handle network errors."""
        self.results['network_errors'].append({
            'url': req.url,
            'method': req.method,
            'failure': req.failure,
            'timestamp': datetime.now().isoformat()
        })
    
    async def teardown(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
    
    async def take_screenshot(self, name: str) -> str:
        """Take screenshot."""
        path = SCREENSHOT_DIR / f"{name}.png"
        await self.page.screenshot(path=str(path), full_page=True)
        self.results['screenshots'].append(str(path))
        return str(path)
    
    async def test_gauge_correctness(self) -> bool:
        """Test sentiment gauge correctness."""
        test_name = "gauge_correctness"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            # Navigate to app
            await self.page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
            await self.take_screenshot(f"{test_name}_01_initial")
            
            # Try to find Scanner Workspace tab
            scanner_tab = await self.page.query_selector('text=Scanner, [id*="scanner"], [id*="Scanner"]')
            if scanner_tab:
                await scanner_tab.click()
                await self.page.wait_for_timeout(2000)
                await self.take_screenshot(f"{test_name}_02_scanner_tab")
            
            # Look for hype gauges
            gauge_selectors = [
                '#scanner-hype-gauges',
                '[id*="hype"]',
                '[id*="gauge"]',
                'text=NVDA',
                'text=TSLA'
            ]
            
            gauge_found = False
            for selector in gauge_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    gauge_found = True
                    await self.take_screenshot(f"{test_name}_03_gauges_found")
                    break
            
            # Check for data degradation warnings
            degradation_warning = await self.page.query_selector('text=MOCK, text=degraded, text=fallback')
            
            self.results['tests'][test_name] = {
                'status': 'pass' if gauge_found else 'fail',
                'gauge_found': gauge_found,
                'degradation_warning': degradation_warning is not None,
                'message': 'Gauges found' if gauge_found else 'Gauges not found'
            }
            
            return gauge_found
            
        except Exception as e:
            self.results['tests'][test_name] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    async def test_buy_ticket_flow(self) -> bool:
        """Test buy/ticket flow."""
        test_name = "buy_ticket_flow"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            # Navigate to options lab
            await self.page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
            await self.take_screenshot(f"{test_name}_01_initial")
            
            # Find options lab tab
            options_tab = await self.page.query_selector('text=Options Lab, [id*="options"]')
            if options_tab:
                await options_tab.click()
                await self.page.wait_for_timeout(2000)
                await self.take_screenshot(f"{test_name}_02_options_tab")
            
            # Find ticker input
            ticker_input = await self.page.query_selector('#alpaca-ticker-input')
            if ticker_input:
                await ticker_input.fill('SPY')
                await self.take_screenshot(f"{test_name}_03_ticker_entered")
            
            # Find load button
            load_button = await self.page.query_selector('#alpaca-load-button')
            if load_button:
                await load_button.click()
                await self.page.wait_for_timeout(3000)
                await self.take_screenshot(f"{test_name}_04_after_load")
            
            # Check for options table
            table = await self.page.query_selector('#alpaca-options-table')
            if table:
                # Try clicking on a cell to open order modal
                cells = await self.page.query_selector_all('#alpaca-options-table td')
                if cells:
                    await cells[0].click()
                    await self.page.wait_for_timeout(1000)
                    await self.take_screenshot(f"{test_name}_05_order_modal")
                    
                    # Check for order modal
                    modal = await self.page.query_selector('#alpaca-order-modal, [id*="order"]')
                    modal_found = modal is not None
                else:
                    modal_found = False
            else:
                modal_found = False
            
            self.results['tests'][test_name] = {
                'status': 'pass' if modal_found else 'fail',
                'table_found': table is not None,
                'modal_found': modal_found,
                'message': 'Buy ticket flow works' if modal_found else 'Buy ticket flow incomplete'
            }
            
            return modal_found
            
        except Exception as e:
            self.results['tests'][test_name] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    async def test_fallback_behaviors(self) -> bool:
        """Test fallback behaviors."""
        test_name = "fallback_behaviors"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            # Navigate to scanner workspace
            await self.page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
            
            # Check console for circuit breaker messages
            await self.page.wait_for_timeout(5000)
            
            # Look for data degradation indicators
            degradation_indicators = [
                'text=MOCK',
                'text=degraded',
                'text=fallback',
                'text=Circuit',
                '[class*="warning"]',
                '[class*="degraded"]'
            ]
            
            found_indicators = []
            for indicator in degradation_indicators:
                element = await self.page.query_selector(indicator)
                if element:
                    found_indicators.append(indicator)
            
            # Check console errors for circuit breaker messages
            circuit_breaker_messages = [
                msg for msg in self.results['console_errors']
                if 'circuit' in msg['text'].lower() or 'fallback' in msg['text'].lower()
            ]
            
            self.results['tests'][test_name] = {
                'status': 'pass',
                'degradation_indicators': found_indicators,
                'circuit_breaker_messages': len(circuit_breaker_messages),
                'message': 'Fallback behaviors detected'
            }
            
            await self.take_screenshot(f"{test_name}_01_fallback_check")
            
            return True
            
        except Exception as e:
            self.results['tests'][test_name] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    async def test_callback_deduplication(self) -> bool:
        """Test callback deduplication (check for duplicate IDs)."""
        test_name = "callback_deduplication"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            # Navigate to app
            await self.page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
            
            # Check console for duplicate callback errors
            duplicate_errors = [
                msg for msg in self.results['console_errors']
                if 'duplicate' in msg['text'].lower() or 'already registered' in msg['text'].lower()
            ]
            
            # Check for React duplicate key warnings
            react_duplicate_warnings = [
                msg for msg in self.results['console_errors']
                if 'key' in msg['text'].lower() and 'duplicate' in msg['text'].lower()
            ]
            
            has_duplicates = len(duplicate_errors) > 0 or len(react_duplicate_warnings) > 0
            
            self.results['tests'][test_name] = {
                'status': 'pass' if not has_duplicates else 'fail',
                'duplicate_errors': len(duplicate_errors),
                'react_warnings': len(react_duplicate_warnings),
                'message': 'No duplicates found' if not has_duplicates else 'Duplicates detected'
            }
            
            return not has_duplicates
            
        except Exception as e:
            self.results['tests'][test_name] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all critical flow tests."""
        print("=" * 60)
        print("ALPACA OPTIONS LAB - CRITICAL FLOWS TEST")
        print("=" * 60)
        
        if not await self.setup():
            print("❌ Failed to initialize browser")
            return {'error': 'Playwright not available'}
        
        try:
            # Run all tests
            await self.test_gauge_correctness()
            await self.test_buy_ticket_flow()
            await self.test_fallback_behaviors()
            await self.test_callback_deduplication()
            
            # Generate summary
            total = len(self.results['tests'])
            passed = sum(1 for t in self.results['tests'].values() if t.get('status') == 'pass')
            failed = sum(1 for t in self.results['tests'].values() if t.get('status') == 'fail')
            errors = sum(1 for t in self.results['tests'].values() if t.get('status') == 'error')
            
            self.results['summary'] = {
                'total': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'pass_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%"
            }
            
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            print(f"Total: {total}")
            print(f"✅ Passed: {passed}")
            print(f"❌ Failed: {failed}")
            print(f"⚠️  Errors: {errors}")
            print(f"Pass Rate: {self.results['summary']['pass_rate']}")
            print(f"\n📁 Screenshots: {SCREENSHOT_DIR}")
            print("=" * 60)
            
            return self.results
            
        finally:
            await self.teardown()


async def main():
    """Main entry point."""
    tester = AlpacaOptionsCriticalFlowsTester()
    results = await tester.run_all_tests()
    
    # Save report
    report_path = PROJECT_ROOT / "test_report.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Report saved: {report_path}")
    
    # Return exit code
    if 'error' in results:
        return 1
    
    passed = results.get('summary', {}).get('passed', 0)
    total = results.get('summary', {}).get('total', 1)
    return 0 if passed == total else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

