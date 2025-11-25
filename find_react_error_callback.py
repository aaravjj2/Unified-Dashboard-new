#!/usr/bin/env python3
"""
Find which callback is causing React error #31 by monitoring browser console.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

print("\n" + "="*70)
print("FINDING REACT ERROR #31 SOURCE")
print("="*70 + "\n")

try:
    driver = webdriver.Chrome(options=chrome_options)
    
    print("Loading dashboard...")
    driver.get('http://localhost:8090')
    
    # Wait for initial load
    time.sleep(3)
    
    # Get initial logs
    initial_logs = driver.get_log('browser')
    initial_errors = [log for log in initial_logs if 'React error #31' in log['message'] or 'Minified React error #31' in log['message']]
    
    if initial_errors:
        print(f"❌ React error #31 occurs on initial page load")
        print(f"   Found {len(initial_errors)} error(s)")
        
        # Try to extract more info from the error
        for err in initial_errors[:1]:
            msg = err['message']
            print(f"\n   Full error message:")
            print(f"   {msg[:500]}...")
            
            # Check if it mentions specific components
            if 'chatbot' in msg.lower():
                print("\n   ⚠️  Error might be related to chatbot components")
            if 'attribution' in msg.lower():
                print("\n   ⚠️  Error might be related to attribution lab")
            if 'research' in msg.lower():
                print("\n   ⚠️  Error might be related to research lab")
    else:
        print("✅ No React error #31 on initial load")
    
    # Try clicking on different tabs to see if error occurs
    print("\n\nTesting tab navigation...")
    
    tabs_to_test = [
        ('Attribution Lab', 'attribution_lab'),
        ('Research Lab', 'research_lab'),
        ('Home Lab', 'home_lab'),
    ]
    
    for tab_name, tab_id in tabs_to_test:
        try:
            print(f"\n  Testing {tab_name}...")
            
            # Clear logs
            driver.get_log('browser')
            
            # Try to find and click the tab
            tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
            for tab in tabs:
                if tab_name.lower() in tab.text.lower():
                    tab.click()
                    time.sleep(2)
                    
                    # Check for new errors
                    new_logs = driver.get_log('browser')
                    new_errors = [log for log in new_logs if 'React error #31' in log['message']]
                    
                    if new_errors:
                        print(f"    ❌ React error #31 triggered by {tab_name}")
                    else:
                        print(f"    ✅ No error from {tab_name}")
                    break
        except Exception as e:
            print(f"    ⚠️  Could not test {tab_name}: {e}")
    
    # Check if chatbot components are present
    print("\n\nChecking for problematic components...")
    try:
        chatbot_elements = driver.find_elements(By.ID, 'chatbot-container')
        if chatbot_elements:
            print(f"  Found chatbot-container: {len(chatbot_elements)}")
            
            # Check its style
            style = chatbot_elements[0].get_attribute('style')
            print(f"  Chatbot style: {style}")
    except Exception as e:
        print(f"  Could not check chatbot: {e}")
    
    driver.quit()
    
    print("\n" + "="*70 + "\n")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
