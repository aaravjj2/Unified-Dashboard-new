#!/usr/bin/env python3
"""Browser test for Market Forecast functionality."""

from playwright.sync_api import sync_playwright
import time

def test_market_forecast():
    """Test that Market Forecast generates a forecast when clicking the button."""
    print("=" * 60)
    print("MARKET FORECAST BROWSER TEST")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Load dashboard
        page.goto("http://127.0.0.1:8051", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)
        print("✅ Dashboard loaded")
        
        # 2. Navigate to Market Forecast tab
        page.click("text=Market Forecast", timeout=10000)
        time.sleep(2)
        print("✅ Market Forecast tab opened")
        
        # 3. Verify initial state - chart should have 0 traces
        pre_traces = page.evaluate("""() => {
            const plotly = document.querySelector('#mf-forecast-chart .js-plotly-plot');
            return plotly && plotly.data ? plotly.data.length : 0;
        }""")
        assert pre_traces == 0, f"Expected 0 traces before click, got {pre_traces}"
        print(f"✅ Initial state: {pre_traces} traces (expected 0)")
        
        # 4. Click Generate Forecast button
        page.click("#mf-run-btn", timeout=10000)
        print("✅ Clicked Generate Forecast button")
        
        # 5. Wait for response
        time.sleep(10)  # Give time for the forecast to generate
        
        # 6. Verify chart has data
        post_traces = page.evaluate("""() => {
            const plotly = document.querySelector('#mf-forecast-chart .js-plotly-plot');
            return plotly && plotly.data ? plotly.data.length : 0;
        }""")
        assert post_traces > 0, f"Expected traces after click, got {post_traces}"
        print(f"✅ After forecast: {post_traces} traces (expected > 0)")
        
        # 7. Verify first trace is Historical
        first_trace_name = page.evaluate("""() => {
            const plotly = document.querySelector('#mf-forecast-chart .js-plotly-plot');
            return plotly && plotly.data && plotly.data[0] ? plotly.data[0].name : null;
        }""")
        assert first_trace_name == "Historical", f"Expected first trace 'Historical', got '{first_trace_name}'"
        print(f"✅ First trace name: '{first_trace_name}' (expected 'Historical')")
        
        # 8. Verify status banner or just confirm chart updated
        try:
            status_text = page.locator("#mf-status-banner").inner_text(timeout=2000)
            if status_text:
                print(f"✅ Status: {status_text[:60]}...")
            else:
                print("ℹ️ Status banner is empty (but chart updated successfully)")
        except Exception:
            print("ℹ️ Status banner not readable (but chart updated successfully)")
        
        page.screenshot(path="/tmp/mf_test_final.png")
        print(f"\n📸 Screenshot: /tmp/mf_test_final.png")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return True

if __name__ == "__main__":
    try:
        success = test_market_forecast()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
