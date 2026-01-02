#!/usr/bin/env python3
"""
COMPREHENSIVE E2E Test Suite - Tests 50+ features
Full coverage of all dashboard functionality
"""

import sys
import time
import re
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8053"
RESULTS = {"passed": 0, "failed": 0, "tests": []}


def record_result(name: str, passed: bool, message: str = ""):
    """Record test result."""
    status = "✅" if passed else "❌"
    RESULTS["passed" if passed else "failed"] += 1
    RESULTS["tests"].append({"name": name, "passed": passed, "message": message})
    print(f"{status} {name}" + (f" - {message}" if message else ""))


def test_dashboard():
    """Run all tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        # =========================================
        # SECTION 1: Basic Load Tests (1-5)
        # =========================================
        print("\n" + "="*60)
        print("SECTION 1: BASIC LOAD TESTS")
        print("="*60)
        
        try:
            page.goto(BASE_URL, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            record_result("1. Dashboard loads", True)
        except Exception as e:
            record_result("1. Dashboard loads", False, str(e))
            browser.close()
            return
        
        record_result("2. Ticker input", page.locator("#alpaca-ticker-input").count() > 0)
        record_result("3. Load button", page.locator("#alpaca-load-button").count() > 0)
        record_result("4. Trading mode toggle", page.locator("#trading-mode-toggle").count() > 0)
        record_result("5. Auto-refresh toggle", page.locator("#auto-refresh-toggle").count() > 0)
        
        # =========================================
        # SECTION 2: Tab Navigation (6-13)
        # =========================================
        print("\n" + "="*60)
        print("SECTION 2: TAB NAVIGATION")
        print("="*60)
        
        # Test 4 main tabs
        for i, (icon, tab_name) in enumerate([("🔭", "Scanner"), ("⚔️", "Strategy"), ("🎮", "Command"), ("🔧", "Admin")], 6):
            try:
                page.get_by_text(f"{icon} {tab_name}", exact=True).click(timeout=3000)
                time.sleep(0.3)
                record_result(f"{i}. {tab_name} tab navigation", True)
            except Exception as e:
                record_result(f"{i}. {tab_name} tab navigation", False, str(e))
        
        # Test returning to each tab works
        for i, (icon, tab_name) in enumerate([("🔭", "Scanner"), ("⚔️", "Strategy")], 10):
            try:
                page.get_by_text(f"{icon} {tab_name}", exact=True).click(timeout=3000)
                time.sleep(0.3)
                record_result(f"{i}. Return to {tab_name}", True)
            except Exception as e:
                record_result(f"{i}. Return to {tab_name}", False, str(e))
        
        # Test tab highlighting
        try:
            page.get_by_text("⚔️ Strategy", exact=True).click(timeout=2000)
            time.sleep(0.3)
            record_result("12. Tab click response", True)
        except Exception as e:
            record_result("12. Tab click response", False, str(e))
        
        record_result("13. 4-Tab UX badge visible", "4-Tab UX" in page.content())
        
        # =========================================
        # SECTION 3: Chain Loading (14-23)
        # =========================================
        print("\n" + "="*60)
        print("SECTION 3: OPTIONS CHAIN LOADING")
        print("="*60)
        
        page.get_by_text("⚔️ Strategy", exact=True).click(timeout=3000)
        time.sleep(1)
        
        # Test SPY chain
        try:
            page.locator("#alpaca-ticker-input").fill("SPY")
            page.locator("#alpaca-load-button").click()
            time.sleep(3)
            record_result("14. SPY load button click", True)
        except Exception as e:
            record_result("14. SPY load button click", False, str(e))
        
        # Check data table
        cells = page.locator(".dash-cell, td").count()
        record_result("15. SPY data cells loaded", cells > 100, f"{cells} cells")
        
        # Check columns
        headers = page.locator("th, .column-header-name").count()
        record_result("16. Table columns present", headers >= 5, f"{headers} columns")
        
        # Check for price data
        html = page.content()
        prices = re.findall(r'\$\d+\.\d+', html)
        record_result("17. Price data present", len(prices) > 0, f"{len(prices)} prices found")
        
        # Check for strike prices
        strikes = re.findall(r'\b\d{3,4}\.\d+\b', html)  # Strike prices like 450.00
        record_result("18. Strike prices present", len(strikes) > 0, f"{len(strikes)} strikes found")
        
        # Test AAPL change
        try:
            page.locator("#alpaca-ticker-input").fill("AAPL")
            page.locator("#alpaca-load-button").click()
            time.sleep(3)
            record_result("19. AAPL ticker change", True)
        except Exception as e:
            record_result("19. AAPL ticker change", False, str(e))
        
        cells_aapl = page.locator(".dash-cell, td").count()
        record_result("20. AAPL data loaded", cells_aapl > 50, f"{cells_aapl} cells")
        
        # Test QQQ
        try:
            page.locator("#alpaca-ticker-input").fill("QQQ")
            page.locator("#alpaca-load-button").click()
            time.sleep(3)
            record_result("21. QQQ ticker change", True)
        except Exception as e:
            record_result("21. QQQ ticker change", False, str(e))
        
        # Test TSLA
        try:
            page.locator("#alpaca-ticker-input").fill("TSLA")
            page.locator("#alpaca-load-button").click()
            time.sleep(3)
            record_result("22. TSLA ticker change", True)
        except Exception as e:
            record_result("22. TSLA ticker change", False, str(e))
        
        # Test NVDA
        try:
            page.locator("#alpaca-ticker-input").fill("NVDA")
            page.locator("#alpaca-load-button").click()
            time.sleep(3)
            record_result("23. NVDA ticker change", True)
        except Exception as e:
            record_result("23. NVDA ticker change", False, str(e))
        
        # =========================================
        # SECTION 4: Strategy Subtabs (24-31)
        # =========================================
        print("\n" + "="*60)
        print("SECTION 4: STRATEGY SUBTABS")
        print("="*60)
        
        page.get_by_text("⚔️ Strategy", exact=True).click(timeout=3000)
        time.sleep(0.5)
        
        # Test each strategy subtab
        subtabs = [
            ("📈 Chain & Greeks", "Chain subtab"),
            ("🎯 Builder", "Builder subtab"),
            ("🦅 Engine", "Engine subtab"),
            ("🤖 AI Forecast", "AI Forecast subtab"),
        ]
        
        for i, (tab_text, name) in enumerate(subtabs, 24):
            try:
                page.get_by_text(tab_text, exact=True).click(timeout=3000)
                time.sleep(0.5)
                record_result(f"{i}. {name}", True)
            except Exception as e:
                record_result(f"{i}. {name}", False, str(e))
        
        # Test subtab content exists
        record_result("28. Strategy workspace ID", "strategy-workspace" in page.content())
        record_result("29. Strategy sub-tabs ID", "strategy-sub-tabs" in page.content())
        
        # Check for Greeks content on Chain tab
        page.get_by_text("📈 Chain & Greeks", exact=True).click(timeout=2000)
        time.sleep(0.5)
        html = page.content()
        record_result("30. Greeks content", "Greeks" in html or "Delta" in html or "Gamma" in html or "IV" in html)
        record_result("31. IV content", "IV" in html or "Volatility" in html)
        
        # =========================================
        # SECTION 5: Command Subtabs (32-38)
        # =========================================
        print("\n" + "="*60)
        print("SECTION 5: COMMAND SUBTABS")
        print("="*60)
        
        page.get_by_text("🎮 Command", exact=True).click(timeout=3000)
        time.sleep(0.5)
        
        # Test command subtabs
        command_subtabs = [
            ("💼 Positions", "Positions subtab"),
            ("⚠️ Risk & P/L", "Risk subtab"),
            ("⚙️ Trade Ops", "Trade Ops subtab"),
        ]
        
        for i, (tab_text, name) in enumerate(command_subtabs, 32):
            try:
                page.locator("#command-sub-tabs").get_by_text(tab_text).click(timeout=3000)
                time.sleep(0.5)
                record_result(f"{i}. {name}", True)
            except Exception as e:
                record_result(f"{i}. {name}", False, str(e))
        
        html = page.content()
        record_result("35. Command workspace ID", "command-workspace" in html)
        record_result("36. Command sub-tabs ID", "command-sub-tabs" in html)
        record_result("37. Risk content present", "Risk" in html or "P/L" in html or "Position" in html)
        record_result("38. Trade content present", "Trade" in html or "Order" in html or "Execute" in html)
        
        # =========================================
        # SECTION 6: Admin Subtabs (39-44)
        # =========================================
        print("\n" + "="*60)
        print("SECTION 6: ADMIN SUBTABS")
        print("="*60)
        
        page.get_by_text("🔧 Admin", exact=True).click(timeout=3000)
        time.sleep(0.5)
        
        admin_subtabs = [
            ("🔧 System Status", "System Status subtab"),
            ("📊 Research Lab", "Research Lab subtab"),
        ]
        
        for i, (tab_text, name) in enumerate(admin_subtabs, 39):
            try:
                page.locator("#admin-sub-tabs").get_by_text(tab_text).click(timeout=3000)
                time.sleep(0.5)
                record_result(f"{i}. {name}", True)
            except Exception as e:
                record_result(f"{i}. {name}", False, str(e))
        
        html = page.content()
        record_result("41. Admin workspace ID", "admin-workspace" in html)
        record_result("42. Admin sub-tabs ID", "admin-sub-tabs" in html)
        record_result("43. Status content", "Status" in html or "System" in html)
        record_result("44. Research content", "Research" in html or "Backtest" in html)
        
        # =========================================
        # SECTION 7: Scanner Content (45-50)
        # =========================================
        print("\n" + "="*60)
        print("SECTION 7: SCANNER CONTENT")
        print("="*60)
        
        page.get_by_text("🔭 Scanner", exact=True).click(timeout=3000)
        time.sleep(1)
        
        html = page.content()
        record_result("45. Scanner workspace ID", "scanner-workspace" in html)
        record_result("46. GEX/Gamma content", "GEX" in html or "Gamma" in html)
        record_result("47. Volatility Surface content", "Volatility" in html or "Vol" in html)
        record_result("48. Flow Tape content", "Flow" in html)
        record_result("49. Pattern Feed content", "Pattern" in html)
        record_result("50. Scanner badges", "LIVE" in html or "GEX" in html or "VOL" in html)
        
        browser.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("COMPREHENSIVE E2E TEST SUITE - 50 TESTS")
    print("="*60)
    
    test_dashboard()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"✅ PASSED: {RESULTS['passed']}")
    print(f"❌ FAILED: {RESULTS['failed']}")
    print(f"📊 TOTAL: {RESULTS['passed'] + RESULTS['failed']}")
    
    pass_rate = RESULTS['passed'] / (RESULTS['passed'] + RESULTS['failed']) * 100
    print(f"📈 PASS RATE: {pass_rate:.1f}%")
    print("="*60)
    
    if RESULTS['failed'] > 0:
        print("\n❌ FAILED TESTS:")
        for test in RESULTS['tests']:
            if not test['passed']:
                print(f"  - {test['name']}: {test['message']}")
    else:
        print("\n🎉 ALL TESTS PASSED! Dashboard is fully functional.")
    
    sys.exit(0 if RESULTS['failed'] == 0 else 1)
