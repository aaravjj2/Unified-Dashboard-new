#!/usr/bin/env python
"""Comprehensive Volatility Lab button test with output monitoring."""
from playwright.sync_api import sync_playwright
import time

def test_volatility_lab_comprehensive():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Collect console messages
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Navigate to Volatility Lab
        print("\n1. Navigating to Volatility Lab...")
        page.click('#tab-volatility_lab')
        time.sleep(2)
        
        # Test 1: Quick Compute Button
        print("\n2. Testing Quick Compute button...")
        try:
            btn = page.locator('#vl-compute-quick-btn')
            if btn.count() > 0:
                print("   Button found, clicking...")
                
                # Get initial state of output areas
                initial_state = page.evaluate('''() => {
                    return {
                        atm_iv: document.getElementById('vl-overview-atm-iv')?.innerText || 'N/A',
                        heatmap: document.getElementById('vl-heatmap')?.innerHTML?.length || 0
                    }
                }''')
                print(f"   Initial state: {initial_state}")
                
                btn.click()
                time.sleep(3)
                
                # Check for changes
                after_state = page.evaluate('''() => {
                    return {
                        atm_iv: document.getElementById('vl-overview-atm-iv')?.innerText || 'N/A',
                        heatmap: document.getElementById('vl-heatmap')?.innerHTML?.length || 0
                    }
                }''')
                print(f"   After click: {after_state}")
                
                if initial_state != after_state:
                    print("   ✅ Output CHANGED after click!")
                else:
                    print("   ❌ NO CHANGE in output")
            else:
                print("   ❌ Button not found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Test 2: Calculate IV Surface
        print("\n3. Testing Calculate IV Surface...")
        try:
            ticker_input = page.locator('#vl-calc-ticker')
            run_btn = page.locator('#vl-calc-run-btn')
            
            if ticker_input.count() > 0 and run_btn.count() > 0:
                print("   Filling ticker SPY...")
                ticker_input.fill('SPY')
                time.sleep(0.5)
                
                # Get heatmap before
                heatmap_before = page.locator('#vl-heatmap').inner_html()
                heatmap_len_before = len(heatmap_before) if heatmap_before else 0
                print(f"   Heatmap HTML length before: {heatmap_len_before}")
                
                print("   Clicking Run...")
                run_btn.click()
                time.sleep(4)
                
                # Get heatmap after
                heatmap_after = page.locator('#vl-heatmap').inner_html()
                heatmap_len_after = len(heatmap_after) if heatmap_after else 0
                print(f"   Heatmap HTML length after: {heatmap_len_after}")
                
                if heatmap_len_after > heatmap_len_before:
                    print("   ✅ Heatmap UPDATED!")
                else:
                    print("   ❌ Heatmap DID NOT update")
                    
                # Check metrics table
                metrics = page.locator('#vl-iv-metrics-table').inner_text()
                print(f"   Metrics table: {metrics[:100] if metrics else 'Empty'}...")
                
            else:
                print("   ❌ Components not found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Test 3: Run Signals
        print("\n4. Testing Run Signals button...")
        try:
            signals_btn = page.locator('#vl-signal-run-btn')
            if signals_btn.count() > 0:
                signals_btn.click()
                time.sleep(3)
                
                signal_table = page.locator('#vl-signal-table').inner_text()
                print(f"   Signal table: {signal_table[:100] if signal_table else 'Empty'}...")
                
                if signal_table and len(signal_table) > 10:
                    print("   ✅ Signals generated!")
                else:
                    print("   ❌ No signals output")
            else:
                print("   ❌ Button not found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Test 4: Run Backtest
        print("\n5. Testing Run Backtest button...")
        try:
            backtest_btn = page.locator('#vl-backtest-run-btn')
            if backtest_btn.count() > 0:
                backtest_btn.click()
                time.sleep(3)
                
                backtest_results = page.locator('#vl-backtest-results').inner_text()
                print(f"   Backtest results: {backtest_results[:100] if backtest_results else 'Empty'}...")
                
                if backtest_results and len(backtest_results) > 10:
                    print("   ✅ Backtest ran!")
                else:
                    print("   ❌ No backtest output")
            else:
                print("   ❌ Button not found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Check console for errors
        print("\n6. Console errors (last 10):")
        for log in console_logs[-10:]:
            if 'error' in log.lower() or 'warn' in log.lower():
                print(f"   {log[:150]}")
        
        page.screenshot(path='/home/aarav/unified-dashboard/volatility_lab_full_test.png')
        print("\n📸 Screenshot saved: volatility_lab_full_test.png")
        
        print("\n✅ Test complete!")
        time.sleep(10)
        browser.close()

if __name__ == '__main__':
    test_volatility_lab_comprehensive()
