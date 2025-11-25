from playwright.sync_api import sync_playwright
import time
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
    time.sleep(5)
    
    print('🎯 Real Backtest Final Test')
    print('='*70)
    
    page.click('text=Strategy Lab', timeout=10000)
    time.sleep(5)
    
    page.fill('#sl-tickers-input', 'AAPL')
    page.click('#sl-validate-btn', timeout=10000)
    time.sleep(8)
    
    page.click('text=Execute & Configure', timeout=10000)
    time.sleep(3)
    
    print('🚀 Running real backtest...')
    page.click('#sl-run-backtest-btn', timeout=10000)
    time.sleep(75)
    
    status = page.locator('#sl-execution-status').inner_text(timeout=5000)
    
    print('\n' + '='*70)
    if 'Real Historical Data' in status:
        print('✅ REAL BACKTEST IS WORKING!')
        print('='*70)
        print(status)
        print('='*70)
    else:
        print('Status:', status[:400])
    
    browser.close()
