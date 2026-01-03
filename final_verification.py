#!/usr/bin/env python3
"""
FINAL VERIFICATION TEST
Tests both Chain Viewer and Command Palette functionality.
"""

from playwright.sync_api import sync_playwright
import time

def run_tests():
    results = {
        'chain_viewer': False,
        'load_command': False,
        'help_command': False,
        'ticker_changes': False
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("="*60)
        print("🔍 FINAL VERIFICATION TEST")
        print("="*60)
        
        page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
        time.sleep(3)
        
        # ===== TEST 1: CHAIN VIEWER =====
        print("\n📊 TEST 1: Chain Viewer (Strategy > Chain & Greeks)")
        
        # Navigate to Chain & Greeks
        page.locator('text=Strategy').first.click()
        time.sleep(1)
        page.locator('text=Chain').first.click()
        time.sleep(2)
        
        # Check chain viewer content
        cv = page.locator('#chain-viewer-table-container')
        if cv.is_visible():
            content = cv.text_content()
            if len(content) > 1000:
                print(f"   ✅ Chain viewer has {len(content)} chars of data")
                results['chain_viewer'] = True
            else:
                print(f"   ❌ Chain viewer only has {len(content)} chars")
        else:
            print("   ❌ Chain viewer not visible")
        
        page.screenshot(path='final_1_chain.png')
        
        # ===== TEST 2: COMMAND PALETTE - /help =====
        print("\n⌨️  TEST 2: Command Palette /help")
        
        # Open palette
        page.locator('#command-palette-trigger').click()
        time.sleep(0.5)
        
        cmd_input = page.locator('#command-input')
        if cmd_input.is_visible():
            cmd_input.fill('/help')
            cmd_input.press('Enter')
            time.sleep(2)
            
            results_el = page.locator('#cmd-results')
            if results_el.is_visible():
                text = results_el.text_content()
                if len(text) > 50:
                    print(f"   ✅ /help returned {len(text)} chars")
                    results['help_command'] = True
                else:
                    print(f"   ❌ /help returned only {len(text)} chars")
            else:
                print("   ❌ Results not visible")
        else:
            print("   ❌ Command input not visible")
        
        page.screenshot(path='final_2_help.png')
        
        # ===== TEST 3: COMMAND PALETTE - /load =====
        print("\n📈 TEST 3: Command Palette /load NVDA")
        
        # Get initial ticker
        ticker_input = page.locator('#alpaca-ticker-input')
        initial_ticker = ticker_input.input_value() if ticker_input.is_visible() else ""
        
        # Load NVDA
        cmd_input = page.locator('#command-input')
        cmd_input.fill('/load NVDA')
        cmd_input.press('Enter')
        time.sleep(5)
        
        # Check status
        status = page.locator('#alpaca-status-message')
        status_text = status.text_content() if status.is_visible() else ""
        
        if 'NVDA' in status_text and 'Successfully' in status_text:
            print(f"   ✅ Status: {status_text[:50]}...")
            results['load_command'] = True
        else:
            print(f"   ❌ Status: {status_text[:50]}")
        
        # Check ticker changed
        new_ticker = ticker_input.input_value() if ticker_input.is_visible() else ""
        if 'NVDA' in new_ticker.upper():
            print(f"   ✅ Ticker changed to: {new_ticker}")
            results['ticker_changes'] = True
        else:
            print(f"   ❌ Ticker is still: {new_ticker}")
        
        page.screenshot(path='final_3_load.png')
        
        browser.close()
    
    return results


if __name__ == "__main__":
    results = run_tests()
    
    print("\n" + "="*60)
    print("📋 RESULTS SUMMARY")
    print("="*60)
    
    tests = [
        ("Chain Viewer displays data", results['chain_viewer']),
        ("/help command works", results['help_command']),
        ("/load command works", results['load_command']),
        ("Ticker updates on /load", results['ticker_changes'])
    ]
    
    passed = sum(1 for _, v in tests if v)
    
    for name, passed_test in tests:
        icon = "✅" if passed_test else "❌"
        print(f"   {icon} {name}")
    
    print(f"\n   TOTAL: {passed}/{len(tests)} tests passed")
    print("="*60)
    
    if passed == len(tests):
        print("\n🎉 ALL TESTS PASSED! Chain Viewer and Commands working!")
    else:
        print("\n⚠️  Some tests failed. Check screenshots.")
    
    print("\n📸 Screenshots: final_1_chain.png, final_2_help.png, final_3_load.png")
