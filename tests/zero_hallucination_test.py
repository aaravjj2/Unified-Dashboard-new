"""
ZERO HALLUCINATION TEST - Raw DOM Inspection + Manual Clicks
Tests what's ACTUALLY in the browser, not assumptions.
"""
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

print("=" * 80)
print("ZERO HALLUCINATION TEST - FULL DOM INSPECTION")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=1000)
    page = browser.new_page()
    
    # Capture network for callbacks
    callback_requests = []
    def track_callback(request):
        if '_dash-update-component' in request.url:
            callback_requests.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'url': request.url[:100]
            })
            print(f"   📡 CALLBACK REQUEST: {request.method} at {datetime.now().strftime('%H:%M:%S')}")
    
    page.on('request', track_callback)
    
    console_errors = []
    page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
    
    try:
        # STEP 1: Load dashboard
        print("STEP 1: Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='domcontentloaded')
        time.sleep(4)
        
        # Capture initial HTML
        page.screenshot(path='/tmp/test_01_initial.png', full_page=True)
        print(f"   Screenshot: /tmp/test_01_initial.png")
        
        # STEP 2: Find Market Trends tab
        print("\nSTEP 2: Finding Market Trends tab...")
        tabs = page.locator('a[role="tab"]').all()
        print(f"   Found {len(tabs)} tabs total")
        
        mt_tab = None
        for i, tab in enumerate(tabs):
            text = tab.inner_text()
            print(f"   Tab {i}: '{text}'")
            if 'Market Trends' in text or 'market_trends' in tab.get_attribute('id') or '':
                mt_tab = tab
                print(f"   ✅ Found Market Trends tab!")
        
        if not mt_tab:
            print("   ❌ Market Trends tab NOT FOUND!")
            browser.close()
            exit(1)
        
        # STEP 3: Click Market Trends tab
        print("\nSTEP 3: Clicking Market Trends tab...")
        mt_tab.click()
        time.sleep(3)
        page.screenshot(path='/tmp/test_02_mt_tab_clicked.png', full_page=True)
        print(f"   Screenshot: /tmp/test_02_mt_tab_clicked.png")
        
        # STEP 4: Inspect ACTUAL DOM - find ALL buttons
        print("\nSTEP 4: Inspecting ALL buttons in current view...")
        all_buttons = page.locator('button').all()
        print(f"   Total <button> elements found: {len(all_buttons)}")
        
        button_info = []
        for i, btn in enumerate(all_buttons):
            try:
                btn_id = btn.get_attribute('id') or '(no id)'
                btn_text = btn.inner_text(timeout=500) or '(no text)'
                btn_visible = btn.is_visible()
                btn_enabled = btn.is_enabled()
                
                button_info.append({
                    'index': i,
                    'id': btn_id,
                    'text': btn_text[:30],
                    'visible': btn_visible,
                    'enabled': btn_enabled
                })
                
                if btn_visible:
                    print(f"   Button {i}: id='{btn_id}', text='{btn_text[:30]}', visible={btn_visible}, enabled={btn_enabled}")
            except:
                pass
        
        # STEP 5: Find Run Analysis button specifically
        print("\nSTEP 5: Finding 'Run Full Analysis' button...")
        run_btn = None
        
        # Try multiple selectors
        selectors = [
            '#run-btn',
            'button:has-text("Run Full Analysis")',
            'button:has-text("Run")',
            'button:has-text("Analysis")'
        ]
        
        for selector in selectors:
            try:
                if page.locator(selector).count() > 0:
                    run_btn = page.locator(selector).first
                    print(f"   ✅ Found with selector: {selector}")
                    btn_id = run_btn.get_attribute('id')
                    btn_text = run_btn.inner_text(timeout=500)
                    print(f"      ID: {btn_id}, Text: '{btn_text}'")
                    break
            except:
                pass
        
        if not run_btn:
            print("   ❌ Run Analysis button NOT FOUND in DOM!")
            print("\n   Dumping page HTML to /tmp/page_dump.html...")
            with open('/tmp/page_dump.html', 'w') as f:
                f.write(page.content())
            print("   Check /tmp/page_dump.html for actual page content")
        else:
            # STEP 6: Click Run Analysis button
            print("\nSTEP 6: Clicking 'Run Full Analysis' button...")
            print(f"   Before click: {len(callback_requests)} callbacks")
            
            run_btn.click()
            page.screenshot(path='/tmp/test_03_run_clicked.png', full_page=True)
            print(f"   Screenshot: /tmp/test_03_run_clicked.png")
            
            # Wait for callback
            print("   Waiting 10 seconds for callback...")
            time.sleep(10)
            
            print(f"   After click: {len(callback_requests)} callbacks")
            
            if callback_requests:
                print("   ✅ CALLBACK FIRED!")
                for req in callback_requests:
                    print(f"      - {req['time']}: {req['url']}")
            else:
                print("   ❌ NO CALLBACK FIRED!")
            
            # Check results-area
            try:
                results_area = page.locator('#results-area')
                if results_area.count() > 0:
                    results_text = results_area.inner_text(timeout=2000)
                    print(f"   Results area length: {len(results_text)} chars")
                    if len(results_text) > 100:
                        print("   ✅ Results area has content!")
                    else:
                        print("   ⚠️  Results area is empty or minimal")
                else:
                    print("   ❌ #results-area NOT FOUND in DOM!")
            except Exception as e:
                print(f"   ❌ Error reading results-area: {e}")
            
            page.screenshot(path='/tmp/test_04_final_state.png', full_page=True)
            print(f"   Screenshot: /tmp/test_04_final_state.png")
        
        # STEP 7: Check for errors
        print("\nSTEP 7: Console errors...")
        if console_errors:
            print(f"   ❌ Found {len(console_errors)} errors:")
            for err in console_errors[:5]:
                print(f"      - {err[:100]}")
        else:
            print("   ✅ No console errors")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE - Keeping browser open for 10 seconds...")
        print("=" * 80)
        time.sleep(10)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        page.screenshot(path='/tmp/test_ERROR.png', full_page=True)
    
    finally:
        browser.close()

print("\nAll screenshots saved to /tmp/test_*.png")
print("HTML dump (if button not found): /tmp/page_dump.html")
