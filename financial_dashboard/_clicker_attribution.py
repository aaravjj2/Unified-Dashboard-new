#!/usr/bin/env python3
"""
Quick diagnostic: Click Attribution Lab tab and capture error
"""
import time
from playwright.sync_api import sync_playwright

def test_attribution_tab():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            print("Loading dashboard...")
            page.goto('http://localhost:8050/', timeout=15000)
            page.wait_for_load_state('networkidle', timeout=10000)
            print("✅ Page loaded")
            
            # Take screenshot of initial state
            page.screenshot(path='test_screenshots/0_initial.png')
            print("📸 Screenshot: 0_initial.png")
            
            # Check which tabs are visible
            print("\nChecking for tabs...")
            tabs = page.locator('[data-value]').all()
            print(f"Found {len(tabs)} tab elements")
            
            for i, tab in enumerate(tabs):
                try:
                    value = tab.get_attribute('data-value')
                    text = tab.inner_text()
                    print(f"  Tab {i}: {value} - '{text}'")
                except:
                    print(f"  Tab {i}: (unable to read)")
            
            # Try to find Attribution Lab
            print("\nLooking for Attribution Lab...")
            
            # Try different selectors
            selectors = [
                '#tab-attribution_lab',
                '[data-value="attribution_lab"]',
                'text="Attribution Lab"',
                'text="📊 Attribution Lab"'
            ]
            
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        print(f"✅ Found with selector: {selector}")
                        element.screenshot(path=f'test_screenshots/found_{selector.replace("#", "").replace("[", "").replace("]", "").replace("=", "")[:20]}.png')
                        
                        # Try clicking
                        print(f"   Attempting click...")
                        element.click(timeout=5000)
                        page.wait_for_timeout(2000)
                        page.screenshot(path='test_screenshots/1_after_click.png')
                        print("   ✅ Click successful!")
                        print("   📸 Screenshot: 1_after_click.png")
                        break
                    else:
                        print(f"❌ Found but not visible: {selector}")
                except Exception as e:
                    print(f"❌ Not found with {selector}: {e}")
            
            # Check console errors
            print("\nConsole errors:")
            page.on('console', lambda msg: print(f"   {msg.type}: {msg.text}"))
            
            # Check network errors
            page.on('response', lambda response: 
                print(f"   {response.status} {response.url}") if response.status >= 400 else None
            )
            
            time.sleep(5)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            page.screenshot(path='test_screenshots/error.png')
            print("📸 Screenshot: error.png")
            
        finally:
            browser.close()

if __name__ == '__main__':
    test_attribution_tab()
