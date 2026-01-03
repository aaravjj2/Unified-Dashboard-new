#!/usr/bin/env python3
"""Test Market Forecast - Use presets and verify callbacks fire"""
from playwright.sync_api import sync_playwright
import time

def main():
    print("=" * 60)
    print("MARKET FORECAST - PRESET & BUTTON TEST")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture network requests
        callback_requests = []
        def on_request(request):
            if '_dash-update-component' in request.url:
                try:
                    body = request.post_data or ''
                    if 'mf-run-btn' in body or 'mf-preset' in body:
                        callback_requests.append({
                            'url': request.url,
                            'has_run_btn': 'mf-run-btn' in body,
                            'has_preset': 'mf-preset' in body
                        })
                except:
                    pass
        
        page.on('request', on_request)
        
        page.goto("http://localhost:8051", timeout=30000)
        page.wait_for_load_state("networkidle")
        print("✅ Page loaded")
        
        # Click Market Forecast tab
        page.click("text=Market Forecast")
        time.sleep(2)
        print("✅ On Market Forecast tab")
        
        # Test 1: Check preset dropdown exists
        preset_select = page.locator("#mf-preset-select")
        if preset_select.count() > 0:
            print("✅ Preset dropdown found")
        else:
            print("❌ Preset dropdown NOT found")
            browser.close()
            return
        
        # Clear request log
        callback_requests.clear()
        
        # Test 2: Select a preset
        print("\n🖱️ Selecting 'Fast & Light' preset...")
        preset_select.select_option("fast")
        time.sleep(2)
        
        # Check if preset callback fired
        preset_fired = any(r['has_preset'] for r in callback_requests)
        print(f"📬 Preset callback request sent: {preset_fired}")
        
        # Check model selection changed
        models_selected = page.evaluate("""
            () => {
                const checklist = document.getElementById('mf-model-checklist');
                if (!checklist) return [];
                const inputs = checklist.querySelectorAll('input[type="checkbox"]:checked');
                // Get the label text for each checked input
                return Array.from(inputs).map(inp => {
                    const label = inp.closest('label');
                    return label ? label.textContent.trim().substring(0, 30) : 'unknown';
                });
            }
        """)
        print(f"📊 Models after preset: {models_selected}")
        
        # Clear request log
        callback_requests.clear()
        
        # Test 3: Click Generate Forecast button
        print("\n🖱️ Clicking Generate Forecast button...")
        run_btn = page.locator("#mf-run-btn")
        
        # Try multiple click methods
        run_btn.click()
        time.sleep(1)
        
        # Check if callback request was sent
        run_btn_fired = any(r['has_run_btn'] for r in callback_requests)
        print(f"📬 Run button callback request sent: {run_btn_fired}")
        
        if not run_btn_fired:
            print("⚠️ Button click didn't trigger callback request!")
            print("   Trying alternative click methods...")
            
            # Try JavaScript click
            page.evaluate("document.getElementById('mf-run-btn').click()")
            time.sleep(1)
            run_btn_fired = any(r['has_run_btn'] for r in callback_requests)
            print(f"📬 After JS click: {run_btn_fired}")
            
            if not run_btn_fired:
                # Try force click
                run_btn.click(force=True)
                time.sleep(1)
                run_btn_fired = any(r['has_run_btn'] for r in callback_requests)
                print(f"📬 After force click: {run_btn_fired}")
        
        # Wait for forecast to complete
        if run_btn_fired:
            print("\n⏳ Waiting for forecast to complete...")
            for i in range(30):
                metrics = page.inner_text("#mf-model-metrics")
                if "RUN FORECAST" not in metrics and len(metrics) > 50:
                    print(f"✅ Forecast completed at {i}s!")
                    print(f"📊 Metrics preview: {metrics[:100]}...")
                    break
                time.sleep(1)
            else:
                print("❌ Forecast did not complete in 30s")
        
        # Final chart check
        traces = page.evaluate("""
            () => {
                const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                return el && el.data ? el.data.length : 0;
            }
        """)
        print(f"\n📊 Final chart traces: {traces}")
        
        # Screenshot
        page.screenshot(path="/tmp/preset_test.png", full_page=True)
        print("📸 Screenshot: /tmp/preset_test.png")
        
        browser.close()
    
    print("\n" + "=" * 60)
    if run_btn_fired and traces > 0:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED - Button click not triggering callback")
    print("=" * 60)

if __name__ == "__main__":
    main()
