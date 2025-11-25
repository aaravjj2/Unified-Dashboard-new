#!/usr/bin/env python3
"""
Test clicking tabs by index position to capture errors from Analysis Hub and Research Lab
"""

from playwright.sync_api import sync_playwright
import json
import time

def test_tabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Collect console messages
        console_messages = []
        page.on('console', lambda msg: console_messages.append({
            'type': msg.type,
            'text': msg.text,
            'location': msg.location
        }))
        
        # Collect page errors
        page_errors = []
        page.on('pageerror', lambda exc: page_errors.append(str(exc)))
        
        print("Loading dashboard...")
        page.goto('http://localhost:8000', wait_until='networkidle', timeout=60000)
        print("✓ Dashboard loaded")
        
        # Wait for tabs to render
        page.wait_for_selector('a[role="tab"]', timeout=10000)
        time.sleep(2)
        
        # Get all main navigation tabs (first tab set)
        main_tabs = page.locator('a[id^="react-aria"][id*="-1-tab-"][role="tab"]').all()
        print(f"\nFound {len(main_tabs)} main navigation tabs")
        
        # Tab names we expect (for reference)
        tab_names = [
            "Market Trends",
            "Market Forecast", 
            "Monthly Picks",
            "Weekly Picks",
            "Analysis Hub",      # Index 4 - FAILING
            "Portfolio Dashboard", # Index 5 - WORKING
            "Research Lab"        # Index 6 - FAILING
        ]
        
        # Test Analysis Hub (index 4)
        print("\n" + "="*60)
        print("Testing Analysis Hub (index 4)")
        print("="*60)
        
        console_messages.clear()
        page_errors.clear()
        
        try:
            main_tabs[4].click()
            print("✓ Clicked Analysis Hub tab")
            page.wait_for_timeout(3000)
            
            # Check for error message in page
            error_elements = page.locator('text=/Internal Server Error|Error:/i').all()
            if error_elements:
                print(f"⚠ Found {len(error_elements)} error elements on page")
                for idx, elem in enumerate(error_elements[:3]):
                    text = elem.text_content()
                    print(f"  Error {idx+1}: {text[:200]}")
            
            # Save screenshot
            page.screenshot(path='analysis_hub_error.png')
            print("✓ Screenshot saved: analysis_hub_error.png")
            
            # Print console errors
            errors = [m for m in console_messages if m['type'] == 'error']
            if errors:
                print(f"\n⚠ Console errors ({len(errors)}):")
                for err in errors[:5]:
                    print(f"  {err['text']}")
            
            # Print page errors
            if page_errors:
                print(f"\n⚠ Page errors ({len(page_errors)}):")
                for err in page_errors[:5]:
                    print(f"  {err}")
                    
        except Exception as e:
            print(f"✗ Error testing Analysis Hub: {e}")
        
        # Test Research Lab (index 6)
        print("\n" + "="*60)
        print("Testing Research Lab (index 6)")
        print("="*60)
        
        console_messages.clear()
        page_errors.clear()
        
        try:
            main_tabs[6].click()
            print("✓ Clicked Research Lab tab")
            page.wait_for_timeout(3000)
            
            # Check for error message in page
            error_elements = page.locator('text=/Internal Server Error|Error:/i').all()
            if error_elements:
                print(f"⚠ Found {len(error_elements)} error elements on page")
                for idx, elem in enumerate(error_elements[:3]):
                    text = elem.text_content()
                    print(f"  Error {idx+1}: {text[:200]}")
            
            # Save screenshot
            page.screenshot(path='research_lab_error.png')
            print("✓ Screenshot saved: research_lab_error.png")
            
            # Print console errors
            errors = [m for m in console_messages if m['type'] == 'error']
            if errors:
                print(f"\n⚠ Console errors ({len(errors)}):")
                for err in errors[:5]:
                    print(f"  {err['text']}")
            
            # Print page errors
            if page_errors:
                print(f"\n⚠ Page errors ({len(page_errors)}):")
                for err in page_errors[:5]:
                    print(f"  {err}")
                    
        except Exception as e:
            print(f"✗ Error testing Research Lab: {e}")
        
        # Save detailed results
        results = {
            'analysis_hub': {
                'console_messages': console_messages[:20],
                'page_errors': page_errors[:10]
            }
        }
        
        with open('tab_errors_detailed.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("\n✓ Detailed results saved to tab_errors_detailed.json")
        
        browser.close()

if __name__ == '__main__':
    test_tabs()
