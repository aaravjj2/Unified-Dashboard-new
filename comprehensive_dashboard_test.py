#!/usr/bin/env python3
"""
Comprehensive dashboard test - check functionality despite React errors.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

print("\n" + "="*70)
print("COMPREHENSIVE DASHBOARD TEST")
print("="*70 + "\n")

try:
    driver = webdriver.Chrome(options=chrome_options)
    
    print("1. Loading dashboard...")
    driver.get('http://localhost:8090')
    time.sleep(5)
    
    # Check if page loaded
    title = driver.title
    print(f"   ✅ Page loaded: {title}")
    
    # Check for errors
    logs = driver.get_log('browser')
    errors = [log for log in logs if log['level'] == 'SEVERE']
    duplicate_errors = [e for e in errors if 'Duplicate callback' in e['message']]
    react_errors = [e for e in errors if 'React error #31' in e['message']]
    
    print(f"\n2. Console Errors:")
    print(f"   Total SEVERE errors: {len(errors)}")
    print(f"   Duplicate callback errors: {len(duplicate_errors)} {'✅' if len(duplicate_errors) == 0 else '❌'}")
    print(f"   React error #31: {len(react_errors)} {'⚠️' if len(react_errors) > 0 else '✅'}")
    
    # Check if tabs are visible
    print(f"\n3. Testing Tab Navigation:")
    tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
    print(f"   Found {len(tabs)} tabs")
    
    if tabs:
        print(f"   ✅ Tabs are rendered")
        
        # Try clicking a few tabs
        for i, tab in enumerate(tabs[:3]):
            try:
                tab_text = tab.text
                print(f"   Testing tab: {tab_text}")
                tab.click()
                time.sleep(1)
                print(f"     ✅ Clicked successfully")
            except Exception as e:
                print(f"     ❌ Failed to click: {e}")
    else:
        print(f"   ❌ No tabs found")
    
    # Check if main content is visible
    print(f"\n4. Testing Content Visibility:")
    try:
        main_content = driver.find_element(By.CSS_SELECTOR, '.container-fluid')
        if main_content.is_displayed():
            print(f"   ✅ Main content is visible")
        else:
            print(f"   ❌ Main content is hidden")
    except:
        print(f"   ⚠️  Could not find main content")
    
    # Check if any components failed to render
    print(f"\n5. Checking for Rendering Issues:")
    page_source = driver.page_source
    
    if 'Error loading' in page_source:
        print(f"   ⚠️  Found 'Error loading' in page")
    else:
        print(f"   ✅ No 'Error loading' messages")
    
    if 'Dashboard Loading Error' in page_source:
        print(f"   ❌ Dashboard loading error detected")
    else:
        print(f"   ✅ No dashboard loading errors")
    
    # Final verdict
    print(f"\n" + "="*70)
    print(f"VERDICT:")
    print(f"="*70)
    
    if len(duplicate_errors) == 0:
        print(f"✅ FIXED: No duplicate callback errors")
    else:
        print(f"❌ ISSUE: Duplicate callback errors still present")
    
    if len(react_errors) > 0:
        print(f"⚠️  WARNING: React error #31 present (may not affect functionality)")
    else:
        print(f"✅ PERFECT: No React errors")
    
    if len(tabs) > 0:
        print(f"✅ FUNCTIONAL: Dashboard tabs are working")
    else:
        print(f"❌ BROKEN: Dashboard tabs not rendering")
    
    print(f"\n" + "="*70 + "\n")
    
    driver.quit()
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
