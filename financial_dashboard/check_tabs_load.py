#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    page.goto('http://localhost:8000', wait_until='networkidle', timeout=60000)
    page.wait_for_selector('a[role="tab"]', timeout=10000)
    time.sleep(2)
    
    tabs = page.locator('a[id^="react-aria"][id*="-1-tab-"][role="tab"]').all()
    
    # Test Analysis Hub
    tabs[4].click()
    time.sleep(3)
    
    btn_selector = 'button:text("Run Attribution Analysis")'
    has_config = page.locator('text=Analysis Configuration').count() > 0
    has_button = page.locator(btn_selector).count() > 0
    has_error = page.locator('text=Internal Server Error').count() > 0
    
    print('Analysis Hub tab (index 4):')
    print(f'  - Has "Analysis Configuration": {has_config}')
    print(f'  - Has "Run Attribution Analysis" button: {has_button}')
    print(f'  - Has "Internal Server Error": {has_error}')
    
    # Test Research Lab
    tabs[6].click()
    time.sleep(3)
    
    btn_selector2 = 'button:text("Run Scenario")'
    has_scenario = page.locator('text=Scenario Analysis').count() > 0
    has_button2 = page.locator(btn_selector2).count() > 0
    has_error2 = page.locator('text=Internal Server Error').count() > 0
    
    print('\nResearch Lab tab (index 6):')
    print(f'  - Has "Scenario Analysis": {has_scenario}')
    print(f'  - Has "Run Scenario" button: {has_button2}')
    print(f'  - Has "Internal Server Error": {has_error2}')
    
    browser.close()
