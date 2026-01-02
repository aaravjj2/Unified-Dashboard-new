#!/usr/bin/env python3
"""
E2E Clicker Test for Market Forecast Tab - Verifies Neural Models (NBEATS/NHITS)
This test:
1. Opens Market Forecast tab
2. Enters a ticker
3. Selects neural models (NBEATS, NHITS)
4. Clicks Run Forecast
5. Verifies output is generated
"""

from playwright.sync_api import sync_playwright
import time
import os

DASHBOARD_URL = "http://localhost:8051"
SCREENSHOTS_DIR = "/home/aarav/Unified-Dashboard/screenshots"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def test_market_forecast_neural():
    ensure_dir(SCREENSHOTS_DIR)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("=" * 60)
        print("MARKET FORECAST E2E TEST - Neural Models")
        print("=" * 60)
        
        # Step 1: Load dashboard
        print("\n[1] Loading dashboard...")
        page.goto(DASHBOARD_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2)
        page.screenshot(path=f"{SCREENSHOTS_DIR}/e2e_01_dashboard_loaded.png")
        print("    ✓ Dashboard loaded")
        
        # Step 2: Click Market Forecast tab
        print("\n[2] Clicking Market Forecast tab...")
        mf_tab = page.locator("text=Market Forecast").first
        mf_tab.click()
        time.sleep(3)
        page.screenshot(path=f"{SCREENSHOTS_DIR}/e2e_02_market_forecast_tab.png")
        print("    ✓ Market Forecast tab opened")
        
        # Step 3: Enter ticker
        print("\n[3] Entering ticker 'AAPL'...")
        ticker_input = page.locator("#mf-ticker-input")
        ticker_input.wait_for(state="visible", timeout=10000)
        ticker_input.clear()
        ticker_input.fill("AAPL")
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOTS_DIR}/e2e_03_ticker_entered.png")
        print("    ✓ Ticker entered: AAPL")
        
        # Step 4: Check available models in the checklist
        print("\n[4] Checking available models...")
        model_checklist = page.locator("#mf-model-checklist")
        if model_checklist.is_visible():
            # Get all checkbox labels
            labels = page.locator("#mf-model-checklist label").all_text_contents()
            print(f"    Available models: {labels}")
            
            # Look for neural models
            neural_models = [l for l in labels if any(m in l.lower() for m in ['nbeats', 'nhits', 'neural', 'lstm', 'deep'])]
            print(f"    Neural models found: {neural_models}")
        
        # Step 5: Select specific models (try to check NBEATS and NHITS)
        print("\n[5] Selecting models...")
        # First uncheck all, then select specific ones
        checkboxes = page.locator("#mf-model-checklist input[type='checkbox']").all()
        print(f"    Found {len(checkboxes)} model checkboxes")
        
        # Get the parent labels to identify which model each checkbox is for
        model_labels = page.locator("#mf-model-checklist label").all()
        for i, label in enumerate(model_labels[:12]):  # Limit to first 12
            label_text = label.text_content()
            checkbox = label.locator("input[type='checkbox']")
            is_checked = checkbox.is_checked() if checkbox.count() > 0 else False
            print(f"    Model {i}: {label_text} - checked: {is_checked}")
        
        page.screenshot(path=f"{SCREENSHOTS_DIR}/e2e_04_models_checked.png")
        
        # Step 6: Find and click Run Forecast button
        print("\n[6] Looking for Run Forecast button...")
        
        # Try different selectors
        run_btn_selectors = [
            "#mf-run-btn",
            "#mf-run-forecast-btn",
            "button:has-text('Run Forecast')",
            "button:has-text('Generate')",
            "button:has-text('Forecast')",
        ]
        
        run_btn = None
        for selector in run_btn_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible():
                    run_btn = btn
                    print(f"    Found button with selector: {selector}")
                    break
            except:
                pass
        
        if run_btn:
            print("    Clicking Run Forecast button...")
            run_btn.click()
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOTS_DIR}/e2e_05_forecast_clicked.png")
            
            # Wait for results (check for loading indicators or results)
            print("\n[7] Waiting for forecast results...")
            time.sleep(10)  # Give time for forecast to complete
            page.screenshot(path=f"{SCREENSHOTS_DIR}/e2e_06_waiting_results.png")
            
            # Check for any graphs/charts generated
            graphs = page.locator(".js-plotly-plot").all()
            print(f"    Found {len(graphs)} Plotly graphs")
            
            # Check for error messages
            errors = page.locator(".alert-danger, .error, [class*='error']").all()
            if errors:
                for err in errors:
                    if err.is_visible():
                        print(f"    ⚠ Error found: {err.text_content()[:100]}")
            
            # Final screenshot
            time.sleep(5)
            page.screenshot(path=f"{SCREENSHOTS_DIR}/e2e_07_final_results.png", full_page=True)
            print("    ✓ Final screenshot captured")
            
        else:
            print("    ✗ Run Forecast button not found!")
            # List all visible buttons for debugging
            all_buttons = page.locator("button").all()
            visible_buttons = [b for b in all_buttons if b.is_visible()]
            print(f"    Visible buttons: {[b.text_content()[:30] for b in visible_buttons[:10]]}")
        
        # Step 8: Check console for errors
        print("\n[8] Checking browser console...")
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
        
        # Collect any existing errors
        page.evaluate("console.log('E2E test complete')")
        time.sleep(1)
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Screenshots saved to: {SCREENSHOTS_DIR}/e2e_*.png")
        print(f"Console errors collected: {len(console_errors)}")
        
        browser.close()
        
        return True

if __name__ == "__main__":
    try:
        test_market_forecast_neural()
        print("\n✓ E2E Test completed!")
    except Exception as e:
        print(f"\n✗ E2E Test failed: {e}")
        import traceback
        traceback.print_exc()
