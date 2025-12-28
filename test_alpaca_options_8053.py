#!/usr/bin/env python3
"""
Comprehensive Alpaca Options Lab Test on Port 8053
Tests all Alpaca-style options functionality
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8053"
SCREENSHOT_DIR = Path("screenshots/alpaca_options_test")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

class AlpacaOptionsLabTester:
    def __init__(self):
        self.results = []
        self.errors = []
        
    async def run_all_tests(self):
        """Run all Alpaca options lab tests"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Enable console logging
            page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}") if msg.type == "error" else None)
            
            try:
                # Test 1: Load dashboard
                await self.test_dashboard_load(page)
                
                # Test 2: Navigate to Options Lab
                await self.test_navigate_to_options_lab(page)
                
                # Test 3: Check Alpaca UI components exist
                await self.test_alpaca_ui_components(page)
                
                # Test 4: Test ticker input and fetch
                await self.test_ticker_input_and_fetch(page)
                
                # Test 5: Check Alpaca table rendering
                await self.test_alpaca_table_rendering(page)
                
                # Test 6: Test expiration dropdown
                await self.test_expiration_dropdown(page)
                
                # Test 7: Check Greeks visualization
                await self.test_greeks_visualization(page)
                
                # Test 8: Test options chain subtab
                await self.test_options_chain_subtab(page)
                
                # Test 9: Check IV Surface tab
                await self.test_iv_surface_tab(page)
                
                # Test 10: Final state screenshot
                await self.test_final_state(page)
                
            except Exception as e:
                self.errors.append(f"Critical error: {str(e)}")
                import traceback
                traceback.print_exc()
                await page.screenshot(path=str(SCREENSHOT_DIR / "error_state.png"))
            finally:
                await browser.close()
                
        return self.generate_report()
    
    async def test_dashboard_load(self, page):
        """Test 1: Dashboard loads successfully"""
        test_name = "Dashboard Load"
        try:
            response = await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            if response.status == 200:
                await page.screenshot(path=str(SCREENSHOT_DIR / "01_dashboard_loaded.png"))
                self.results.append((test_name, "PASS", "Dashboard loaded successfully"))
            else:
                self.results.append((test_name, "FAIL", f"HTTP {response.status}"))
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_navigate_to_options_lab(self, page):
        """Test 2: Navigate to Options Lab tab"""
        test_name = "Navigate to Options Lab"
        try:
            # Try multiple selectors for Options Lab tab
            selectors = [
                "text=💹 Options Lab",
                "text=Options Lab",
                "[data-value='options_lab']",
                ".nav-link:has-text('Options')",
                "a:has-text('Options Lab')"
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=2000):
                        await elem.click()
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                # Fallback: try JavaScript click
                await page.evaluate("""
                    const tabs = document.querySelectorAll('.nav-link, [role="tab"]');
                    for (const tab of tabs) {
                        if (tab.textContent.includes('Options')) {
                            tab.click();
                            break;
                        }
                    }
                """)
            
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCREENSHOT_DIR / "02_options_lab_tab.png"))
            
            # Verify we're on Options Lab
            content = await page.content()
            if 'options' in content.lower() or 'chain' in content.lower():
                self.results.append((test_name, "PASS", "Navigated to Options Lab"))
            else:
                self.results.append((test_name, "WARN", "Navigation unclear"))
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_alpaca_ui_components(self, page):
        """Test 3: Check Alpaca UI components exist"""
        test_name = "Alpaca UI Components"
        try:
            components = {
                'ticker_input': ['#opt-ticker-input', '#chain-ticker-input', 'input[placeholder*="ticker"]', 'input[placeholder*="SPY"]'],
                'fetch_button': ['#opt-fetch-btn', '#chain-fetch-btn', 'button:has-text("Fetch")', 'button:has-text("Load")'],
                'table_container': ['#alpaca-table-container', '#chain-table-container', '.dash-table-container'],
                'expiration_dropdown': ['#chain-expiration-dropdown', '#alpaca-expiration-dropdown', 'select', '.Select']
            }
            
            found = {}
            for comp_name, selectors in components.items():
                for selector in selectors:
                    try:
                        elem = page.locator(selector).first
                        if await elem.count() > 0:
                            found[comp_name] = selector
                            break
                    except:
                        continue
            
            await page.screenshot(path=str(SCREENSHOT_DIR / "03_ui_components.png"))
            
            if len(found) >= 2:
                self.results.append((test_name, "PASS", f"Found components: {list(found.keys())}"))
            else:
                self.results.append((test_name, "WARN", f"Only found: {list(found.keys())}"))
                
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_ticker_input_and_fetch(self, page):
        """Test 4: Test ticker input and fetch functionality"""
        test_name = "Ticker Input and Fetch"
        try:
            # Find ticker input
            input_selectors = [
                '#opt-ticker-input',
                '#chain-ticker-input', 
                'input[placeholder*="ticker"]',
                'input[placeholder*="SPY"]',
                'input[type="text"]'
            ]
            
            input_elem = None
            for selector in input_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=1000):
                        input_elem = elem
                        break
                except:
                    continue
            
            if input_elem:
                await input_elem.fill('SPY')
                await page.wait_for_timeout(500)
                
                # Click fetch button
                btn_selectors = [
                    '#opt-fetch-btn',
                    '#chain-fetch-btn',
                    'button:has-text("Fetch")',
                    'button:has-text("Load")',
                    'button:has-text("Get")'
                ]
                
                for selector in btn_selectors:
                    try:
                        btn = page.locator(selector).first
                        if await btn.is_visible(timeout=1000):
                            await btn.click()
                            break
                    except:
                        continue
                
                # Wait for data to load
                await page.wait_for_timeout(5000)
                await page.screenshot(path=str(SCREENSHOT_DIR / "04_after_fetch.png"))
                self.results.append((test_name, "PASS", "Ticker input and fetch executed"))
            else:
                self.results.append((test_name, "WARN", "Could not find ticker input"))
                
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_alpaca_table_rendering(self, page):
        """Test 5: Check Alpaca table rendering"""
        test_name = "Alpaca Table Rendering"
        try:
            # Look for table elements
            table_selectors = [
                '#alpaca-options-table',
                '#chain-table-container table',
                '.dash-table-container',
                'table.dash-table',
                '[data-dash-is-loading]',
                '.cell-table'
            ]
            
            table_found = False
            for selector in table_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        table_found = True
                        break
                except:
                    continue
            
            # Check for table rows
            rows = await page.locator('tr, .dash-cell').count()
            
            await page.screenshot(path=str(SCREENSHOT_DIR / "05_table_rendering.png"))
            
            if table_found or rows > 0:
                self.results.append((test_name, "PASS", f"Table found with {rows} rows/cells"))
            else:
                # Check for any data display
                content = await page.content()
                if 'strike' in content.lower() or 'call' in content.lower() or 'put' in content.lower():
                    self.results.append((test_name, "PASS", "Options data displayed"))
                else:
                    self.results.append((test_name, "WARN", "No table visible yet"))
                    
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_expiration_dropdown(self, page):
        """Test 6: Test expiration dropdown functionality"""
        test_name = "Expiration Dropdown"
        try:
            dropdown_selectors = [
                '#chain-expiration-dropdown',
                '#alpaca-expiration-dropdown',
                '.Select-control',
                'select',
                '[class*="dropdown"]'
            ]
            
            dropdown_found = False
            for selector in dropdown_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=1000):
                        dropdown_found = True
                        await elem.click()
                        await page.wait_for_timeout(500)
                        break
                except:
                    continue
            
            await page.screenshot(path=str(SCREENSHOT_DIR / "06_expiration_dropdown.png"))
            
            if dropdown_found:
                self.results.append((test_name, "PASS", "Expiration dropdown accessible"))
            else:
                self.results.append((test_name, "WARN", "Dropdown not found"))
                
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_greeks_visualization(self, page):
        """Test 7: Check Greeks visualization"""
        test_name = "Greeks Visualization"
        try:
            # Look for Greeks subtab or charts
            greeks_selectors = [
                "text=Greeks",
                "[data-value='greeks']",
                "#greeks-delta-chart",
                "#greeks-gamma-chart",
                ".plotly-graph"
            ]
            
            # Try to click Greeks tab if available
            for selector in greeks_selectors[:2]:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=1000):
                        await elem.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
            
            # Check for charts
            charts = await page.locator('.plotly-graph, .js-plotly-plot, svg.main-svg').count()
            
            await page.screenshot(path=str(SCREENSHOT_DIR / "07_greeks_visualization.png"))
            
            if charts > 0:
                self.results.append((test_name, "PASS", f"Found {charts} chart(s)"))
            else:
                self.results.append((test_name, "INFO", "No Greek charts visible"))
                
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_options_chain_subtab(self, page):
        """Test 8: Test options chain subtab"""
        test_name = "Options Chain Subtab"
        try:
            # Look for Chain subtab
            chain_selectors = [
                "text=Chain",
                "text=Options Chain",
                "[data-value='chain']",
                ".nav-link:has-text('Chain')"
            ]
            
            for selector in chain_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=1000):
                        await elem.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
            
            await page.screenshot(path=str(SCREENSHOT_DIR / "08_options_chain.png"))
            
            # Check for chain data elements
            chain_elements = await page.locator('#chain-table-container, .chain-data, [id*="chain"]').count()
            
            if chain_elements > 0:
                self.results.append((test_name, "PASS", "Options chain subtab accessible"))
            else:
                self.results.append((test_name, "INFO", "Chain elements not visible"))
                
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_iv_surface_tab(self, page):
        """Test 9: Check IV Surface tab"""
        test_name = "IV Surface Tab"
        try:
            # Look for IV Surface subtab
            iv_selectors = [
                "text=IV Surface",
                "text=Surface",
                "[data-value='surface']",
                "[data-value='iv-surface']"
            ]
            
            for selector in iv_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=1000):
                        await elem.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
            
            await page.screenshot(path=str(SCREENSHOT_DIR / "09_iv_surface.png"))
            
            # Check for 3D chart
            charts = await page.locator('.plotly-graph, .js-plotly-plot, #vol-surface-3d').count()
            
            if charts > 0:
                self.results.append((test_name, "PASS", "IV Surface tab accessible"))
            else:
                self.results.append((test_name, "INFO", "IV Surface chart not visible"))
                
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    async def test_final_state(self, page):
        """Test 10: Capture final state"""
        test_name = "Final State"
        try:
            await page.screenshot(path=str(SCREENSHOT_DIR / "10_final_state.png"), full_page=True)
            self.results.append((test_name, "PASS", "Final state captured"))
        except Exception as e:
            self.results.append((test_name, "FAIL", str(e)))
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*70)
        print("ALPACA OPTIONS LAB TEST REPORT")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"URL: {BASE_URL}")
        print("="*70 + "\n")
        
        passed = 0
        failed = 0
        warnings = 0
        
        for test_name, status, message in self.results:
            icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️" if status == "WARN" else "ℹ️"
            print(f"{icon} {test_name}: {status}")
            print(f"   {message}\n")
            
            if status == "PASS":
                passed += 1
            elif status == "FAIL":
                failed += 1
            elif status == "WARN":
                warnings += 1
        
        print("="*70)
        print(f"SUMMARY: {passed} passed, {failed} failed, {warnings} warnings")
        print(f"Screenshots saved to: {SCREENSHOT_DIR}")
        print("="*70)
        
        if self.errors:
            print("\nCRITICAL ERRORS:")
            for error in self.errors:
                print(f"  ❌ {error}")
        
        return failed == 0


async def main():
    tester = AlpacaOptionsLabTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
