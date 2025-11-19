#!/usr/bin/env python3
"""
Test browser console errors using Selenium.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')

# Enable browser logging
chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

print("\n" + "="*70)
print("BROWSER CONSOLE ERROR TEST")
print("="*70 + "\n")

try:
    driver = webdriver.Chrome(options=chrome_options)
    
    print("Loading dashboard at http://localhost:8090...")
    driver.get('http://localhost:8090')
    
    # Wait for page to load
    print("Waiting for page to load...")
    time.sleep(5)
    
    # Get browser console logs
    logs = driver.get_log('browser')
    
    # Filter for errors
    errors = [log for log in logs if log['level'] == 'SEVERE']
    warnings = [log for log in logs if log['level'] == 'WARNING']
    
    print(f"\nFound {len(errors)} errors and {len(warnings)} warnings\n")
    
    # Check for duplicate callback errors
    duplicate_errors = [e for e in errors if 'Duplicate callback' in e['message']]
    react_errors = [e for e in errors if 'React error #31' in e['message'] or 'Minified React error #31' in e['message']]
    
    if duplicate_errors:
        print(f"❌ Found {len(duplicate_errors)} duplicate callback errors:")
        for err in duplicate_errors[:3]:  # Show first 3
            msg = err['message']
            if 'perf-total-return' in msg:
                print("  - perf-total-return")
            if 'factors-exposures' in msg:
                print("  - factors-exposures")
            if 'sectors-weights-p' in msg:
                print("  - sectors-weights-p")
            if 'residual-alpha' in msg:
                print("  - residual-alpha")
    else:
        print("✅ No duplicate callback errors found")
    
    if react_errors:
        print(f"\n❌ Found {len(react_errors)} React error #31 (invalid children):")
        for err in react_errors[:2]:  # Show first 2
            print(f"  - {err['message'][:200]}...")
    else:
        print("\n✅ No React error #31 found")
    
    # Show all severe errors
    if errors:
        print(f"\n\nAll Severe Errors ({len(errors)}):")
        for i, err in enumerate(errors[:5], 1):  # Show first 5
            print(f"\n{i}. {err['message'][:300]}...")
    
    driver.quit()
    
    print("\n" + "="*70 + "\n")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
