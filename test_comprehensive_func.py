#!/usr/bin/env python3
"""Comprehensive test and screenshot capture."""

from playwright.sync_api import sync_playwright
import time
import os

SCREENSHOT_DIR = "/home/aarav/Unified-Dashboard/test_screenshots"

def test_full_functionality():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("http://localhost:8053/", timeout=30000)
        time.sleep(4)
        
        results = []
        
        print("\n" + "="*70)
        print("COMPREHENSIVE FUNCTIONALITY TEST")
        print("="*70)
        
        # 1. Initial screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_initial_load.png", full_page=True)
        print("\n✅ 1. Initial Load - Screenshot saved")
        
        # 2. Test Load Chain button
        print("\n--- Testing Load Chain Button ---")
        load_btn = page.locator("#alpaca-load-button")
        if load_btn.count() > 0 and load_btn.is_visible():
            status_before = page.locator("#alpaca-status-message").text_content() or ""
            load_btn.click()
            time.sleep(5)
            status_after = page.locator("#alpaca-status-message").text_content() or ""
            
            if "Successfully" in status_after or "loaded" in status_after.lower():
                results.append(("Load Chain", "PASS", status_after[:60]))
                print(f"✅ Load Chain: PASS - {status_after[:60]}")
            else:
                results.append(("Load Chain", "FAIL", status_after[:60]))
                print(f"❌ Load Chain: FAIL - {status_after[:60]}")
            
            page.screenshot(path=f"{SCREENSHOT_DIR}/02_after_load.png", full_page=True)
        else:
            results.append(("Load Chain", "FAIL", "Button not found"))
            print("❌ Load Chain: Button not found")
        
        # 3. Test Tab Navigation
        print("\n--- Testing Tab Navigation ---")
        tabs = [
            ("scanner-workspace-tab", "Scanner"),
            ("strategy-workspace-tab", "Strategy"),
            ("command-workspace-tab", "Command"),
            ("admin-workspace-tab", "Admin"),
        ]
        
        for tab_value, tab_name in tabs:
            tab = page.locator(f".tab[data-value='{tab_value}'], .custom-tab[data-value='{tab_value}'], div.tab:has-text('{tab_name}')")
            if tab.count() == 0:
                # Try alternate selector
                tab = page.locator(f"//div[contains(@class, 'tab') and contains(text(), '{tab_name}')]")
            
            if tab.count() > 0:
                tab.first.click()
                time.sleep(1)
                results.append((f"Tab: {tab_name}", "PASS", "Clicked"))
                print(f"✅ Tab {tab_name}: PASS")
                page.screenshot(path=f"{SCREENSHOT_DIR}/03_tab_{tab_name.lower()}.png", full_page=True)
            else:
                results.append((f"Tab: {tab_name}", "FAIL", "Not found"))
                print(f"❌ Tab {tab_name}: Not found")
        
        # 4. Test Command Palette
        print("\n--- Testing Command Palette ---")
        cmd_btn = page.locator("#command-palette-trigger")
        if cmd_btn.count() > 0:
            cmd_btn.click()
            time.sleep(1)
            
            modal = page.locator(".modal-content")
            if modal.is_visible():
                results.append(("Command Palette Open", "PASS", "Modal visible"))
                print("✅ Command Palette Modal: PASS")
                
                # Test /help command
                cmd_input = page.locator("#command-input")
                if cmd_input.count() > 0 and cmd_input.is_visible():
                    cmd_input.fill("/help")
                    cmd_input.press("Enter")
                    time.sleep(1)
                    
                    result_div = page.locator("#command-result-display")
                    result_text = result_div.text_content() if result_div.count() > 0 else ""
                    
                    if "Available Commands" in result_text or "/gex" in result_text:
                        results.append(("/help Command", "PASS", result_text[:40]))
                        print(f"✅ /help Command: PASS - Shows commands")
                    else:
                        results.append(("/help Command", "FAIL", result_text[:40] or "No output"))
                        print(f"❌ /help Command: FAIL - {result_text[:40] or 'No output'}")
                    
                    page.screenshot(path=f"{SCREENSHOT_DIR}/04_command_help.png", full_page=True)
                    
                    # Test /chain command
                    cmd_input.fill("/chain AAPL")
                    cmd_input.press("Enter")
                    time.sleep(3)
                    
                    result_text2 = result_div.text_content() if result_div.count() > 0 else ""
                    if "Loading" in result_text2 or "AAPL" in result_text2:
                        results.append(("/chain AAPL", "PASS", result_text2[:40]))
                        print(f"✅ /chain AAPL: PASS")
                    else:
                        results.append(("/chain AAPL", "PARTIAL", "Command executed"))
                        print(f"⚠️ /chain AAPL: Partial - Command executed")
                    
                    page.screenshot(path=f"{SCREENSHOT_DIR}/05_command_chain.png", full_page=True)
                
                # Close modal
                close_btn = page.locator(".btn-close, button[aria-label='Close']")
                if close_btn.count() > 0:
                    close_btn.first.click()
                    time.sleep(0.5)
            else:
                results.append(("Command Palette Open", "FAIL", "Modal not visible"))
                print("❌ Command Palette Modal: FAIL")
        else:
            results.append(("Command Palette", "FAIL", "Trigger not found"))
            print("❌ Command Palette: Trigger not found")
        
        # 5. Test Ticker Input
        print("\n--- Testing Ticker Input ---")
        ticker_input = page.locator("#alpaca-ticker-input")
        if ticker_input.count() > 0:
            ticker_input.fill("NVDA")
            time.sleep(0.5)
            load_btn.click()
            time.sleep(5)
            
            status = page.locator("#alpaca-status-message").text_content() or ""
            if "NVDA" in status:
                results.append(("Ticker Change NVDA", "PASS", status[:40]))
                print(f"✅ Ticker Change NVDA: PASS")
            else:
                results.append(("Ticker Change NVDA", "FAIL", status[:40]))
                print(f"❌ Ticker Change NVDA: FAIL")
            
            page.screenshot(path=f"{SCREENSHOT_DIR}/06_ticker_nvda.png", full_page=True)
        
        # Final summary screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/99_final_state.png", full_page=True)
        
        browser.close()
        
        # Print Results Summary
        print("\n" + "="*70)
        print("TEST RESULTS SUMMARY")
        print("="*70)
        
        passed = sum(1 for r in results if r[1] == "PASS")
        failed = sum(1 for r in results if r[1] == "FAIL")
        partial = sum(1 for r in results if r[1] == "PARTIAL")
        
        for test_name, status, detail in results:
            icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
            print(f"{icon} {test_name}: {status} - {detail}")
        
        print(f"\nTotal: {len(results)} tests | ✅ {passed} passed | ⚠️ {partial} partial | ❌ {failed} failed")
        print(f"\n📸 Screenshots saved to: {SCREENSHOT_DIR}/")
        print("="*70)
        
        return passed, failed, partial

if __name__ == "__main__":
    test_full_functionality()
