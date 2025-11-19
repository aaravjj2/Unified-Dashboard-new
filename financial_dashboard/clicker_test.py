#!/usr/bin/env python3
"""
Unified Dashboard Clicker Test

Automated browser test using Playwright to:
1. Launch browser and navigate to Unified Dashboard
2. Click through all 7 tabs
3. Verify each tab content is not empty and has no console errors
4. Take screenshots for each tab
5. Save results to outputs/clicker_testdef main():
    parser = argparse.ArgumentParser(description='Automated Dash dashboard test')
    parser.add_argument('--url', default='http://localhost:8000',
                        help='Base URL of dashboard (default: http://localhost:8000 for finance)')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode')
    parser.add_argument('--output-dir', default='outputs/clicker_test_{timestamp}',
                        help='Directory to save outputs')
    args = parser.parse_args()

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    python3 clicker_test.py
    python3 clicker_test.py --headless  # Run without visible browser
    python3 clicker_test.py --slow      # Slow down for demo (500ms delays)
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
import asyncio

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("ERROR: Playwright not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class DashboardClickerTest:
    """Automated clicker test for Unified Dashboard"""
    
    def __init__(self, base_url: str = "http://localhost:8000", headless: bool = True, slow_mo: int = 0):
        self.base_url = base_url
        self.headless = headless
        self.slow_mo = slow_mo
        
        # Output directory
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = Path(f'outputs/clicker_test_{self.timestamp}')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Test results
        self.results = []
        self.console_errors = []
    
    async def run(self):
        """Run the complete test suite"""
        logger.info(f"🚀 Starting Unified Dashboard Clicker Test")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Output directory: {self.output_dir}")
        
        async with async_playwright() as playwright:
            # Launch browser
            browser = await playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            
            # Create context and page
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            # Listen for console errors
            page.on('console', self._handle_console_message)
            
            try:
                # Navigate to dashboard
                logger.info(f"Navigating to {self.base_url}...")
                try:
                    # Primary navigation: wait for network to be idle (may hang if iframes continue to load)
                    await page.goto(self.base_url, timeout=30000, wait_until='networkidle')
                except PlaywrightTimeoutError:
                    logger.warning("Page.goto networkidle timeout; retrying with 'load' wait (fallback)")
                    # Fallback: wait for full load, longer timeout to allow embedded apps to start
                    await page.goto(self.base_url, timeout=60000, wait_until='load')

                await asyncio.sleep(2)  # Wait for initial render
                
                # Take screenshot of initial state
                await self._take_screenshot(page, "00_initial_load")
                
                # Test each tab
                await self._test_tab(page, "Market Trends", 0)
                await self._test_tab(page, "Market Forecast", 1)
                await self._test_tab(page, "Monthly Picks", 2)
                await self._test_tab(page, "Weekly Picks", 3)
                await self._test_tab(page, "Analysis Hub", 4)
                await self._test_tab(page, "Portfolio", 5)
                await self._test_tab(page, "Research Lab", 6)
                
                # Generate report
                self._generate_report()
                
                logger.info("✅ Test completed successfully")
                
            except Exception as e:
                logger.error(f"Test failed: {e}", exc_info=True)
                await self._take_screenshot(page, "error_state")
                raise
            
            finally:
                await browser.close()
    
    async def _test_tab(self, page, tab_name: str, tab_index: int):
        """Test a single tab"""
        logger.info(f"Testing tab: {tab_name} (index {tab_index})")
        
        try:
            # Try multiple tab selectors to support various dashboard structures:
            # - dbc.Tabs uses .nav-link elements
            # - Unified dashboard button.tab-btn
            # - Generic bootstrap nav-tabs
            candidate_selectors = [
                f'.nav-link:has-text("{tab_name}")',  # dbc.Tabs (bootstrap)
                f'button.tab-btn:has-text("{tab_name}")',  # Custom tab buttons
                f'a.nav-link:has-text("{tab_name}")',  # Link-based tabs
                f'.nav-tabs button:has-text("{tab_name}")',  # Generic nav-tabs buttons
                f'[role="tab"]:has-text("{tab_name}")'  # ARIA tabs
            ]

            clicked = False
            last_error = None
            for sel in candidate_selectors:
                try:
                    await page.wait_for_selector(sel, timeout=8000)
                    await page.click(sel)
                    clicked = True
                    break
                except PlaywrightTimeoutError as e:
                    last_error = e
                except Exception as e:
                    last_error = e

            if not clicked:
                # Re-raise the last timeout to be handled by outer except
                raise last_error or PlaywrightTimeoutError('Tab selector not found')
            
            # Wait for content to load
            await asyncio.sleep(3)
            
            # Check if content is visible
            content_visible = await self._check_content_visible(page)
            
            # Take screenshot
            screenshot_name = f"{tab_index+1:02d}_{tab_name.lower().replace(' ', '_')}"
            await self._take_screenshot(page, screenshot_name)
            
            # Record result
            result = {
                'tab_name': tab_name,
                'tab_index': tab_index,
                'content_visible': content_visible,
                'screenshot': f"{screenshot_name}.png",
                'status': 'PASS' if content_visible else 'FAIL'
            }
            
            self.results.append(result)
            
            if content_visible:
                logger.info(f"  ✅ {tab_name}: Content visible")
            else:
                logger.warning(f"  ⚠️ {tab_name}: Content not visible or empty")
            
        except PlaywrightTimeoutError:
            logger.error(f"  ❌ {tab_name}: Timeout finding tab selector")
            self.results.append({
                'tab_name': tab_name,
                'tab_index': tab_index,
                'content_visible': False,
                'screenshot': None,
                'status': 'FAIL',
                'error': 'Timeout'
            })
        
        except Exception as e:
            logger.error(f"  ❌ {tab_name}: Error - {e}")
            self.results.append({
                'tab_name': tab_name,
                'tab_index': tab_index,
                'content_visible': False,
                'screenshot': None,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def _check_content_visible(self, page) -> bool:
        """Check if tab content is visible and not empty"""
        try:
            # Wait for any content div to be visible
            await page.wait_for_selector('.tab-content', state='visible', timeout=5000)
            
            # First, prefer inspecting any iframe inside the active tab pane.
            # Many micro-apps are embedded as iframes in the unified dashboard,
            # and iframe content is not part of the parent .tab-content innerText.
            try:
                # Try to find an iframe inside the active pane, then any iframe
                iframe_handle = await page.query_selector('.tab-content .tab-pane.active iframe')
                if not iframe_handle:
                    iframe_handle = await page.query_selector('.tab-content iframe')

                if iframe_handle:
                    frame = await iframe_handle.content_frame()
                    if frame:
                        try:
                            # Get the textual body of the iframe
                            content = await frame.inner_text('body')
                        except Exception:
                            # As a fallback, evaluate in the frame context
                            content = await frame.evaluate("() => (document.body && document.body.innerText) || ''")

                        if content and len(content.strip()) > 50:
                            return True
            except Exception as _e:
                # Non-fatal: continue to fallback check on parent
                logger.debug(f"iframe content check failed: {_e}")

            # Fallback: check if there's actual content in the parent .tab-content
            content = await page.inner_text('.tab-content')

            # Consider content visible if it has more than 50 characters
            # (filters out minimal "Loading..." or error messages)
            return len(content.strip()) > 50
            
        except PlaywrightTimeoutError:
            return False
        except Exception as e:
            logger.warning(f"Error checking content visibility: {e}")
            return False
    
    async def _take_screenshot(self, page, name: str):
        """Take and save screenshot"""
        screenshot_path = self.output_dir / f"{name}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"  📸 Screenshot saved: {screenshot_path.name}")
    
    def _handle_console_message(self, msg):
        """Capture console messages (errors, warnings)"""
        if msg.type in ['error', 'warning']:
            error_msg = f"[{msg.type.upper()}] {msg.text}"
            self.console_errors.append(error_msg)
            
            if msg.type == 'error':
                logger.warning(f"  🔴 Console error: {msg.text}")
    
    def _generate_report(self):
        """Generate test report"""
        report_path = self.output_dir / 'test_report.txt'
        
        with open(report_path, 'w') as f:
            f.write("="*60 + "\n")
            f.write("Unified Dashboard Clicker Test Report\n")
            f.write("="*60 + "\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Base URL: {self.base_url}\n")
            f.write("\n")
            
            # Tab results
            f.write("Tab Test Results:\n")
            f.write("-"*60 + "\n")
            
            passed = sum(1 for r in self.results if r['status'] == 'PASS')
            total = len(self.results)
            
            for result in self.results:
                status_icon = "✅" if result['status'] == 'PASS' else "❌"
                f.write(f"{status_icon} {result['tab_name']:<20} {result['status']}\n")
                
                if result.get('error'):
                    f.write(f"   Error: {result['error']}\n")
                
                if result.get('screenshot'):
                    f.write(f"   Screenshot: {result['screenshot']}\n")
            
            f.write("\n")
            f.write(f"Summary: {passed}/{total} tabs passed\n")
            f.write("\n")
            
            # Console errors
            if self.console_errors:
                f.write("Console Errors:\n")
                f.write("-"*60 + "\n")
                for error in self.console_errors:
                    f.write(f"{error}\n")
            else:
                f.write("✅ No console errors detected\n")
            
            f.write("\n")
            f.write("="*60 + "\n")
        
        logger.info(f"📄 Test report saved: {report_path}")
        
        # Print summary to console
        print("\n" + "="*60)
        print(f"Test Summary: {passed}/{total} tabs passed")
        
        if self.console_errors:
            print(f"⚠️  {len(self.console_errors)} console error(s) detected")
        else:
            print("✅ No console errors")
        
        print(f"Report: {report_path}")
        print("="*60 + "\n")
        
        return passed == total


async def main():
    parser = argparse.ArgumentParser(description='Unified Dashboard Clicker Test')
    parser.add_argument('--url', default='http://localhost:8000',
                       help='Dashboard URL (default: http://localhost:8000)')
    parser.add_argument('--headless', action='store_true',
                       help='Run browser in headless mode')
    parser.add_argument('--slow', action='store_true',
                       help='Slow down for demo (500ms delays)')
    args = parser.parse_args()
    
    slow_mo = 500 if args.slow else 0
    
    tester = DashboardClickerTest(
        base_url=args.url,
        headless=args.headless,
        slow_mo=slow_mo
    )
    
    await tester.run()


if __name__ == '__main__':
    asyncio.run(main())
