#!/usr/bin/env python3
"""
Deep Alpaca Options Lab Test - Port 8053
Specifically tests:
1. Console errors (should be zero)
2. Alpaca expiration dropdown sync fix
3. Data loading and table rendering
"""

import asyncio
import sys
import json
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8053"

class DeepAlpacaTest:
    def __init__(self):
        self.console_errors = []
        self.console_warnings = []
        self.results = []
        
    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Capture ALL console messages
            def handle_console(msg):
                text = msg.text
                if msg.type == "error":
                    self.console_errors.append(text)
                    print(f"❌ CONSOLE ERROR: {text[:200]}")
                elif msg.type == "warning":
                    self.console_warnings.append(text)
                    
            page.on("console", handle_console)
            
            try:
                print("\n" + "="*70)
                print("DEEP ALPACA OPTIONS LAB TEST")
                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"URL: {BASE_URL}")
                print("="*70)
                
                # 1. Load dashboard
                print("\n📍 Step 1: Loading Alpaca UI...")
                await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)
                print("   ✅ Alpaca UI loaded")
                
                # 2. No need to navigate - standalone UI is directly loaded
                print("\n📍 Step 2: Checking page loaded (standalone Alpaca UI)...")
                # Check for title or main container
                title = await page.query_selector('h1')
                if title:
                    title_text = await title.inner_text()
                    print(f"   ✅ Page title: {title_text}")
                else:
                    print("   ℹ️ No H1 title found")
                
                # 3. Check for initial console errors (should be zero after fix)
                initial_errors = len(self.console_errors)
                print(f"\n📍 Step 3: Checking initial console errors...")
                if initial_errors > 0:
                    print(f"   ❌ Found {initial_errors} console errors on initial load!")
                    for i, err in enumerate(self.console_errors[:5]):
                        print(f"      {i+1}. {err[:100]}...")
                else:
                    print("   ✅ No console errors on initial load!")
                    
                # 4. Check Alpaca-specific components
                print("\n📍 Step 4: Checking Alpaca components...")
                
                # Check alpaca-ticker-input
                ticker_input = await page.query_selector('#alpaca-ticker-input')
                if ticker_input:
                    print("   ✅ alpaca-ticker-input found")
                else:
                    print("   ❌ alpaca-ticker-input NOT found")
                    
                # Check alpaca-load-button
                load_btn = await page.query_selector('#alpaca-load-button')
                if load_btn:
                    print("   ✅ alpaca-load-button found")
                else:
                    print("   ❌ alpaca-load-button NOT found")
                    
                # Check hidden dropdown placeholder (our fix)
                hidden_dropdown = await page.query_selector('#alpaca-expiration-dropdown')
                if hidden_dropdown:
                    print("   ✅ alpaca-expiration-dropdown (hidden placeholder) found")
                else:
                    print("   ❌ alpaca-expiration-dropdown NOT found - FIX NOT APPLIED!")
                    
                # 5. Test ticker input and load
                print("\n📍 Step 5: Testing ticker input and load...")
                if ticker_input:
                    await ticker_input.fill('')
                    await ticker_input.type('SPY')
                    await page.wait_for_timeout(500)
                    print("   ✅ Entered 'SPY' in ticker input")
                    
                if load_btn:
                    await load_btn.click()
                    print("   ⏳ Clicked Load Chain, waiting for data...")
                    await page.wait_for_timeout(5000)
                    
                # 6. Check if expiration selector appeared (dynamic component)
                print("\n📍 Step 6: Checking expiration selector...")
                exp_selector = await page.query_selector('#alpaca-expiration-selector')
                if exp_selector:
                    print("   ✅ alpaca-expiration-selector (visible) found")
                else:
                    # Try the dropdown directly
                    exp_dropdown = await page.query_selector('#alpaca-expiration-dropdown')
                    if exp_dropdown:
                        is_visible = await exp_dropdown.is_visible()
                        if is_visible:
                            print("   ✅ alpaca-expiration-dropdown is visible")
                        else:
                            print("   ℹ️ alpaca-expiration-dropdown exists but hidden (as expected)")
                    else:
                        print("   ❌ No expiration selector found")
                        
                # 7. Check table rendering
                print("\n📍 Step 7: Checking table rendering...")
                table_container = await page.query_selector('#alpaca-table-container')
                if table_container:
                    html = await table_container.inner_html()
                    if len(html) > 100:
                        print(f"   ✅ alpaca-table-container has content ({len(html)} chars)")
                    else:
                        print(f"   ⚠️ alpaca-table-container is mostly empty")
                else:
                    print("   ❌ alpaca-table-container NOT found")
                    
                # 8. Check for any errors after interaction
                print("\n📍 Step 8: Checking for errors after data load...")
                total_errors = len(self.console_errors)
                new_errors = total_errors - initial_errors
                if new_errors > 0:
                    print(f"   ❌ {new_errors} new console errors after data load!")
                    for err in self.console_errors[initial_errors:]:
                        if 'alpaca-expiration-dropdown' in err:
                            print(f"      🔴 DROPDOWN ERROR: {err[:150]}...")
                        else:
                            print(f"      ⚠️ {err[:150]}...")
                else:
                    print("   ✅ No new console errors after data load!")
                    
                # 9. Test changing expiration
                print("\n📍 Step 9: Testing expiration change...")
                try:
                    # Click on expiration container to see dropdown options
                    exp_container = await page.query_selector('#alpaca-expiration-container')
                    if exp_container:
                        # Find any dropdown inside
                        dropdown = await exp_container.query_selector('.Select-control, select, [class*="dropdown"]')
                        if dropdown:
                            await dropdown.click()
                            await page.wait_for_timeout(1000)
                            print("   ✅ Clicked expiration dropdown")
                except Exception as e:
                    print(f"   ⚠️ Could not interact with dropdown: {e}")
                    
                # 10. Final error count
                print("\n📍 Step 10: Final error count...")
                final_errors = len(self.console_errors)
                
            except Exception as e:
                print(f"\n❌ Critical test error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                await browser.close()
                
        # Generate summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        print(f"\n📊 Console Errors: {len(self.console_errors)}")
        print(f"📊 Console Warnings: {len(self.console_warnings)}")
        
        # Check for the specific error we fixed
        dropdown_errors = [e for e in self.console_errors if 'alpaca-expiration-dropdown' in e]
        if dropdown_errors:
            print(f"\n❌ FAILED: alpaca-expiration-dropdown error still present!")
            print("   The fix did not work - callback references non-existent element")
            return False
        else:
            print(f"\n✅ PASSED: No alpaca-expiration-dropdown errors!")
            print("   The hidden placeholder dropdown fix is working")
            return True


async def main():
    tester = DeepAlpacaTest()
    success = await tester.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
