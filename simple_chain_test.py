#!/usr/bin/env python3
"""Simple test for chain viewer."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("Loading page...")
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(2)
    
    # Click Strategy
    print("Clicking Strategy...")
    page.click('text=📊 Strategy Lab')
    time.sleep(1)
    
    # Click Chain
    print("Clicking Chain & Greeks...")
    page.click('text=📈 Chain & Greeks')
    time.sleep(1)
    
    # Screenshot before
    page.screenshot(path='before_load.png')
    print("Screenshot before: before_load.png")
    
    # Get chain viewer
    chain_viewer = page.locator('#chain-viewer-table-container')
    print(f"Chain viewer visible: {chain_viewer.is_visible()}")
    
    if chain_viewer.is_visible():
        content = chain_viewer.text_content()
        print(f"Initial content: {content[:100]}...")
    
    # Click load
    print("\nClicking Load Chain...")
    load_btn = page.locator('#alpaca-load-button')
    print(f"Load button visible: {load_btn.is_visible()}")
    load_btn.click()
    
    # Wait
    print("Waiting 8 seconds...")
    time.sleep(8)
    
    # Screenshot after
    page.screenshot(path='after_load.png')
    print("Screenshot after: after_load.png")
    
    # Get final content
    if chain_viewer.is_visible():
        content = chain_viewer.text_content()
        print(f"Final content length: {len(content)}")
        print(f"Final content (first 200): {content[:200]}")
    
    # Get status
    status = page.locator('#alpaca-status-message')
    if status.is_visible():
        print(f"Status: {status.text_content()}")
    
    browser.close()
    print("\nDone!")
