#!/usr/bin/env python3
"""
E2E Clicker Test - Run NBEATS and NHITS Neural Forecasts
This test specifically selects and runs NBEATS and NHITS models
"""

from playwright.sync_api import sync_playwright
import time
import os

DASHBOARD_URL = "http://localhost:8051"
SCREENSHOTS_DIR = "/home/aarav/Unified-Dashboard/screenshots"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def test_neural_forecast():
    ensure_dir(SCREENSHOTS_DIR)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("=" * 70)
        print("NBEATS / NHITS NEURAL FORECAST TEST")
        print("=" * 70)
        
        # Load dashboard
        print("\n[1] Loading dashboard...")
        page.goto(DASHBOARD_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2)
        
        # Click Market Forecast tab
        print("[2] Opening Market Forecast tab...")
        page.locator("text=Market Forecast").first.click()
        time.sleep(3)
        
        # Enter ticker
        print("[3] Entering ticker 'AAPL'...")
        ticker_input = page.locator("#mf-ticker-input")
        ticker_input.wait_for(state="visible", timeout=10000)
        ticker_input.clear()
        ticker_input.fill("AAPL")
        time.sleep(1)
        
        # Uncheck all models first
        print("[4] Configuring models - selecting NBEATS and NHITS...")
        model_labels = page.locator("#mf-model-checklist label").all()
        
        # First uncheck all currently checked models
        for label in model_labels:
            label_text = label.text_content().lower()
            checkbox = label.locator("input[type='checkbox']")
            if checkbox.count() > 0 and checkbox.is_checked():
                checkbox.click()
                time.sleep(0.2)
        
        time.sleep(0.5)
        
        # Now check only NBEATS and NHITS
        models_to_select = ['nbeats', 'nhits']
        selected_models = []
        
        for label in model_labels:
            label_text = label.text_content().lower()
            for model in models_to_select:
                if model in label_text and 'ensemble' not in label_text:
                    checkbox = label.locator("input[type='checkbox']")
                    if checkbox.count() > 0:
                        checkbox.click()
                        selected_models.append(label.text_content())
                        print(f"    ✓ Selected: {label.text_content()}")
                        time.sleep(0.3)
                    break
        
        page.screenshot(path=f"{SCREENSHOTS_DIR}/neural_01_models_selected.png")
        
        # Click Run Forecast
        print("[5] Running forecast with neural models...")
        run_btn = page.locator("#mf-run-btn")
        run_btn.click()
        
        # Wait and monitor for results
        print("[6] Waiting for neural forecast computation...")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/neural_02_forecast_started.png")
        
        # Wait for loading to complete (check for loading indicator or wait fixed time)
        max_wait = 120  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check if loading indicator is present
            loading = page.locator(".dash-spinner, .loading, [class*='loading']").first
            if loading.count() > 0 and loading.is_visible():
                elapsed = int(time.time() - start_time)
                print(f"    ... Loading ({elapsed}s)")
                time.sleep(5)
            else:
                break
            
            if int(time.time() - start_time) % 15 == 0:
                page.screenshot(path=f"{SCREENSHOTS_DIR}/neural_progress_{int(time.time() - start_time)}s.png")
        
        time.sleep(5)  # Final wait
        page.screenshot(path=f"{SCREENSHOTS_DIR}/neural_03_forecast_complete.png", full_page=True)
        
        # Check results
        print("\n[7] Checking results...")
        
        # Look for forecast output
        graphs = page.locator(".js-plotly-plot").all()
        print(f"    Found {len(graphs)} charts/graphs")
        
        # Look for model-specific outputs
        page_content = page.content()
        
        # Check for NBEATS in output
        nbeats_mentioned = 'nbeats' in page_content.lower()
        nhits_mentioned = 'nhits' in page_content.lower()
        
        print(f"    NBEATS in output: {nbeats_mentioned}")
        print(f"    NHITS in output: {nhits_mentioned}")
        
        # Check for any error messages
        error_elements = page.locator(".alert-danger, .text-danger, [class*='error']").all()
        errors_found = []
        for err in error_elements:
            if err.is_visible():
                err_text = err.text_content()[:200]
                if err_text.strip():
                    errors_found.append(err_text)
        
        if errors_found:
            print(f"    ⚠ Errors found:")
            for e in errors_found:
                print(f"      - {e}")
        else:
            print("    ✓ No visible errors")
        
        # Check for forecast data display areas
        forecast_elements = page.locator("#mf-forecast-graph, #mf-metrics-output, #mf-results, [id*='forecast']").all()
        print(f"    Forecast elements found: {len(forecast_elements)}")
        
        # Take final full-page screenshot
        page.screenshot(path=f"{SCREENSHOTS_DIR}/neural_04_final_state.png", full_page=True)
        
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"Models selected: {selected_models}")
        print(f"Charts generated: {len(graphs)}")
        print(f"Errors: {len(errors_found)}")
        print(f"Screenshots saved to: {SCREENSHOTS_DIR}/neural_*.png")
        
        browser.close()
        
        return len(graphs) > 0 and len(errors_found) == 0

if __name__ == "__main__":
    try:
        success = test_neural_forecast()
        if success:
            print("\n✓ Neural forecast test PASSED!")
        else:
            print("\n✗ Neural forecast test FAILED!")
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
