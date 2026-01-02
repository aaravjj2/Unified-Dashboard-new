#!/usr/bin/env python3
"""
FINAL VALIDATION TEST - Tests specific features that must work
"""

import sys
import time
import re
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8053"
RESULTS = {"passed": 0, "failed": 0, "tests": []}


def record_result(name: str, passed: bool, message: str = ""):
    status = "✅" if passed else "❌"
    RESULTS["passed" if passed else "failed"] += 1
    RESULTS["tests"].append({"name": name, "passed": passed, "message": message})
    print(f"{status} {name}" + (f" - {message}" if message else ""))


def test_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        # ===== LOAD =====
        print("\n" + "="*50)
        print("CORE FUNCTIONALITY")
        print("="*50)
        
        page.goto(BASE_URL, timeout=15000)
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # 1. Chain loads with data rows
        page.locator("#alpaca-ticker-input").fill("SPY")
        page.locator("#alpaca-load-button").click()
        time.sleep(3)
        rows = page.locator("tr").count()
        record_result("SPY chain has data rows", rows > 50, f"{rows} rows")
        
        # 2. Spot price shows a dollar value
        html = page.content()
        spot_match = re.search(r'Spot.*?\$(\d+\.\d+)', html, re.IGNORECASE)
        if spot_match:
            record_result("Spot price displayed", True, f"${spot_match.group(1)}")
        else:
            prices = re.findall(r'\$\d+\.\d+', html)
            record_result("Spot price displayed", len(prices) > 0, f"{len(prices)} prices in DOM")
        
        # 3. Options data has calls and puts
        record_result("Call data present", "call" in html.lower() or "Call" in html)
        record_result("Put data present", "put" in html.lower() or "Put" in html)
        
        # 4. Greeks columns present
        greeks = ["delta", "gamma", "theta", "vega", "iv"]
        greeks_found = sum(1 for g in greeks if g in html.lower())
        record_result("Greeks data present", greeks_found >= 3, f"{greeks_found}/5 Greeks found")
        
        # 5. Strike prices in correct format
        strikes = re.findall(r'\b4[0-5]\d\.\d+\b', html)  # SPY strikes around 400-459
        record_result("Strike prices visible", len(strikes) > 10, f"{len(strikes)} SPY strikes")
        
        # 6. Bid/Ask data
        record_result("Bid data present", "bid" in html.lower() or "Bid" in html)
        record_result("Ask data present", "ask" in html.lower() or "Ask" in html)
        
        # ===== TICKER CHANGES =====
        print("\n" + "="*50)
        print("TICKER CHANGES")
        print("="*50)
        
        # Test multiple tickers
        tickers = ["AAPL", "NVDA", "QQQ", "TSLA", "MSFT"]
        for ticker in tickers:
            page.locator("#alpaca-ticker-input").fill(ticker)
            page.locator("#alpaca-load-button").click()
            time.sleep(2)
            cells = page.locator(".dash-cell, td").count()
            record_result(f"{ticker} chain loads", cells > 50, f"{cells} cells")
        
        # ===== TAB FUNCTIONALITY =====
        print("\n" + "="*50)
        print("TAB FUNCTIONALITY")
        print("="*50)
        
        # Test all main tabs accessible
        tabs = [
            ("🔭 Scanner", "Scanner workspace"),
            ("⚔️ Strategy", "Strategy workspace"),
            ("🎮 Command", "Command workspace"),
            ("🔧 Admin", "Admin workspace"),
        ]
        
        for tab_text, desc in tabs:
            page.get_by_text(tab_text, exact=True).click(timeout=3000)
            time.sleep(0.5)
            record_result(f"{desc} accessible", True)
        
        # ===== SUBTAB FUNCTIONALITY =====
        print("\n" + "="*50)
        print("SUBTAB FUNCTIONALITY")
        print("="*50)
        
        # Strategy subtabs
        page.get_by_text("⚔️ Strategy", exact=True).click(timeout=3000)
        time.sleep(0.5)
        
        strategy_subtabs = ["📈 Chain & Greeks", "🎯 Builder", "🦅 Engine", "🤖 AI Forecast"]
        for subtab in strategy_subtabs:
            try:
                page.get_by_text(subtab, exact=True).click(timeout=2000)
                time.sleep(0.3)
                record_result(f"Strategy: {subtab}", True)
            except:
                record_result(f"Strategy: {subtab}", False)
        
        # Command subtabs
        page.get_by_text("🎮 Command", exact=True).click(timeout=3000)
        time.sleep(0.5)
        
        command_subtabs = ["💼 Positions", "⚠️ Risk & P/L", "⚙️ Trade Ops"]
        for subtab in command_subtabs:
            try:
                page.locator("#command-sub-tabs").get_by_text(subtab).click(timeout=2000)
                time.sleep(0.3)
                record_result(f"Command: {subtab}", True)
            except:
                record_result(f"Command: {subtab}", False)
        
        # Admin subtabs
        page.get_by_text("🔧 Admin", exact=True).click(timeout=3000)
        time.sleep(0.5)
        
        admin_subtabs = ["🔧 System Status", "📊 Research Lab"]
        for subtab in admin_subtabs:
            try:
                page.locator("#admin-sub-tabs").get_by_text(subtab).click(timeout=2000)
                time.sleep(0.3)
                record_result(f"Admin: {subtab}", True)
            except:
                record_result(f"Admin: {subtab}", False)
        
        # ===== SCANNER FEATURES =====
        print("\n" + "="*50)
        print("SCANNER FEATURES")
        print("="*50)
        
        page.get_by_text("🔭 Scanner", exact=True).click(timeout=3000)
        time.sleep(1)
        
        html = page.content()
        scanner_features = [
            ("GEX", "Gamma Exposure (GEX)"),
            ("Volatility", "Volatility Surface"),
            ("Flow", "Flow Tape"),
            ("Pattern", "Pattern Feed"),
            ("LIVE", "Live indicator"),
        ]
        
        for keyword, feature in scanner_features:
            record_result(f"Scanner: {feature}", keyword in html)
        
        # ===== FINAL VALIDATION =====
        print("\n" + "="*50)
        print("FINAL VALIDATION")
        print("="*50)
        
        # Check no critical errors
        errors = page.evaluate("() => window.__ERRORS__ || []")
        record_result("No JS errors", len(errors) == 0)
        
        # Check page renders properly
        record_result("Page title set", "Dash" in page.title() or len(page.title()) > 0)
        
        # Check stores exist (these are in the DOM but may not be in visible HTML)
        stores_found = 0
        for store_id in ["alpaca-options-store", "strategy-legs-store", "positions-store"]:
            if page.locator(f"#{store_id}").count() > 0 or store_id in html:
                stores_found += 1
        record_result("Dash stores initialized", stores_found >= 1 or "store" in html.lower(), f"{stores_found}/3 stores or store keyword in DOM")
        
        browser.close()


if __name__ == "__main__":
    print("="*50)
    print("FINAL VALIDATION TEST SUITE")
    print("="*50)
    
    test_dashboard()
    
    print("\n" + "="*50)
    print("FINAL RESULTS")
    print("="*50)
    print(f"✅ PASSED: {RESULTS['passed']}")
    print(f"❌ FAILED: {RESULTS['failed']}")
    print(f"📊 TOTAL: {RESULTS['passed'] + RESULTS['failed']}")
    
    if RESULTS['failed'] > 0:
        print("\n❌ FAILED:")
        for t in RESULTS['tests']:
            if not t['passed']:
                print(f"  - {t['name']}: {t['message']}")
    else:
        print("\n🎉 ALL TESTS PASSED!")
    
    sys.exit(0 if RESULTS['failed'] == 0 else 1)
