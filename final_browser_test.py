#!/usr/bin/env python3
"""Final simple browser test."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

print("\n" + "="*70)
print("FINAL DASHBOARD TEST")
print("="*70 + "\n")

driver = webdriver.Chrome(options=chrome_options)

try:
    print("Loading http://localhost:8090...")
    driver.get('http://localhost:8090')
    time.sleep(8)
    
    # Get title
    title = driver.title
    print(f"✅ Page loaded: {title}")
    
    # Check for errors
    logs = driver.get_log('browser')
    severe_errors = [log for log in logs if log['level'] == 'SEVERE']
    duplicate_errors = [e for e in severe_errors if 'Duplicate callback' in e['message']]
    
    print(f"\nConsole Errors:")
    print(f"  Total SEVERE: {len(severe_errors)}")
    print(f"  Duplicate callbacks: {len(duplicate_errors)} {'✅ FIXED' if len(duplicate_errors) == 0 else '❌ ISSUE'}")
    
    # Try to find tabs
    try:
        tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        print(f"\nTabs found: {len(tabs)}")
        if tabs:
            print(f"✅ Tabs are rendering")
            for tab in tabs[:5]:
                print(f"  - {tab.text}")
        else:
            print(f"⚠️  No tabs found (may still be loading)")
    except Exception as e:
        print(f"⚠️  Could not check tabs: {e}")
    
    print("\n" + "="*70)
    print("FINAL VERDICT:")
    print("="*70)
    
    if len(duplicate_errors) == 0:
        print("✅ SUCCESS: Duplicate callback errors are FIXED")
    else:
        print("❌ FAILED: Duplicate callback errors still present")
    
    print("\n" + "="*70 + "\n")
    
finally:
    driver.quit()
