#!/usr/bin/env python3
"""
Test Research Lab callback firing by checking browser console logs.
"""

from playwright.sync_api import sync_playwright
import time

def test_research_lab_callback():
    """Test if Research Lab callbacks fire when clicking tabs."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()
        
        # Track console messages
        console_messages = []
        def handle_console(msg):
            console_messages.append(f"[{msg.type}] {msg.text}")
            print(f"CONSOLE [{msg.type}]: {msg.text}")
        
        page.on("console", handle_console)
        
        try:
            # Load dashboard
            print("Loading dashboard...")
            page.goto("http://localhost:8051/", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # Click Research Lab tab
            print("\nClicking Research Lab tab...")
            page.click('a#research-lab-tab', timeout=10000)
            time.sleep(2)
            
            # Check if research-lab-content div exists
            content_div = page.query_selector('#research-lab-content')
            print(f"\nresearch-lab-content div exists: {content_div is not None}")
            
            if content_div:
                inner_html = content_div.inner_html()
                print(f"Content length: {len(inner_html)} chars")
                print(f"First 200 chars: {inner_html[:200]}")
            
            # Click Market Scan subtab
            print("\nClicking Market Scan subtab...")
            page.click('a[data-rb-event-key="market-scan"]', timeout=10000)
            time.sleep(2)
            
            # Check content again
            if content_div:
                inner_html = content_div.inner_html()
                print(f"\nAfter Market Scan click:")
                print(f"Content length: {len(inner_html)} chars")
                print(f"First 200 chars: {inner_html[:200]}")
            
            # Click Research Notes subtab
            print("\nClicking Research Notes subtab...")
            page.click('a[data-rb-event-key="research-notes"]', timeout=10000)
            time.sleep(2)
            
            # Check content again
            if content_div:
                inner_html = content_div.inner_html()
                print(f"\nAfter Research Notes click:")
                print(f"Content length: {len(inner_html)} chars")
                print(f"First 200 chars: {inner_html[:200]}")
            
            # Look for Dash callback logs
            print("\n" + "="*60)
            print("Console messages containing 'callback' or 'research':")
            for msg in console_messages:
                if 'callback' in msg.lower() or 'research' in msg.lower():
                    print(msg)
            
            print("\n" + "="*60)
            print(f"Total console messages: {len(console_messages)}")
            
            time.sleep(3)
            
        finally:
            browser.close()

if __name__ == "__main__":
    test_research_lab_callback()
