#!/usr/bin/env python3
"""
Simplified Greeks validation - check if Options Lab loads and console is clean.
"""
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = 8050
URL = f"http://localhost:{PORT}"
SCREENSHOTS_DIR = Path("reports/options_validation/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("OPTIONS LAB CONSOLE CHECK")
print(f"Port: {PORT}")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Headed per requirements
    context = browser.new_context()
    page = context.new_page()
    
    # Collect console messages
    console_messages = []
    errors = []
    
    page.on("console", lambda msg: console_messages.append({
        "type": msg.type,
        "text": msg.text
    }))
    
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    
    print(f"✓ Navigating to {URL}")
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    page.screenshot(path=str(SCREENSHOTS_DIR / "console_check_1_home.png"))
    
    print("✓ Navigating to Options Lab...")
    page.click("text=💹 Options Lab")
    time.sleep(3)
    
    page.screenshot(path=str(SCREENSHOTS_DIR / "console_check_2_options_lab.png"))
    
    print("✓ Waiting for page to stabilize...")
    time.sleep(5)
    
    page.screenshot(path=str(SCREENSHOTS_DIR / "console_check_3_stabilized.png"))
    
    # Check for errors
    print("\n📋 Console Messages:")
    print(f"   Total: {len(console_messages)}")
    print(f"   Errors: {sum(1 for m in console_messages if m['type'] == 'error')}")
    print(f"   Warnings: {sum(1 for m in console_messages if m['type'] == 'warning')}")
    
    if errors:
        print(f"\n❌ Page Errors ({len(errors)}):")
        for err in errors:
            print(f"   {err}")
    
    # Print recent console errors
    console_errors = [m for m in console_messages if m['type'] == 'error']
    if console_errors:
        print(f"\n❌ Console Errors ({len(console_errors)}):")
        for msg in console_errors[-10:]:  # Last 10
            print(f"   {msg['text']}")
    
    # Check if Options Lab is visible
    options_lab_visible = page.evaluate("""
        () => {
            const optionsTab = document.querySelector('[id*="options"]');
            return {
                tab_exists: !!optionsTab,
                tab_visible: optionsTab ? optionsTab.offsetParent !== null : false,
                tab_id: optionsTab ? optionsTab.id : null
            };
        }
    """)
    
    print(f"\n📊 Options Lab Status:")
    print(f"   Tab exists: {options_lab_visible.get('tab_exists')}")
    print(f"   Tab visible: {options_lab_visible.get('tab_visible')}")
    print(f"   Tab ID: {options_lab_visible.get('tab_id')}")
    
    # Check for chain viewer subtab
    chain_viewer = page.evaluate("""
        () => {
            const subtabs = document.querySelector('[id="options-subtabs"]');
            const chainTab = document.querySelector('[value="options-chain-tab"]');
            return {
                subtabs_exists: !!subtabs,
                chain_tab_exists: !!chainTab,
                active_tab: subtabs ? subtabs.value : null
            };
        }
    """)
    
    print(f"\n📊 Chain Viewer Status:")
    print(f"   Subtabs exist: {chain_viewer.get('subtabs_exists')}")
    print(f"   Chain tab exists: {chain_viewer.get('chain_tab_exists')}")
    print(f"   Active tab: {chain_viewer.get('active_tab')}")
    
    print("\n✅ Test complete. Check screenshots for visual validation.")
    
    browser.close()
