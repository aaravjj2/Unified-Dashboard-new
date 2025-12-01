#!/usr/bin/env python3
"""
AGENT 1A DIAGNOSTIC: Callback Trigger Check
Test if callbacks are actually firing when tabs are loaded.
"""
import time
from playwright.sync_api import sync_playwright

def check_callback_triggers():
    """Check if callbacks fire and populate content."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        # Enable console logging to catch client-side errors
        page = context.new_page()
        
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        
        print("\n" + "="*70)
        print("AGENT 1A - CALLBACK TRIGGER DIAGNOSTIC")
        print("="*70)
        
        # Load dashboard
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        print("✓ Dashboard loaded")
        time.sleep(2)
        
        # Check for Dash loading errors
        print("\n--- CONSOLE MESSAGES ---")
        for msg in console_messages[-20:]:
            if 'error' in msg.lower() or 'warning' in msg.lower():
                print(f"  {msg}")
        
        # Click Weekly Picks and wait longer
        print("\n--- TESTING WEEKLY PICKS CALLBACK ---")
        weekly_tab = page.get_by_text("Weekly Picks", exact=True).first
        weekly_tab.click()
        print("✓ Clicked Weekly Picks tab")
        
        # Wait for callback to fire (check multiple times)
        for attempt in range(6):
            time.sleep(2)
            wp_content = page.locator('#wp-content')
            wp_html = wp_content.inner_html() if wp_content.count() > 0 else ""
            print(f"  Attempt {attempt+1}: #wp-content innerHTML length = {len(wp_html)} chars")
            
            if len(wp_html) > 100:
                print(f"  ✅ Content populated!")
                break
        else:
            print(f"  ❌ Content never populated after 12 seconds")
        
        # Check Monthly Picks
        print("\n--- TESTING MONTHLY PICKS CALLBACK ---")
        monthly_tab = page.get_by_text("Monthly Picks", exact=True).first
        monthly_tab.click()
        print("✓ Clicked Monthly Picks tab")
        
        # Wait for callback to fire
        for attempt in range(6):
            time.sleep(2)
            mp_content = page.locator('#mp-content')
            mp_html = mp_content.inner_html() if mp_content.count() > 0 else ""
            print(f"  Attempt {attempt+1}: #mp-content innerHTML length = {len(mp_html)} chars")
            
            if len(mp_html) > 100:
                print(f"  ✅ Content populated!")
                break
        else:
            print(f"  ❌ Content never populated after 12 seconds")
        
        # Check for Dash-specific errors
        print("\n--- CHECKING FOR DASH ERRORS ---")
        dash_errors = [msg for msg in console_messages if 'callback' in msg.lower() or 'dash' in msg.lower()]
        if dash_errors:
            print("  Found Dash-related messages:")
            for msg in dash_errors[-10:]:
                print(f"    {msg}")
        else:
            print("  No Dash-specific errors found")
        
        browser.close()

if __name__ == '__main__':
    check_callback_triggers()
