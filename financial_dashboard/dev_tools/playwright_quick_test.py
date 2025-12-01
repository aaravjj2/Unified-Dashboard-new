#!/usr/bin/env python3
"""Quick Playwright test to validate Market Trends dashboard loads without errors."""
from playwright.sync_api import sync_playwright
import time
import os
import sys

OUT = os.path.join(os.path.dirname(__file__), 'playwright_snapshots')
os.makedirs(OUT, exist_ok=True)

def test_market_trends():
    """Test that Market Trends page loads and displays cached data."""
    print("Starting Market Trends quick test...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page()
        
        console_logs = []
        errors = []
        
        def handle_console(msg):
            console_logs.append(f"{msg.type}: {msg.text}")
            if msg.type in ['error', 'warning']:
                print(f"Console {msg.type}: {msg.text}")
        
        def handle_page_error(error):
            errors.append(str(error))
            print(f"Page error: {error}")
        
        page.on('console', handle_console)
        page.on('pageerror', handle_page_error)
        
        # Load page
        print("Loading http://127.0.0.1:8050...")
        try:
            page.goto('http://127.0.0.1:8050/', timeout=30000, wait_until='networkidle')
            print("✓ Page loaded")
        except Exception as exc:
            print(f"✗ Failed to load page: {exc}")
            return False
        
        # Wait for page to hydrate
        time.sleep(3)
        
        # Check for critical elements
        checks = {
            'H3 title': 'h3:has-text("Market Trends")',
            'Run button': '#run-btn',
            'Tickers input': '#tickers-input',
            'Status div': '#status',
            'Results area': '#results-area',
        }
        
        all_passed = True
        for name, selector in checks.items():
            try:
                elem = page.wait_for_selector(selector, timeout=5000)
                if elem:
                    print(f"✓ Found {name}")
                else:
                    print(f"✗ Missing {name}")
                    all_passed = False
            except Exception as exc:
                print(f"✗ Missing {name}: {exc}")
                all_passed = False
        
        # Check if cached results loaded
        try:
            results_text = page.inner_text('#results-area')
            if len(results_text) > 100:
                print(f"✓ Results area has content ({len(results_text)} chars)")
            else:
                print(f"⚠ Results area has minimal content ({len(results_text)} chars)")
        except Exception as exc:
            print(f"⚠ Could not read results area: {exc}")
        
        # Take screenshot
        screenshot_path = os.path.join(OUT, 'quick_test.png')
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"✓ Screenshot saved to {screenshot_path}")
        
        # Save HTML
        html_path = os.path.join(OUT, 'quick_test.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(page.content())
        print(f"✓ HTML saved to {html_path}")
        
        # Check for errors
        if errors:
            print(f"\n✗ Page errors detected: {len(errors)}")
            for err in errors[:5]:
                print(f"  - {err}")
            all_passed = False
        else:
            print("✓ No page errors detected")
        
        browser.close()
        
        return all_passed

if __name__ == '__main__':
    success = test_market_trends()
    if success:
        print("\n✓ All checks passed!")
        sys.exit(0)
    else:
        print("\n✗ Some checks failed")
        sys.exit(1)
