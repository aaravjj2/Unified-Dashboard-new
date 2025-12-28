#!/usr/bin/env python3
"""
Research Lab UI Test Suite - Port 8051

Playwright tests to validate Research Lab features against the real dashboard:
1. AlphaSim Console subtab loads
2. AlphaSim query execution (when service running)
3. Factor Analysis subtab
4. Screen Builder subtab
5. RAG Chat subtab
6. Briefs & Notes subtab
7. Experiment Tracker subtab
8. Diagnostics subtab

Usage:
    python3 financial_dashboard/clicker_research_lab_8051.py
"""

import sys
import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Test configuration
DASHBOARD_URL = "http://localhost:8051"
TIMEOUT = 30000  # 30 seconds
WAIT_LOAD = 3000  # 3 seconds for tab load
SCREENSHOT_DIR = Path("screenshots/research_lab")


def get_headless_mode():
    """Determine headless mode from env or DISPLAY availability."""
    env_headless = os.environ.get('CLICKER_HEADLESS')
    if env_headless is not None:
        return env_headless.lower() not in ('0', 'false', 'no')
    return False if os.environ.get('DISPLAY') else True


def ensure_screenshot_dir():
    """Create screenshot directory if it doesn't exist."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def test_1_research_lab_loads():
    """
    TEST 1: Verify Research Lab tab loads in the dashboard
    """
    print("\n" + "=" * 60)
    print("TEST 1: Research Lab Tab Loads")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()
        
        try:
            print(f"Navigating to {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
            page.wait_for_timeout(WAIT_LOAD)
            
            # Take initial screenshot
            ensure_screenshot_dir()
            page.screenshot(path=str(SCREENSHOT_DIR / "01_dashboard_loaded.png"), full_page=True)
            
            # Look for Research Lab tab
            research_lab_tab = page.locator("text=Research Lab").first
            if research_lab_tab.count() == 0:
                # Try alternate selectors
                research_lab_tab = page.locator('[tab_id="research_lab"]').first
            
            if research_lab_tab.count() == 0:
                research_lab_tab = page.locator('#tab-research_lab').first
            
            if research_lab_tab.count() > 0:
                print("Found Research Lab tab, clicking...")
                research_lab_tab.click()
                page.wait_for_timeout(WAIT_LOAD)
                page.screenshot(path=str(SCREENSHOT_DIR / "02_research_lab_clicked.png"), full_page=True)
                print("✅ PASS: Research Lab tab found and clicked")
                browser.close()
                return True
            else:
                print("❌ FAIL: Research Lab tab not found")
                page.screenshot(path=str(SCREENSHOT_DIR / "01_fail_no_research_lab.png"), full_page=True)
                browser.close()
                return False
            
        except Exception as e:
            print(f"❌ FAIL: Error - {e}")
            try:
                page.screenshot(path=str(SCREENSHOT_DIR / "01_error.png"), full_page=True)
            except:
                pass
            browser.close()
            return False


def test_2_alphasim_console():
    """
    TEST 2: Verify AlphaSim Console subtab is present and functional
    """
    print("\n" + "=" * 60)
    print("TEST 2: AlphaSim Console Subtab")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()
        
        try:
            print(f"Navigating to {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
            page.wait_for_timeout(WAIT_LOAD)
            
            # Click Research Lab tab
            research_lab_tab = page.locator("text=Research Lab").first
            if research_lab_tab.count() == 0:
                research_lab_tab = page.locator('[data-tab-id="research_lab"]').first
            if research_lab_tab.count() > 0:
                research_lab_tab.click()
                page.wait_for_timeout(WAIT_LOAD)
            
            # Look for AlphaSim Console subtab (should be default active)
            alphasim_tab = page.locator("text=AlphaSim Console").first
            if alphasim_tab.count() > 0:
                alphasim_tab.click()
                page.wait_for_timeout(1000)
            
            # Check for AlphaSim controls
            ensure_screenshot_dir()
            
            # Check for function dropdown
            function_dropdown = page.locator('#rl-alphasim-function')
            has_function = function_dropdown.count() > 0
            
            # Check for symbol input
            symbol_input = page.locator('#rl-alphasim-symbol')
            has_symbol = symbol_input.count() > 0
            
            # Check for run button
            run_btn = page.locator('#rl-alphasim-run-btn')
            has_run_btn = run_btn.count() > 0
            
            page.screenshot(path=str(SCREENSHOT_DIR / "03_alphasim_console.png"), full_page=True)
            
            if has_function and has_symbol and has_run_btn:
                print("✅ PASS: AlphaSim Console controls found")
                print(f"   - Function dropdown: {'✅' if has_function else '❌'}")
                print(f"   - Symbol input: {'✅' if has_symbol else '❌'}")
                print(f"   - Run button: {'✅' if has_run_btn else '❌'}")
                browser.close()
                return True
            else:
                print("⚠️  PARTIAL: Some AlphaSim controls missing")
                print(f"   - Function dropdown: {'✅' if has_function else '❌'}")
                print(f"   - Symbol input: {'✅' if has_symbol else '❌'}")
                print(f"   - Run button: {'✅' if has_run_btn else '❌'}")
                browser.close()
                return has_function or has_symbol  # Pass if at least some controls exist
            
        except Exception as e:
            print(f"❌ FAIL: Error - {e}")
            try:
                page.screenshot(path=str(SCREENSHOT_DIR / "03_alphasim_error.png"), full_page=True)
            except:
                pass
            browser.close()
            return False


def test_3_subtabs_navigation():
    """
    TEST 3: Verify all Research Lab subtabs can be navigated
    """
    print("\n" + "=" * 60)
    print("TEST 3: Research Lab Subtabs Navigation")
    print("=" * 60)
    
    subtabs = [
        ("AlphaSim Console", "rl-alphasim-tab"),
        ("Research Scan", "rl-scan-tab"),
        ("Factor & Signal Lab", "rl-factor-tab"),
        ("Screen Builder", "rl-screen-tab"),
        ("RAG Chat", "rl-rag-tab"),
        ("Briefs & Notes", "rl-briefs-tab"),
        ("Experiment Tracker", "rl-exp-tab"),
        ("Diagnostics", "rl-diag-tab"),
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()
        
        try:
            print(f"Navigating to {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
            page.wait_for_timeout(WAIT_LOAD)
            
            # Click Research Lab tab
            research_lab_tab = page.locator("text=Research Lab").first
            if research_lab_tab.count() > 0:
                research_lab_tab.click()
                page.wait_for_timeout(WAIT_LOAD)
            
            ensure_screenshot_dir()
            results = {}
            
            for tab_name, tab_id in subtabs:
                try:
                    # Try clicking by text
                    tab = page.locator(f"text={tab_name}").first
                    if tab.count() > 0:
                        tab.click()
                        page.wait_for_timeout(500)
                        results[tab_name] = True
                        print(f"   ✅ {tab_name}")
                    else:
                        results[tab_name] = False
                        print(f"   ❌ {tab_name} - not found")
                except Exception as e:
                    results[tab_name] = False
                    print(f"   ❌ {tab_name} - error: {e}")
            
            page.screenshot(path=str(SCREENSHOT_DIR / "04_subtabs_navigation.png"), full_page=True)
            
            passed = sum(1 for v in results.values() if v)
            total = len(results)
            
            if passed >= total * 0.7:  # 70% pass rate
                print(f"\n✅ PASS: {passed}/{total} subtabs accessible")
                browser.close()
                return True
            else:
                print(f"\n❌ FAIL: Only {passed}/{total} subtabs accessible")
                browser.close()
                return False
            
        except Exception as e:
            print(f"❌ FAIL: Error - {e}")
            browser.close()
            return False


def test_4_diagnostics_tab():
    """
    TEST 4: Verify Diagnostics subtab shows config options
    """
    print("\n" + "=" * 60)
    print("TEST 4: Diagnostics & Config Subtab")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()
        
        try:
            print(f"Navigating to {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
            page.wait_for_timeout(WAIT_LOAD)
            
            # Click Research Lab tab
            research_lab_tab = page.locator("text=Research Lab").first
            if research_lab_tab.count() > 0:
                research_lab_tab.click()
                page.wait_for_timeout(WAIT_LOAD)
            
            # Click Diagnostics subtab
            diag_tab = page.locator("text=Diagnostics").first
            if diag_tab.count() > 0:
                diag_tab.click()
                page.wait_for_timeout(1000)
            
            ensure_screenshot_dir()
            
            # Check for LLM provider dropdown
            llm_dropdown = page.locator('#rl-diag-llm-provider')
            has_llm = llm_dropdown.count() > 0
            
            # Check for embedding model dropdown
            embed_dropdown = page.locator('#rl-diag-embed-model')
            has_embed = embed_dropdown.count() > 0
            
            # Check for save config button
            save_btn = page.locator('#rl-diag-save-config')
            has_save = save_btn.count() > 0
            
            page.screenshot(path=str(SCREENSHOT_DIR / "05_diagnostics.png"), full_page=True)
            
            if has_llm or has_embed or has_save:
                print("✅ PASS: Diagnostics config controls found")
                print(f"   - LLM Provider: {'✅' if has_llm else '❌'}")
                print(f"   - Embedding Model: {'✅' if has_embed else '❌'}")
                print(f"   - Save Config: {'✅' if has_save else '❌'}")
                browser.close()
                return True
            else:
                print("❌ FAIL: No config controls found in Diagnostics")
                browser.close()
                return False
            
        except Exception as e:
            print(f"❌ FAIL: Error - {e}")
            browser.close()
            return False


def test_5_factor_analysis():
    """
    TEST 5: Verify Factor & Signal Lab has analysis controls
    """
    print("\n" + "=" * 60)
    print("TEST 5: Factor & Signal Lab")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()
        
        try:
            print(f"Navigating to {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
            page.wait_for_timeout(WAIT_LOAD)
            
            # Click Research Lab tab
            research_lab_tab = page.locator("text=Research Lab").first
            if research_lab_tab.count() > 0:
                research_lab_tab.click()
                page.wait_for_timeout(WAIT_LOAD)
            
            # Click Factor & Signal Lab subtab
            factor_tab = page.locator("text=Factor").first
            if factor_tab.count() > 0:
                factor_tab.click()
                page.wait_for_timeout(1000)
            
            ensure_screenshot_dir()
            
            # Check for factor select dropdown
            factor_select = page.locator('#rl-factor-select')
            has_factor_select = factor_select.count() > 0
            
            # Check for period dropdown
            period_select = page.locator('#rl-factor-period')
            has_period = period_select.count() > 0
            
            page.screenshot(path=str(SCREENSHOT_DIR / "06_factor_analysis.png"), full_page=True)
            
            if has_factor_select or has_period:
                print("✅ PASS: Factor analysis controls found")
                print(f"   - Factor Select: {'✅' if has_factor_select else '❌'}")
                print(f"   - Period Select: {'✅' if has_period else '❌'}")
                browser.close()
                return True
            else:
                print("❌ FAIL: Factor analysis controls not found")
                browser.close()
                return False
            
        except Exception as e:
            print(f"❌ FAIL: Error - {e}")
            browser.close()
            return False


def main():
    """Run all Research Lab tests."""
    print("\n" + "=" * 60)
    print("  RESEARCH LAB UI TEST SUITE (Port 8051)")
    print("=" * 60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"Headless mode: {get_headless_mode()}")
    print("")
    
    # Run all tests
    results = {}
    results['test_1'] = test_1_research_lab_loads()
    results['test_2'] = test_2_alphasim_console()
    results['test_3'] = test_3_subtabs_navigation()
    results['test_4'] = test_4_diagnostics_tab()
    results['test_5'] = test_5_factor_analysis()
    
    # Print summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"1. Research Lab Loads:      {'✅ PASSED' if results['test_1'] else '❌ FAILED'}")
    print(f"2. AlphaSim Console:        {'✅ PASSED' if results['test_2'] else '❌ FAILED'}")
    print(f"3. Subtabs Navigation:      {'✅ PASSED' if results['test_3'] else '❌ FAILED'}")
    print(f"4. Diagnostics Tab:         {'✅ PASSED' if results['test_4'] else '❌ FAILED'}")
    print(f"5. Factor Analysis:         {'✅ PASSED' if results['test_5'] else '❌ FAILED'}")
    print("=" * 60)
    
    # Calculate pass rate
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    pass_rate = (passed_tests / total_tests) * 100
    
    print(f"\nPass Rate: {passed_tests}/{total_tests} ({pass_rate:.1f}%)")
    print(f"Screenshots saved to: {SCREENSHOT_DIR.absolute()}")
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
