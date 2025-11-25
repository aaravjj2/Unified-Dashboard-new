#!/usr/bin/env python3
"""
Test for duplicate callback errors after fix.
This script launches a headful browser, navigates to Market Trends,
and captures console errors to verify duplicates are eliminated.
"""

import time
import sys
from playwright.sync_api import sync_playwright

def test_for_duplicates():
    """Check browser console for duplicate callback errors."""
    
    console_messages = []
    duplicate_errors = []
    
    def handle_console(msg):
        """Capture all console messages."""
        text = msg.text
        console_messages.append(text)
        if 'duplicate' in text.lower():
            duplicate_errors.append(text)
            print(f"⚠️  DUPLICATE ERROR: {text[:200]}")
    
    with sync_playwright() as p:
        # Launch headful browser for manual inspection
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        # Attach console listener
        page.on("console", handle_console)
        
        print("🌐 Navigating to dashboard...")
        page.goto('http://localhost:8051', wait_until='networkidle', timeout=60000)
        
        print("🔍 Clicking Market Trends tab...")
        page.click('a.nav-link:has-text("Market Trends")', timeout=10000)
        page.wait_for_timeout(3000)
        
        print("✅ Test complete - browser will stay open for 10 seconds")
        print(f"\n📊 RESULTS:")
        print(f"   Total console messages: {len(console_messages)}")
        print(f"   Duplicate errors: {len(duplicate_errors)}")
        
        if duplicate_errors:
            print("\n❌ DUPLICATE CALLBACKS STILL PRESENT:")
            for i, error in enumerate(duplicate_errors[:10], 1):
                print(f"   {i}. {error[:150]}...")
            return False
        else:
            print("\n✅ NO DUPLICATE CALLBACKS DETECTED!")
            return True
        
        # Keep browser open for manual inspection
        page.wait_for_timeout(10000)
        browser.close()

if __name__ == '__main__':
    success = test_for_duplicates()
    sys.exit(0 if success else 1)
