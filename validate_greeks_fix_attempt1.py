#!/usr/bin/env python
"""
FIX A - Repair Attempt 1: Validate Greeks Graphs Show Data
Agent-1A validation script to check if Gamma/Theta/Vega charts have data
REQUIREMENT: Headed Chromium only
PORT: 8050
"""
import time
import json
from playwright.sync_api import sync_playwright, expect

def validate_greeks_graphs(url="http://localhost:8050"):
    """
    Validate that Greeks graphs (Gamma, Theta, Vega) show data
    Returns: dict with test results
    """
    results = {
        "test": "FIX A - Greeks Graphs Repair Attempt 1",
        "timestamp": time.time(),
        "url": url,
        "greeks_charts": {},
        "success": False,
        "message": ""
    }
    
    with sync_playwright() as p:
        # CRITICAL: Headed Chromium only (headless forbidden by super-prompt)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"🌐 Navigating to {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        print("⏳ Waiting for page to load...")
        time.sleep(10)
        
        # Close any auto-opening modals (e.g. Research Notes)
        print("🚫 Closing any auto-opening modals...")
        try:
            close_button = page.locator('button.btn-close').first
            if close_button.is_visible(timeout=2000):
                close_button.click()
                print("  ✅ Closed modal")
                time.sleep(1)
        except:
            print("  ℹ️ No modal to close")
        
        # Navigate to Options Lab tab
        print("📍 Clicking Options Lab tab...")
        try:
            options_tab = page.locator('text=Options Lab').first
            options_tab.wait_for(state="visible", timeout=30000)
            options_tab.click(timeout=10000, force=True)  # Force click to bypass overlays
        except Exception as e:
            print(f"⚠️ Failed to click Options Lab tab, trying alternate selector: {e}")
            # Try URL hash navigation instead
            page.goto(f"{url}#options-lab", wait_until="domcontentloaded", timeout=30000)
        
        time.sleep(5)
        
        # Enter a ticker symbol to load data
        print("🔍 Entering ticker symbol (AAPL)...")
        ticker_input = page.locator('#options-ticker-input')
        ticker_input.fill('AAPL')
        ticker_input.press('Enter')
        time.sleep(5)  # Wait for data to load
        
        # Check if Greeks graphs have data
        greeks_chart_ids = [
            'greeks-gamma-chart',
            'greeks-theta-chart',
            'greeks-vega-chart'
        ]
        
        for chart_id in greeks_chart_ids:
            print(f"📊 Checking {chart_id}...")
            chart = page.locator(f'#{chart_id}')
            
            if chart.count() == 0:
                results["greeks_charts"][chart_id] = {
                    "found": False,
                    "error": "Element not found"
                }
                continue
            
            # Check if chart has data by looking for plotly traces
            chart_html = chart.inner_html()
            has_plot_data = 'data-plot' in chart_html or 'plotly' in chart_html.lower()
            
            # Check for "No data" or empty state
            chart_text = chart.inner_text()
            is_empty = (
                'no data' in chart_text.lower() or
                'loading' in chart_text.lower() or
                len(chart_text.strip()) < 10
            )
            
            results["greeks_charts"][chart_id] = {
                "found": True,
                "has_plot_data": has_plot_data,
                "is_empty": is_empty,
                "text_length": len(chart_text),
                "status": "✅ HAS DATA" if (has_plot_data and not is_empty) else "❌ EMPTY"
            }
            
            print(f"  {results['greeks_charts'][chart_id]['status']}")
        
        # Determine overall success
        greeks_with_data = [
            chart_id for chart_id, data in results["greeks_charts"].items()
            if data.get("found") and data.get("has_plot_data") and not data.get("is_empty")
        ]
        
        results["success"] = len(greeks_with_data) == len(greeks_chart_ids)
        results["greeks_with_data_count"] = len(greeks_with_data)
        results["total_greeks_charts"] = len(greeks_chart_ids)
        
        if results["success"]:
            results["message"] = f"✅ All {len(greeks_chart_ids)} Greeks charts show data"
        else:
            results["message"] = f"❌ Only {len(greeks_with_data)}/{len(greeks_chart_ids)} Greeks charts show data"
        
        # Take screenshot for evidence
        screenshot_path = f"/home/aarav/unified-dashboard/reports/options_validation/diagnostics/greeks_fix_attempt1_screenshot_{int(time.time())}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        results["screenshot"] = screenshot_path
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Keep browser open for 5 seconds for manual inspection
        print("🔍 Keeping browser open for 5 seconds for manual inspection...")
        time.sleep(5)
        
        browser.close()
    
    return results


if __name__ == "__main__":
    print("="*70)
    print("FIX A - Repair Attempt 1: Validate Greeks Graphs")
    print("="*70)
    
    results = validate_greeks_graphs()
    
    print("\n" + "="*70)
    print("RESULTS:")
    print("="*70)
    print(json.dumps(results, indent=2))
    
    # Save results to file
    report_path = f"/home/aarav/unified-dashboard/reports/options_validation/diagnostics/greeks_fix_attempt1_results_{int(time.time())}.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📝 Results saved to: {report_path}")
    print(f"\n{results['message']}")
    
    exit(0 if results["success"] else 1)
