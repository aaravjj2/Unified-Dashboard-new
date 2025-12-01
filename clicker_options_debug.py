#!/usr/bin/env python3
"""
Options Lab Clicker Debug - Capture actual errors on each subtab
"""

import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://127.0.0.1:8051"
SCREENSHOT_DIR = "/tmp/options_lab_debug"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

SUBTABS = [
    "options-chain-tab",
    "options-greeks-tab", 
    "options-vol-tab",
    "options-flow-tab",
    "options-iv-tab",
    "options-strategy-tab",
    "options-manual-tab",
    "options-portfolio-tab",
    "options-screener-tab",
    "options-ai-tab",
    "options-earnings-tab",
    "options-journal-tab",
    "options-backtest-tab",
    "options-settings-tab",
]

def run_debug():
    console_errors = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        # Capture console errors
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ["error", "warning"] else None)
        
        print("=" * 60)
        print("OPTIONS LAB SUBTAB ERROR DETECTION")
        print("=" * 60)
        
        # Load dashboard
        page.goto(DASHBOARD_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Navigate to Options Lab
        page.locator("#tab-options_lab").click()
        time.sleep(2)
        
        # Load mock data first
        page.locator("#options-mock-btn").click()
        time.sleep(3)
        page.screenshot(path=f"{SCREENSHOT_DIR}/00_mock_loaded.png")
        
        # Test each subtab
        for i, tab_id in enumerate(SUBTABS):
            print(f"\n[{i+1}] Testing: {tab_id}")
            
            try:
                tab = page.locator(f"#{tab_id}")
                if tab.count() > 0:
                    tab.click()
                    time.sleep(2)
                    
                    # Take screenshot
                    page.screenshot(path=f"{SCREENSHOT_DIR}/{i+1:02d}_{tab_id}.png")
                    
                    # Check for error indicators in the content
                    content = page.content()
                    has_error = False
                    
                    # Check for common error patterns
                    error_patterns = [
                        "Callback error",
                        "Error loading",
                        "Something went wrong",
                        "Exception",
                        "Traceback",
                        "KeyError",
                        "TypeError",
                        "AttributeError",
                        "not configured",
                        "webhook",
                    ]
                    
                    for pattern in error_patterns:
                        if pattern.lower() in content.lower():
                            has_error = True
                            print(f"  ⚠️  Found error pattern: '{pattern}'")
                    
                    if not has_error:
                        print(f"  ✓ No obvious errors")
                else:
                    print(f"  ✗ Tab not found!")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        # Print console errors
        if console_errors:
            print("\n" + "=" * 60)
            print("CONSOLE ERRORS/WARNINGS:")
            print("=" * 60)
            for err in console_errors[:20]:
                print(f"  {err[:100]}")
        
        print(f"\n\nScreenshots saved to: {SCREENSHOT_DIR}")
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    run_debug()
