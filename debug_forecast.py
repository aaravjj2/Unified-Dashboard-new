#!/usr/bin/env python3
"""Debug why Market Forecast isn't generating output"""

from playwright.sync_api import sync_playwright
import time

def debug_forecast():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Collect ALL console messages
        console_msgs = []
        page.on('console', lambda msg: console_msgs.append(f'{msg.type}: {msg.text}'))
        
        print('='*60)
        print('MARKET FORECAST DEBUG')
        print('='*60)
        
        print('\n[1] Loading dashboard...')
        page.goto('http://localhost:8051', timeout=60000)
        page.wait_for_load_state('networkidle')
        time.sleep(3)
        
        print('[2] Clicking Market Forecast tab...')
        page.locator('text=Market Forecast').first.click()
        time.sleep(3)
        
        print('[3] Entering ticker AAPL...')
        ticker = page.locator('#mf-ticker-input')
        ticker.clear()
        ticker.fill('AAPL')
        time.sleep(1)
        
        # Check models
        print('\n[4] Checking selected models...')
        labels = page.locator('#mf-model-checklist label').all()
        for label in labels:
            cb = label.locator('input[type=checkbox]')
            if cb.count() > 0:
                checked = cb.is_checked()
                if checked:
                    print(f'  ✓ {label.text_content()}')
        
        # Find run button
        print('\n[5] Checking run button...')
        run_btn = page.locator('#mf-run-btn')
        if run_btn.count() > 0:
            print(f'  Text: {run_btn.text_content()}')
            print(f'  Visible: {run_btn.is_visible()}')
            print(f'  Enabled: {run_btn.is_enabled()}')
        else:
            print('  ❌ #mf-run-btn NOT FOUND!')
        
        page.screenshot(path='screenshots/debug_01_before.png')
        
        print('\n[6] Clicking Generate Forecast button...')
        run_btn.click()
        
        # Watch for changes
        print('[7] Monitoring for 30 seconds...')
        for i in range(6):
            time.sleep(5)
            
            # Check for loading spinner
            spinner = page.locator('._dash-loading-callback').first
            if spinner.count() > 0 and spinner.is_visible():
                print(f'  {(i+1)*5}s: Loading spinner visible')
            
            # Check graphs count
            graphs = page.locator('.js-plotly-plot').all()
            print(f'  {(i+1)*5}s: {len(graphs)} graphs')
            
            # Check for specific output area
            output = page.locator('#mf-forecast-output, #mf-results, [id*=forecast-graph]').all()
            print(f'  {(i+1)*5}s: {len(output)} output elements')
        
        page.screenshot(path='screenshots/debug_02_after.png', full_page=True)
        
        # Check page text
        print('\n[8] Checking page content...')
        body_text = page.inner_text('body')
        
        if "Click 'Generate Forecast'" in body_text:
            print('  ⚠️ Still showing placeholder text!')
        
        # Look for actual prediction values
        import re
        prices = re.findall(r'\$\d+\.?\d*', body_text)
        if prices:
            print(f'  Found {len(prices)} price values: {prices[:5]}...')
        
        # Print console errors
        print('\n[9] Console messages:')
        errors = [m for m in console_msgs if 'error' in m.lower()]
        for e in errors[:10]:
            print(f'  ❌ {e[:150]}')
        
        # Check network requests
        print('\n[10] All console messages:')
        for m in console_msgs[-20:]:
            print(f'  {m[:100]}')
        
        browser.close()

if __name__ == "__main__":
    debug_forecast()
