#!/usr/bin/env python3
"""Check page content."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    # Get all visible text
    print("=== VISIBLE TEXT (first 2000 chars) ===")
    body = page.locator('body')
    text = body.text_content()
    print(text[:2000])
    
    # Check for chain viewer
    print("\n=== CHAIN VIEWER ===")
    cv = page.query_selector('#chain-viewer-table-container')
    print(f"Found: {cv is not None}")
    if cv:
        print(f"Text: {cv.text_content()[:200]}")
    
    # Take screenshot
    page.screenshot(path='page_state.png')
    print("\nScreenshot saved: page_state.png")
    
    browser.close()
