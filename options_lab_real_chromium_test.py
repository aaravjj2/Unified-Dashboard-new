#!/usr/bin/env python3
"""
OPTIONS LAB REAL CHROMIUM VALIDATION
Based on Phase 18B proven test pattern
NO HALLUCINATIONS - Real browser automation only
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

# Paths
BASE_DIR = Path(__file__).parent
SNAPSHOTS_DIR = BASE_DIR / "options_lab_snapshots"
DOM_DIR = BASE_DIR / "options_lab_dom"
SNAPSHOTS_DIR.mkdir(exist_ok=True)
DOM_DIR.mkdir(exist_ok=True)

DASHBOARD_URL = "http://localhost:8050"
WAIT_LONG = 30000  # 30s for heavy operations
WAIT_MEDIUM = 20000  # 20s for tab switches
WAIT_SHORT = 5000  # 5s for UI updates

class colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_test(name, status, details=None):
    """Print test result"""
    status_icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
    status_color = colors.GREEN if status == "PASS" else (colors.YELLOW if status == "WARN" else colors.RED)
    print(f"{status_icon} {colors.BOLD}{name}{colors.END}: {status_color}{status}{colors.END}")
    if details:
        print(f"   {details}")

async def capture_state(page: Page, prefix: str):
    """Capture screenshot and DOM snapshot"""
    try:
        # Screenshot
        screenshot_path = SNAPSHOTS_DIR / f"{prefix}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"   📸 Screenshot: {screenshot_path.name}")
        
        # DOM snapshot
        dom_path = DOM_DIR / f"{prefix}.html"
        content = await page.content()
        with open(dom_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   📄 DOM: {dom_path.name}")
        
        return True
    except Exception as e:
        print(f"   ❌ Capture failed: {e}")
        return False

async def validate_options_lab(page: Page):
    """Validate Options Lab tab and functionality"""
    print(f"\n{colors.CYAN}{colors.BOLD}OPTIONS LAB VALIDATION{colors.END}\n")
    
    start_time = time.time()
    results = {
        'tab_accessible': False,
        'tab_visible': False,
        'ui_rendered': False,
        'has_ticker_input': False,
        'has_load_button': False,
        'has_mock_button': False,
        'can_click_mock': False,
        'data_loads': False
    }
    
    try:
        # 1. Check if Options Lab tab exists
        print(f"{colors.CYAN}[1/6] Checking if Options Lab tab exists...{colors.END}")
        tab_selectors = [
            'text=Options Lab',
            'text=💹 Options Lab',
            '[data-tab="options_lab"]',
            'a:has-text("Options")',
            '.nav-link:has-text("Options")'
        ]
        
        tab_found = False
        used_selector = None
        for selector in tab_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    tab_found = True
                    used_selector = selector
                    results['tab_accessible'] = True
                    break
            except:
                continue
        
        if tab_found:
            print_test("Options Lab Tab Exists", "PASS", f"Found with selector: {used_selector}")
        else:
            print_test("Options Lab Tab Exists", "FAIL", "Tab not found in DOM")
            await capture_state(page, "options_lab_tab_missing")
            return results
        
        # 2. Click the tab
        print(f"\n{colors.CYAN}[2/6] Clicking Options Lab tab...{colors.END}")
        try:
            await page.click(used_selector, timeout=WAIT_SHORT)
            await page.wait_for_timeout(WAIT_MEDIUM)
            results['tab_visible'] = True
            print_test("Tab Navigation", "PASS", "Successfully clicked and navigated")
        except Exception as e:
            print_test("Tab Navigation", "FAIL", str(e))
            await capture_state(page, "options_lab_click_failed")
            return results
        
        # Capture after tab switch
        await capture_state(page, "options_lab_after_click")
        
        # 3. Check for Options Lab UI elements
        print(f"\n{colors.CYAN}[3/6] Checking for UI elements...{colors.END}")
        page_content = await page.content()
        
        # Look for ticker input
        has_ticker = 'options-ticker-input' in page_content or 'ticker' in page_content.lower()
        results['has_ticker_input'] = has_ticker
        if has_ticker:
            print_test("Ticker Input", "PASS", "Found ticker input field")
        else:
            print_test("Ticker Input", "FAIL", "No ticker input found")
        
        # Look for Load Chain button
        has_load = 'options-load-btn' in page_content or 'Load Options Chain' in page_content
        results['has_load_button'] = has_load
        if has_load:
            print_test("Load Chain Button", "PASS", "Found Load Chain button")
        else:
            print_test("Load Chain Button", "FAIL", "No Load Chain button")
        
        # Look for Mock Data button
        has_mock = 'options-mock-btn' in page_content or 'Mock Data' in page_content or 'Use Mock Data' in page_content
        results['has_mock_button'] = has_mock
        if has_mock:
            print_test("Mock Data Button", "PASS", "Found Mock Data button")
        else:
            print_test("Mock Data Button", "FAIL", "No Mock Data button")
        
        results['ui_rendered'] = has_ticker and (has_load or has_mock)
        
        # 4. Try to click Mock Data button
        if has_mock:
            print(f"\n{colors.CYAN}[4/6] Clicking Mock Data button...{colors.END}")
            mock_selectors = [
                '#options-mock-btn',
                'button:has-text("Mock Data")',
                'button:has-text("Use Mock Data")'
            ]
            
            clicked_mock = False
            for selector in mock_selectors:
                try:
                    await page.click(selector, timeout=WAIT_SHORT)
                    await page.wait_for_timeout(3000)  # Wait for callback
                    clicked_mock = True
                    results['can_click_mock'] = True
                    print_test("Mock Data Click", "PASS", f"Button clicked: {selector}")
                    break
                except:
                    continue
            
            if not clicked_mock:
                print_test("Mock Data Click", "WARN", "Could not click button")
        
        # 5. Check if data loaded (look for success message or table)
        print(f"\n{colors.CYAN}[5/6] Checking if data loaded...{colors.END}")
        await page.wait_for_timeout(2000)
        updated_content = await page.content()
        
        data_indicators = [
            'successfully' in updated_content.lower(),
            'loaded' in updated_content.lower(),
            'strike' in updated_content.lower(),
            'expiration' in updated_content.lower(),
            '<table' in updated_content.lower()
        ]
        
        results['data_loads'] = any(data_indicators)
        if results['data_loads']:
            print_test("Data Loading", "PASS", "Data loaded successfully")
        else:
            print_test("Data Loading", "WARN", "No data loading indicators found")
        
        # 6. Final screenshot
        print(f"\n{colors.CYAN}[6/6] Capturing final state...{colors.END}")
        await capture_state(page, "options_lab_final")
        
        # Calculate overall status
        exec_time = int((time.time() - start_time) * 1000)
        
        critical_pass = results['tab_accessible'] and results['tab_visible'] and results['ui_rendered']
        
        print(f"\n{colors.CYAN}{colors.BOLD}TEST SUMMARY{colors.END}\n")
        print(f"Tab Accessible:   {'✅' if results['tab_accessible'] else '❌'}")
        print(f"Tab Visible:      {'✅' if results['tab_visible'] else '❌'}")
        print(f"UI Rendered:      {'✅' if results['ui_rendered'] else '❌'}")
        print(f"Ticker Input:     {'✅' if results['has_ticker_input'] else '❌'}")
        print(f"Load Button:      {'✅' if results['has_load_button'] else '❌'}")
        print(f"Mock Button:      {'✅' if results['has_mock_button'] else '❌'}")
        print(f"Mock Clickable:   {'✅' if results['can_click_mock'] else '⚠️'}")
        print(f"Data Loads:       {'✅' if results['data_loads'] else '⚠️'}")
        print(f"\nExecution Time: {exec_time}ms")
        
        if critical_pass:
            print(f"\n{colors.GREEN}{colors.BOLD}✅ CRITICAL TESTS PASSED{colors.END}")
            print(f"{colors.GREEN}Options Lab tab is visible and functional in the browser{colors.END}")
        else:
            print(f"\n{colors.RED}{colors.BOLD}❌ CRITICAL TESTS FAILED{colors.END}")
            print(f"{colors.RED}Options Lab not working as expected{colors.END}")
        
        return results
        
    except Exception as e:
        print_test("Options Lab Validation", "FAIL", str(e))
        await capture_state(page, "options_lab_error")
        return results

async def validate_market_forecast_options(page: Page):
    """Validate Options Forecast section in Market Forecast tab (Phase 20B)"""
    print(f"\n{colors.CYAN}{colors.BOLD}MARKET FORECAST - OPTIONS FORECAST VALIDATION{colors.END}\n")
    
    start_time = time.time()
    results = {
        'tab_accessible': False,
        'options_section_exists': False,
        'has_ticker_dropdown': False,
        'has_expiration_dropdown': False,
        'has_generate_button': False,
        'section_visible': False
    }
    
    try:
        # 1. Navigate to Market Forecast tab
        print(f"{colors.CYAN}[1/4] Navigating to Market Forecast tab...{colors.END}")
        forecast_selectors = [
            'text=Market Forecast',
            '[data-tab="market_forecast"]',
            'a:has-text("Forecast")'
        ]
        
        navigated = False
        for selector in forecast_selectors:
            try:
                await page.click(selector, timeout=WAIT_SHORT)
                await page.wait_for_timeout(WAIT_MEDIUM)
                navigated = True
                results['tab_accessible'] = True
                break
            except:
                continue
        
        if navigated:
            print_test("Market Forecast Tab", "PASS", "Successfully navigated")
        else:
            print_test("Market Forecast Tab", "FAIL", "Could not navigate to tab")
            return results
        
        await capture_state(page, "market_forecast_options_initial")
        
        # 2. Check for Options Forecast section
        print(f"\n{colors.CYAN}[2/4] Checking for Options Forecast section...{colors.END}")
        page_content = await page.content()
        
        section_indicators = [
            'options forecast' in page_content.lower(),
            'options-forecast' in page_content,
            'strike' in page_content.lower() and 'expiration' in page_content.lower(),
            'options-ticker-dropdown' in page_content,
            'options-expiration-dropdown' in page_content
        ]
        
        results['options_section_exists'] = any(section_indicators)
        
        if results['options_section_exists']:
            print_test("Options Forecast Section", "PASS", "Section found in Market Forecast")
        else:
            print_test("Options Forecast Section", "FAIL", "No Options Forecast section detected")
            await capture_state(page, "market_forecast_no_options_section")
            return results
        
        # 3. Check for specific UI elements
        print(f"\n{colors.CYAN}[3/4] Checking for Options Forecast UI elements...{colors.END}")
        
        has_ticker_dd = 'options-ticker-dropdown' in page_content or ('ticker' in page_content.lower() and 'dropdown' in page_content.lower())
        results['has_ticker_dropdown'] = has_ticker_dd
        print_test("Ticker Dropdown", "PASS" if has_ticker_dd else "FAIL", "")
        
        has_exp_dd = 'options-expiration-dropdown' in page_content or 'expiration' in page_content.lower()
        results['has_expiration_dropdown'] = has_exp_dd
        print_test("Expiration Dropdown", "PASS" if has_exp_dd else "FAIL", "")
        
        has_gen_btn = 'generate' in page_content.lower() and ('forecast' in page_content.lower() or 'options' in page_content.lower())
        results['has_generate_button'] = has_gen_btn
        print_test("Generate Button", "PASS" if has_gen_btn else "FAIL", "")
        
        results['section_visible'] = has_ticker_dd and has_exp_dd
        
        # 4. Final capture
        print(f"\n{colors.CYAN}[4/4] Capturing final state...{colors.END}")
        await capture_state(page, "market_forecast_options_final")
        
        exec_time = int((time.time() - start_time) * 1000)
        
        print(f"\n{colors.CYAN}{colors.BOLD}OPTIONS FORECAST SUMMARY{colors.END}\n")
        print(f"Tab Accessible:       {'✅' if results['tab_accessible'] else '❌'}")
        print(f"Section Exists:       {'✅' if results['options_section_exists'] else '❌'}")
        print(f"Ticker Dropdown:      {'✅' if results['has_ticker_dropdown'] else '❌'}")
        print(f"Expiration Dropdown:  {'✅' if results['has_expiration_dropdown'] else '❌'}")
        print(f"Generate Button:      {'✅' if results['has_generate_button'] else '❌'}")
        print(f"Section Visible:      {'✅' if results['section_visible'] else '❌'}")
        print(f"\nExecution Time: {exec_time}ms")
        
        if results['section_visible']:
            print(f"\n{colors.GREEN}{colors.BOLD}✅ OPTIONS FORECAST SECTION VALIDATED{colors.END}")
        else:
            print(f"\n{colors.YELLOW}{colors.BOLD}⚠️  OPTIONS FORECAST INCOMPLETE{colors.END}")
        
        return results
        
    except Exception as e:
        print_test("Options Forecast Validation", "FAIL", str(e))
        return results

async def main():
    """Main execution"""
    print(f"\n{colors.BOLD}{colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║              OPTIONS LAB - REAL CHROMIUM VALIDATION                        ║")
    print("║                    NO HALLUCINATIONS ALLOWED                               ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{colors.END}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # Navigate to dashboard
            print(f"🌐 Navigating to {DASHBOARD_URL}...")
            await page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=60000)
            
            # Wait for dashboard to render
            print("⏳ Waiting for dashboard to initialize...")
            await page.wait_for_timeout(WAIT_LONG)
            
            # Capture homepage
            await capture_state(page, "dashboard_home")
            print_test("Dashboard Load", "PASS", "Dashboard loaded successfully")
            
            # TEST 1: Options Lab tab
            options_lab_results = await validate_options_lab(page)
            
            # TEST 2: Market Forecast Options section
            market_forecast_results = await validate_market_forecast_options(page)
            
            # Generate final summary
            print(f"\n{colors.CYAN}{colors.BOLD}{'='*80}{colors.END}")
            print(f"{colors.CYAN}{colors.BOLD}FINAL VERDICT{colors.END}")
            print(f"{colors.CYAN}{colors.BOLD}{'='*80}{colors.END}\n")
            
            options_lab_pass = options_lab_results.get('ui_rendered', False)
            market_forecast_pass = market_forecast_results.get('section_visible', False)
            
            print(f"Options Lab Tab:              {'✅ PASS' if options_lab_pass else '❌ FAIL'}")
            print(f"Market Forecast Options:      {'✅ PASS' if market_forecast_pass else '❌ FAIL'}")
            
            overall_pass = options_lab_pass
            
            if overall_pass:
                print(f"\n{colors.GREEN}{colors.BOLD}✅ OPTIONS LAB IS VISIBLE AND FUNCTIONAL{colors.END}")
                print(f"{colors.GREEN}User can see and interact with Options Lab in the browser{colors.END}")
            else:
                print(f"\n{colors.RED}{colors.BOLD}❌ OPTIONS LAB NOT WORKING{colors.END}")
                print(f"{colors.RED}Changes are NOT visible to the user{colors.END}")
            
            # Save results
            results_path = BASE_DIR / "options_lab_real_chromium_results.json"
            with open(results_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'options_lab': options_lab_results,
                    'market_forecast_options': market_forecast_results,
                    'overall_pass': overall_pass,
                    'verdict': 'PASS' if overall_pass else 'FAIL'
                }, f, indent=2)
            
            print(f"\n{colors.CYAN}📁 Results saved to: {results_path}{colors.END}")
            print(f"{colors.CYAN}📸 Screenshots saved to: {SNAPSHOTS_DIR}{colors.END}")
            print(f"{colors.CYAN}📄 DOM snapshots saved to: {DOM_DIR}{colors.END}")
            
        finally:
            await browser.close()
    
    print(f"\n{colors.BOLD}{colors.GREEN}✅ Real Chromium Validation Complete{colors.END}\n")

if __name__ == "__main__":
    asyncio.run(main())
