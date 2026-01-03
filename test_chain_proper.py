#!/usr/bin/env python3
"""
Proper test navigating to Strategy > Chain & Greeks and testing the load chain.
"""

from playwright.sync_api import sync_playwright
import time
import os

PROOF_DIR = "/home/aarav/Unified-Dashboard/chain_proof"

def test_chain_and_greeks():
    os.makedirs(PROOF_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("\n" + "="*70)
        print("🔗 CHAIN & GREEKS PROPER TEST")
        print("="*70)
        
        # Load page
        page.goto("http://localhost:8053/", timeout=30000)
        time.sleep(4)
        
        # Screenshot 1: Initial (Scanner tab)
        page.screenshot(path=f"{PROOF_DIR}/01_scanner_initial.png")
        print("\n1️⃣ Initial state (Scanner tab)")
        print(f"   📸 Saved: 01_scanner_initial.png")
        
        # Click Strategy tab
        print("\n2️⃣ Clicking Strategy tab...")
        strategy_tab = page.locator(".tab:has-text('Strategy')").first
        if strategy_tab.count() > 0:
            strategy_tab.click()
            time.sleep(2)
            print("   ✅ Strategy tab clicked")
        else:
            print("   ❌ Strategy tab not found")
            
        page.screenshot(path=f"{PROOF_DIR}/02_strategy_tab.png")
        print(f"   📸 Saved: 02_strategy_tab.png")
        
        # Look for subtabs in Strategy
        print("\n3️⃣ Looking for Strategy subtabs...")
        subtabs = page.locator(".tab").all()
        print(f"   Found {len(subtabs)} total tabs")
        
        # Find Chain & Greeks subtab
        chain_subtab = page.locator(".tab:has-text('Chain'), .tab:has-text('Greeks')").first
        if chain_subtab.count() > 0:
            print(f"   Found Chain subtab: '{chain_subtab.text_content()[:30]}'")
            chain_subtab.click()
            time.sleep(2)
            print("   ✅ Chain subtab clicked")
        else:
            print("   ⚠️ Chain subtab not found, might already be active")
        
        page.screenshot(path=f"{PROOF_DIR}/03_chain_greeks_subtab.png")
        print(f"   📸 Saved: 03_chain_greeks_subtab.png")
        
        # Now test the Load Chain button
        print("\n4️⃣ Testing Load Chain button...")
        
        # Get status before
        status_elem = page.locator("#alpaca-status-message")
        status_before = status_elem.text_content() if status_elem.count() > 0 else "(not found)"
        print(f"   Status BEFORE: '{status_before[:60]}'")
        
        # Click Load Chain
        load_btn = page.locator("#alpaca-load-button")
        if load_btn.count() > 0 and load_btn.is_visible():
            print("   Clicking Load Chain...")
            load_btn.click()
            
            # Wait and capture status changes
            for i in range(6):
                time.sleep(1)
                status = status_elem.text_content() if status_elem.count() > 0 else ""
                print(f"   [{i+1}s] {status[:50]}")
        
        status_after = status_elem.text_content() if status_elem.count() > 0 else "(not found)"
        print(f"   Status AFTER: '{status_after[:60]}'")
        
        page.screenshot(path=f"{PROOF_DIR}/04_after_load_chain.png")
        print(f"   📸 Saved: 04_after_load_chain.png")
        
        # Check for chain data display
        print("\n5️⃣ Checking for chain data components...")
        
        chain_components = [
            ("#chain-viewer-table-container", "Chain Viewer Table"),
            ("#greeks-delta-value", "Greeks Delta"),
            ("#greeks-gamma-value", "Greeks Gamma"),
            ("#chain-viewer-expiration", "Expiration Dropdown"),
            ("#alpaca-expiration-dropdown", "Expiration Dropdown (alt)"),
        ]
        
        for selector, name in chain_components:
            elem = page.locator(selector)
            if elem.count() > 0:
                visible = elem.is_visible()
                content = elem.text_content()[:30] if elem.text_content() else "(empty)"
                print(f"   {name}: visible={visible}, content='{content}'")
            else:
                print(f"   {name}: NOT FOUND")
        
        # Test Command Palette
        print("\n6️⃣ Testing Command Palette...")
        
        cmd_btn = page.locator("#command-palette-trigger")
        if cmd_btn.count() > 0:
            cmd_btn.click()
            time.sleep(1)
            
            modal = page.locator(".modal-content")
            if modal.is_visible():
                print("   ✅ Modal opened")
                page.screenshot(path=f"{PROOF_DIR}/05_command_palette.png")
                
                # Test /help
                cmd_input = page.locator("#command-input")
                cmd_input.fill("/help")
                cmd_input.press("Enter")
                time.sleep(1)
                
                result = page.locator("#command-result-display")
                result_text = result.text_content() if result.count() > 0 else ""
                print(f"   /help result: {len(result_text)} chars")
                
                page.screenshot(path=f"{PROOF_DIR}/06_help_result.png")
                print(f"   📸 Saved: 06_help_result.png")
                
                # Test /chain AAPL
                print("   Testing /chain AAPL...")
                cmd_input.fill("/chain AAPL")
                cmd_input.press("Enter")
                time.sleep(4)
                
                # Modal might close, check status
                status = page.locator("#alpaca-status-message").text_content() or ""
                print(f"   After /chain AAPL status: '{status[:50]}'")
                
                page.screenshot(path=f"{PROOF_DIR}/07_chain_aapl.png")
                print(f"   📸 Saved: 07_chain_aapl.png")
            else:
                print("   ❌ Modal did not open")
        
        # Final full page
        page.screenshot(path=f"{PROOF_DIR}/08_final.png", full_page=True)
        print(f"\n   📸 Full page: 08_final.png")
        
        browser.close()
        
        # Summary
        print("\n" + "="*70)
        print("📊 RESULTS SUMMARY")
        print("="*70)
        print(f"\nScreenshots saved to: {PROOF_DIR}/")
        print("\nFiles:")
        for f in sorted(os.listdir(PROOF_DIR)):
            if f.endswith('.png'):
                size = os.path.getsize(os.path.join(PROOF_DIR, f))
                print(f"   - {f} ({size:,} bytes)")
        
        print(f"\n🔍 KEY RESULTS:")
        print(f"   Status changed: {status_before != status_after}")
        print(f"   Contains 'Successfully': {'Successfully' in status_after}")
        print(f"   Contains 'SPY' or ticker: {'SPY' in status_after or 'AAPL' in status_after}")
        
        if "Successfully" in status_after:
            print("\n✅ CHAIN LOADING IS WORKING!")
        else:
            print("\n⚠️ Chain loading may have issues")

if __name__ == "__main__":
    test_chain_and_greeks()
