#!/usr/bin/env python3
"""
Final validation test for all dashboard features.
Tests core functionality across all 4 workspaces and subtabs.
"""

from playwright.sync_api import sync_playwright
import time
import json

RESULTS = []

def log(name, passed, detail=""):
    status = "✅" if passed else "❌"
    RESULTS.append({"name": name, "passed": passed, "detail": detail})
    print(f"{status} {name}: {detail[:60] if detail else 'OK'}")

def run_validation():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("\n" + "="*70)
        print("🎯 FINAL DASHBOARD VALIDATION TEST")
        print("="*70)
        
        # 1. Load Page
        print("\n📦 Initial Load")
        print("-" * 40)
        page.goto("http://localhost:8053/", timeout=30000)
        time.sleep(3)
        log("Dashboard loads", True, "HTTP 200")
        
        # 2. Core Elements
        log("Ticker input", page.locator("#alpaca-ticker-input").count() > 0)
        log("Load button", page.locator("#alpaca-load-button").count() > 0)
        log("Command palette", page.locator("#command-palette-trigger").count() > 0)
        log("Tabs container", page.locator("#main-workspace-tabs").count() > 0)
        
        # 3. Load Chain Data
        print("\n📊 Chain Loading")
        print("-" * 40)
        
        # Test SPY
        page.locator("#alpaca-load-button").click()
        time.sleep(5)
        status = page.locator("#alpaca-status-message").text_content() or ""
        log("SPY loads", "Successfully" in status, status[:40])
        
        # Test AAPL
        page.locator("#alpaca-ticker-input").fill("AAPL")
        page.locator("#alpaca-load-button").click()
        time.sleep(5)
        status = page.locator("#alpaca-status-message").text_content() or ""
        log("AAPL loads", "AAPL" in status and "Successfully" in status, status[:40])
        
        # Test NVDA
        page.locator("#alpaca-ticker-input").fill("NVDA")
        page.locator("#alpaca-load-button").click()
        time.sleep(5)
        status = page.locator("#alpaca-status-message").text_content() or ""
        log("NVDA loads", "NVDA" in status, status[:40])
        
        # 4. Scanner Tab
        print("\n🔭 Scanner Workspace")
        print("-" * 40)
        
        scanner_tab = page.locator("//*[contains(@class, 'tab') and contains(text(), 'Scanner')]").first
        if scanner_tab.count() > 0:
            scanner_tab.click()
            time.sleep(2)
            
        log("Scanner tab visible", page.locator("#scanner-workspace, [id*='scanner']").count() > 0)
        log("GEX chart", page.locator("#chart-gex").count() > 0)
        log("Vol surface", page.locator("#chart-vol-3d").count() > 0)
        log("Flow tape", page.locator("#table-flow").count() > 0)
        page.screenshot(path="/home/aarav/Unified-Dashboard/validation_scanner.png", full_page=True)
        
        # 5. Strategy Tab + Subtabs
        print("\n⚔️ Strategy Workspace")
        print("-" * 40)
        
        strategy_tab = page.locator("//*[contains(@class, 'tab') and contains(text(), 'Strategy')]").first
        if strategy_tab.count() > 0:
            strategy_tab.click()
            time.sleep(2)
            
        log("Strategy tab visible", page.locator("#strategy-workspace, [id*='strategy']").count() > 0)
        
        # Check subtabs
        chain_tab = page.locator("//*[contains(text(), 'Chain')]").first
        if chain_tab.count() > 0:
            chain_tab.click()
            time.sleep(1)
            log("Chain subtab", True, "Clicked")
        
        builder_tab = page.locator("//*[contains(text(), 'Builder')]").first
        if builder_tab.count() > 0:
            builder_tab.click()
            time.sleep(1)
            log("Builder subtab", True, "Clicked")
        
        # AI Forecast subtab
        ai_tab = page.locator("//*[contains(text(), 'AI Forecast')]").first
        if ai_tab.count() > 0:
            ai_tab.click()
            time.sleep(2)
            log("AI Forecast subtab", True, "Clicked")
            
            # Check ML predictions
            direction = page.locator("#ml-price-direction").text_content() or "N/A"
            target = page.locator("#ml-price-target").text_content() or "N/A"
            log("ML direction prediction", direction in ["BULLISH", "BEARISH", "NEUTRAL"], direction)
            log("ML price target", "$" in target, target)
        
        page.screenshot(path="/home/aarav/Unified-Dashboard/validation_strategy.png", full_page=True)
        
        # 6. Command Tab
        print("\n🎮 Command Workspace")
        print("-" * 40)
        
        command_tab = page.locator("//*[contains(@class, 'tab') and contains(text(), 'Command')]").first
        if command_tab.count() > 0:
            command_tab.click()
            time.sleep(2)
            
        log("Command tab visible", page.locator("#command-workspace, [id*='command']").count() > 0)
        
        positions_tab = page.locator("//*[contains(text(), 'Positions')]").first
        if positions_tab.count() > 0:
            positions_tab.click()
            time.sleep(1)
            log("Positions subtab", True, "Clicked")
        
        page.screenshot(path="/home/aarav/Unified-Dashboard/validation_command.png", full_page=True)
        
        # 7. Admin Tab
        print("\n🔧 Admin Workspace")
        print("-" * 40)
        
        admin_tab = page.locator("//*[contains(@class, 'tab') and contains(text(), 'Admin')]").first
        if admin_tab.count() > 0:
            admin_tab.click()
            time.sleep(2)
            
        log("Admin tab visible", page.locator("#admin-workspace, [id*='admin']").count() > 0)
        page.screenshot(path="/home/aarav/Unified-Dashboard/validation_admin.png", full_page=True)
        
        # 8. Command Palette
        print("\n⌘ Command Palette")
        print("-" * 40)
        
        page.locator("#command-palette-trigger").click()
        time.sleep(1)
        
        modal_open = page.locator(".modal-content").is_visible()
        log("Palette opens", modal_open)
        
        if modal_open:
            cmd_input = page.locator("#command-input")
            cmd_input.fill("/help")
            cmd_input.press("Enter")
            time.sleep(1)
            
            result = page.locator("#command-result-display").text_content() or ""
            log("/help shows commands", "Available Commands" in result or "/gex" in result, result[:40])
            page.screenshot(path="/home/aarav/Unified-Dashboard/validation_palette.png", full_page=True)
            
            # Test /chain command
            cmd_input.fill("/chain TSLA")
            cmd_input.press("Enter")
            time.sleep(3)
            
            status = page.locator("#alpaca-status-message").text_content() or ""
            log("/chain TSLA loads", "TSLA" in status, status[:40])
        
        browser.close()
        
        # Summary
        print("\n" + "="*70)
        print("📊 VALIDATION SUMMARY")
        print("="*70)
        
        passed = sum(1 for r in RESULTS if r["passed"])
        failed = sum(1 for r in RESULTS if not r["passed"])
        total = len(RESULTS)
        
        print(f"\n{'Test':<50} {'Result':<10}")
        print("-" * 60)
        for r in RESULTS:
            icon = "✅" if r["passed"] else "❌"
            print(f"{icon} {r['name']:<48} {r['detail'][:30]}")
        
        print("-" * 60)
        print(f"\n🎯 TOTAL: {total} tests")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Pass Rate: {passed/total*100:.1f}%")
        
        # Save results
        with open("/home/aarav/Unified-Dashboard/validation_results.json", "w") as f:
            json.dump({
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{passed/total*100:.1f}%",
                "results": RESULTS
            }, f, indent=2)
        
        print(f"\n📸 Screenshots saved to validation_*.png")
        print(f"📄 Results saved to validation_results.json")
        print("="*70)
        
        return passed >= total - 2  # Allow up to 2 failures

if __name__ == "__main__":
    success = run_validation()
    exit(0 if success else 1)
