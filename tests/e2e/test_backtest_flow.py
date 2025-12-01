#!/usr/bin/env python3
"""
Check Strategy Lab callback flow by watching network/logs.
"""

import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8051"

def test_backtest_flow():
    print("🚀 Testing Strategy Lab backtest flow...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Capture console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text))
        
        # Capture network requests
        requests = []
        page.on("request", lambda req: requests.append(req.url) if '_dash-update-component' in req.url else None)
        
        page.goto(BASE_URL, timeout=30000)
        time.sleep(3)
        
        # Go to Strategy Lab
        page.locator('text=Strategy Lab').first.click()
        time.sleep(2)
        
        # Setup subtab
        page.locator('.nav-link:has-text("Setup")').first.click()
        time.sleep(1)
        
        # Fill tickers
        page.locator('input#sl-tickers-input').fill("AAPL")
        time.sleep(1)
        
        # Click Validate
        print("🔵 Clicking Validate...")
        page.locator('#sl-validate-btn').click()
        time.sleep(3)
        
        # Check validation result
        result = page.locator('#sl-validation-result').text_content()
        print(f"✅ Validation result: {result[:80]}...")
        
        # Go to Execute
        print("\n🔵 Going to Execute subtab...")
        page.locator('.nav-link:has-text("Execute")').first.click()
        time.sleep(1)
        
        # Clear network log
        requests.clear()
        
        # Click Run Backtest
        print("🔵 Clicking Run Backtest...")
        run_btn = page.locator('button#sl-run-backtest-btn')
        print(f"   Button visible: {run_btn.is_visible()}")
        print(f"   Button enabled: {run_btn.is_enabled()}")
        
        run_btn.click()
        print("   Clicked! Waiting for response...")
        
        # Wait and monitor
        for i in range(15):
            time.sleep(1)
            print(f"   ... {i+1}s (requests: {len(requests)})")
            
            # Check execution status
            status = page.locator('#sl-execution-status')
            if status.is_visible():
                text = status.text_content()
                if text and 'Complete' in text:
                    print(f"   ✅ Status: {text[:100]}...")
                    break
                elif text and len(text) > 5:
                    print(f"   Status update: {text[:80]}...")
        
        # Check Results tab
        print("\n🔵 Checking Results subtab...")
        page.locator('.nav-link:has-text("Results")').first.click()
        time.sleep(2)
        
        # Check metrics
        cagr = page.locator('#sl-metric-cagr')
        if cagr.is_visible():
            print(f"   CAGR: {cagr.text_content()}")
        else:
            print("   ⚠️ CAGR not visible")
        
        sharpe = page.locator('#sl-metric-sharpe')
        if sharpe.is_visible():
            print(f"   Sharpe: {sharpe.text_content()}")
        
        maxdd = page.locator('#sl-metric-maxdd')
        if maxdd.is_visible():
            print(f"   Max DD: {maxdd.text_content()}")
        
        # Check equity curve
        equity = page.locator('#sl-equity-curve .js-plotly-plot')
        if equity.count() > 0:
            print("   ✅ Equity curve chart rendered")
        else:
            print("   ⚠️ Equity curve not rendered")
        
        # Check Benchmark
        print("\n🔵 Checking Benchmark subtab...")
        page.locator('.nav-link:has-text("Benchmark")').first.click()
        time.sleep(2)
        
        bench_chart = page.locator('#sl-benchmark-comparison-chart .js-plotly-plot')
        if bench_chart.count() > 0:
            print("   ✅ Benchmark chart rendered")
        else:
            content = page.locator('#sl-benchmark-comparison-chart').inner_html()
            if 'Run backtest' in content:
                print("   ⚠️ Still showing placeholder")
            else:
                print("   ⚠️ Benchmark chart empty/missing")
        
        # Check Risk
        print("\n🔵 Checking Risk subtab...")
        page.locator('.nav-link:has-text("Risk")').first.click()
        time.sleep(2)
        
        risk_dd = page.locator('#sl-risk-max-dd')
        if risk_dd.is_visible():
            print(f"   Max Drawdown: {risk_dd.text_content()}")
        
        risk_vol = page.locator('#sl-risk-volatility')
        if risk_vol.is_visible():
            print(f"   Volatility: {risk_vol.text_content()}")
        
        print("\n📊 Summary:")
        print(f"   Total network requests to callbacks: {len(requests)}")
        print(f"   Console messages: {len(console_messages)}")
        
        # Print any errors
        errors = [m for m in console_messages if 'error' in m.lower()]
        if errors:
            print(f"   Console errors: {errors[:5]}")
        
        print("\n✅ Test complete. Browser stays open 20s for inspection...")
        time.sleep(20)
        
        browser.close()


if __name__ == "__main__":
    test_backtest_flow()
