#!/usr/bin/env python3
"""
Test button functionality by checking callback registration
"""

import sys
import time
from playwright.sync_api import sync_playwright

def test_buttons():
    """Test if buttons trigger callbacks"""
    
    print("="*80)
    print("BUTTON FUNCTIONALITY TEST")
    print("="*80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        
        results = {}
        
        try:
            # Start dashboard in background
            print("\n📍 Starting dashboard...")
            import subprocess
            dashboard_process = subprocess.Popen(
                ['python', '-m', 'financial_dashboard.index'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for startup
            time.sleep(8)
            
            print("📍 Loading dashboard...")
            page.goto("http://localhost:8051/", timeout=30000)
            time.sleep(2)
            
            # Test 1: Portfolio Refresh Button
            print("\n--- Test 1: Portfolio Refresh Button ---")
            page.click('a[role="tab"]:has-text("Portfolio")')
            time.sleep(1)
            
            # Get initial state
            initial_html = page.content()
            initial_ticker_count = initial_html.count('ticker')
            
            # Try to find and click refresh button
            try:
                refresh_btn = page.locator('#portfolio-refresh-btn, button:has-text("Refresh")')
                if refresh_btn.count() > 0:
                    print("✅ Found refresh button")
                    refresh_btn.first.click()
                    time.sleep(2)
                    
                    # Check if content changed
                    new_html = page.content()
                    new_ticker_count = new_html.count('ticker')
                    
                    if new_ticker_count != initial_ticker_count:
                        print("✅ Button triggered update")
                        results['portfolio_refresh'] = 'WORKING'
                    else:
                        print("❌ Button clicked but no update")
                        results['portfolio_refresh'] = 'NOT_WORKING'
                else:
                    print("⚠️  Refresh button not found")
                    results['portfolio_refresh'] = 'NOT_FOUND'
            except Exception as e:
                print(f"❌ Error: {e}")
                results['portfolio_refresh'] = 'ERROR'
            
            # Test 2: Check console errors
            print("\n--- Test 2: Console Errors ---")
            console_errors = []
            
            def handle_console(msg):
                if msg.type == 'error':
                    console_errors.append(msg.text)
            
            page.on('console', handle_console)
            page.reload()
            time.sleep(2)
            
            print(f"Console errors: {len(console_errors)}")
            results['console_errors'] = len(console_errors)
            
            if len(console_errors) > 100:
                print("❌ Many console errors (>100)")
            elif len(console_errors) > 0:
                print(f"⚠️  Some console errors ({len(console_errors)})")
            else:
                print("✅ No console errors")
            
            # Test 3: Research Lab tabs
            print("\n--- Test 3: Research Lab Tabs ---")
            page.click('a[role="tab"]:has-text("Research Lab")')
            time.sleep(1)
            
            tabs_to_check = ['Factor Analysis', 'Correlation Explorer', 'Strategy Backtest']
            
            for tab_name in tabs_to_check:
                try:
                    page.click(f'a[role="tab"]:has-text("{tab_name}")')
                    time.sleep(0.5)
                    
                    body_text = page.locator('body').inner_text()
                    
                    if len(body_text) > 200:
                        print(f"✅ {tab_name}: Has content ({len(body_text)} chars)")
                        results[f'research_lab_{tab_name.lower().replace(" ", "_")}'] = 'HAS_CONTENT'
                    else:
                        print(f"❌ {tab_name}: Empty or minimal content")
                        results[f'research_lab_{tab_name.lower().replace(" ", "_")}'] = 'EMPTY'
                except Exception as e:
                    print(f"❌ {tab_name}: Error - {e}")
                    results[f'research_lab_{tab_name.lower().replace(" ", "_")}'] = 'ERROR'
            
            # Test 4: Market Forecast
            print("\n--- Test 4: Market Forecast ---")
            try:
                page.click('a[role="tab"]:has-text("Market Forecast")')
                time.sleep(1)
                
                body_text = page.locator('body').inner_text()
                has_aapl = 'AAPL' in body_text
                has_chart = page.locator('#mf-forecast-chart').count() > 0
                
                if has_aapl and has_chart:
                    print("✅ Market Forecast: Has AAPL forecast and chart")
                    results['market_forecast'] = 'WORKING'
                elif has_chart:
                    print("⚠️  Market Forecast: Has chart but no AAPL data")
                    results['market_forecast'] = 'PARTIAL'
                else:
                    print("❌ Market Forecast: No chart found")
                    results['market_forecast'] = 'NOT_WORKING'
                    
                # Screenshot
                page.screenshot(path='reports/fix_verification/screenshots/market_forecast.png')
                print("📸 Screenshot saved: market_forecast.png")
                
            except Exception as e:
                print(f"❌ Market Forecast error: {e}")
                results['market_forecast'] = 'ERROR'
            
            # Screenshot Research Lab
            page.click('a[role="tab"]:has-text("Research Lab")')
            time.sleep(0.5)
            page.click('a[role="tab"]:has-text("Factor Analysis")')
            time.sleep(0.5)
            page.screenshot(path='reports/fix_verification/screenshots/research_lab_factor_analysis.png')
            print("📸 Screenshot saved: research_lab_factor_analysis.png")
            
        finally:
            browser.close()
            dashboard_process.terminate()
            dashboard_process.wait()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        import json
        with open('reports/fix_verification/tests/button_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        for key, value in results.items():
            print(f"{key:40s} {value}")
        
        print("\n" + "="*80)
        
        working_count = sum(1 for v in results.values() if v in ['WORKING', 'HAS_CONTENT'])
        total_count = len(results)
        
        print(f"Working: {working_count}/{total_count}")
        
        if working_count == total_count:
            print("✅ ALL TESTS PASSED")
            return 0
        else:
            print("⚠️  SOME TESTS FAILED")
            return 1

if __name__ == '__main__':
    sys.exit(test_buttons())
