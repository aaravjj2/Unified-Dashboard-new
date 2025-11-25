"""
Test Market Trends button functionality (reload-model, toggle-brief, CSV download)
Verify buttons work even if browser console shows duplicate warnings
"""

from playwright.sync_api import sync_playwright
import time
import json

def test_market_trends_buttons():
    """Test all 3 Market Trends buttons"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visual for user
        page = browser.new_page()
        
        print("🔍 Loading dashboard...")
        page.goto('http://localhost:8051', wait_until='networkidle', timeout=60000)
        time.sleep(5)
        
        print("\n📍 Navigating to Market Trends tab...")
        market_trends_tab = page.locator('a.nav-link[data-bs-target="#market-trends"]')
        if not market_trends_tab.is_visible():
            print("❌ Market Trends tab not found!")
            browser.close()
            return
        
        market_trends_tab.click()
        time.sleep(3)
        
        # Test 1: Reload Model button
        print("\n🧪 TEST 1: Testing reload-model button...")
        reload_btn = page.locator('#reload-model-btn')
        
        if not reload_btn.is_visible():
            print("❌ Reload Model button not found!")
        else:
            # Get current status before click
            status_before = page.locator('#model-status').inner_text() if page.locator('#model-status').is_visible() else "N/A"
            print(f"   Status before: {status_before}")
            
            # Click button
            reload_btn.click()
            print("   ✅ Button clicked!")
            time.sleep(2)
            
            # Check if status changed
            status_after = page.locator('#model-status').inner_text() if page.locator('#model-status').is_visible() else "N/A"
            print(f"   Status after: {status_after}")
            
            if status_before != status_after:
                print("   ✅ Status CHANGED - Button works!")
            else:
                print("   ⚠️  Status unchanged - Check console for errors")
        
        # Test 2: Toggle Brief button
        print("\n🧪 TEST 2: Testing toggle-brief button...")
        toggle_btn = page.locator('#toggle-brief-btn')
        
        if not toggle_btn.is_visible():
            print("❌ Toggle Brief button not found!")
        else:
            # Check brief visibility before
            brief_div = page.locator('#full-brief')
            visible_before = brief_div.is_visible() if brief_div.count() > 0 else False
            print(f"   Brief visible before: {visible_before}")
            
            # Click button
            toggle_btn.click()
            print("   ✅ Button clicked!")
            time.sleep(2)
            
            # Check brief visibility after
            visible_after = brief_div.is_visible() if brief_div.count() > 0 else False
            print(f"   Brief visible after: {visible_after}")
            
            if visible_before != visible_after:
                print("   ✅ Visibility TOGGLED - Button works!")
            else:
                print("   ⚠️  Visibility unchanged - Check console for errors")
        
        # Test 3: CSV Download button
        print("\n🧪 TEST 3: Testing CSV download button...")
        csv_btn = page.locator('#download-csv-btn')
        
        if not csv_btn.is_visible():
            print("❌ CSV Download button not found!")
        else:
            # Set up download listener
            with page.expect_download(timeout=10000) as download_info:
                csv_btn.click()
                print("   ✅ Button clicked!")
            
            try:
                download = download_info.value
                print(f"   ✅ Download triggered! File: {download.suggested_filename}")
                print("   ✅ CSV Download works!")
            except Exception as e:
                print(f"   ⚠️  Download not triggered: {e}")
        
        # Keep browser open for manual inspection
        print("\n\n📌 Browser will stay open for 15 seconds for manual inspection...")
        time.sleep(15)
        
        browser.close()
        print("\n✅ Test complete!")

if __name__ == '__main__':
    test_market_trends_buttons()
