#!/usr/bin/env python3
"""Test Market Forecast - writes results to file"""
from playwright.sync_api import sync_playwright
import time

def main():
    results = []
    results.append("=" * 60)
    results.append("MARKET FORECAST - GENERATE FORECAST TEST")
    results.append("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate
        page.goto("http://localhost:8051", timeout=30000)
        page.wait_for_load_state("networkidle")
        results.append("✅ Page loaded")
        
        # Click Market Forecast tab
        mf_tab = page.locator("text=Market Forecast").first
        if mf_tab.is_visible():
            mf_tab.click()
            time.sleep(2)
            results.append("✅ Clicked Market Forecast tab")
        else:
            results.append("❌ Market Forecast tab NOT found")
            browser.close()
            with open("/tmp/forecast_test_results.txt", "w") as f:
                f.write("\n".join(results))
            return
        
        # Check for Generate Forecast button
        run_btn = page.locator("#mf-run-btn")
        if run_btn.is_visible():
            results.append("✅ Generate Forecast button found")
        else:
            results.append("❌ Generate Forecast button NOT found")
        
        # Check chart BEFORE clicking
        chart_before = page.locator("#mf-forecast-chart .js-plotly-plot")
        has_chart_before = chart_before.count() > 0
        results.append(f"📊 Chart exists BEFORE click: {has_chart_before}")
        
        # Click Generate Forecast
        run_btn.click()
        results.append("🖱️ Clicked Generate Forecast button")
        
        # Wait for loading to appear then disappear
        try:
            page.wait_for_selector("#mf-forecast-chart .dash-spinner, #mf-forecast-chart .loading", timeout=3000)
            results.append("⏳ Loading indicator appeared")
        except:
            results.append("⚠️ No loading indicator detected")
        
        # Wait for forecast to complete (up to 60 seconds)
        results.append("⏳ Waiting up to 60s for forecast...")
        start = time.time()
        chart_found = False
        
        for i in range(60):
            # Check for plotly chart with data
            chart = page.locator("#mf-forecast-chart .js-plotly-plot")
            if chart.count() > 0:
                # Check if chart has actual traces
                traces = page.evaluate("""
                    () => {
                        const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                        if (el && el.data) {
                            return el.data.length;
                        }
                        return 0;
                    }
                """)
                if traces > 0:
                    elapsed = time.time() - start
                    results.append(f"✅ CHART RENDERED with {traces} traces in {elapsed:.1f}s")
                    chart_found = True
                    break
            time.sleep(1)
        
        if not chart_found:
            results.append("❌ NO CHART rendered after 60s")
        
        # Check comparison chart
        comp_chart = page.locator("#mf-model-comparison-chart .js-plotly-plot")
        if comp_chart.count() > 0:
            results.append("✅ Model comparison chart found")
        else:
            results.append("❌ Model comparison chart NOT found")
        
        # Check metrics
        metrics = page.locator("#mf-model-metrics")
        if metrics.count() > 0:
            metrics_text = metrics.inner_text()
            if len(metrics_text) > 10:
                results.append(f"✅ Metrics displayed ({len(metrics_text)} chars)")
            else:
                results.append("❌ Metrics empty")
        else:
            results.append("❌ Metrics element not found")
        
        # Screenshot
        page.screenshot(path="/tmp/forecast_final.png", full_page=True)
        results.append("📸 Screenshot saved: /tmp/forecast_final.png")
        
        browser.close()
    
    results.append("=" * 60)
    results.append("TEST COMPLETE")
    results.append("=" * 60)
    
    # Write results
    with open("/tmp/forecast_test_results.txt", "w") as f:
        f.write("\n".join(results))
    
    # Also print
    for r in results:
        print(r)

if __name__ == "__main__":
    main()
