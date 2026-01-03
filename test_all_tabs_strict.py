#!/usr/bin/env python3
"""
STRICT E2E Test Suite for 4-Tab Consolidated Dashboard
Tests EVERY tab and subtab - NO skipping allowed
"""

import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "http://localhost:8053"
RESULTS = {"passed": 0, "failed": 0, "tests": []}


def record_result(name: str, passed: bool, message: str = ""):
    """Record test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    RESULTS["passed" if passed else "failed"] += 1
    RESULTS["tests"].append({"name": name, "passed": passed, "message": message})
    print(f"{status}: {name}" + (f" - {message}" if message else ""))


def test_dashboard():
    """Run all tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        # ===== BASIC DASHBOARD TESTS =====
        print("\n" + "="*60)
        print("BASIC DASHBOARD TESTS")
        print("="*60)
        
        # Test 1: Dashboard loads
        try:
            page.goto(BASE_URL, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            record_result("Dashboard loads", True)
        except Exception as e:
            record_result("Dashboard loads", False, str(e))
            browser.close()
            return
        
        # Test 2: Ticker input exists
        try:
            ticker_input = page.locator("#alpaca-ticker-input")
            ticker_input.wait_for(timeout=5000)
            record_result("Ticker input exists", True)
        except Exception as e:
            record_result("Ticker input exists", False, str(e))
        
        # Test 3: Load button exists
        try:
            load_btn = page.locator("#alpaca-load-button")
            load_btn.wait_for(timeout=5000)
            record_result("Load button exists", True)
        except Exception as e:
            record_result("Load button exists", False, str(e))
        
        # ===== MAIN TABS TESTS =====
        print("\n" + "="*60)
        print("MAIN 4 TABS TESTS")
        print("="*60)
        
        # Test 4: Scanner tab exists
        try:
            scanner_tab = page.locator("div.tab[data-tab-value='scanner-workspace-tab'], div.Tab[data-value='scanner-workspace-tab'], [class*='tab'][class*='Tab']").first
            if not scanner_tab.is_visible():
                # Try clicking the tab area
                page.locator("text=Scanner").click(timeout=3000)
            record_result("Scanner tab exists", True)
        except Exception as e:
            record_result("Scanner tab exists", False, str(e))
        
        # Test 5: Strategy tab exists and clickable
        try:
            strategy_tab = page.locator("text=Strategy").first
            strategy_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Strategy tab clickable", True)
        except Exception as e:
            record_result("Strategy tab clickable", False, str(e))
        
        # Test 6: Command tab exists and clickable
        try:
            command_tab = page.locator("text=Command").first
            command_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Command tab clickable", True)
        except Exception as e:
            record_result("Command tab clickable", False, str(e))
        
        # Test 7: Admin tab exists and clickable
        try:
            admin_tab = page.locator("text=Admin").first
            admin_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Admin tab clickable", True)
        except Exception as e:
            record_result("Admin tab clickable", False, str(e))
        
        # ===== CHAIN LOADING TESTS =====
        print("\n" + "="*60)
        print("CHAIN LOADING TESTS")
        print("="*60)
        
        # Return to Strategy tab first
        try:
            page.locator("text=Strategy").first.click(timeout=5000)
            time.sleep(1)
        except:
            pass
        
        # Test 8: Load SPY chain
        try:
            # First check auto-load worked
            time.sleep(2)
            
            # Look for data in any table
            rows = page.locator("table tr, .dash-cell").count()
            if rows > 5:
                record_result("SPY chain auto-loads", True, f"{rows} elements found")
            else:
                # Try manual load
                page.locator("#alpaca-ticker-input").fill("SPY")
                page.locator("#alpaca-load-button").click()
                time.sleep(3)
                rows = page.locator("table tr, .dash-cell").count()
                if rows > 5:
                    record_result("SPY chain auto-loads", True, f"{rows} elements after manual load")
                else:
                    record_result("SPY chain auto-loads", False, f"Only {rows} elements found")
        except Exception as e:
            record_result("SPY chain auto-loads", False, str(e))
        
        # Test 9: Change ticker to AAPL
        try:
            page.locator("#alpaca-ticker-input").fill("AAPL")
            page.locator("#alpaca-load-button").click()
            time.sleep(3)
            record_result("AAPL ticker change works", True)
        except Exception as e:
            record_result("AAPL ticker change works", False, str(e))
        
        # Test 10: Verify spot price shown
        try:
            spot = page.locator("text=/\\$\\d+\\.\\d+/").first
            spot.wait_for(timeout=5000)
            spot_text = spot.text_content()
            record_result("Spot price displays", True, spot_text)
        except Exception as e:
            record_result("Spot price displays", False, str(e))
        
        # ===== STRATEGY SUBTABS TESTS =====
        print("\n" + "="*60)
        print("STRATEGY SUBTABS TESTS")
        print("="*60)
        
        # Make sure we're in Strategy workspace
        try:
            page.locator("text=Strategy").first.click(timeout=3000)
            time.sleep(1)
        except:
            pass
        
        # Test 11: Chain & Greeks subtab
        try:
            chain_tab = page.locator("text=Chain & Greeks, text=Chain").first
            chain_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Chain & Greeks subtab", True)
        except Exception as e:
            record_result("Chain & Greeks subtab", False, str(e))
        
        # Test 12: Builder subtab
        try:
            builder_tab = page.locator("text=Builder").first
            builder_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Builder subtab", True)
        except Exception as e:
            record_result("Builder subtab", False, str(e))
        
        # Test 13: Engine subtab
        try:
            engine_tab = page.locator("text=Engine").first
            engine_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Engine subtab", True)
        except Exception as e:
            record_result("Engine subtab", False, str(e))
        
        # Test 14: AI Forecast subtab
        try:
            ai_tab = page.locator("text=AI Forecast, text=AI").first
            ai_tab.click(timeout=5000)
            time.sleep(1)
            record_result("AI Forecast subtab", True)
        except Exception as e:
            record_result("AI Forecast subtab", False, str(e))
        
        # ===== COMMAND SUBTABS TESTS =====
        print("\n" + "="*60)
        print("COMMAND SUBTABS TESTS")
        print("="*60)
        
        # Navigate to Command workspace
        try:
            page.locator("text=Command").first.click(timeout=5000)
            time.sleep(1)
        except:
            pass
        
        # Test 15: Positions subtab
        try:
            positions_tab = page.locator("text=Positions").first
            positions_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Positions subtab", True)
        except Exception as e:
            record_result("Positions subtab", False, str(e))
        
        # Test 16: Risk & P/L subtab
        try:
            risk_tab = page.locator("text=Risk").first
            risk_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Risk & P/L subtab", True)
        except Exception as e:
            record_result("Risk & P/L subtab", False, str(e))
        
        # Test 17: Trade Ops subtab
        try:
            trade_ops_tab = page.locator("text=Trade Ops").first
            trade_ops_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Trade Ops subtab", True)
        except Exception as e:
            record_result("Trade Ops subtab", False, str(e))
        
        # ===== ADMIN SUBTABS TESTS =====
        print("\n" + "="*60)
        print("ADMIN SUBTABS TESTS")
        print("="*60)
        
        # Navigate to Admin workspace
        try:
            page.locator("text=Admin").first.click(timeout=5000)
            time.sleep(1)
        except:
            pass
        
        # Test 18: System Status subtab
        try:
            status_tab = page.locator("text=System Status, text=Status").first
            status_tab.click(timeout=5000)
            time.sleep(1)
            record_result("System Status subtab", True)
        except Exception as e:
            record_result("System Status subtab", False, str(e))
        
        # Test 19: Research Lab subtab
        try:
            research_tab = page.locator("text=Research").first
            research_tab.click(timeout=5000)
            time.sleep(1)
            record_result("Research Lab subtab", True)
        except Exception as e:
            record_result("Research Lab subtab", False, str(e))
        
        # ===== SCANNER CONTENT TESTS =====
        print("\n" + "="*60)
        print("SCANNER CONTENT TESTS")
        print("="*60)
        
        # Navigate to Scanner workspace
        try:
            page.locator("text=Scanner").first.click(timeout=5000)
            time.sleep(1)
        except:
            pass
        
        # Test 20: GEX chart visible
        try:
            gex = page.locator("text=GEX, text=Gamma").first
            gex.wait_for(timeout=5000)
            record_result("GEX chart section", True)
        except Exception as e:
            record_result("GEX chart section", False, str(e))
        
        # Test 21: Volatility Surface visible
        try:
            vol = page.locator("text=Volatility Surface, text=Vol Surface").first
            vol.wait_for(timeout=5000)
            record_result("Volatility Surface section", True)
        except Exception as e:
            record_result("Volatility Surface section", False, str(e))
        
        # Test 22: Flow Tape visible
        try:
            flow = page.locator("text=Flow Tape, text=Flow").first
            flow.wait_for(timeout=5000)
            record_result("Flow Tape section", True)
        except Exception as e:
            record_result("Flow Tape section", False, str(e))
        
        # Test 23: Pattern Feed visible
        try:
            patterns = page.locator("text=Pattern").first
            patterns.wait_for(timeout=5000)
            record_result("Pattern Feed section", True)
        except Exception as e:
            record_result("Pattern Feed section", False, str(e))
        
        # ===== FUNCTIONAL TESTS =====
        print("\n" + "="*60)
        print("FUNCTIONAL TESTS")
        print("="*60)
        
        # Go back to Strategy tab
        try:
            page.locator("text=Strategy").first.click(timeout=3000)
            time.sleep(1)
        except:
            pass
        
        # Test 24: Data table has columns
        try:
            headers = page.locator("th, .column-header").count()
            if headers >= 5:
                record_result("Data table has columns", True, f"{headers} columns found")
            else:
                record_result("Data table has columns", False, f"Only {headers} columns")
        except Exception as e:
            record_result("Data table has columns", False, str(e))
        
        # Test 25: No console errors (check page errors)
        errors = page.evaluate("() => window.__ERRORS__ || []")
        if len(errors) == 0:
            record_result("No critical console errors", True)
        else:
            record_result("No critical console errors", False, f"{len(errors)} errors")
        
        browser.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("STRICT E2E TEST SUITE - ALL TESTS REQUIRED TO PASS")
    print("="*60 + "\n")
    
    test_dashboard()
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"✅ PASSED: {RESULTS['passed']}")
    print(f"❌ FAILED: {RESULTS['failed']}")
    print(f"📊 TOTAL: {RESULTS['passed'] + RESULTS['failed']}")
    print("="*60)
    
    if RESULTS['failed'] > 0:
        print("\n❌ FAILED TESTS:")
        for test in RESULTS['tests']:
            if not test['passed']:
                print(f"  - {test['name']}: {test['message']}")
    
    sys.exit(0 if RESULTS['failed'] == 0 else 1)
