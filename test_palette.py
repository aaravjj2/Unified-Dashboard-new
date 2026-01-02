#!/usr/bin/env python3
"""Test command palette via trigger button."""

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
    
    # Find command palette trigger
    print("\n1. Finding command palette trigger (⌘K button)...")
    cmd_trigger = page.locator('#command-palette-trigger')
    print(f"   Found: {cmd_trigger.count() > 0}")
    print(f"   Visible: {cmd_trigger.is_visible()}")
    
    if cmd_trigger.is_visible():
        # Click to open
        print("\n2. Clicking trigger to open palette...")
        cmd_trigger.click()
        time.sleep(1)
        
        # Check for command input
        cmd_input = page.locator('#command-input')
        print(f"   Command input visible: {cmd_input.is_visible()}")
        
        if cmd_input.is_visible():
            page.screenshot(path='palette_open.png')
            
            # Test /help
            print("\n3. Testing /help...")
            cmd_input.fill('/help')
            cmd_input.press('Enter')
            time.sleep(2)
            
            # Check results
            results = page.locator('#cmd-results')
            if results.is_visible():
                text = results.text_content()
                print(f"   Help output: {len(text)} chars")
                if len(text) > 50:
                    print("   ✅ /help works!")
            
            page.screenshot(path='palette_help.png')
            
            # Test /load AAPL
            print("\n4. Testing /load AAPL...")
            cmd_input.fill('/load AAPL')
            cmd_input.press('Enter')
            time.sleep(5)
            
            page.screenshot(path='palette_load.png')
            
            # Check status
            status = page.locator('#alpaca-status-message')
            if status.is_visible():
                status_text = status.text_content()
                print(f"   Status: {status_text}")
                if 'AAPL' in status_text:
                    print("   ✅ /load works!")
        else:
            # Maybe it's a modal
            print("   Looking for modal input...")
            modal_input = page.locator('[id*="input"]')
            for i in range(modal_input.count()):
                inp = modal_input.nth(i)
                if inp.is_visible():
                    id_attr = inp.get_attribute('id') or 'no-id'
                    print(f"   Visible input: {id_attr}")
    
    print("\n" + "="*60)
    print("Screenshots: palette_open.png, palette_help.png, palette_load.png")
    print("="*60)
    
    browser.close()
