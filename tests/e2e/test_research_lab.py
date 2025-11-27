#!/usr/bin/env python3
"""Quick test for Research Lab tab."""
from playwright.sync_api import sync_playwright
import time

def test_research_lab():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture console errors
        errors = []
        def log_console(msg):
            if msg.type == 'error':
                errors.append(msg.text)
        page.on('console', log_console)
        
        print("🔗 Navigating to dashboard...")
        page.goto("http://127.0.0.1:8051/", wait_until="load", timeout=30000)
        page.wait_for_selector('.nav-link', timeout=10000)
        page.wait_for_timeout(2000)
        
        print("📍 Looking for Research Lab tab...")
        research_link = page.locator('.nav-link:has-text("Research")').first
        if research_link.is_visible(timeout=5000):
            print("✅ Research Lab tab found")
            research_link.click()
            page.wait_for_timeout(3000)
            
            # Check content
            content = page.content()
            print(f"   Page contains 'Research': {'research' in content.lower()}")
            print(f"   Page contains 'Factor': {'factor' in content.lower()}")
            print(f"   Page contains 'Error': {'error' in content.lower()}")
            
            # Check for IDs
            if 'research-lab' in content:
                print("✅ Research Lab content loaded")
            else:
                print("⚠️ Research Lab content may not be loaded")
                
            # Take screenshot
            page.screenshot(path='/tmp/research_lab_test.png')
            print("📸 Screenshot saved to /tmp/research_lab_test.png")
        else:
            print("❌ Research Lab tab NOT found")
        
        # Print any console errors
        if errors:
            print("\n❌ Console Errors:")
            for e in errors[:5]:
                print(f"   {e[:100]}")
        else:
            print("\n✅ No console errors")
        
        browser.close()

if __name__ == "__main__":
    test_research_lab()
