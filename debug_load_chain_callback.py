#!/usr/bin/env python3
"""
Check if Load Chain button callback is actually firing and what happens.
"""
import time
from playwright.sync_api import sync_playwright

PORT = 8050
URL = f"http://localhost:{PORT}"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # Capture console logs
    console_logs = []
    page.on("console", lambda msg: console_logs.append({
        "type": msg.type,
        "text": msg.text
    }))
    
    print("=" * 80)
    print("LOAD CHAIN CALLBACK DEBUG")
    print("=" * 80)
    
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    print("\n1. Navigating to Options Lab...")
    page.click("text=💹 Options Lab")
    time.sleep(3)
    
    print("\n2. Entering ticker SPY...")
    page.fill("#options-ticker-input", "SPY")
    time.sleep(1)
    
    print("\n3. Clicking Load Chain button...")
    # Check button state before clicking
    button_info = page.evaluate("""
        () => {
            const btn = document.getElementById('options-load-btn');
            return {
                exists: !!btn,
                disabled: btn?.disabled,
                text: btn?.textContent,
                n_clicks: btn?.getAttribute('n_clicks')
            };
        }
    """)
    print(f"   Button before click: {button_info}")
    
    page.click("#options-load-btn")
    time.sleep(2)
    
    # Check button state after clicking
    button_info_after = page.evaluate("""
        () => {
            const btn = document.getElementById('options-load-btn');
            return {
                disabled: btn?.disabled,
                n_clicks: btn?.getAttribute('n_clicks')
            };
        }
    """)
    print(f"   Button after click: {button_info_after}")
    
    print("\n4. Waiting 15 seconds for callback to execute...")
    time.sleep(15)
    
    # Check status message
    status_msg = page.evaluate("""
        () => {
            const status = document.getElementById('options-status-message');
            return status ? status.textContent : null;
        }
    """)
    print(f"\n📋 Status message: {status_msg}")
    
    # Check store again
    store_data = page.evaluate("""
        () => {
            const store = document.getElementById('options-chain-store');
            if (store && store.textContent) {
                try {
                    const data = JSON.parse(store.textContent);
                    return {
                        has_data: data && Object.keys(data).length > 0,
                        keys: Object.keys(data || {}),
                        spot_price: data?.spot_price,
                        calls_count: data?.calls?.length || 0,
                        puts_count: data?.puts?.length || 0
                    };
                } catch (e) {
                    return { error: e.message, raw: store.textContent.substring(0, 200) };
                }
            }
            return { has_data: false, raw: store ? store.textContent : 'Store element not found' };
        }
    """)
    print(f"\n📦 Chain Store after callback: {store_data}")
    
    # Check for relevant console errors
    print(f"\n📝 Console messages ({len(console_logs)} total):")
    errors = [log for log in console_logs if log['type'] == 'error']
    warnings = [log for log in console_logs if log['type'] == 'warning']
    
    if errors:
        print(f"\n   Errors ({len(errors)}):")
        for err in errors[-5:]:  # Last 5 errors
            print(f"      {err['text'][:150]}")
    
    if warnings:
        print(f"\n   Warnings ({len(warnings)}):")
        for warn in warnings[-3:]:  # Last 3 warnings
            print(f"      {warn['text'][:150]}")
    
    print("\n✅ Diagnostic complete")
    time.sleep(5)
    browser.close()
