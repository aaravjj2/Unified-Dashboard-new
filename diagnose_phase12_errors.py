#!/usr/bin/env python3
"""Quick diagnostic to capture console and network errors"""

from playwright.sync_api import sync_playwright
import json

BASE_URL = "http://localhost:8050"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    console_logs = []
    network_errors = []
    
    page.on("console", lambda msg: console_logs.append({
        "type": msg.type,
        "text": msg.text,
        "location": msg.location
    }))
    
    page.on("response", lambda response: 
            network_errors.append({
                "status": response.status,
                "url": response.url,
                "statusText": response.status_text
            }) if response.status >= 400 else None)
    
    print("Loading dashboard...")
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    print(f"\n✅ Dashboard loaded")
    print(f"📊 Console logs: {len(console_logs)}")
    print(f"🚨 Network errors: {len(network_errors)}")
    
    # Click first tab (Command Center)
    print("\nClicking Command Center tab...")
    page.locator("ul.nav a.nav-link").nth(0).click()
    page.wait_for_timeout(5000)
    
    print(f"📊 Console logs after click: {len(console_logs)}")
    print(f"🚨 Network errors after click: {len(network_errors)}")
    
    # Show errors
    print("\n=== CONSOLE ERRORS ===")
    for log in console_logs:
        if log["type"] == "error":
            print(f"  - {log['text'][:150]}")
    
    print("\n=== NETWORK ERRORS ===")
    for err in network_errors:
        print(f"  - {err['status']} {err['url']}")
    
    # Save full log
    with open("phase12_error_diagnostic.json", "w") as f:
        json.dump({
            "console_logs": console_logs,
            "network_errors": network_errors
        }, f, indent=2)
    
    print("\n✅ Saved to phase12_error_diagnostic.json")
    
    browser.close()
