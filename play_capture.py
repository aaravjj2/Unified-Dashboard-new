from playwright.sync_api import sync_playwright
import time, sys

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:8050', wait_until='domcontentloaded', timeout=60000)
    time.sleep(2)
    try:
        page.click('text=Market Trends', timeout=10000)
        print('Clicked Market Trends tab')
    except Exception as e:
        print('Market Trends tab click failed (may already be active):', e)
    time.sleep(2)
    print('Clicking Run Full Analysis (#run-btn)')
    try:
        page.click('#run-btn', timeout=8000)
        print('Clicked #run-btn')
    except Exception as e:
        print('run-btn click failed:', e)
    time.sleep(2)
    try:
        page.click('button:has-text("Backtest Trend Signals")', timeout=8000)
        print('Clicked Backtest Trend Signals')
    except Exception as e:
        print('backtest click failed (maybe not visible):', e)
    print('Waiting 60s for server activity (increase if needed)...')
    time.sleep(60)
    browser.close()
    sys.exit(0)
