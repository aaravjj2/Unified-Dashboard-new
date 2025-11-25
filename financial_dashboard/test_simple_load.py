#!/usr/bin/env python3
"""Simple test to verify dashboard loads."""

from playwright.sync_api import sync_playwright
import time

def test_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()
        
        print("Loading dashboard...")
        page.goto("http://127.0.0.1:8050", wait_until="networkidle", timeout=30000)
        
        print("Waiting for page to render...")
        time.sleep(5)
        
        # Take screenshot
        page.screenshot(path="test_load_screenshot.png")
        
        # Check for h1
        h1_elements = page.locator("h1").all()
        print(f"Found {len(h1_elements)} h1 elements")
        for h1 in h1_elements:
            print(f"  - {h1.inner_text()}")
        
        # Check for tabs
        tab_elements = page.locator(".tab").all()
        print(f"Found {len(tab_elements)} tab elements")
        for tab in tab_elements:
            print(f"  - {tab.inner_text()}")
        
        # Check all text content
        body_text = page.locator("body").inner_text()
        print(f"\nBody contains 'Unified Market Dashboard': {'Unified Market Dashboard' in body_text}")
        
        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    test_dashboard()
