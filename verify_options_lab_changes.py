#!/usr/bin/env python3
"""
Verify that the Options Lab Contract Selector & Analysis section is visible.
"""
from playwright.sync_api import sync_playwright
import json
import sys

def verify_options_lab_changes():
    results = {
        "success": False,
        "container_selector_found": False,
        "forecast_button_found": False,
        "tradingview_button_found": False,
        "errors": []
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print("🔍 Loading Options Lab...")
            page.goto("http://localhost:8050/options-lab", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Check for the new Contract Selector card header
            print("🔍 Checking for Contract Selector & Analysis section...")
            contract_selector_header = page.locator("text=Contract Selector & Analysis").count()
            if contract_selector_header > 0:
                results["container_selector_found"] = True
                print("✅ Contract Selector & Analysis section found!")
            else:
                results["errors"].append("Contract Selector & Analysis section not found")
                print("❌ Contract Selector & Analysis section NOT found")
            
            # Check for Generate Forecast button
            print("🔍 Checking for Generate Forecast button...")
            forecast_btn = page.locator("#options-forecast-btn").count()
            if forecast_btn > 0:
                results["forecast_button_found"] = True
                print("✅ Generate Forecast button found!")
            else:
                results["errors"].append("Generate Forecast button not found")
                print("❌ Generate Forecast button NOT found")
            
            # Check for TradingView Signals button
            print("🔍 Checking for TradingView Signals button...")
            tradingview_btn = page.locator("#tradingview-fetch-btn").count()
            if tradingview_btn > 0:
                results["tradingview_button_found"] = True
                print("✅ TradingView Signals button found!")
            else:
                results["errors"].append("TradingView Signals button not found")
                print("❌ TradingView Signals button NOT found")
            
            # Take a screenshot
            page.screenshot(path="options_lab_verification.png", full_page=True)
            print("📸 Screenshot saved to options_lab_verification.png")
            
            # Overall success
            results["success"] = all([
                results["container_selector_found"],
                results["forecast_button_found"],
                results["tradingview_button_found"]
            ])
            
            browser.close()
            
    except Exception as e:
        results["errors"].append(str(e))
        print(f"❌ Error during verification: {e}")
    
    # Save results
    with open("options_lab_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    if results["success"]:
        print("✅ ALL OPTIONS LAB CHANGES VERIFIED SUCCESSFULLY!")
    else:
        print("❌ VERIFICATION FAILED")
        print(f"Errors: {results['errors']}")
    print("="*60)
    
    return 0 if results["success"] else 1

if __name__ == "__main__":
    sys.exit(verify_options_lab_changes())
