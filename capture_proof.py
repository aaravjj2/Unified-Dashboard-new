#!/usr/bin/env python3
"""
Capture concrete proof screenshots and analyze what's actually happening.
"""

from playwright.sync_api import sync_playwright
import time
import os
from datetime import datetime

PROOF_DIR = "/home/aarav/Unified-Dashboard/proof_screenshots"

def capture_proof():
    os.makedirs(PROOF_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("\n" + "="*70)
        print("📸 CAPTURING PROOF SCREENSHOTS")
        print("="*70)
        
        # 1. Initial Load
        print("\n1️⃣ Loading dashboard...")
        page.goto("http://localhost:8053/", timeout=60000)
        time.sleep(5)
        
        # Capture initial state
        initial_path = f"{PROOF_DIR}/01_initial_state_{timestamp}.png"
        page.screenshot(path=initial_path, full_page=True)
        print(f"   📸 Saved: {initial_path}")
        
        # Get page content analysis
        print("\n   📋 Page Analysis:")
        title = page.title()
        print(f"      - Title: {title}")
        
        body_text = page.locator("body").text_content() or ""
        print(f"      - Body has content: {len(body_text) > 100}")
        print(f"      - Body length: {len(body_text)} chars")
        
        # Check key elements
        elements = {
            "alpaca-load-button": page.locator("#alpaca-load-button"),
            "alpaca-ticker-input": page.locator("#alpaca-ticker-input"),
            "command-palette-trigger": page.locator("#command-palette-trigger"),
            "alpaca-status-message": page.locator("#alpaca-status-message"),
            "main-workspace-tabs": page.locator("#main-workspace-tabs"),
        }
        
        print("\n   🔍 Element Check:")
        for name, elem in elements.items():
            exists = elem.count() > 0
            visible = elem.is_visible() if exists else False
            print(f"      - {name}: exists={exists}, visible={visible}")
        
        # 2. Click Load Chain button
        print("\n2️⃣ Clicking Load Chain button...")
        
        # Get status BEFORE click
        status_before = page.locator("#alpaca-status-message").text_content() or "(empty)"
        print(f"   Status BEFORE click: '{status_before[:100]}'")
        
        # Take screenshot before click
        before_click_path = f"{PROOF_DIR}/02_before_click_{timestamp}.png"
        page.screenshot(path=before_click_path, full_page=True)
        print(f"   📸 Saved: {before_click_path}")
        
        # Click the button
        load_btn = page.locator("#alpaca-load-button")
        if load_btn.count() > 0 and load_btn.is_visible():
            load_btn.click()
            print("   ✅ Button clicked!")
        else:
            print("   ❌ Button not found or not visible!")
        
        # Wait for response
        print("   ⏳ Waiting 8 seconds for callback...")
        time.sleep(8)
        
        # Get status AFTER click
        status_after = page.locator("#alpaca-status-message").text_content() or "(empty)"
        print(f"   Status AFTER click: '{status_after[:100]}'")
        
        # Take screenshot after click
        after_click_path = f"{PROOF_DIR}/03_after_click_{timestamp}.png"
        page.screenshot(path=after_click_path, full_page=True)
        print(f"   📸 Saved: {after_click_path}")
        
        # 3. Test Command Palette
        print("\n3️⃣ Testing Command Palette...")
        
        cmd_btn = page.locator("#command-palette-trigger")
        if cmd_btn.count() > 0:
            cmd_btn.click()
            time.sleep(1)
            
            modal_visible = page.locator(".modal-content").is_visible()
            print(f"   Modal opened: {modal_visible}")
            
            if modal_visible:
                palette_path = f"{PROOF_DIR}/04_command_palette_{timestamp}.png"
                page.screenshot(path=palette_path, full_page=True)
                print(f"   📸 Saved: {palette_path}")
                
                # Type /help
                cmd_input = page.locator("#command-input")
                if cmd_input.count() > 0:
                    cmd_input.fill("/help")
                    cmd_input.press("Enter")
                    time.sleep(1)
                    
                    result = page.locator("#command-result-display").text_content() or "(empty)"
                    print(f"   /help result: '{result[:100]}'")
                    
                    help_path = f"{PROOF_DIR}/05_help_command_{timestamp}.png"
                    page.screenshot(path=help_path, full_page=True)
                    print(f"   📸 Saved: {help_path}")
                    
                    # Test /chain AAPL
                    cmd_input.fill("/chain AAPL")
                    cmd_input.press("Enter")
                    time.sleep(5)
                    
                    chain_path = f"{PROOF_DIR}/06_chain_command_{timestamp}.png"
                    page.screenshot(path=chain_path, full_page=True)
                    print(f"   📸 Saved: {chain_path}")
                    
                    # Check status
                    status_chain = page.locator("#alpaca-status-message").text_content() or "(empty)"
                    print(f"   Status after /chain: '{status_chain[:100]}'")
        
        # 4. Check different tickers
        print("\n4️⃣ Testing different tickers...")
        
        tickers = ["NVDA", "TSLA", "GOOGL"]
        for ticker in tickers:
            ticker_input = page.locator("#alpaca-ticker-input")
            if ticker_input.count() > 0:
                ticker_input.fill(ticker)
                page.locator("#alpaca-load-button").click()
                time.sleep(5)
                
                status = page.locator("#alpaca-status-message").text_content() or "(empty)"
                success = "Successfully" in status or ticker in status
                icon = "✅" if success else "❌"
                print(f"   {icon} {ticker}: {status[:60]}")
                
                ticker_path = f"{PROOF_DIR}/07_{ticker.lower()}_{timestamp}.png"
                page.screenshot(path=ticker_path, full_page=True)
        
        # 5. Final state
        print("\n5️⃣ Capturing final state...")
        final_path = f"{PROOF_DIR}/08_final_state_{timestamp}.png"
        page.screenshot(path=final_path, full_page=True)
        print(f"   📸 Saved: {final_path}")
        
        # Get console errors
        print("\n6️⃣ Checking for JavaScript errors...")
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.reload()
        time.sleep(3)
        
        if errors:
            print("   ⚠️ Console Errors Found:")
            for err in errors[:10]:
                print(f"      - {err[:100]}")
        else:
            print("   ✅ No JavaScript errors detected")
        
        browser.close()
        
        # Summary
        print("\n" + "="*70)
        print("📊 PROOF SUMMARY")
        print("="*70)
        
        print(f"\n📁 Screenshots saved to: {PROOF_DIR}/")
        print("\nFiles created:")
        for f in sorted(os.listdir(PROOF_DIR)):
            if f.endswith('.png') and timestamp in f:
                fpath = os.path.join(PROOF_DIR, f)
                size = os.path.getsize(fpath)
                print(f"   - {f} ({size:,} bytes)")
        
        print("\n🔍 KEY FINDINGS:")
        print(f"   - Status before click: '{status_before[:50]}'")
        print(f"   - Status after click: '{status_after[:50]}'")
        print(f"   - Status changed: {status_before != status_after}")
        print(f"   - Contains 'Successfully': {'Successfully' in status_after}")
        
        print("\n" + "="*70)

if __name__ == "__main__":
    capture_proof()
