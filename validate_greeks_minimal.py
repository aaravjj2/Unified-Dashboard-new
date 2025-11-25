#!/usr/bin/env python
"""
Minimal Greeks validation: Navigate to Options Lab and screenshot
"""
import time
from playwright.sync_api import sync_playwright

url = "http://localhost:8050"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print(f"Navigate to {url}...")
    page.goto(url, timeout=60000)
    time.sleep(15)
    
    print("Close any modal...")
    try:
        page.locator('button.btn-close').first.click(timeout=2000)
    except:
        pass
    
    time.sleep(2)
    
    print("Navigate via URL hash...")
    page.goto(f"{url}/#options-lab", timeout=30000)
    time.sleep(5)
    
    print("Find ticker input...")
    ticker_inputs = page.locator('input[type="text"]').all()
    print(f"Found {len(ticker_inputs)} text inputs")
    
    # Find the visible one
    for i, inp in enumerate(ticker_inputs):
        if inp.is_visible():
            print(f"Input {i} is visible, filling with AAPL...")
            inp.fill("AAPL")
            inp.press("Enter")
            break
    
    time.sleep(10)
    
    screenshot = f"/home/aarav/unified-dashboard/reports/options_validation/diagnostics/greeks_attempt2_{int(time.time())}.png"
    page.screenshot(path=screenshot, full_page=True)
    print(f"Screenshot saved: {screenshot}")
    
    print("Check for Greeks charts...")
    gamma_chart = page.locator('#greeks-gamma-chart')
    if gamma_chart.count() > 0:
        print(f"✅ Gamma chart found")
        print(f"   Inner text: {gamma_chart.inner_text()[:100]}")
    else:
        print(f"❌ Gamma chart not found")
    
    time.sleep(10)
    browser.close()

print("Done!")
