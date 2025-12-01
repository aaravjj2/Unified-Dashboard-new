#!/usr/bin/env python3
"""Test backtest callback flow with detailed logging."""
from playwright.sync_api import sync_playwright
import time
import json

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        requests_log = []
        responses_log = []
        
        def log_request(request):
            if "_dash" in request.url:
                data = {
                    "url": request.url,
                    "method": request.method,
                    "post_data": request.post_data[:500] if request.post_data else None
                }
                requests_log.append(data)
                print(f"📡 REQ: {request.method} {request.url.split('?')[0]}")
                if request.post_data:
                    print(f"   POST: {request.post_data[:200]}")
        
        def log_response(response):
            if "_dash" in response.url:
                try:
                    body = response.body().decode('utf-8', errors='ignore')[:1000]
                except:
                    body = "[binary]"
                data = {
                    "url": response.url,
                    "status": response.status,
                    "body_preview": body[:300]
                }
                responses_log.append(data)
                status_icon = "✅" if response.status == 200 else "❌"
                print(f"{status_icon} RESP {response.status}: {response.url.split('?')[0]}")
                if response.status == 200 and "update-component" in response.url:
                    print(f"   BODY: {body[:300]}")
        
        page.on("request", log_request)
        page.on("response", log_response)
        
        print("="*60)
        print("🔗 Step 1: Navigate to dashboard")
        print("="*60)
        page.goto("http://127.0.0.1:8051/", wait_until="load", timeout=30000)
        page.wait_for_timeout(3000)
        
        print("\n" + "="*60)
        print("📍 Step 2: Click Strategy Lab tab")
        print("="*60)
        page.click('a[href="/strategy-lab"]')
        page.wait_for_url("**/strategy-lab**", timeout=10000)
        page.wait_for_timeout(2000)
        
        print("\n" + "="*60)
        print("📍 Step 3: Click Execute & Configure subtab")
        print("="*60)
        page.click('text=Execute & Configure')
        page.wait_for_timeout(2000)
        
        # Get button state
        print("\n" + "="*60)
        print("🔘 Step 4: Check button state")
        print("="*60)
        btn = page.locator("#sl-run-backtest-btn")
        print(f"   Button visible: {btn.is_visible()}")
        print(f"   Button enabled: {btn.is_enabled()}")
        print(f"   Button text: {btn.text_content()}")
        
        # Check initial store
        print("\n" + "="*60)
        print("📦 Step 5: Check initial store state")
        print("="*60)
        store_script = """
        () => {
            const store = document.getElementById('sl-backtest-results');
            return store ? store.getAttribute('data-dash-is-loading') : 'not found';
        }
        """
        store_state = page.evaluate(store_script)
        print(f"   Store loading state: {store_state}")
        
        # Clear request logs before click
        requests_log.clear()
        responses_log.clear()
        
        print("\n" + "="*60)
        print("🚀 Step 6: CLICK RUN BACKTEST")
        print("="*60)
        btn.click()
        
        # Wait for callback
        print("⏳ Waiting for callback response (15 seconds)...")
        page.wait_for_timeout(15000)
        
        print("\n" + "="*60)
        print("📊 Step 7: Check execution status")
        print("="*60)
        status_div = page.locator("#sl-execution-status")
        if status_div.count() > 0:
            status_text = status_div.inner_text()
            print(f"   Execution Status: {status_text[:500]}")
        else:
            print("   ❌ sl-execution-status not found")
        
        # Check store after click
        print("\n" + "="*60)
        print("📦 Step 8: Check store after backtest")
        print("="*60)
        store_value_script = """
        () => {
            const stores = document.querySelectorAll('[id*="backtest-results"]');
            const results = [];
            stores.forEach(s => {
                results.push({
                    id: s.id,
                    hasData: s.textContent && s.textContent.length > 10
                });
            });
            return JSON.stringify(results);
        }
        """
        store_info = page.evaluate(store_value_script)
        print(f"   Store info: {store_info}")
        
        print("\n" + "="*60)
        print("🔍 Step 9: Check Results subtab")
        print("="*60)
        page.click('text=Results')
        page.wait_for_timeout(3000)
        
        # Look for results content
        results_content = page.locator('#strategy-lab-results-content, [id*="sl-results"], [id*="equity-curve"]')
        if results_content.count() > 0:
            print(f"   Results elements found: {results_content.count()}")
            for i in range(min(3, results_content.count())):
                el = results_content.nth(i)
                print(f"   Element {i}: visible={el.is_visible()}, text={el.inner_text()[:100] if el.inner_text() else 'empty'}")
        else:
            print("   ❌ No results content elements found")
        
        # Dump all requests/responses
        print("\n" + "="*60)
        print("📝 Summary: Callback Requests/Responses")
        print("="*60)
        print(f"   Total requests after click: {len(requests_log)}")
        print(f"   Total responses after click: {len(responses_log)}")
        
        for resp in responses_log:
            if "update-component" in resp["url"]:
                print(f"\n   📥 Callback Response:")
                print(f"      Status: {resp['status']}")
                print(f"      Body: {resp['body_preview']}")
        
        browser.close()
        
        print("\n✅ Test complete")

if __name__ == "__main__":
    test()
