"""
Deep diagnostic: Capture callback request/response cycle
"""
from playwright.sync_api import sync_playwright
import time
import json

print("=" * 80)
print("CALLBACK DIAGNOSTIC - Network Traffic Analysis")
print("=" * 80)

callback_requests = []
callback_responses = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # Capture ALL network requests
    def log_request(request):
        if '_dash-update-component' in request.url or 'POST' in request.method:
            callback_requests.append({
                'url': request.url,
                'method': request.method,
                'time': time.time()
            })
            print(f"📤 REQUEST: {request.method} {request.url[:100]}")
    
    def log_response(response):
        if '_dash-update-component' in response.url:
            callback_responses.append({
                'url': response.url,
                'status': response.status,
                'time': time.time()
            })
            print(f"📥 RESPONSE: {response.status} {response.url[:100]}")
    
    page.on('request', log_request)
    page.on('response', log_response)
    
    # Capture console
    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))
    
    print("\n1️⃣  Loading dashboard...")
    page.goto('http://localhost:8050', wait_until='domcontentloaded')
    time.sleep(3)
    
    print("\n2️⃣  Clicking Market Trends tab...")
    page.click('#tab-market_trends')
    time.sleep(2)
    
    print("\n3️⃣  Clicking 'Run Full Analysis' button...")
    print(f"   ⏰ Current time: {time.time()}")
    page.click('#run-btn')
    
    print("\n⏳ Waiting 10 seconds for callback traffic...")
    time.sleep(10)
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"📤 Callback REQUESTS sent: {len(callback_requests)}")
    for req in callback_requests:
        print(f"   - {req['method']} at {req['time']:.2f}")
    
    print(f"\n📥 Callback RESPONSES received: {len(callback_responses)}")
    for resp in callback_responses:
        print(f"   - Status {resp['status']} at {resp['time']:.2f}")
    
    print(f"\n💬 Console messages ({len(console_msgs)} total):")
    for msg in console_msgs[-20:]:
        print(f"   {msg}")
    
    if len(callback_requests) == 0:
        print("\n❌ CRITICAL: NO CALLBACK REQUESTS SENT!")
        print("   This means the button click did NOT trigger the callback.")
        print("   Possible causes:")
        print("   1. Component ID mismatch")
        print("   2. Dash not initialized properly")
        print("   3. prevent_initial_call blocking")
    
    time.sleep(5)
    browser.close()

print("\n" + "=" * 80)
