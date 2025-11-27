#!/usr/bin/env python3
"""
Comprehensive diagnostic for Strategy Lab subtabs.
Captures before/after screenshots and identifies what's working.
"""
from playwright.sync_api import sync_playwright
import time
import os
from pathlib import Path

SCREENSHOT_DIR = Path("/home/aarav/unified-dashboard/reports/strategy_lab/subtab_diagnosis")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def diagnose_subtabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Capture console messages
        console_errors = []
        def log_console(msg):
            if msg.type == 'error':
                console_errors.append(f"[{msg.type}] {msg.text[:200]}")
        page.on('console', log_console)
        
        print("=" * 70)
        print("STRATEGY LAB SUBTAB DIAGNOSTIC")
        print("=" * 70)
        
        # Navigate to dashboard
        print("\n🔗 Navigating to dashboard...")
        page.goto("http://127.0.0.1:8051/", wait_until="load", timeout=30000)
        page.wait_for_selector('.nav-link', timeout=15000)
        page.wait_for_timeout(3000)
        
        # Navigate to Strategy Lab
        print("📍 Clicking Strategy Lab tab...")
        for selector in ['text=Strategy Lab', '.nav-link:has-text("Strategy")']:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=3000):
                    el.click()
                    break
            except:
                pass
        page.wait_for_timeout(3000)
        
        # Define the 4 subtabs to test
        subtabs = [
            {"name": "Setup", "key": "setup"},
            {"name": "Execute", "key": "execute"},
            {"name": "Results", "key": "results"},
            {"name": "Benchmark", "key": "benchmark"},
        ]
        
        results = {}
        
        # ============================================================
        # STEP 1: BEFORE STATE - Capture all subtabs BEFORE backtest
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 1: BEFORE BACKTEST STATE")
        print("=" * 70)
        
        for tab in subtabs:
            print(f"\n📸 Capturing BEFORE: {tab['name']} subtab...")
            
            # Click subtab
            link = page.locator(f".nav-link:has-text(\"{tab['name']}\")").first
            if link.is_visible(timeout=5000):
                link.click()
                page.wait_for_timeout(2000)
            
            # Take screenshot
            screenshot_path = SCREENSHOT_DIR / f"{tab['key']}_BEFORE.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"   📸 Saved: {screenshot_path}")
            
            # Analyze content
            content = page.content()
            results[tab['key']] = {
                'before': {
                    'has_charts': 'plotly' in content.lower() or 'js-plotly-plot' in content,
                    'has_metrics': 'metric' in content.lower(),
                    'has_data': False,  # Will check specific elements
                }
            }
            
            # Check for specific data elements
            if tab['key'] == 'setup':
                results[tab['key']]['before']['has_data'] = page.locator('#sl-tickers-input').count() > 0
            elif tab['key'] == 'execute':
                results[tab['key']]['before']['has_data'] = page.locator('#sl-run-backtest-btn').count() > 0
            elif tab['key'] == 'results':
                results[tab['key']]['before']['has_data'] = 'sl-equity-curve' in content or 'sl-metric' in content
            elif tab['key'] == 'benchmark':
                results[tab['key']]['before']['has_data'] = 'sl-benchmark' in content or 'benchmark' in content.lower()
        
        # ============================================================
        # STEP 2: RUN BACKTEST
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 2: RUNNING BACKTEST")
        print("=" * 70)
        
        # Go to Setup
        print("\n📝 Step 1: Setup...")
        setup_link = page.locator('.nav-link:has-text("Setup")').first
        if setup_link.is_visible(timeout=5000):
            setup_link.click()
            page.wait_for_timeout(2000)
        
        # Fill tickers
        tickers = page.locator('input#sl-tickers-input').first
        if tickers.is_visible(timeout=3000):
            tickers.fill("AAPL")
            print("   ✅ Filled ticker: AAPL")
        else:
            print("   ❌ Ticker input not found!")
        
        # Click Validate
        validate_btn = page.locator('#sl-validate-btn').first
        if validate_btn.is_visible(timeout=3000):
            validate_btn.click()
            page.wait_for_timeout(3000)
            print("   ✅ Clicked Validate")
        else:
            print("   ❌ Validate button not found!")
        
        # Check validation status
        status = page.locator('#sl-validation-status').first
        if status.is_visible(timeout=3000):
            status_text = status.inner_text()
            print(f"   📋 Validation status: {status_text[:100]}")
        
        # Go to Execute
        print("\n🚀 Step 2: Execute...")
        exec_link = page.locator('.nav-link:has-text("Execute")').first
        if exec_link.is_visible(timeout=5000):
            exec_link.click()
            page.wait_for_timeout(2000)
        
        # Click Run Backtest
        run_btn = page.locator('#sl-run-backtest-btn').first
        if run_btn.is_visible(timeout=5000):
            if run_btn.is_enabled():
                print("   🔘 Run Backtest button is ENABLED")
                run_btn.click()
                print("   ⏳ Waiting for backtest to complete...")
                page.wait_for_timeout(10000)  # Wait for backtest
                print("   ✅ Backtest triggered")
            else:
                print("   ❌ Run Backtest button is DISABLED!")
        else:
            print("   ❌ Run Backtest button not found!")
        
        # Screenshot after clicking Run
        page.screenshot(path=str(SCREENSHOT_DIR / "execute_AFTER_RUN.png"))
        
        # Check progress indicator
        progress = page.locator('#sl-backtest-progress, .sl-backtest-progress, [id*="progress"]')
        if progress.count() > 0:
            print(f"   📊 Found {progress.count()} progress elements")
        
        # ============================================================
        # STEP 3: AFTER STATE - Capture all subtabs AFTER backtest
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 3: AFTER BACKTEST STATE")
        print("=" * 70)
        
        for tab in subtabs:
            print(f"\n📸 Capturing AFTER: {tab['name']} subtab...")
            
            # Click subtab
            link = page.locator(f".nav-link:has-text(\"{tab['name']}\")").first
            if link.is_visible(timeout=5000):
                link.click()
                page.wait_for_timeout(3000)
            
            # Take screenshot
            screenshot_path = SCREENSHOT_DIR / f"{tab['key']}_AFTER.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"   📸 Saved: {screenshot_path}")
            
            # Analyze content
            content = page.content()
            
            results[tab['key']]['after'] = {
                'has_charts': 'plotly' in content.lower() or 'js-plotly-plot' in content,
                'has_metrics': 'metric' in content.lower(),
                'has_data': False,
            }
            
            # Check for specific data elements - more detailed
            if tab['key'] == 'setup':
                results[tab['key']]['after']['has_data'] = 'AAPL' in content
                
            elif tab['key'] == 'execute':
                # Check if any results appeared
                has_results_indicator = any([
                    'backtest' in content.lower() and ('complete' in content.lower() or 'success' in content.lower()),
                    'sl-backtest-results' in content,
                ])
                results[tab['key']]['after']['has_data'] = has_results_indicator
                
            elif tab['key'] == 'results':
                # Check for actual result data
                has_equity = 'sl-equity-curve' in content
                has_metrics = 'sl-metric-cagr' in content or 'sl-metric-sharpe' in content
                has_chart_data = 'trace' in content.lower() or '"y":' in content
                results[tab['key']]['after']['has_data'] = has_equity or has_metrics
                results[tab['key']]['after']['has_chart_data'] = has_chart_data
                
                # Count specific metric elements
                metric_elements = page.locator('[id^="sl-metric-"]').count()
                results[tab['key']]['after']['metric_count'] = metric_elements
                print(f"   📊 Found {metric_elements} metric elements")
                
                # Check equity curve
                equity_curve = page.locator('#sl-equity-curve')
                if equity_curve.count() > 0:
                    # Check if chart has data
                    chart_content = equity_curve.inner_html()
                    has_real_data = '"y":' in chart_content and 'trace' in chart_content.lower()
                    print(f"   📈 Equity curve has data: {has_real_data}")
                    results[tab['key']]['after']['equity_has_data'] = has_real_data
                
            elif tab['key'] == 'benchmark':
                has_benchmark = 'sl-benchmark' in content or 'benchmark-chart' in content.lower()
                has_alpha = 'alpha' in content.lower()
                results[tab['key']]['after']['has_data'] = has_benchmark or has_alpha
                
                # Check benchmark elements
                bench_chart = page.locator('#sl-benchmark-chart, [id*="benchmark-chart"]')
                if bench_chart.count() > 0:
                    chart_content = bench_chart.first.inner_html()
                    has_real_data = '"y":' in chart_content
                    print(f"   📊 Benchmark chart has data: {has_real_data}")
                    results[tab['key']]['after']['chart_has_data'] = has_real_data
        
        # ============================================================
        # STEP 4: SUMMARY REPORT
        # ============================================================
        print("\n" + "=" * 70)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 70)
        
        for tab_key, data in results.items():
            print(f"\n📋 {tab_key.upper()}:")
            before = data.get('before', {})
            after = data.get('after', {})
            
            # Check for changes
            data_before = before.get('has_data', False)
            data_after = after.get('has_data', False)
            
            if data_after and not data_before:
                status = "✅ WORKING - Data appeared after backtest"
            elif data_after and data_before:
                status = "✅ WORKING - Data present"
            elif not data_after and tab_key in ['results', 'benchmark']:
                status = "❌ NOT WORKING - No data after backtest"
            else:
                status = "⚠️ NEEDS INVESTIGATION"
            
            print(f"   Status: {status}")
            print(f"   Before: has_data={data_before}")
            print(f"   After:  has_data={data_after}")
            
            if 'metric_count' in after:
                print(f"   Metrics found: {after['metric_count']}")
            if 'equity_has_data' in after:
                print(f"   Equity chart has data: {after['equity_has_data']}")
            if 'chart_has_data' in after:
                print(f"   Chart has data: {after['chart_has_data']}")
        
        # Console errors
        if console_errors:
            print("\n⚠️ Console Errors:")
            for err in console_errors[:10]:
                print(f"   {err}")
        else:
            print("\n✅ No console errors")
        
        print("\n" + "=" * 70)
        print(f"Screenshots saved to: {SCREENSHOT_DIR}")
        print("=" * 70)
        
        browser.close()
        
        return results

if __name__ == "__main__":
    diagnose_subtabs()
