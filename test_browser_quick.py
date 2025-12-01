#!/usr/bin/env python3
"""
Quick browser test: Just click the button and see if callback fires
"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("📂 Loading dashboard...")
    page.goto("http://localhost:8051/")
    page.wait_for_load_state("networkidle")
    
    print("📍 Clicking Market Trends tab...")
    page.click("text=Market Trends")
    time.sleep(2)
    
    print("🔍 Looking for Run Analysis button...")
    button = page.locator("#run-btn")
    print(f"Button visible: {button.is_visible()}")
    
    print("🖱️ Clicking Run Analysis button...")
    button.click()
    
    print("⏳ Waiting 5 seconds for callback...")
    time.sleep(5)
    
    # Check for status message
    status = page.locator("#status")
    status_text = status.inner_text() if status.is_visible() else "(not visible)"
    print(f"📊 Status text: {status_text}")
    
    print("\n✅ Test complete. Browser window will stay open for 10 seconds...")
    time.sleep(10)
    
    browser.close()
