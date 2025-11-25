#!/usr/bin/env python3
"""
Simple test to confirm callback executes
"""

import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    # Start dashboard
    print("Starting dashboard...")
    proc = subprocess.Popen([
        sys.executable, '-m', 'financial_dashboard.index'
    ], env={'AZURE_ENABLED': 'false', 'OPTIONS_DETERMINISTIC': '1'},
       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    time.sleep(15)
    print("Dashboard should be ready\n")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto('http://localhost:8050')
            page.wait_for_load_state('networkidle')
            
            print("Clicking Market Trends tab...")
            page.click('text=Market Trends')
            time.sleep(2)
            
            print("Clicking Run Analysis button...")
            page.click('#mt-run-analysis-btn')
            print("Button clicked, waiting 3s for callback...")
            time.sleep(3)
            
            browser.close()
            print("\nTest complete - checking server logs...\n")
            
    finally:
        proc.terminate()
        # Read remaining output
        output, _ = proc.communicate(timeout=5)
        
        print("="*80)
        print("SERVER OUTPUT (last 100 lines):")
        print("="*80)
        lines = output.split('\n')
        for line in lines[-100:]:
            if any(keyword in line for keyword in ['🚨', 'CALLBACK', 'ENTRY', 'n_clicks', 'triggered_id']):
                print(line)

if __name__ == '__main__':
    main()
