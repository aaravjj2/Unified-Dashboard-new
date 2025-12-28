#!/usr/bin/env python3
"""
Debug the load button - actually test if it works.
"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    print("1. Navigating to http://localhost:8053...")
    page.goto("http://localhost:8053", wait_until="networkidle")
    time.sleep(5)
    
    print("2. Taking initial screenshot...")
    page.screenshot(path="debug_01_initial.png")
    
    print("3. Finding ticker input...")
    ticker_input = page.locator("#alpaca-ticker-input")
    print(f"   Ticker input visible: {ticker_input.is_visible()}")
    
    print("4. Finding load button...")
    load_button = page.locator("#alpaca-load-button")
    print(f"   Load button visible: {load_button.is_visible()}")
    
    print("5. Filling ticker with SPY...")
    ticker_input.fill("SPY")
    time.sleep(1)
    
    print("6. Clicking load button...")
    page.screenshot(path="debug_02_before_click.png")
    load_button.click()
    print("   Button clicked!")
    
    print("7. Waiting for response...")
    time.sleep(8)
    page.screenshot(path="debug_03_after_click.png")
    
    print("8. Checking for status message...")
    status = page.locator("#alpaca-status-message")
    if status.is_visible():
        status_text = status.inner_text()
        print(f"   Status text: '{status_text}'")
    else:
        print("   Status message not visible")
    
    print("9. Checking for table container...")
    table_container = page.locator("#alpaca-table-container")
    print(f"   Table container visible: {table_container.is_visible()}")
    if table_container.is_visible():
        table_html = table_container.inner_html()
        print(f"   Table HTML length: {len(table_html)} chars")
        print(f"   First 200 chars: {table_html[:200]}")
    
    print("10. Checking browser console for errors...")
    console_messages = []
    page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
    time.sleep(2)
    
    print(f"    Found {len(console_messages)} console messages")
    for msg in console_messages[-10:]:
        print(f"    {msg}")
    
    print("\n11. Checking network activity...")
    # Get all XHR/fetch requests
    page.on("request", lambda req: print(f"    → {req.method} {req.url}"))
    page.on("response", lambda res: print(f"    ← {res.status} {res.url}"))
    
    print("\n12. Taking final screenshot and keeping browser open...")
    page.screenshot(path="debug_04_final.png", full_page=True)
    
    print("\n⏸️  Browser will stay open for 10 seconds...")
    time.sleep(10)
    
    browser.close()
    print("\n✅ Debug complete. Check debug_*.png files.")
