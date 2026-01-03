#!/usr/bin/env python3
"""Test commands work properly."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("="*60)
    print("COMMAND PALETTE TEST")
    print("="*60)
    
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    # Test Ctrl+K to open command palette
    print("\n1. Opening Command Palette with Ctrl+K...")
    page.keyboard.press('Control+k')
    time.sleep(1)
    
    cmd_input = page.locator('#cmd-palette-input')
    if cmd_input.is_visible():
        print("   ✅ Command palette opened")
    else:
        print("   ❌ Command palette NOT visible")
        
    page.screenshot(path='cmd_1_open.png')
    
    # Test /help command
    print("\n2. Typing /help...")
    cmd_input.fill('/help')
    page.keyboard.press('Enter')
    time.sleep(2)
    
    page.screenshot(path='cmd_2_help.png')
    
    # Check if help results appear
    results = page.locator('#cmd-results')
    if results.is_visible():
        content = results.text_content()
        print(f"   Results visible: {len(content)} chars")
        if len(content) > 100:
            print("   ✅ Help output shown")
        else:
            print(f"   ❌ Results too short: {content[:100]}")
    else:
        print("   ❌ Results not visible")
    
    # Close palette
    page.keyboard.press('Escape')
    time.sleep(0.5)
    
    # Test /load command
    print("\n3. Testing /load NVDA...")
    page.keyboard.press('Control+k')
    time.sleep(0.5)
    
    cmd_input = page.locator('#cmd-palette-input')
    cmd_input.fill('/load NVDA')
    page.keyboard.press('Enter')
    time.sleep(5)
    
    page.screenshot(path='cmd_3_load_nvda.png')
    
    # Check if ticker changed
    ticker = page.locator('#alpaca-ticker-input')
    if ticker.is_visible():
        val = ticker.input_value()
        print(f"   Ticker value: {val}")
        if 'NVDA' in val.upper():
            print("   ✅ Ticker changed to NVDA")
        else:
            print(f"   ❌ Ticker not changed: {val}")
    
    # Check status
    status = page.locator('#alpaca-status-message')
    if status.is_visible():
        status_text = status.text_content()
        print(f"   Status: {status_text[:50]}...")
        if 'NVDA' in status_text:
            print("   ✅ NVDA loaded")
    
    # Test /goto command
    print("\n4. Testing /goto strategy...")
    page.keyboard.press('Control+k')
    time.sleep(0.5)
    cmd_input = page.locator('#cmd-palette-input')
    cmd_input.fill('/goto strategy')
    page.keyboard.press('Enter')
    time.sleep(2)
    
    page.screenshot(path='cmd_4_goto.png')
    
    print("\n" + "="*60)
    print("Command tests completed. Check screenshots cmd_1-4")
    print("="*60)
    
    browser.close()
