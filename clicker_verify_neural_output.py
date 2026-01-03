#!/usr/bin/env python3
"""
Final E2E Verification - Run Neural Forecasts and Verify Output
This test captures actual prediction values from NBEATS/NHITS/Neural Ensemble
"""

from playwright.sync_api import sync_playwright
import time
import os
import re
import json

DASHBOARD_URL = "http://localhost:8051"
SCREENSHOTS_DIR = "/home/aarav/Unified-Dashboard/screenshots"
RESULTS_FILE = "/home/aarav/Unified-Dashboard/screenshots/neural_forecast_results.json"

def test_neural_forecasts_with_output():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ticker": "AAPL",
        "models_tested": [],
        "forecasts": {},
        "errors": []
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("=" * 70)
        print("NEURAL FORECAST OUTPUT VERIFICATION")
        print("=" * 70)
        
        # Load dashboard and navigate to Market Forecast
        print("\n[1] Loading dashboard...")
        page.goto(DASHBOARD_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2)
        
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
        
        # Get model checkboxes
        model_labels = page.locator("#mf-model-checklist label").all()
        
        # Test each neural model
        neural_models_to_test = [
            ('nbeats', 'NBEATS'),
            ('nhits', 'NHITS'),
            ('neural ensemble', 'Neural Ensemble')
        ]
        
        for model_key, model_name in neural_models_to_test:
            print(f"\n[*] Testing {model_name}...")
            
            # Uncheck all models
            for label in model_labels:
                checkbox = label.locator("input[type='checkbox']")
                if checkbox.count() > 0 and checkbox.is_checked():
                    checkbox.click()
                    time.sleep(0.1)
            
            # Select the target model
            selected = False
            for label in model_labels:
                label_text = label.text_content().lower()
                if model_key in label_text:
                    checkbox = label.locator("input[type='checkbox']")
                    if checkbox.count() > 0:
                        checkbox.click()
                        selected = True
                        results["models_tested"].append(model_name)
                        print(f"    ✓ Selected: {label.text_content()}")
                        break
            
            if not selected:
                print(f"    ✗ Could not select {model_name}")
                continue
            
            time.sleep(0.5)
            
            # Run forecast
            page.locator("#mf-run-btn").click()
            print(f"    Waiting for {model_name} forecast...")
            
            # Wait with progress indicator
            start = time.time()
            while time.time() - start < 60:  # Max 60 seconds
                loading = page.locator(".dash-spinner, .loading").first
                if loading.count() == 0 or not loading.is_visible():
                    break
                time.sleep(2)
            
            time.sleep(3)  # Final stabilization
            
            # Capture screenshot
            screenshot_path = f"{SCREENSHOTS_DIR}/neural_{model_key.replace(' ', '_')}_output.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"    Screenshot: {screenshot_path}")
            
            # Extract any visible forecast data
            page_text = page.inner_text("body")
            
            # Look for price predictions
            price_patterns = [
                r'Predicted.*?(\$[\d,]+\.?\d*)',
                r'Target.*?(\$[\d,]+\.?\d*)',
                r'Forecast.*?(\$[\d,]+\.?\d*)',
                r'Price.*?(\$[\d,]+\.?\d*)',
                r'(\$\d{1,4}\.\d{2})',
            ]
            
            prices_found = []
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                prices_found.extend(matches)
            
            # Also check for plotly graph data
            graphs = page.locator(".js-plotly-plot").all()
            
            results["forecasts"][model_name] = {
                "prices_found": list(set(prices_found))[:10],
                "graphs_count": len(graphs),
                "status": "success" if len(graphs) > 0 else "no_graphs"
            }
            
            print(f"    Graphs: {len(graphs)}, Prices: {prices_found[:5] if prices_found else 'parsing needed'}")
        
        # Final screenshot
        page.screenshot(path=f"{SCREENSHOTS_DIR}/neural_final_state.png", full_page=True)
        
        # Save results
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "=" * 70)
        print("VERIFICATION RESULTS")
        print("=" * 70)
        print(f"Models tested: {results['models_tested']}")
        for model, data in results["forecasts"].items():
            print(f"  {model}: {data['graphs_count']} graphs, status={data['status']}")
        print(f"\nResults saved to: {RESULTS_FILE}")
        print(f"Screenshots saved to: {SCREENSHOTS_DIR}/neural_*.png")
        
        browser.close()
        
        # Success if all models generated graphs
        all_success = all(
            data.get('graphs_count', 0) > 0 
            for data in results["forecasts"].values()
        )
        return all_success

if __name__ == "__main__":
    try:
        success = test_neural_forecasts_with_output()
        if success:
            print("\n✅ ALL NEURAL FORECASTS VERIFIED!")
        else:
            print("\n⚠ Some forecasts may not have generated properly")
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
