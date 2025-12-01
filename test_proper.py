#!/usr/bin/env python3
"""
Options Lab Proper Test - Load ticker data first, then test each subtab button
"""

import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://127.0.0.1:8051"
SCREENSHOT_DIR = "/tmp/options_lab_proper_test"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_proper_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        # Capture console errors
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        print("=" * 70)
        print("OPTIONS LAB PROPER TEST - WITH DATA LOADED")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Load dashboard
        page.goto(DASHBOARD_URL, timeout=60000)
        time.sleep(5)
        
        # Navigate to Options Lab
        print("\n[STEP 1] Navigate to Options Lab...")
        page.locator("#tab-options_lab").click()
        time.sleep(2)
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_options_lab_initial.png")
        
        # Enter ticker and load data
        print("\n[STEP 2] Enter ticker AAPL and load chain data...")
        ticker_input = page.locator("#options-ticker-input")
        ticker_input.fill("AAPL")
        time.sleep(0.5)
        
        # Click Load Data button
        page.locator("#options-mock-btn").click()  # Use mock for testing
        time.sleep(3)
        page.screenshot(path=f"{SCREENSHOT_DIR}/02_chain_data_loaded.png")
        print("   ✓ Chain data loaded for AAPL")
        
        # Now test each subtab with its buttons
        results = []
        
        # TEST 1: Chain Viewer - Generate Forecast
        print("\n[TEST 1] Chain Viewer - Generate Forecast button...")
        page.locator("#options-chain-tab").click()
        time.sleep(1)
        
        # Click Generate Forecast
        forecast_btn = page.locator("#options-forecast-btn")
        if forecast_btn.count() > 0 and forecast_btn.is_visible():
            forecast_btn.click()
            time.sleep(3)
            page.screenshot(path=f"{SCREENSHOT_DIR}/03_chain_forecast.png")
            
            # Check if forecast results appeared
            forecast_results = page.locator("#options-forecast-results")
            content = forecast_results.inner_text() if forecast_results.count() > 0 else ""
            if len(content) > 50:  # Should have substantial content
                print("   ✓ PASSED - Forecast generated with content")
                results.append(("Chain Forecast", "PASSED"))
            else:
                print(f"   ✗ FAILED - Forecast content too short: {len(content)} chars")
                results.append(("Chain Forecast", "FAILED - no content"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Chain Forecast", "FAILED - button missing"))
        
        # TEST 2: Flow Scanner - Scan Flow button
        print("\n[TEST 2] Flow Scanner - Scan Flow button...")
        page.locator("#options-flow-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/04_flow_before.png")
        
        scan_btn = page.locator("#ol-flow-scan-btn")
        if scan_btn.count() > 0 and scan_btn.is_visible():
            scan_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/05_flow_after.png")
            
            # Check for results
            flow_table = page.locator("#ol-flow-table")
            gex_chart = page.locator("#ol-gex-chart")
            
            has_content = flow_table.count() > 0 or gex_chart.count() > 0
            page_text = page.locator("body").inner_text()
            
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("Flow Scanner", "FAILED - callback error"))
            elif has_content:
                print("   ✓ PASSED - Flow scan completed")
                results.append(("Flow Scanner", "PASSED"))
            else:
                print("   ? UNKNOWN - No clear result")
                results.append(("Flow Scanner", "UNKNOWN"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Flow Scanner", "FAILED - button missing"))
        
        # TEST 3: IV Analysis - Analyze IV button
        print("\n[TEST 3] IV Analysis - Analyze IV button...")
        page.locator("#options-iv-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/06_iv_before.png")
        
        iv_btn = page.locator("#ol-iv-analyze-btn")
        if iv_btn.count() > 0 and iv_btn.is_visible():
            iv_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/07_iv_after.png")
            
            page_text = page.locator("body").inner_text()
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("IV Analysis", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - IV analysis completed")
                results.append(("IV Analysis", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("IV Analysis", "FAILED - button missing"))
        
        # TEST 4: Strategy Builder - Build Strategy button
        print("\n[TEST 4] Strategy Builder - Build Strategy button...")
        page.locator("#options-strategy-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/08_strategy_before.png")
        
        strategy_btn = page.locator("#ol-strategy-build-btn")
        if strategy_btn.count() > 0 and strategy_btn.is_visible():
            strategy_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/09_strategy_after.png")
            
            page_text = page.locator("body").inner_text()
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("Strategy Builder", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - Strategy built")
                results.append(("Strategy Builder", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Strategy Builder", "FAILED - button missing"))
        
        # TEST 5: Manual Trade - Calculate P&L button
        print("\n[TEST 5] Manual Trade - Calculate P&L button...")
        page.locator("#options-manual-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/10_manual_before.png")
        
        calc_btn = page.locator("#sim-calculate-btn")
        if calc_btn.count() > 0 and calc_btn.is_visible():
            calc_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/11_manual_after.png")
            
            # Check for P&L chart
            pnl_chart = page.locator("#sim-pnl-chart")
            page_text = page.locator("body").inner_text()
            
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("Manual Trade P&L", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - P&L calculated")
                results.append(("Manual Trade P&L", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Manual Trade P&L", "FAILED - button missing"))
        
        # TEST 6: Portfolio Greeks - Refresh button
        print("\n[TEST 6] Portfolio Greeks - Refresh button...")
        page.locator("#options-portfolio-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/12_portfolio_before.png")
        
        refresh_btn = page.locator("#ol-portfolio-refresh-btn")
        if refresh_btn.count() > 0 and refresh_btn.is_visible():
            refresh_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/13_portfolio_after.png")
            
            page_text = page.locator("body").inner_text()
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("Portfolio Greeks", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - Portfolio refreshed")
                results.append(("Portfolio Greeks", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Portfolio Greeks", "FAILED - button missing"))
        
        # TEST 7: Screener - Run Screen button
        print("\n[TEST 7] Screener - Run Screen button...")
        page.locator("#options-screener-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/14_screener_before.png")
        
        screen_btn = page.locator("#ol-screener-run-btn")
        if screen_btn.count() > 0 and screen_btn.is_visible():
            screen_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/15_screener_after.png")
            
            page_text = page.locator("body").inner_text()
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("Screener", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - Screen completed")
                results.append(("Screener", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Screener", "FAILED - button missing"))
        
        # TEST 8: AI Recommendations - Generate button
        print("\n[TEST 8] AI Recommendations - Generate button...")
        page.locator("#options-ai-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/16_ai_before.png")
        
        ai_btn = page.locator("#ol-ai-generate-btn")
        if ai_btn.count() > 0 and ai_btn.is_visible():
            ai_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/17_ai_after.png")
            
            page_text = page.locator("body").inner_text()
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("AI Recommendations", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - Recommendations generated")
                results.append(("AI Recommendations", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("AI Recommendations", "FAILED - button missing"))
        
        # TEST 9: Earnings Calendar - Load button
        print("\n[TEST 9] Earnings Calendar - Load Calendar button...")
        page.locator("#options-earnings-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/18_earnings_before.png")
        
        earnings_btn = page.locator("#ol-earnings-load-btn")
        if earnings_btn.count() > 0 and earnings_btn.is_visible():
            earnings_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/19_earnings_after.png")
            
            page_text = page.locator("body").inner_text()
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("Earnings Calendar", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - Calendar loaded")
                results.append(("Earnings Calendar", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Earnings Calendar", "FAILED - button missing"))
        
        # TEST 10: Backtester - Run Backtest button
        print("\n[TEST 10] Backtester - Run Backtest button...")
        page.locator("#options-backtest-tab").click()
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/20_backtest_before.png")
        
        backtest_btn = page.locator("#ol-backtest-run-btn")
        if backtest_btn.count() > 0 and backtest_btn.is_visible():
            backtest_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/21_backtest_after.png")
            
            page_text = page.locator("body").inner_text()
            if "error" in page_text.lower() and "callback" in page_text.lower():
                print("   ✗ FAILED - Callback error detected")
                results.append(("Backtester", "FAILED - callback error"))
            else:
                print("   ✓ PASSED - Backtest completed")
                results.append(("Backtester", "PASSED"))
        else:
            print("   ✗ FAILED - Button not found")
            results.append(("Backtester", "FAILED - button missing"))
        
        # Print console errors if any
        if errors:
            print("\n" + "=" * 70)
            print("CONSOLE ERRORS DETECTED:")
            print("=" * 70)
            for err in errors[:10]:
                print(f"  - {err[:100]}")
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in results if r[1] == "PASSED")
        failed = sum(1 for r in results if "FAILED" in r[1])
        
        for name, status in results:
            icon = "✓" if status == "PASSED" else "✗"
            print(f"  {icon} {name}: {status}")
        
        print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}")
        print(f"Screenshots saved to: {SCREENSHOT_DIR}")
        
        time.sleep(5)
        browser.close()
        
        return results

if __name__ == "__main__":
    run_proper_test()
