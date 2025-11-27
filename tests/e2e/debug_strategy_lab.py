#!/usr/bin/env python3
"""
Debug Strategy Lab - Interactive headed testing

Run with:
    python tests/e2e/debug_strategy_lab.py
"""

import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8051"

def debug_strategy_lab():
    print("🚀 Starting headed browser for Strategy Lab debugging...")
    
    with sync_playwright() as p:
        # Launch headed browser
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        print(f"📍 Navigating to {BASE_URL}")
        page.goto(BASE_URL, timeout=30000)
        time.sleep(2)
        
        # Navigate to Strategy Lab
        print("🔵 Clicking Strategy Lab tab...")
        page.locator('text=Strategy Lab').first.click()
        time.sleep(2)
        
        # Check Setup subtab
        print("🔵 Checking Setup subtab...")
        page.locator('.nav-link:has-text("Setup")').first.click()
        time.sleep(1)
        
        # Fill tickers
        tickers_input = page.locator('input#sl-tickers-input')
        if tickers_input.is_visible():
            print("✅ Found tickers input")
            tickers_input.fill("AAPL")
            time.sleep(0.5)
        else:
            print("❌ Tickers input not found")
        
        # Check dropdowns
        entry_dropdown = page.locator('#sl-entry-condition.dash-dropdown')
        if entry_dropdown.is_visible():
            value = entry_dropdown.locator('.Select-value-label').text_content()
            print(f"✅ Entry condition: {value}")
        
        exit_dropdown = page.locator('#sl-exit-condition.dash-dropdown')
        if exit_dropdown.is_visible():
            value = exit_dropdown.locator('.Select-value-label').text_content()
            print(f"✅ Exit condition: {value}")
        
        # Click Validate
        print("🔵 Clicking Validate button...")
        validate_btn = page.locator('#sl-validate-btn')
        if validate_btn.is_visible():
            validate_btn.click()
            time.sleep(2)
            print("✅ Validate clicked")
            
            # Check validation result
            result = page.locator('#sl-validation-result')
            if result.is_visible():
                text = result.text_content()
                print(f"   Validation result: {text[:100]}...")
        
        # Go to Execute subtab
        print("\n🔵 Clicking Execute subtab...")
        page.locator('.nav-link:has-text("Execute")').first.click()
        time.sleep(1)
        
        # Check Run Backtest button
        run_btn = page.locator('button#sl-run-backtest-btn, #sl-run-backtest-btn')
        if run_btn.is_visible():
            print(f"✅ Run Backtest button found")
            print(f"   Enabled: {run_btn.is_enabled()}")
            print(f"   Text: {run_btn.text_content()}")
            
            # Check button's onclick handler
            btn_html = run_btn.evaluate("el => el.outerHTML")
            print(f"   HTML: {btn_html[:200]}...")
            
            # Try clicking it
            print("🔵 Clicking Run Backtest button...")
            run_btn.click()
            time.sleep(5)  # Wait for backtest
            
            # Check for progress or results
            progress = page.locator('#sl-backtest-progress, #sl-progress-container')
            if progress.is_visible():
                print(f"✅ Progress visible: {progress.text_content()[:100]}")
            else:
                print("⚠️ No progress indicator visible")
            
            status = page.locator('#sl-execution-status')
            if status.is_visible():
                print(f"   Status: {status.text_content()}")
        else:
            print("❌ Run Backtest button not found")
        
        # Check Results subtab
        print("\n🔵 Clicking Results subtab...")
        page.locator('.nav-link:has-text("Results")').first.click()
        time.sleep(2)
        
        # Check for equity curve
        equity = page.locator('#sl-equity-curve')
        if equity.is_visible():
            print("✅ Equity curve container found")
        else:
            print("⚠️ Equity curve not visible")
        
        # Check metrics
        for metric_id in ['sl-metric-cagr', 'sl-metric-sharpe', 'sl-metric-maxdd']:
            el = page.locator(f'#{metric_id}')
            if el.is_visible():
                print(f"   {metric_id}: {el.text_content()}")
        
        # Check Benchmark subtab
        print("\n🔵 Clicking Benchmark subtab...")
        page.locator('.nav-link:has-text("Benchmark")').first.click()
        time.sleep(2)
        
        bench_chart = page.locator('#sl-benchmark-comparison-chart')
        if bench_chart.is_visible():
            # Check if it has data or placeholder
            content = bench_chart.inner_html()
            if 'Run backtest' in content.lower() or 'no data' in content.lower():
                print("⚠️ Benchmark chart has placeholder - no data yet")
            else:
                print("✅ Benchmark chart has content")
        
        # Check Risk subtab
        print("\n🔵 Clicking Risk subtab...")
        page.locator('.nav-link:has-text("Risk")').first.click()
        time.sleep(2)
        
        risk_dd = page.locator('#sl-risk-max-dd')
        if risk_dd.is_visible():
            print(f"   Max Drawdown: {risk_dd.text_content()}")
        
        # Keep browser open for manual inspection
        print("\n✅ Debug complete. Browser stays open for 30 seconds for manual inspection...")
        time.sleep(30)
        
        browser.close()


if __name__ == "__main__":
    debug_strategy_lab()
