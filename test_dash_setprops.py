#!/usr/bin/env python3
"""Test: Use Dash's internal setProps to trigger button click"""
from playwright.sync_api import sync_playwright
import time

def main():
    print("=" * 60)
    print("TEST: DIRECT DASH SETPROPS")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Track requests
        requests_sent = []
        def on_request(req):
            if '_dash-update' in req.url and req.post_data:
                if 'mf-run-btn' in req.post_data:
                    requests_sent.append(True)
        page.on('request', on_request)
        
        page.goto("http://localhost:8050", timeout=30000)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Market Forecast
        page.click("text=Market Forecast")
        time.sleep(2)
        print("✅ On Market Forecast tab")
        
        # Get current n_clicks
        n_clicks_before = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                // Find React fiber
                const key = Object.keys(btn).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
                if (!key) return 'no fiber';
                
                let fiber = btn[key];
                // Walk up to find the component with setProps
                while (fiber) {
                    if (fiber.memoizedProps && fiber.memoizedProps.setProps) {
                        return {
                            n_clicks: fiber.memoizedProps.n_clicks,
                            hasSetProps: true
                        };
                    }
                    if (fiber.stateNode && fiber.stateNode.setProps) {
                        return {
                            n_clicks: fiber.memoizedProps?.n_clicks,
                            hasSetProps: true,
                            via: 'stateNode'
                        };
                    }
                    fiber = fiber.return;
                }
                return {hasSetProps: false};
            }
        """)
        print(f"📊 Before: {n_clicks_before}")
        
        # Try to trigger the button via React's synthetic event
        print("\n🖱️ Triggering via React synthetic event...")
        result = page.evaluate("""
            () => {
                const btn = document.getElementById('mf-run-btn');
                
                // Method 1: Find React's onClick handler
                const key = Object.keys(btn).find(k => k.startsWith('__reactProps'));
                if (key && btn[key] && btn[key].onClick) {
                    // Call React's onClick directly
                    btn[key].onClick({
                        preventDefault: () => {},
                        stopPropagation: () => {},
                        target: btn,
                        currentTarget: btn
                    });
                    return 'Called onClick via __reactProps';
                }
                
                // Method 2: Dispatch a native event that React will capture
                const nativeEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    button: 0,
                    buttons: 1
                });
                btn.dispatchEvent(nativeEvent);
                return 'Dispatched native event';
            }
        """)
        print(f"📊 Method result: {result}")
        
        time.sleep(3)
        
        # Check if request was sent
        print(f"\n📬 Requests with mf-run-btn: {len(requests_sent)}")
        
        # Wait for forecast
        if requests_sent:
            print("⏳ Waiting for forecast...")
            for i in range(30):
                metrics = page.inner_text("#mf-model-metrics")
                if "RUN FORECAST" not in metrics:
                    print(f"✅ Forecast generated at {i}s!")
                    break
                time.sleep(1)
        
        # Check final state
        traces = page.evaluate("""
            () => {
                const el = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                return el && el.data ? el.data.length : 0;
            }
        """)
        metrics = page.inner_text("#mf-model-metrics")
        
        print(f"\n📊 Final traces: {traces}")
        print(f"📊 Metrics: {metrics[:80]}...")
        
        browser.close()
    
    print("\n" + "=" * 60)
    if traces > 0:
        print("✅ SUCCESS")
    else:
        print("❌ FAILED - callback not triggered")
    print("=" * 60)

if __name__ == "__main__":
    main()
