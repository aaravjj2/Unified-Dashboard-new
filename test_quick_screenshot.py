#!/usr/bin/env python3
"""Quick screenshot test to see what's rendering."""
import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

# Start dashboard
env = os.environ.copy()
env['AZURE_ENABLED'] = 'false'

proc = subprocess.Popen(
    [sys.executable, 'financial_dashboard/app.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    cwd='/home/aarav/unified-dashboard',
    env=env
)

# Wait for startup
time.sleep(5)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.goto('http://localhost:8050')
        time.sleep(2)
        
        # Click Market Trends
        page.click('text=Market Trends')
        time.sleep(3)
        
        # Screenshot
        page.screenshot(path='/tmp/mt_render.png', full_page=True)
        print("Screenshot saved to /tmp/mt_render.png")
        
        # Get page HTML for Market Trends tab
        html = page.content()
        
        # Check for status element
        has_status = '#status' in html or 'id="status"' in html
        print(f"\nHas status element: {has_status}")
        
        # Check for results-area
        has_results = 'results-area' in html
        print(f"Has results-area: {has_results}")
        
        # Check what tab content exists
        if 'Market Trends' in html:
            print("✅ Found 'Market Trends' text in HTML")
            
            # Extract a snippet
            idx = html.find('Market Trends')
            snippet = html[max(0, idx-200):min(len(html), idx+500)]
            print(f"\nSnippet around 'Market Trends':\n{snippet[:300]}...")
        
        browser.close()

finally:
    proc.terminate()
    proc.wait()
