#!/usr/bin/env python3
"""
Comprehensive Dashboard Test - Check Console Errors and Neural Output
"""

from playwright.sync_api import sync_playwright
import time
import os
import json

DASHBOARD_URL = "http://localhost:8051"
SCREENSHOTS_DIR = "/home/aarav/Unified-Dashboard/screenshots"

def test_comprehensive():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        console_messages = []
        
        # Capture ALL console messages
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text,
            "location": str(msg.location) if msg.location else None
        }))
        
        print("=" * 70)
        print("COMPREHENSIVE DASHBOARD TEST")
        print("=" * 70)
        
        # Load dashboard
        print("\n[1] Loading dashboard and capturing console...")
        page.goto(DASHBOARD_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)
        
        # Click Market Forecast tab
        print("[2] Opening Market Forecast tab...")
        page.locator("text=Market Forecast").first.click()
        time.sleep(3)
        
        # Enter ticker and run NBEATS forecast
        print("[3] Running NBEATS forecast for AAPL...")
        ticker_input = page.locator("#mf-ticker-input")
        ticker_input.wait_for(state="visible", timeout=10000)
        ticker_input.clear()
        ticker_input.fill("AAPL")
        time.sleep(1)
        
        # Select only NBEATS
        model_labels = page.locator("#mf-model-checklist label").all()
        
        # Uncheck all
        for label in model_labels:
            checkbox = label.locator("input[type='checkbox']")
            if checkbox.count() > 0 and checkbox.is_checked():
                checkbox.click()
                time.sleep(0.1)
        
        # Check NBEATS only
        for label in model_labels:
            if 'nbeats' in label.text_content().lower() and 'ensemble' not in label.text_content().lower():
                checkbox = label.locator("input[type='checkbox']")
                if checkbox.count() > 0:
                    checkbox.click()
                    print(f"    Selected: {label.text_content()}")
                break
        
        time.sleep(0.5)
        
        # Run forecast
        page.locator("#mf-run-btn").click()
        print("[4] Waiting for NBEATS forecast...")
        time.sleep(15)  # Wait for forecast
        
        page.screenshot(path=f"{SCREENSHOTS_DIR}/comprehensive_01_nbeats.png", full_page=True)
        
        # Now check Neural Ensemble
        print("[5] Running Neural Ensemble forecast...")
        
        # Uncheck NBEATS, check Neural Ensemble
        for label in model_labels:
            label_text = label.text_content().lower()
            checkbox = label.locator("input[type='checkbox']")
            if checkbox.count() > 0:
                if 'nbeats' in label_text and 'ensemble' not in label_text:
                    if checkbox.is_checked():
                        checkbox.click()
                        time.sleep(0.1)
                elif 'neural ensemble' in label_text:
                    if not checkbox.is_checked():
                        checkbox.click()
                        print(f"    Selected: {label.text_content()}")
                        time.sleep(0.1)
        
        time.sleep(0.5)
        page.locator("#mf-run-btn").click()
        print("[6] Waiting for Neural Ensemble forecast...")
        time.sleep(20)  # Neural ensemble takes longer
        
        page.screenshot(path=f"{SCREENSHOTS_DIR}/comprehensive_02_ensemble.png", full_page=True)
        
        # Extract any visible metrics or predictions
        print("\n[7] Extracting visible output...")
        
        # Check for prediction values in the page
        page_text = page.inner_text("body")
        
        # Look for prediction-related text
        prediction_keywords = ['prediction', 'forecast', 'price', 'target', 'accuracy', 'mae', 'rmse', 'mape']
        found_predictions = []
        for line in page_text.split('\n'):
            line_lower = line.lower()
            for kw in prediction_keywords:
                if kw in line_lower and len(line.strip()) < 200:
                    found_predictions.append(line.strip())
                    break
        
        print(f"    Found {len(found_predictions)} prediction-related lines")
        for pred in found_predictions[:10]:  # Show first 10
            print(f"      {pred[:80]}")
        
        # Analyze console messages
        print("\n[8] Console Analysis...")
        errors = [m for m in console_messages if m['type'] == 'error']
        warnings = [m for m in console_messages if m['type'] == 'warning']
        
        print(f"    Total messages: {len(console_messages)}")
        print(f"    Errors: {len(errors)}")
        print(f"    Warnings: {len(warnings)}")
        
        if errors:
            print("\n    ERROR DETAILS:")
            for i, err in enumerate(errors[:10]):  # Show first 10 errors
                print(f"    [{i+1}] {err['text'][:200]}")
        
        # Check specifically for persistence errors
        persistence_errors = [e for e in errors if 'persistence' in e['text'].lower()]
        if persistence_errors:
            print(f"\n    ⚠ PERSISTENCE ERRORS: {len(persistence_errors)}")
            for pe in persistence_errors:
                print(f"      {pe['text'][:150]}")
        
        # Save console log
        with open(f"{SCREENSHOTS_DIR}/console_log.json", 'w') as f:
            json.dump(console_messages, f, indent=2, default=str)
        print(f"\n    Console log saved to: {SCREENSHOTS_DIR}/console_log.json")
        
        # Final summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Console errors: {len(errors)}")
        print(f"Console warnings: {len(warnings)}")
        print(f"Persistence errors: {len(persistence_errors)}")
        print(f"Screenshots saved: {SCREENSHOTS_DIR}/comprehensive_*.png")
        
        browser.close()
        
        return len(errors) == 0

if __name__ == "__main__":
    try:
        success = test_comprehensive()
        if success:
            print("\n✓ Test PASSED - No console errors!")
        else:
            print("\n⚠ Test completed with console errors")
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
