"""Quick verification script to check if all 8 Volatility Lab subtabs are visible."""
from playwright.sync_api import sync_playwright
import time

def verify_subtabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)  # 60 second timeout
        
        print("🔍 Opening dashboard...")
        page.goto("http://localhost:8050", wait_until="domcontentloaded")
        time.sleep(5)
        
        print("🔍 Looking for Volatility Lab tab...")
        vol_lab_tab = page.locator('text="⚡ Volatility Lab"').first
        if vol_lab_tab.is_visible():
            print("✅ Found Volatility Lab tab in navbar")
            vol_lab_tab.click()
            time.sleep(2)
        else:
            print("❌ Volatility Lab tab NOT FOUND in navbar")
            browser.close()
            return False
        
        print("\n🔍 Checking for 8 subtabs...")
        expected_subtabs = [
            ("Historical HV", "Historical HV"),
            ("IV Surface", "IV Surface"),
            ("Correlation", "Correlation"),
            ("Factor Analytics", "Factor Analytics"),
            ("Advanced Charts", "Advanced Charts"),
            ("Metrics Table", "Metrics Table"),
            ("Custom Scenarios", "Custom Scenarios"),
            ("Alerts", "Alerts & Diagnostics")  # Search for "Alerts" to handle truncation
        ]
        
        found_count = 0
        for search_text, display_name in expected_subtabs:
            subtab = page.locator(f'text="{search_text}"').first
            if subtab.is_visible():
                print(f"  ✅ {display_name}")
                found_count += 1
            else:
                print(f"  ❌ {display_name} NOT FOUND")
        
        print(f"\n📊 Result: {found_count}/8 subtabs visible")
        
        if found_count == 8:
            print("✅ SUCCESS: All 8 subtabs are visible!")
            
            # Test clicking each subtab
            print("\n🔍 Testing subtab interactions...")
            for search_text, display_name in expected_subtabs[:3]:  # Test first 3
                try:
                    page.locator(f'text="{search_text}"').first.click()
                    time.sleep(0.5)
                    print(f"  ✅ Clicked {display_name}")
                except Exception as e:
                    print(f"  ⚠️ Error clicking {display_name}: {e}")
            
            screenshot_path = "test-artifacts/vol_lab_8subtabs_verified.png"
            page.screenshot(path=screenshot_path)
            print(f"\n📸 Screenshot saved: {screenshot_path}")
        else:
            print(f"❌ FAILED: Only {found_count}/8 subtabs visible")
        
        browser.close()
        return found_count == 8

if __name__ == "__main__":
    import sys
    success = verify_subtabs()
    sys.exit(0 if success else 1)
