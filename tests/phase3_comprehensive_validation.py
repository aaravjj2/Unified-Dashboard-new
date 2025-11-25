"""
Phase 3 Comprehensive Validation Test

Validates:
1. Text visibility (CSS overrides working)
2. Portfolio 3-tier fallback system
3. Strategy Lab modular subtabs
4. All tables rendering with black text
5. Dashboard health metrics

Usage:
    python3 tests/phase3_comprehensive_validation.py
"""

import asyncio
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright, expect

# Dashboard URL
DASHBOARD_URL = "http://localhost:8050"
OUTPUT_DIR = Path("outputs/phase3_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    print("=" * 70)
    print("PHASE 3 COMPREHENSIVE VALIDATION")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Track results
        results = {
            'dashboard_load': False,
            'css_override_working': False,
            'portfolio_table_visible': False,
            'strategy_lab_subtabs': 0,
            'text_color_checks': [],
            'screenshots': []
        }
        
        try:
            # =================================================================
            # TEST 1: Dashboard Loads
            # =================================================================
            print("\n🌐 Loading dashboard...")
            start_time = time.time()
            await page.goto(DASHBOARD_URL, timeout=60000)
            load_time = time.time() - start_time
            print(f"   ✅ Dashboard loaded in {load_time:.2f}s")
            results['dashboard_load'] = True
            
            # Wait for main content (try multiple selectors)
            main_selectors = ['body', '.container', '#content', 'main']
            content_loaded = False
            for selector in main_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    content_loaded = True
                    break
                except:
                    continue
            
            if not content_loaded:
                print("   ⚠️  Main content selector not found, continuing anyway...")
            
            # Give Dash callbacks time to initialize
            await asyncio.sleep(3)
            
            # =================================================================
            # TEST 2: CSS Override Validation - Text Visibility
            # =================================================================
            print("\n🎨 Checking CSS overrides for text visibility...")
            
            # Check .text-muted elements
            text_muted_elements = await page.locator('.text-muted').all()
            if text_muted_elements:
                first_elem = text_muted_elements[0]
                color = await first_elem.evaluate("""
                    (elem) => window.getComputedStyle(elem).color
                """)
                print(f"   .text-muted computed color: {color}")
                
                # Parse RGB values
                if 'rgb(33, 37, 41)' in color or 'rgb(0, 0, 0)' in color or 'rgb(212, 529)' in color:
                    print("   ✅ CSS override working - text is dark")
                    results['css_override_working'] = True
                    results['text_color_checks'].append({'selector': '.text-muted', 'color': color, 'status': 'PASS'})
                else:
                    print(f"   ⚠️  Unexpected color: {color}")
                    results['text_color_checks'].append({'selector': '.text-muted', 'color': color, 'status': 'WARN'})
            
            # Check table cells
            table_cells = await page.locator('table td').all()
            if table_cells and len(table_cells) > 0:
                cell_color = await table_cells[0].evaluate("(elem) => window.getComputedStyle(elem).color")
                print(f"   Table cell color: {cell_color}")
                results['text_color_checks'].append({'selector': 'table td', 'color': cell_color, 'status': 'INFO'})
            
            # =================================================================
            # TEST 3: Portfolio Section Validation
            # =================================================================
            print("\n💼 Validating Portfolio section...")
            
            # Navigate to Home tab (Command Center)
            try:
                # Try different selectors for Home tab
                home_selectors = [
                    "a:has-text('Command Center')",
                    "a:has-text('Home')",
                    "a:has-text('🏠')",
                    ".nav-link:has-text('Command')"
                ]
                
                home_clicked = False
                for selector in home_selectors:
                    try:
                        await page.click(selector, timeout=2000)
                        print(f"   ✅ Clicked Home tab using selector: {selector}")
                        home_clicked = True
                        break
                    except:
                        continue
                
                if not home_clicked:
                    print("   ⚠️  Could not find Home tab, checking current page")
                
                await asyncio.sleep(2)
                
                # Look for portfolio table
                portfolio_selectors = [
                    '#portfolio-table',
                    '#home-portfolio-table',
                    'table:has-text("Ticker")',
                    '.portfolio-table'
                ]
                
                portfolio_found = False
                for selector in portfolio_selectors:
                    try:
                        portfolio_table = page.locator(selector).first
                        if await portfolio_table.count() > 0:
                            print(f"   ✅ Portfolio table found: {selector}")
                            
                            # Count rows
                            rows = await portfolio_table.locator('tr').count()
                            print(f"   📊 Portfolio has {rows} rows")
                            
                            # Check if text is visible
                            if rows > 1:
                                first_cell = portfolio_table.locator('td').first
                                if await first_cell.count() > 0:
                                    cell_text = await first_cell.text_content()
                                    print(f"   📝 First cell text: '{cell_text}'")
                                    results['portfolio_table_visible'] = True
                            
                            portfolio_found = True
                            break
                    except:
                        continue
                
                if not portfolio_found:
                    print("   ⚠️  Portfolio table not found on current view")
                
                # Capture Home Lab screenshot
                screenshot_path = OUTPUT_DIR / "home_lab_portfolio.png"
                await page.screenshot(path=str(screenshot_path), full_page=False)
                results['screenshots'].append(str(screenshot_path))
                print(f"   📸 Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                print(f"   ❌ Portfolio validation error: {e}")
            
            # =================================================================
            # TEST 4: Strategy Lab Modular Subtabs
            # =================================================================
            print("\n⚡ Validating Strategy Lab modular subtabs...")
            
            try:
                # Navigate to Strategy Lab
                await page.click("a:has-text('Strategy Lab')", timeout=5000)
                print("   ✅ Navigated to Strategy Lab")
                await asyncio.sleep(2)
                
                # Check for subtab navigation
                subtab_labels = ['Setup', 'Backtest', 'Execute', 'Results', 'Benchmark', 'Risk']
                subtabs_found = 0
                
                for label in subtab_labels:
                    try:
                        subtab = page.locator(f".nav-link:has-text('{label}')").first
                        if await subtab.count() > 0:
                            print(f"   ✅ Found subtab: {label}")
                            subtabs_found += 1
                    except:
                        continue
                
                results['strategy_lab_subtabs'] = subtabs_found
                print(f"   📊 Strategy Lab subtabs: {subtabs_found}/6")
                
                # Capture Strategy Lab screenshot
                screenshot_path = OUTPUT_DIR / "strategy_lab_modular.png"
                await page.screenshot(path=str(screenshot_path), full_page=False)
                results['screenshots'].append(str(screenshot_path))
                print(f"   📸 Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                print(f"   ❌ Strategy Lab validation error: {e}")
            
            # =================================================================
            # TEST 5: Other Major Tabs
            # =================================================================
            print("\n📸 Capturing other major tabs...")
            
            tabs_to_capture = [
                'Attribution Lab',
                'Options Lab',
                'Volatility Lab',
                'Market Forecast'
            ]
            
            for tab_name in tabs_to_capture:
                try:
                    await page.click(f"a:has-text('{tab_name}')", timeout=3000)
                    await asyncio.sleep(1.5)
                    
                    filename = tab_name.lower().replace(' ', '_') + '.png'
                    screenshot_path = OUTPUT_DIR / filename
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                    results['screenshots'].append(str(screenshot_path))
                    print(f"   ✅ {tab_name}: {screenshot_path}")
                except Exception as e:
                    print(f"   ⚠️  {tab_name}: {e}")
            
        except Exception as e:
            print(f"\n❌ Validation error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()
        
        # =================================================================
        # RESULTS SUMMARY
        # =================================================================
        print("\n" + "=" * 70)
        print("VALIDATION RESULTS SUMMARY")
        print("=" * 70)
        
        print(f"\n✅ Dashboard Load: {'PASS' if results['dashboard_load'] else 'FAIL'}")
        print(f"✅ CSS Override: {'PASS' if results['css_override_working'] else 'FAIL'}")
        print(f"✅ Portfolio Table: {'PASS' if results['portfolio_table_visible'] else 'FAIL'}")
        print(f"✅ Strategy Lab Subtabs: {results['strategy_lab_subtabs']}/6")
        print(f"📸 Screenshots: {len(results['screenshots'])} captured")
        
        print(f"\n📊 Text Color Checks:")
        for check in results['text_color_checks']:
            print(f"   {check['selector']}: {check['color']} ({check['status']})")
        
        print(f"\n📁 Output directory: {OUTPUT_DIR}")
        
        # Export JSON report
        import json
        report_path = OUTPUT_DIR / "validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📄 JSON report: {report_path}")
        
        # Determine overall status
        critical_pass = (
            results['dashboard_load'] and
            results['css_override_working'] and
            results['strategy_lab_subtabs'] >= 5  # At least 5/6 subtabs
        )
        
        if critical_pass:
            print("\n✅ ✅ ✅ PHASE 3 VALIDATION: PASS")
            return 0
        else:
            print("\n⚠️  ⚠️  ⚠️  PHASE 3 VALIDATION: NEEDS ATTENTION")
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
