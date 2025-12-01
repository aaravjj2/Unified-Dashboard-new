#!/usr/bin/env python3
"""
Debug test: Check if n_clicks updates and if callback executes
"""

import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("=" * 80)
    print("CALLBACK DEBUG TEST")
    print("=" * 80)
    
    # Start dashboard
    print("🚀 Starting dashboard...")
    proc = subprocess.Popen([
        sys.executable, '-m', 'financial_dashboard.index'
    ], env={'AZURE_ENABLED': 'false', 'OPTIONS_DETERMINISTIC': '1'})
    
    time.sleep(2)
    print("   ✅ Dashboard started")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=500)
            page = browser.new_page()
            
            # Track requests to see if callback fires
            requests = []
            def track_request(request):
                if '/_dash-update-component' in request.url:
                    requests.append({
                        'url': request.url,
                        'post_data': request.post_data
                    })
            page.on('request', track_request)
            
            # Navigate and activate tab
            print("\n📍 Loading dashboard...")
            page.goto('http://localhost:8050')
            page.wait_for_load_state('networkidle')
            
            print("📍 Activating Market Trends tab...")
            page.click('text=Market Trends')
            time.sleep(2)
            
            # Check initial n_clicks
            print("\n📍 Checking button state BEFORE click...")
            initial_clicks = page.evaluate("""
                () => {
                    const btn = document.getElementById('mt-run-analysis-btn');
                    if (!btn) return 'BUTTON NOT FOUND';
                    return btn.getAttribute('n_clicks') || '0';
                }
            """)
            print(f"   Initial n_clicks: {initial_clicks}")
            
            # Clear request tracking
            requests.clear()
            
            # Click button
            print("\n📍 Clicking Run Analysis button...")
            page.click('#mt-run-analysis-btn')
            time.sleep(2)
            
            # Check n_clicks after
            final_clicks = page.evaluate("""
                () => {
                    const btn = document.getElementById('mt-run-analysis-btn');
                    if (!btn) return 'BUTTON NOT FOUND';
                    return btn.getAttribute('n_clicks') || '0';
                }
            """)
            print(f"   Final n_clicks: {final_clicks}")
            
            # Check if callback request was sent
            print(f"\n📍 Dash update requests sent: {len(requests)}")
            if requests:
                for i, req in enumerate(requests[:3]):
                    print(f"\n   Request {i+1}:")
                    print(f"   URL: {req['url']}")
                    if req['post_data']:
                        # Parse post data
                        try:
                            import json
                            data = json.loads(req['post_data'])
                            print(f"   Inputs: {data.get('inputs', [])}")
                            print(f"   Outputs: {list(data.get('output', '').split('.'))[:2]}")
                        except:
                            print(f"   Data: {req['post_data'][:200]}")
            else:
                print("   ❌ NO CALLBACK REQUESTS SENT!")
            
            # Check status div
            print("\n📍 Checking status div...")
            status_info = page.evaluate("""
                () => {
                    const status = document.getElementById('status');
                    if (!status) return {exists: false};
                    return {
                        exists: true,
                        display: status.style.display,
                        text: status.textContent,
                        html: status.innerHTML
                    };
                }
            """)
            print(f"   Status exists: {status_info.get('exists')}")
            if status_info.get('exists'):
                print(f"   Display: {status_info.get('display')}")
                print(f"   Text: {status_info.get('text')}")
            
            print("\n⏳ Waiting 5s for observation...")
            time.sleep(5)
            
            browser.close()
            
    finally:
        print("\n🛑 Stopping dashboard...")
        proc.terminate()
        proc.wait(timeout=5)
        print("   ✅ Stopped")

if __name__ == '__main__':
    main()
