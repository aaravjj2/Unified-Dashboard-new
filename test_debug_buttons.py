#!/usr/bin/env python3
"""Debug test to check why buttons and commands aren't working."""

from playwright.sync_api import sync_playwright
import time

def test_buttons():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8053/", timeout=30000)
        time.sleep(3)
        
        print("\n" + "="*60)
        print("BUTTON DEBUG TEST")
        print("="*60)
        
        # Check load button
        load_btn = page.locator("#alpaca-load-button")
        print(f"\n1. Load Button (#alpaca-load-button):")
        print(f"   - Found: {load_btn.count() > 0}")
        if load_btn.count() > 0:
            print(f"   - Visible: {load_btn.is_visible()}")
            print(f"   - Enabled: {load_btn.is_enabled()}")
            
            # Check status message before click
            status_before = page.locator("#alpaca-status-message").text_content() or "empty"
            print(f"   - Status before click: {status_before[:50]}...")
            
            # Click and wait
            load_btn.click()
            print("   - CLICKED load button")
            time.sleep(5)  # Wait for callback
            
            status_after = page.locator("#alpaca-status-message").text_content() or "empty"
            print(f"   - Status after click: {status_after[:50]}...")
            
            # Check if options store has data
            store = page.locator("#alpaca-options-store")
            store_data = store.get_attribute("data") if store.count() > 0 else None
            print(f"   - Store has data: {bool(store_data) and store_data != 'null'}")
        
        # Check command palette trigger
        print(f"\n2. Command Palette Trigger (#command-palette-trigger):")
        cmd_trigger = page.locator("#command-palette-trigger")
        print(f"   - Found: {cmd_trigger.count() > 0}")
        if cmd_trigger.count() > 0:
            print(f"   - Visible: {cmd_trigger.is_visible()}")
            
            # Click to open palette
            cmd_trigger.click()
            time.sleep(1)
            
            # Check if modal opened
            modal = page.locator("#command-palette-modal")
            is_open = modal.locator(".modal-content").is_visible() if modal.count() > 0 else False
            print(f"   - Modal opened after click: {is_open}")
            
            # Try typing a command
            cmd_input = page.locator("#command-input")
            if cmd_input.count() > 0 and cmd_input.is_visible():
                cmd_input.fill("/help")
                cmd_input.press("Enter")
                time.sleep(1)
                
                # Check for result
                result_div = page.locator("#command-result-display")
                result_text = result_div.text_content() if result_div.count() > 0 else "empty"
                print(f"   - /help result: {result_text[:100] if result_text else 'empty'}...")
        
        # Check ticker input
        print(f"\n3. Ticker Input (#alpaca-ticker-input):")
        ticker_input = page.locator("#alpaca-ticker-input")
        print(f"   - Found: {ticker_input.count() > 0}")
        if ticker_input.count() > 0:
            print(f"   - Value: {ticker_input.input_value()}")
        
        # List all buttons on page
        print(f"\n4. All Buttons on Page:")
        all_buttons = page.locator("button")
        print(f"   - Total buttons found: {all_buttons.count()}")
        for i in range(min(10, all_buttons.count())):
            btn = all_buttons.nth(i)
            btn_id = btn.get_attribute("id") or "no-id"
            btn_text = btn.text_content()[:30] if btn.text_content() else "no-text"
            print(f"   - Button {i}: id='{btn_id}', text='{btn_text}'")
        
        # Check console errors
        print(f"\n5. JavaScript Console Messages:")
        messages = []
        page.on("console", lambda msg: messages.append(f"[{msg.type}] {msg.text}"))
        page.reload()
        time.sleep(3)
        if messages:
            for msg in messages[:10]:
                print(f"   - {msg}")
        else:
            print("   - No console messages captured")
        
        # Check for callback responses in network
        print(f"\n6. Network Activity Test:")
        requests = []
        page.on("request", lambda req: requests.append(req.url) if "_dash-update-component" in req.url else None)
        load_btn.click()
        time.sleep(3)
        print(f"   - Dash callback requests: {len([r for r in requests if '_dash' in r])}")
        
        # Take screenshot
        page.screenshot(path="/home/aarav/Unified-Dashboard/debug_buttons.png", full_page=True)
        print(f"\n✅ Screenshot saved to debug_buttons.png")
        
        browser.close()
        print("\n" + "="*60)

if __name__ == "__main__":
    test_buttons()
