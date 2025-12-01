#!/usr/bin/env python3
"""Test all Strategy Lab subtabs after backtest."""
from playwright.sync_api import sync_playwright
import time

def test_all_subtabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("🔗 Navigating to dashboard...")
        page.goto("http://127.0.0.1:8051/", wait_until="load", timeout=30000)
        page.wait_for_selector('.nav-link, .nav-tabs', timeout=10000)
        page.wait_for_timeout(2000)
        
        print("📍 Clicking Strategy Lab tab...")
        # Try multiple selectors
        for selector in ['text=Strategy Lab', '.nav-link:has-text("Strategy")']:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=3000):
                    el.click()
                    break
            except:
                pass
        page.wait_for_timeout(2000)
        
        # Setup
        print("\n📍 Step 1: Setup subtab...")
        # Use nav-link selector like the working test
        setup_link = page.locator('.nav-link:has-text("Setup")').first
        if setup_link.is_visible(timeout=5000):
            setup_link.click()
        else:
            print("   ⚠️ Setup link not visible, skipping click")
        page.wait_for_timeout(1500)
        
        tickers = page.locator('input#sl-tickers-input').first
        if tickers.is_visible(timeout=3000):
            tickers.fill("AAPL")
        
        # Validate
        validate_btn = page.locator('#sl-validate-btn').first
        if validate_btn.is_visible(timeout=3000):
            validate_btn.click()
            page.wait_for_timeout(2000)
            print("✅ Strategy validated")
        
        # Execute
        print("\n📍 Step 2: Execute & Configure subtab...")
        exec_link = page.locator('.nav-link:has-text("Execute")').first
        if exec_link.is_visible(timeout=5000):
            exec_link.click()
        page.wait_for_timeout(2000)
        
        run_btn = page.locator('button#sl-run-backtest-btn, #sl-run-backtest-btn').first
        if run_btn.is_visible(timeout=3000) and run_btn.is_enabled():
            print("🚀 Clicking Run Backtest...")
            run_btn.click()
            page.wait_for_timeout(10000)  # Wait for backtest
            print("✅ Backtest executed")
        
        # Check Results subtab
        print("\n📊 Step 3: Checking Results subtab...")
        results_link = page.locator('.nav-link:has-text("Results")').first
        if results_link.is_visible(timeout=5000):
            results_link.click()
        page.wait_for_timeout(3000)
        
        content = page.content()
        results_checks = {
            'sl-metric-cagr': 'sl-metric-cagr' in content,
            'sl-metric-sharpe': 'sl-metric-sharpe' in content,
            'sl-equity-curve': 'sl-equity-curve' in content,
        }
        print(f"   Results elements: {results_checks}")
        results_ok = all(results_checks.values())
        
        # Check Benchmark subtab
        print("\n📊 Step 4: Checking Benchmark subtab...")
        bench_link = page.locator('.nav-link:has-text("Benchmark")').first
        if bench_link.is_visible(timeout=5000):
            bench_link.click()
        page.wait_for_timeout(3000)
        
        content = page.content()
        benchmark_checks = {
            'sl-benchmark-chart': 'sl-benchmark-chart' in content or 'benchmark' in content.lower(),
            'sl-benchmark-metrics': 'sl-benchmark-metrics' in content or 'alpha' in content.lower(),
        }
        print(f"   Benchmark elements: {benchmark_checks}")
        benchmark_ok = any(benchmark_checks.values())
        
        # Check Risk subtab
        print("\n📊 Step 5: Checking Risk & Factors subtab...")
        risk_link = page.locator('.nav-link:has-text("Risk")').first
        if risk_link.is_visible(timeout=5000):
            risk_link.click()
        page.wait_for_timeout(3000)
        
        content = page.content()
        risk_checks = {
            'sl-risk-chart': 'sl-risk-chart' in content or 'risk' in content.lower(),
            'sl-drawdown': 'drawdown' in content.lower(),
            'sl-volatility': 'volatility' in content.lower(),
        }
        print(f"   Risk elements: {risk_checks}")
        risk_ok = any(risk_checks.values())
        
        # Summary
        print("\n" + "="*60)
        print("📋 SUMMARY")
        print("="*60)
        print(f"   Results subtab: {'✅ CONNECTED' if results_ok else '❌ MISSING DATA'}")
        print(f"   Benchmark subtab: {'✅ CONNECTED' if benchmark_ok else '❌ MISSING DATA'}")
        print(f"   Risk subtab: {'✅ CONNECTED' if risk_ok else '❌ MISSING DATA'}")
        print("="*60)
        
        browser.close()
        
        return results_ok, benchmark_ok, risk_ok

if __name__ == "__main__":
    test_all_subtabs()
