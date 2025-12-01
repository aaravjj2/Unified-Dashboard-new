#!/usr/bin/env python3
"""Test minimal Market Trends to confirm callbacks work"""
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

# Temporarily replace market_trends with minimal version
print("Swapping to minimal Market Trends...")
subprocess.run([
    'mv',
    '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends.py',
    '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends_BROKEN.py'
], check=False)

subprocess.run([
    'mv',
    '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends_minimal.py',
    '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends.py'
], check=False)

try:
    # Start dashboard
    print("Starting dashboard with minimal Market Trends...")
    proc = subprocess.Popen([
        sys.executable, '-m', 'financial_dashboard.index'
    ], env={'AZURE_ENABLED': 'false', 'OPTIONS_DETERMINISTIC': '1'})
    
    time.sleep(12)
    print("Dashboard started\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.goto('http://localhost:8050')
        page.wait_for_load_state('networkidle')
        
        print("Clicking Market Trends tab...")
        page.click('text=Market Trends')
        time.sleep(2)
        
        # Check initial status
        initial_status = page.text_content('#status')
        print(f"Initial status: {initial_status}")
        
        # Click Run Analysis button
        print("\nClicking Run Analysis button...")
        page.click('#mt-run-analysis-btn')
        time.sleep(3)
        
        # Check updated status
        final_status = page.text_content('#status')
        results = page.text_content('#results-area')
        
        print(f"\n{'='*60}")
        print(f"Final status: {final_status}")
        print(f"Results: {results}")
        print(f"{'='*60}")
        
        if "complete" in final_status.lower() and "Job executed" in results:
            print("\n✅ SUCCESS - Callback works!")
        else:
            print("\n❌ FAIL - Callback didn't fire")
        
        time.sleep(5)
        browser.close()
        
finally:
    # Restore original file
    print("\nRestoring original Market Trends...")
    subprocess.run(['pkill', '-f', 'financial_dashboard.index'], check=False)
    time.sleep(2)
    
    subprocess.run([
        'mv',
        '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends.py',
        '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends_minimal.py'
    ], check=False)
    
    subprocess.run([
        'mv',
        '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends_BROKEN.py',
        '/home/aarav/unified-dashboard/financial_dashboard/tabs/market_trends.py'
    ], check=False)
    
    print("Files restored")
