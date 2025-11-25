#!/usr/bin/env python
"""Check for JavaScript errors and Dash initialization."""
from playwright.sync_api import sync_playwright
import time

def check_js_errors():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Collect console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        
        # Collect errors
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        
        print("Loading http://localhost:8050...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(5)
        
        print(f"\n🔍 Console messages ({len(console_messages)} total):")
        for msg in console_messages[:20]:  # First 20
            print(f"  {msg}")
        
        print(f"\n❌ JavaScript errors ({len(errors)} total):")
        for err in errors:
            print(f"  {err}")
        
        # Check if _dash-component-suites loaded
        scripts = page.query_selector_all('script[src*="dash"]')
        print(f"\n📜 Dash scripts loaded: {len(scripts)}")
        for script in scripts[:5]:
            src = script.get_attribute('src')
            print(f"  - {src}")
        
        # Check if window.dash exists
        dash_exists = page.evaluate('typeof window.dash !== "undefined"')
        print(f"\n🔍 window.dash exists: {dash_exists}")
        
        browser.close()

if __name__ == '__main__':
    check_js_errors()
