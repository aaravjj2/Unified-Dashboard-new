#!/usr/bin/env python3
"""
Test with Dash debug mode to get unminified React errors.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

print("\n" + "="*70)
print("DETAILED REACT ERROR ANALYSIS")
print("="*70 + "\n")

try:
    driver = webdriver.Chrome(options=chrome_options)
    
    print("Loading dashboard...")
    driver.get('http://localhost:8090')
    
    time.sleep(5)
    
    # Get all logs
    logs = driver.get_log('browser')
    
    # Find React errors
    react_errors = [log for log in logs if 'React' in log['message'] and 'error' in log['message'].lower()]
    
    print(f"Found {len(react_errors)} React-related errors\n")
    
    for i, err in enumerate(react_errors, 1):
        print(f"\nError {i}:")
        print(f"Level: {err['level']}")
        print(f"Source: {err['source']}")
        print(f"Message (first 1000 chars):")
        print(err['message'][:1000])
        print("-" * 70)
    
    # Try to find the component causing the issue by inspecting the DOM
    print("\n\nInspecting DOM for problematic components...")
    
    # Check if there are any elements with data-dash-is-loading
    try:
        loading_elements = driver.find_elements_by_css_selector('[data-dash-is-loading="true"]')
        if loading_elements:
            print(f"Found {len(loading_elements)} elements still loading")
    except:
        pass
    
    # Get page source to look for issues
    page_source = driver.page_source
    
    # Check for common issues
    if '{props' in page_source or '{type' in page_source:
        print("⚠️  Found raw component objects in page source!")
        # Find the context
        import re
        matches = re.finditer(r'.{50}\{props.{50}', page_source)
        for match in list(matches)[:3]:
            print(f"  Context: ...{match.group()}...")
    
    driver.quit()
    
    print("\n" + "="*70 + "\n")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
