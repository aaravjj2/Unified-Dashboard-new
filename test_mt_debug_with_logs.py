#!/usr/bin/env python3
"""
Debug test with server logs visible
"""

import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("=" * 80)
    print("CALLBACK DEBUG TEST WITH SERVER LOGS")
    print("=" * 80)
    
    # Start dashboard with logs visible
    print("🚀 Starting dashboard...")
    proc = subprocess.Popen([
        sys.executable, '-m', 'financial_dashboard.index'
    ], env={'AZURE_ENABLED': 'false', 'OPTIONS_DETERMINISTIC': '1'})
    
    time.sleep(10)
    print("   ✅ Dashboard started, running browser test...\n")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=300)
            page = browser.new_page()
            
            # Navigate and activate tab
            print("📍 Loading dashboard...")
            page.goto('http://localhost:8050')
            page.wait_for_load_state('networkidle')
            
            print("📍 Activating Market Trends tab...")
            page.click('text=Market Trends')
            time.sleep(2)
            
            # Click button
            print("📍 Clicking Run Analysis button...")
            page.click('#mt-run-analysis-btn')
            print("   ✅ Button clicked, waiting 5s for server response...")
            time.sleep(5)
            
            # Check status
            status_info = page.evaluate("""
                () => {
                    const status = document.getElementById('status');
                    if (!status) return {exists: false};
                    return {
                        exists: true,
                        display: status.style.display,
                        text: status.textContent.trim(),
                        html: status.innerHTML
                    };
                }
            """)
            print(f"\n📍 Status div after click:")
            print(f"   Exists: {status_info.get('exists')}")
            print(f"   Display: {status_info.get('display')}")
            print(f"   Text: '{status_info.get('text')}'")
            
            if status_info.get('text'):
                print("   ✅ SUCCESS - Status updated!")
            else:
                print("   ❌ FAIL - No status text")
            
            print("\n⏳ Keeping browser open for 10s to review...")
            time.sleep(10)
            
            browser.close()
            
    finally:
        print("\n🛑 Stopping dashboard...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
        print("   ✅ Stopped")

if __name__ == '__main__':
    main()
