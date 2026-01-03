#!/usr/bin/env python3
"""Check command tab contents."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    # Click Command tab
    page.locator('text=Command').first.click()
    time.sleep(2)
    
    # Get body text
    body = page.locator('body')
    text = body.text_content()
    
    # Find the command section
    print("=== PAGE TEXT (first 3000) ===")
    print(text[:3000])
    
    # Find all inputs
    print("\n=== ALL INPUT ELEMENTS ===")
    inputs = page.locator('input')
    for i in range(min(inputs.count(), 20)):
        inp = inputs.nth(i)
        id_attr = inp.get_attribute('id') or 'no-id'
        placeholder = inp.get_attribute('placeholder') or ''
        print(f"  {i}: id={id_attr}, placeholder={placeholder[:30]}")
    
    # Find command-related elements
    print("\n=== COMMAND ELEMENTS ===")
    cmd_els = page.locator('[id*="cmd"], [id*="command"], [class*="command"]')
    for i in range(min(cmd_els.count(), 20)):
        el = cmd_els.nth(i)
        id_attr = el.get_attribute('id') or 'no-id'
        cls = el.get_attribute('class') or ''
        print(f"  {i}: id={id_attr}, class={cls[:50]}")
    
    page.screenshot(path='cmd_tab_inspect.png')
    
    browser.close()
