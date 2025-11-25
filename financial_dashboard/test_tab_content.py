#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = p.new_page()
    
    page.goto('http://localhost:8000', wait_until='networkidle', timeout=60000)
    page.wait_for_selector('a[role="tab"]', timeout=10000)
    time.sleep(2)
    
    tabs = page.locator('a[id^="react-aria"][id*="-1-tab-"][role="tab"]').all()
    
    # Click Analysis Hub
    print("Clicking Analysis Hub (index 4)...")
    tabs[4].click()
    time.sleep(3)
    
    # Check if Analysis Hub content loaded
    has_analysis_config = page.locator('text=Analysis Configuration').count() > 0
    has_run_button = page.locator('button:has-text("Run Attribution Analysis")').count() > 0
    has_internal_error = page.locator('text=Internal Server Error').count() > 0
    
    print(f"Analysis Hub tab:")
    print(f"  - Has 'Analysis Configuration': {has_analysis_config}")
    print(f"  - Has 'Run Attribution Analysis' button: {has_run_button}")
    print(f"  - Has 'Internal Server Error': {has_internal_error}")
    
    # Click Research Lab
    print("\nClicking Research Lab (index 6)...")
    tabs[6].click()
    time.sleep(3)
    
    # Check if Research Lab content loaded
    has_scenario = page.locator('text=Scenario Analysis').count() > 0
    has_vix = page.locator('text=VIX Change').count() > 0
    has_run_scenario = page.locator('button:has-text("Run Scenario")').count() > 0
    has_internal_error_rl = page.locator('text=Internal Server Error').count() > 0
    
    print(f"Research Lab tab:")
    print(f"  - Has 'Scenario Analysis': {has_scenario}")
    print(f"  - Has 'VIX Change': {has_vix}")
    print(f"  - Has 'Run Scenario' button: {has_run_scenario}")
    print(f"  - Has 'Internal Server Error': {has_internal_error_rl}")
    
    browser.close()
