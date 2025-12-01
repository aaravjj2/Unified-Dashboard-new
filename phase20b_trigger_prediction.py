#!/usr/bin/env python3
"""
Phase 20B - Trigger New Prediction with SHAP Values
Simple Playwright script to click Run Prediction button
"""
import sys
from playwright.sync_api import sync_playwright
import time

def trigger_prediction():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("🌐 Loading Azure ML Lab...")
            page.goto('http://localhost:8050/azure-ml-lab', wait_until='networkidle', timeout=30000)
            time.sleep(2)
            
            print("🖱️  Scrolling to Run Prediction button...")
            button = page.locator('#azure-ml-run-prediction-btn')
            button.scroll_into_view_if_needed()
            time.sleep(1)
            
            print("🖱️  Clicking Run Prediction button...")
            button.click(force=True)
            
            print("⏳ Waiting for prediction to complete...")
            time.sleep(6)
            
            print("✅ Prediction triggered successfully")
            
            # Check if success message appears
            content = page.content()
            if "Phase 20A" in content or "ML Prediction Complete" in content:
                print("✅ Success message confirmed in UI")
            
            browser.close()
            return 0
            
        except Exception as e:
            print(f"❌ Error: {e}")
            browser.close()
            return 1

if __name__ == "__main__":
    sys.exit(trigger_prediction())
