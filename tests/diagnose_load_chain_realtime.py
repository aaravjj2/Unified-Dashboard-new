#!/usr/bin/env python3
"""
Real-time diagnostic: Click Load Chain and capture full error details
"""
from playwright.sync_api import sync_playwright
import time
import subprocess

print("=" * 80)
print("🔬 LOAD CHAIN DIAGNOSTIC - REAL-TIME ERROR CAPTURE")
print("=" * 80)

# Check if app is running
try:
    result = subprocess.run(['pgrep', '-f', 'gunicorn.*financial_dashboard'], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ App not running! Starting it...")
        subprocess.Popen(['python', '-m', 'gunicorn', '-w', '1', '-b', '127.0.0.1:8050', 
                         '--timeout', '120', 'financial_dashboard.app:server'],
                        stdout=open('/tmp/gunicorn_diagnostic.log', 'w'),
                        stderr=subprocess.STDOUT)
        print("⏳ Waiting 15s for startup...")
        time.sleep(15)
    else:
        print(f"✅ App running (PID: {result.stdout.strip()})")
except Exception as e:
    print(f"⚠️  Could not check app status: {e}")

print("\n🌐 Launching browser...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    # Capture console messages
    console_messages = []
    def handle_console(msg):
        console_messages.append(f"[{msg.type}] {msg.text}")
    page.on('console', handle_console)
    
    # Capture errors
    page_errors = []
    def handle_error(error):
        page_errors.append(str(error))
    page.on('pageerror', handle_error)
    
    # Capture network errors
    network_errors = []
    def handle_response(response):
        if response.status >= 400:
            network_errors.append({
                'url': response.url,
                'status': response.status,
                'body': None  # Will fetch later
            })
    page.on('response', handle_response)
    
    try:
        print("📄 Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle')
        time.sleep(2)
        
        print("🎯 Clicking Options Lab tab...")
        page.click('text=💹 Options Lab', timeout=10000)
        time.sleep(2)
        
        print("📝 Entering ticker SPY...")
        ticker_input = page.query_selector('#options-ticker-input')
        if ticker_input:
            ticker_input.fill('SPY')
            time.sleep(1)
        else:
            print("❌ Ticker input not found!")
        
        print("🔘 Clicking Load Chain button...")
        load_btn = page.query_selector('button.options-load-btn')
        if load_btn:
            # Clear previous network errors
            network_errors.clear()
            
            load_btn.click()
            print("⏳ Waiting for response (10s)...")
            time.sleep(10)
            
            print("\n" + "=" * 80)
            print("📊 DIAGNOSTIC RESULTS")
            print("=" * 80)
            
            # Check for network errors
            if network_errors:
                print(f"\n❌ NETWORK ERRORS DETECTED: {len(network_errors)}")
                for err in network_errors:
                    print(f"\n   URL: {err['url']}")
                    print(f"   Status: {err['status']}")
                    
                    # Try to get response body
                    if '_dash-update-component' in err['url']:
                        print("\n   🔍 Fetching error details from server logs...")
                        try:
                            logs = subprocess.run(['tail', '-100', '/tmp/gunicorn_clean.log'],
                                                capture_output=True, text=True)
                            error_section = []
                            in_error = False
                            for line in logs.stdout.split('\n'):
                                if 'ERROR' in line or 'Exception' in line or 'Traceback' in line:
                                    in_error = True
                                if in_error:
                                    error_section.append(line)
                                    if line.strip() and not line.startswith(' '):
                                        if len(error_section) > 1:  # Got full error
                                            break
                            
                            if error_section:
                                print("\n   📜 SERVER ERROR:")
                                for line in error_section[:30]:  # First 30 lines
                                    print(f"      {line}")
                        except Exception as e:
                            print(f"   ⚠️  Could not read logs: {e}")
            else:
                print("\n✅ NO NETWORK ERRORS - Request succeeded!")
            
            # Check page errors
            if page_errors:
                print(f"\n⚠️  PAGE ERRORS: {len(page_errors)}")
                for err in page_errors:
                    print(f"   - {err}")
            else:
                print("\n✅ NO PAGE ERRORS")
            
            # Check console
            print(f"\n💬 CONSOLE MESSAGES: {len(console_messages)}")
            error_logs = [m for m in console_messages if 'error' in m.lower()]
            if error_logs:
                print(f"   ❌ Error messages found: {len(error_logs)}")
                for log in error_logs[-5:]:  # Last 5
                    print(f"      {log[:200]}")
            else:
                print("   ✅ No error messages in console")
            
            # Check UI state
            print("\n🎨 UI STATE CHECK:")
            status = page.query_selector('#options-status-message')
            if status:
                status_text = status.inner_text()
                print(f"   Status message: {status_text[:100]}")
            else:
                print("   ⚠️  No status message")
            
            table = page.query_selector('#chain-table-container')
            if table:
                table_text = table.inner_text()
                if len(table_text) > 50:
                    print(f"   ✅ Table has content ({len(table_text)} chars)")
                else:
                    print(f"   ⚠️  Table appears empty: {table_text[:100]}")
            else:
                print("   ❌ Table container not found")
            
        else:
            print("❌ Load Chain button not found!")
        
        print("\n" + "=" * 80)
        print("🔍 ADDITIONAL CHECKS")
        print("=" * 80)
        
        # Check if fix is actually in the running code
        print("\n📝 Verifying fix is active...")
        try:
            with open('/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/options_lab/callbacks.py', 'r') as f:
                content = f.read()
                if 'serializable_chain_data' in content and 'to_dict(\'records\')' in content:
                    print("   ✅ DataFrame serialization fix IS present in callbacks.py")
                else:
                    print("   ❌ DataFrame serialization fix NOT FOUND in callbacks.py!")
        except Exception as e:
            print(f"   ⚠️  Could not check file: {e}")
        
        # Check server logs
        print("\n📜 Recent server logs (last 20 lines):")
        try:
            logs = subprocess.run(['tail', '-20', '/tmp/gunicorn_clean.log'],
                                capture_output=True, text=True)
            for line in logs.stdout.split('\n')[-10:]:
                if line.strip():
                    print(f"   {line}")
        except Exception as e:
            print(f"   ⚠️  Could not read logs: {e}")
        
        print("\n📸 Screenshot: diagnostic_final_state.png")
        page.screenshot(path='test-artifacts/diagnostic_final_state.png', full_page=True)
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n⏸️  Keeping browser open for 5 seconds for inspection...")
        time.sleep(5)
        browser.close()

print("\n" + "=" * 80)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 80)
print("\n💡 If error persists:")
print("   1. Check screenshot: test-artifacts/diagnostic_final_state.png")
print("   2. Hard refresh browser: Ctrl+Shift+R")
print("   3. Check server logs: tail -100 /tmp/gunicorn_clean.log")
print("=" * 80)
