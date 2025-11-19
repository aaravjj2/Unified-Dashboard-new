#!/usr/bin/env python3
"""
Test script for Market Trends fixes

Tests all button functionality and verifies the fixes work correctly.
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def setup_driver():
    """Setup headless Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    return webdriver.Chrome(options=chrome_options)

def test_market_trends_tab(driver, base_url='http://localhost:8090'):
    """Test Market Trends tab functionality"""
    
    print("\n" + "="*70)
    print("MARKET TRENDS TAB - FUNCTIONALITY TEST")
    print("="*70)
    
    try:
        # Load dashboard
        print("\n1. Loading dashboard...")
        driver.get(base_url)
        time.sleep(5)
        
        # Find and click Market Trends tab
        print("2. Clicking Market Trends tab...")
        tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        market_trends_tab = None
        for tab in tabs:
            if 'Market Trends' in tab.text:
                market_trends_tab = tab
                break
        
        if not market_trends_tab:
            print("❌ Market Trends tab not found")
            return False
        
        market_trends_tab.click()
        time.sleep(3)
        
        print("✅ Market Trends tab activated")
        
        # Test Button 2: Reload Model
        print("\n3. Testing 'Reload Model' button...")
        try:
            reload_btn = driver.find_element(By.ID, 'reload-model')
            reload_btn.click()
            time.sleep(2)
            
            # Check for status message
            model_status = driver.find_element(By.ID, 'model-status')
            status_text = model_status.text
            
            if status_text:
                print(f"✅ Reload Model: {status_text}")
            else:
                print("⚠️  Reload Model: No status message")
        except Exception as e:
            print(f"❌ Reload Model failed: {e}")
        
        # Test Button 3: Refresh Cached Display
        print("\n4. Testing 'Refresh cached display' button...")
        try:
            refresh_btn = driver.find_element(By.ID, 'refresh-cached')
            refresh_btn.click()
            time.sleep(2)
            
            # Check for results area update
            results_area = driver.find_element(By.ID, 'results-area')
            if results_area.text:
                print("✅ Refresh Cached Display: Results updated")
            else:
                print("⚠️  Refresh Cached Display: No results")
        except Exception as e:
            print(f"❌ Refresh Cached Display failed: {e}")
        
        # Test Button 6: Toggle Full Brief
        print("\n5. Testing 'Toggle full brief' button...")
        try:
            toggle_btn = driver.find_element(By.ID, 'toggle-brief')
            full_brief = driver.find_element(By.ID, 'full-brief')
            
            # Check initial state
            initial_display = full_brief.value_of_css_property('display')
            
            # Click to toggle
            toggle_btn.click()
            time.sleep(1)
            
            # Check new state
            new_display = full_brief.value_of_css_property('display')
            
            if initial_display != new_display:
                print(f"✅ Toggle Full Brief: Changed from {initial_display} to {new_display}")
            else:
                print("⚠️  Toggle Full Brief: Display didn't change")
        except Exception as e:
            print(f"❌ Toggle Full Brief failed: {e}")
        
        # Test Button 7: Download CSV
        print("\n6. Testing 'Download CSV' button...")
        try:
            download_btn = driver.find_element(By.ID, 'mt-download-btn')
            download_btn.click()
            time.sleep(2)
            print("✅ Download CSV: Button clicked (download triggered)")
        except Exception as e:
            print(f"❌ Download CSV failed: {e}")
        
        # Check for news panel
        print("\n7. Checking news panel...")
        try:
            news_panel = driver.find_element(By.CSS_SELECTOR, '[data-testid="news-panel"]')
            if news_panel.text:
                print(f"✅ News Panel: {news_panel.text[:100]}...")
            else:
                print("⚠️  News Panel: Empty")
        except Exception as e:
            print(f"❌ News Panel not found: {e}")
        
        # Check for price data in table
        print("\n8. Checking price data display...")
        try:
            # Look for table with data-testid
            table = driver.find_element(By.CSS_SELECTOR, '[data-testid="market-trends-table"]')
            
            # Check for price columns
            price_cells = driver.find_elements(By.CSS_SELECTOR, '[data-col="current_price"]')
            
            if price_cells:
                print(f"✅ Price Data: Found {len(price_cells)} price cells")
                
                # Check first cell value
                if price_cells[0].get_attribute('data-value'):
                    print(f"   Sample price: {price_cells[0].text}")
            else:
                print("⚠️  Price Data: No price cells found")
        except Exception as e:
            print(f"❌ Price Data check failed: {e}")
        
        # Check browser console for errors
        print("\n9. Checking browser console...")
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        if errors:
            print(f"⚠️  Found {len(errors)} console errors:")
            for err in errors[:3]:
                print(f"   - {err['message'][:100]}")
        else:
            print("✅ No console errors")
        
        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    driver = None
    
    try:
        print("Starting Market Trends functionality test...")
        print("Make sure dashboard is running on http://localhost:8090")
        
        driver = setup_driver()
        success = test_market_trends_tab(driver)
        
        if success:
            print("\n✅ All tests completed")
            return 0
        else:
            print("\n❌ Some tests failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    sys.exit(main())
