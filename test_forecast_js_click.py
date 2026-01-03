#!/usr/bin/env python3
"""Test Market Forecast using JavaScript dispatch click"""
from playwright.sync_api import sync_playwright
import time

def main():
    print("=" * 60)
    print("MARKET FORECAST - JS DISPATCH CLICK TEST")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("http://localhost:8050", timeout=30000)
        page.wait_for_load_state("networkidle")
        print("✅ Page loaded")
        
        # Click Market Forecast tab
        page.click("text=Market Forecast")
        time.sleep(3)
        print("✅ On Market Forecast tab")
        
        # Get initial trace count
        traces_before = page.evaluate("""
            () => {
                const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                return el && el.data ? el.data.length : 0;
            }
        """)
        print(f"📊 Traces BEFORE: {traces_before}")
        
        # Use JS to properly click the button AND trigger React event
        print("🖱️ Dispatching click via JavaScript...")
        page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                if (btn) {
                    // Create and dispatch a proper click event
                    const event = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    btn.dispatchEvent(event);
                }
            }
        """)
        
        # Wait for callback to complete
        print("⏳ Waiting up to 60s for forecast...")
        for i in range(60):
            traces_now = page.evaluate("""
                () => {
                    const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                    return el && el.data ? el.data.length : 0;
                }
            """)
            
            if traces_now > traces_before:
                print(f"✅ NEW TRACES! {traces_before} -> {traces_now} at {i}s")
                break
            
            if i % 10 == 0:
                print(f"  ...waiting ({i}s, traces={traces_now})")
            
            time.sleep(1)
        
        # Final check
        traces_final = page.evaluate("""
            () => {
                const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                return el && el.data ? el.data.length : 0;
            }
        """)
        
        metrics = page.inner_text("#mf-model-metrics") if page.locator("#mf-model-metrics").count() > 0 else "N/A"
        
        print(f"\n📊 FINAL TRACES: {traces_final}")
        print(f"📊 METRICS: {metrics[:100]}...")
        
        if traces_final > 0 and "RUN FORECAST" not in metrics:
            print("\n✅ SUCCESS - Forecast generated!")
        else:
            print("\n❌ FAIL - No forecast generated")
        
        page.screenshot(path="/tmp/forecast_js_click.png", full_page=True)
        print("📸 Screenshot: /tmp/forecast_js_click.png")
        
        browser.close()
    
    print("=" * 60)

if __name__ == "__main__":
    main()
