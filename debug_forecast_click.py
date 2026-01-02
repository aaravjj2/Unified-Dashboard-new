#!/usr/bin/env python3
"""Debug: Check what happens when we click the Generate Forecast button"""
from playwright.sync_api import sync_playwright
import time
import json

def main():
    print("=" * 60)
    print("DEBUG: MARKET FORECAST BUTTON CLICK")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Enable request logging
        requests_log = []
        def log_request(request):
            if '_dash-update-component' in request.url:
                try:
                    body = request.post_data
                    if body and 'mf-run-btn' in body:
                        requests_log.append({
                            'url': request.url,
                            'body': body[:500] if body else None
                        })
                except:
                    pass
        
        page.on('request', log_request)
        
        # Navigate
        page.goto("http://localhost:8050", timeout=30000)
        page.wait_for_load_state("networkidle")
        print("✅ Page loaded")
        
        # Click Market Forecast tab
        page.click("text=Market Forecast")
        time.sleep(2)
        print("✅ Clicked Market Forecast tab")
        
        # Get button state before click
        btn_before = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                if (btn) {
                    return {
                        exists: true,
                        disabled: btn.disabled,
                        className: btn.className,
                        innerText: btn.innerText,
                        nClicks: btn.getAttribute('n_clicks')
                    };
                }
                return {exists: false};
            }
        """)
        print(f"📊 Button BEFORE: {json.dumps(btn_before, indent=2)}")
        
        # Check if there's a ticker value
        ticker_value = page.evaluate("""
            () => {
                const ticker = document.getElementById('mf-ticker-input');
                if (ticker) {
                    return ticker.value;
                }
                return null;
            }
        """)
        print(f"📊 Ticker value: {ticker_value}")
        
        # Check if models are selected
        models_selected = page.evaluate("""
            () => {
                const checklist = document.getElementById('mf-model-checklist');
                if (checklist) {
                    const checked = checklist.querySelectorAll('input:checked');
                    return Array.from(checked).map(c => c.value);
                }
                return [];
            }
        """)
        print(f"📊 Models selected: {models_selected}")
        
        # Clear requests log before clicking
        requests_log.clear()
        
        # Click the button
        print("\n🖱️ CLICKING GENERATE FORECAST BUTTON...")
        page.click("#mf-run-btn")
        
        # Wait and collect requests
        time.sleep(5)
        
        print(f"\n📬 Captured {len(requests_log)} callback requests with mf-run-btn:")
        for req in requests_log:
            print(f"   URL: {req['url']}")
            if req['body']:
                # Parse and pretty print
                try:
                    body = json.loads(req['body'])
                    inputs = body.get('inputs', [])
                    for inp in inputs:
                        if inp.get('id') == 'mf-run-btn':
                            print(f"   mf-run-btn value: {inp}")
                except:
                    print(f"   Body: {req['body'][:200]}")
        
        # Get button state after click
        btn_after = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                if (btn) {
                    return {
                        exists: true,
                        disabled: btn.disabled,
                        className: btn.className,
                    };
                }
                return {exists: false};
            }
        """)
        print(f"\n📊 Button AFTER: {json.dumps(btn_after, indent=2)}")
        
        # Wait longer for callback to complete
        print("\n⏳ Waiting 30 more seconds for callback...")
        time.sleep(30)
        
        # Check chart traces
        traces = page.evaluate("""
            () => {
                const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                if (el && el.data) {
                    return el.data.length;
                }
                return 0;
            }
        """)
        print(f"📊 Final chart traces: {traces}")
        
        # Check metrics
        metrics = page.inner_text("#mf-model-metrics") if page.locator("#mf-model-metrics").count() > 0 else "N/A"
        print(f"📊 Metrics: {metrics[:100]}...")
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
