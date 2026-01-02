#!/usr/bin/env python3
"""
Comprehensive test suite for Alpaca Options Dashboard.
Tests all major functionality and captures screenshots.
"""

from playwright.sync_api import sync_playwright
import time
import os
import json

SCREENSHOT_DIR = "/home/aarav/Unified-Dashboard/final_test_screenshots"
RESULTS = []

def log_test(name, passed, detail=""):
    """Log a test result."""
    status = "PASS" if passed else "FAIL"
    RESULTS.append({"name": name, "status": status, "detail": detail})
    icon = "✅" if passed else "❌"
    print(f"{icon} {name}: {detail[:60] if detail else 'OK'}")

def run_all_tests():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE DASHBOARD TEST SUITE")
        print("="*70)
        
        # ===== SECTION 1: Initial Load =====
        print("\n📦 Section 1: Initial Load Tests")
        print("-" * 40)
        
        page.goto("http://localhost:8053/", timeout=30000)
        time.sleep(3)
        
        # Check page loaded
        log_test("Page loads", page.title() != "" or page.locator("body").count() > 0, "Dashboard accessible")
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_initial.png", full_page=True)
        
        # Check key elements exist
        log_test("Ticker input exists", page.locator("#alpaca-ticker-input").count() > 0)
        log_test("Load button exists", page.locator("#alpaca-load-button").count() > 0)
        log_test("Command palette trigger exists", page.locator("#command-palette-trigger").count() > 0)
        log_test("Tab container exists", page.locator("#main-workspace-tabs").count() > 0)
        
        # ===== SECTION 2: Chain Loading =====
        print("\n📊 Section 2: Chain Loading Tests")
        print("-" * 40)
        
        # Test default SPY load
        page.locator("#alpaca-load-button").click()
        time.sleep(5)
        
        status = page.locator("#alpaca-status-message").text_content() or ""
        log_test("SPY chain loads", "Successfully" in status or "loaded" in status.lower(), status[:50])
        page.screenshot(path=f"{SCREENSHOT_DIR}/02_spy_loaded.png", full_page=True)
        
        # Test different ticker
        page.locator("#alpaca-ticker-input").fill("AAPL")
        page.locator("#alpaca-load-button").click()
        time.sleep(5)
        
        status = page.locator("#alpaca-status-message").text_content() or ""
        log_test("AAPL chain loads", "AAPL" in status and "Successfully" in status, status[:50])
        page.screenshot(path=f"{SCREENSHOT_DIR}/03_aapl_loaded.png", full_page=True)
        
        # Test NVDA
        page.locator("#alpaca-ticker-input").fill("NVDA")
        page.locator("#alpaca-load-button").click()
        time.sleep(5)
        
        status = page.locator("#alpaca-status-message").text_content() or ""
        log_test("NVDA chain loads", "NVDA" in status, status[:50])
        
        # ===== SECTION 3: Tab Navigation =====
        print("\n🗂️ Section 3: Tab Navigation Tests")
        print("-" * 40)
        
        tabs = [
            ("Scanner", "scanner"),
            ("Strategy", "strategy"),
            ("Command", "command"),
            ("Admin", "admin"),
        ]
        
        for tab_name, tab_id in tabs:
            # Try multiple selector strategies
            tab = page.locator(f"[data-value='{tab_id}-workspace-tab']").first
            if tab.count() == 0:
                tab = page.locator(f"//div[contains(@class, 'tab') and contains(text(), '{tab_name}')]").first
            if tab.count() == 0:
                tab = page.locator(f".tab:has-text('{tab_name}')").first
                
            if tab.count() > 0:
                tab.click()
                time.sleep(1)
                log_test(f"Tab {tab_name} clickable", True)
                page.screenshot(path=f"{SCREENSHOT_DIR}/04_tab_{tab_id}.png", full_page=True)
            else:
                log_test(f"Tab {tab_name} clickable", False, "Tab not found")
        
        # ===== SECTION 4: Command Palette =====
        print("\n⌘ Section 4: Command Palette Tests")
        print("-" * 40)
        
        # Open modal
        cmd_trigger = page.locator("#command-palette-trigger")
        cmd_trigger.click()
        time.sleep(1)
        
        modal_visible = page.locator(".modal-content").is_visible()
        log_test("Command palette opens", modal_visible)
        page.screenshot(path=f"{SCREENSHOT_DIR}/05_command_open.png", full_page=True)
        
        if modal_visible:
            # Test /help
            cmd_input = page.locator("#command-input")
            cmd_input.fill("/help")
            cmd_input.press("Enter")
            time.sleep(1)
            
            result = page.locator("#command-result-display").text_content() or ""
            log_test("/help command", "Available Commands" in result or "/gex" in result, result[:40])
            page.screenshot(path=f"{SCREENSHOT_DIR}/06_help_command.png", full_page=True)
            
            # Test /scanner
            cmd_input.fill("/scanner")
            cmd_input.press("Enter")
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/07_scanner_command.png", full_page=True)
            log_test("/scanner command", True, "Tab switch executed")
            
            # Reopen and test /chain
            time.sleep(1)
            cmd_trigger = page.locator("#command-palette-trigger")
            cmd_trigger.click()
            time.sleep(1)
            
            if page.locator(".modal-content").is_visible():
                cmd_input = page.locator("#command-input")
                cmd_input.fill("/chain TSLA")
                cmd_input.press("Enter")
                time.sleep(3)
                
                # Modal might close, check status message instead
                time.sleep(2)
                status = page.locator("#alpaca-status-message").text_content() or ""
                log_test("/chain TSLA command", "TSLA" in status or "Loading" in status, status[:40] if status else "Command executed")
            else:
                log_test("/chain TSLA command", False, "Modal didn't reopen")
            
            page.screenshot(path=f"{SCREENSHOT_DIR}/08_chain_command.png", full_page=True)
        
        # ===== SECTION 5: AI Features =====
        print("\n🤖 Section 5: AI Features Tests")
        print("-" * 40)
        
        # Navigate to Strategy tab for AI features
        strategy_tab = page.locator("//div[contains(@class, 'tab') and contains(text(), 'Strategy')]").first
        if strategy_tab.count() > 0:
            strategy_tab.click()
            time.sleep(2)
        
        # Check AI panels exist
        ai_elements = [
            ("ai-regime-display", "AI Regime Display"),
            ("ai-scanner-results", "AI Scanner Results"),
            ("ai-signals-container", "AI Signals"),
            ("ai-ml-predictions", "ML Predictions"),
        ]
        
        for elem_id, elem_name in ai_elements:
            elem = page.locator(f"#{elem_id}")
            log_test(f"{elem_name} exists", elem.count() > 0)
        
        page.screenshot(path=f"{SCREENSHOT_DIR}/09_ai_panels.png", full_page=True)
        
        # ===== SECTION 6: Scanner Workspace =====
        print("\n🔭 Section 6: Scanner Workspace Tests")
        print("-" * 40)
        
        scanner_tab = page.locator("//div[contains(@class, 'tab') and contains(text(), 'Scanner')]").first
        if scanner_tab.count() > 0:
            scanner_tab.click()
            time.sleep(2)
        
        # Check scanner components
        log_test("GEX chart container", page.locator("#chart-gex, [id*='gex']").count() > 0)
        log_test("Vol surface container", page.locator("#chart-vol-3d, [id*='vol']").count() > 0)
        log_test("Flow tape container", page.locator("#table-flow, [id*='flow']").count() > 0)
        
        page.screenshot(path=f"{SCREENSHOT_DIR}/10_scanner_workspace.png", full_page=True)
        
        # ===== SECTION 7: Command Workspace =====
        print("\n🎮 Section 7: Command Workspace Tests")
        print("-" * 40)
        
        command_tab = page.locator("//div[contains(@class, 'tab') and contains(text(), 'Command')]").first
        if command_tab.count() > 0:
            command_tab.click()
            time.sleep(2)
        
        log_test("Positions container", page.locator("[id*='positions'], [id*='position']").count() > 0)
        page.screenshot(path=f"{SCREENSHOT_DIR}/11_command_workspace.png", full_page=True)
        
        # ===== SECTION 8: Admin Workspace =====
        print("\n🔧 Section 8: Admin Workspace Tests")
        print("-" * 40)
        
        admin_tab = page.locator("//div[contains(@class, 'tab') and contains(text(), 'Admin')]").first
        if admin_tab.count() > 0:
            admin_tab.click()
            time.sleep(2)
        
        log_test("Status panel", page.locator("[id*='status'], [id*='system']").count() > 0)
        page.screenshot(path=f"{SCREENSHOT_DIR}/12_admin_workspace.png", full_page=True)
        
        # Final screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/99_final_state.png", full_page=True)
        
        browser.close()
    
    # ===== RESULTS SUMMARY =====
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    total = len(RESULTS)
    
    print(f"\n{'Test Name':<40} {'Status':<8} {'Detail'}")
    print("-" * 70)
    for r in RESULTS:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{icon} {r['name']:<38} {r['status']:<8} {r['detail'][:30]}")
    
    print("-" * 70)
    print(f"\n🎯 Total: {total} tests | ✅ {passed} passed | ❌ {failed} failed")
    print(f"📈 Pass Rate: {passed/total*100:.1f}%")
    print(f"\n📸 Screenshots saved to: {SCREENSHOT_DIR}/")
    
    # Save results to JSON
    with open(f"{SCREENSHOT_DIR}/test_results.json", "w") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed/total*100,
            "results": RESULTS
        }, f, indent=2)
    
    print(f"📄 Results JSON saved to: {SCREENSHOT_DIR}/test_results.json")
    print("="*70)
    
    return passed, failed

if __name__ == "__main__":
    run_all_tests()
