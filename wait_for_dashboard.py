#!/usr/bin/env python3
"""
Wait for dashboard to fully load and test.
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
print("WAITING FOR DASHBOARD TO LOAD")
print("="*70 + "\n")

try:
    driver = webdriver.Chrome(options=chrome_options)
    
    print("Loading dashboard...")
    driver.get('http://localhost:8090')
    
    # Wait up to 30 seconds for tabs to appear
    print("Waiting for tabs to render...")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[role="tab"]'))
        )
        print("✅ Tabs appeared!")
    except:
        print("❌ Tabs did not appear within 30 seconds")
    
    time.sleep(2)
    
    # Check title
    title = driver.title
    print(f"Page title: {title}")
    
    # Check for tabs
    tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
    print(f"Found {len(tabs)} tabs")
    
    # Check errors
    logs = driver.get_log('browser')
    errors = [log for log in logs if log['level'] == 'SEVERE']
    print(f"Found {len(errors)} SEVERE errors")
    
    for err in errors:
        if 'Duplicate callback' in err['message']:
            print("  ❌ Duplicate callback error")
        elif 'React error #31' in err['message']:
            print("  ⚠️  React error #31")
    
    driver.quit()
    
    print("\n" + "="*70 + "\n")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
