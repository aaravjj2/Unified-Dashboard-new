#!/usr/bin/env python3
"""Test commands from Command tab."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("="*60)
    print("COMMAND TAB TEST")
    print("="*60)
    
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    # Click Command tab
    print("\n1. Clicking Command tab...")
    page.locator('text=Command').first.click()
    time.sleep(2)
    page.screenshot(path='cmd_tab_1.png')
    
    # Look for command input
    print("\n2. Looking for command input...")
    cmd_input = page.locator('#command-input')
    if cmd_input.count() > 0:
        print(f"   Found! Visible: {cmd_input.is_visible()}")
        
        # Type /help
        print("\n3. Testing /help...")
        cmd_input.fill('/help')
        cmd_input.press('Enter')
        time.sleep(2)
        page.screenshot(path='cmd_tab_2_help.png')
        
        # Check results
        results = page.locator('#cmd-results')
        if results.count() > 0:
            text = results.text_content()
            print(f"   Results: {len(text)} chars")
            print(f"   First 200: {text[:200]}")
        
        # Test /load AAPL
        print("\n4. Testing /load AAPL...")
        cmd_input.fill('/load AAPL')
        cmd_input.press('Enter')
        time.sleep(5)
        page.screenshot(path='cmd_tab_3_load.png')
        
        # Check status
        status = page.locator('#alpaca-status-message')
        if status.is_visible():
            print(f"   Status: {status.text_content()}")
        
        # Check ticker
        ticker = page.locator('#alpaca-ticker-input')
        if ticker.count() > 0:
            val = ticker.input_value()
            print(f"   Ticker value: {val}")
    else:
        print("   NOT FOUND")
        # Try other command palette button
        cmd_btn = page.locator('#cmd-palette-btn, #command-palette-btn, [id*="command"]')
        print(f"   Found command buttons: {cmd_btn.count()}")
    
    print("\n" + "="*60)
    print("Screenshots: cmd_tab_1.png, cmd_tab_2_help.png, cmd_tab_3_load.png")
    print("="*60)
    
    browser.close()
