#!/usr/bin/env python3
"""Test Market Forecast - writes results to file - PORT 8050"""
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
        
        # Navigate to PORT 8050
        page.goto("http://localhost:8050", timeout=30000)
        page.wait_for_load_state("networkidle")
        results.append("✅ Page loaded (port 8050)")
        
        # Click Market Forecast tab
        mf_tab = page.locator("text=Market Forecast").first
        if mf_tab.is_visible():
            mf_tab.click()
            time.sleep(2)
            results.append("✅ Clicked Market Forecast tab")
        else:
            results.append("❌ Market Forecast tab NOT found")
            browser.close()
            with open("/tmp/forecast_8050_results.txt", "w") as f:
                f.write("\n".join(results))
            return
        
        # Check for Generate Forecast button
        run_btn = page.locator("#mf-run-btn")
        if run_btn.is_visible():
            results.append("✅ Generate Forecast button found")
        else:
            results.append("❌ Generate Forecast button NOT found")
        
        # Get chart trace count BEFORE clicking
        traces_before = page.evaluate("""
            () => {
                const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                if (el && el.data) {
                    return el.data.length;
                }
                return 0;
            }
        """)
        results.append(f"📊 Chart traces BEFORE click: {traces_before}")
        
        # Click Generate Forecast
        run_btn.click()
        results.append("🖱️ Clicked Generate Forecast button")
        
        # Wait for forecast to complete (up to 45 seconds)
        results.append("⏳ Waiting up to 45s for forecast...")
        start = time.time()
        new_traces = False
        
        for i in range(45):
            # Check for plotly chart with MORE traces than before
            traces_now = page.evaluate("""
                () => {
                    const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                    if (el && el.data) {
                        return el.data.length;
                    }
                    return 0;
                }
            """)
            
            if traces_now > traces_before:
                elapsed = time.time() - start
                results.append(f"✅ NEW TRACES: {traces_before} -> {traces_now} (+{traces_now - traces_before}) in {elapsed:.1f}s")
                new_traces = True
                break
            
            # Also check if the chart HTML changed (different approach)
            if i == 15:  # After 15 seconds, take mid-check
                results.append(f"  ...checking at 15s: {traces_now} traces")
            
            time.sleep(1)
        
        if not new_traces:
            traces_final = page.evaluate("""
                () => {
                    const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                    if (el && el.data) {
                        return el.data.length;
                    }
                    return 0;
                }
            """)
            results.append(f"❌ NO NEW TRACES after 45s (traces: {traces_final})")
        
        # Check comparison chart
        comp_traces = page.evaluate("""
            () => {
                const el = document.querySelector('#mf-model-comparison-chart .js-plotly-plot');
                if (el && el.data) {
                    return el.data.length;
                }
                return 0;
            }
        """)
        results.append(f"📊 Model comparison chart traces: {comp_traces}")
        
        # Check metrics
        metrics = page.locator("#mf-model-metrics")
        if metrics.count() > 0:
            metrics_text = metrics.inner_text()
            if len(metrics_text) > 10:
                results.append(f"✅ Metrics displayed ({len(metrics_text)} chars)")
                results.append(f"   Preview: {metrics_text[:100]}...")
            else:
                results.append(f"❌ Metrics empty or minimal: '{metrics_text}'")
        else:
            results.append("❌ Metrics element not found")
        
        # Screenshot
        page.screenshot(path="/tmp/forecast_8050.png", full_page=True)
        results.append("📸 Screenshot saved: /tmp/forecast_8050.png")
        
        browser.close()
    
    results.append("=" * 60)
    results.append("TEST COMPLETE")
    results.append("=" * 60)
    
    # Write results
    with open("/tmp/forecast_8050_results.txt", "w") as f:
        f.write("\n".join(results))
    
    # Also print
    for r in results:
        print(r)

if __name__ == "__main__":
    main()
