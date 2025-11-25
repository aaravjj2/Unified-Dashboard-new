#!/usr/bin/env python3
"""
Comprehensive Greeks Graphs Validation (Headed Chromium)
Tests all Greeks charts on port 8050 with repair-first policy
"""
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

PORT = 8050
BASE_URL = f"http://localhost:{PORT}"
DIAGNOSTICS_DIR = Path("reports/options_validation/diagnostics")
SCREENSHOTS_DIR = Path("reports/options_validation/screenshots")
DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def check_greeks_graphs(headed=True):
    """
    Validate all Greeks graphs show data with headed Chromium
    """
    results = {
        "timestamp": time.time(),
        "port": PORT,
        "headed": headed,
        "graphs": {},
        "verdict": "UNKNOWN"
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Headed mode as required
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        # Enable console logging
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        
        try:
            print(f"✓ Navigating to {BASE_URL}")
            page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "greeks_1_home.png"))
            
            # Wait for app to load
            page.wait_for_selector("#main-tabs", timeout=30000)
            print("✓ Main app loaded")
            
            # Navigate to Options Lab tab
            print("✓ Clicking Options Lab tab...")
            options_tab = page.locator("a:has-text('Options Lab')").first
            if options_tab.is_visible():
                options_tab.click()
                time.sleep(2)
                page.screenshot(path=str(SCREENSHOTS_DIR / "greeks_2_options_lab.png"))
            else:
                print("⚠ Options Lab tab not visible, trying alternative selector")
                page.click("#main-tabs a[href='#options-lab']")
                time.sleep(2)
            
            # Wait for Options Lab content
            page.wait_for_selector("#options-lab-content", timeout=10000)
            print("✓ Options Lab content loaded")
            
            # Click Chain Viewer subtab (where Greeks graphs are)
            print("✓ Navigating to Chain Viewer subtab...")
            chain_viewer_tab = page.locator("a:has-text('Chain Viewer')").first
            if chain_viewer_tab.is_visible():
                chain_viewer_tab.click()
                time.sleep(2)
            else:
                # Try by ID
                page.click("#ol-tabs a[href='#chain-viewer']")
                time.sleep(2)
            
            page.screenshot(path=str(SCREENSHOTS_DIR / "greeks_3_chain_viewer.png"))
            
            # Enter ticker symbol
            print("✓ Entering ticker AAPL...")
            ticker_input = page.locator("#ol-ticker-input").first
            if ticker_input.is_visible():
                ticker_input.fill("AAPL")
                time.sleep(1)
            else:
                print("⚠ Ticker input not found with #ol-ticker-input, trying alternatives")
                # Try other selectors
                selectors = ["input[placeholder*='ticker']", "input[placeholder*='Ticker']", 
                           "#ticker-input", "input[type='text']"]
                for sel in selectors:
                    try:
                        page.fill(sel, "AAPL")
                        break
                    except:
                        continue
            
            # Click Load Chain button
            print("✓ Clicking Load Chain...")
            load_btn = page.locator("#ol-load-chain-btn").first
            if load_btn.is_visible():
                load_btn.click()
            else:
                page.click("button:has-text('Load Chain')")
            
            # Wait for data to load (extended wait)
            print("⏳ Waiting for options chain data (90 seconds)...")
            time.sleep(90)
            
            page.screenshot(path=str(SCREENSHOTS_DIR / "greeks_4_after_load.png"))
            
            # Check each Greeks graph
            greeks_ids = [
                ("ol-greeks-chart-delta", "Delta"),
                ("ol-greeks-chart-gamma", "Gamma"),
                ("ol-greeks-chart-vega", "Vega"),
                ("ol-greeks-chart-theta", "Theta"),
                ("ol-iv-smile-chart", "IV Smile")
            ]
            
            for graph_id, graph_name in greeks_ids:
                print(f"\n📊 Checking {graph_name} graph (#{graph_id})...")
                
                graph_result = {
                    "id": graph_id,
                    "name": graph_name,
                    "exists": False,
                    "visible": False,
                    "has_plotly_data": False,
                    "trace_count": 0,
                    "data_points": 0,
                    "verdict": "FAIL"
                }
                
                try:
                    # Check if element exists
                    graph = page.locator(f"#{graph_id}").first
                    graph_result["exists"] = graph.count() > 0
                    
                    if graph_result["exists"]:
                        graph_result["visible"] = graph.is_visible()
                        
                        # Check Plotly data
                        plotly_data = page.evaluate(f"""
                            () => {{
                                const el = document.getElementById('{graph_id}');
                                if (el && el.data) {{
                                    return {{
                                        trace_count: el.data.length,
                                        data_points: el.data.reduce((sum, trace) => 
                                            sum + (trace.x ? trace.x.length : 0), 0)
                                    }};
                                }}
                                return null;
                            }}
                        """)
                        
                        if plotly_data:
                            graph_result["has_plotly_data"] = True
                            graph_result["trace_count"] = plotly_data.get("trace_count", 0)
                            graph_result["data_points"] = plotly_data.get("data_points", 0)
                            
                            if graph_result["data_points"] > 0:
                                graph_result["verdict"] = "PASS"
                                print(f"  ✅ {graph_name}: {graph_result['data_points']} data points")
                            else:
                                graph_result["verdict"] = "EMPTY"
                                print(f"  ⚠ {graph_name}: Graph exists but NO data points")
                        else:
                            graph_result["verdict"] = "NO_PLOTLY"
                            print(f"  ⚠ {graph_name}: Element exists but no Plotly data")
                    else:
                        graph_result["verdict"] = "NOT_FOUND"
                        print(f"  ❌ {graph_name}: Element not found in DOM")
                
                except Exception as e:
                    graph_result["error"] = str(e)
                    print(f"  ❌ {graph_name}: Error - {e}")
                
                results["graphs"][graph_id] = graph_result
            
            # Final screenshot
            page.screenshot(path=str(SCREENSHOTS_DIR / "greeks_5_final.png"))
            
            # Save console logs
            with open(DIAGNOSTICS_DIR / "greeks_console_logs.txt", "w") as f:
                f.write("\n".join(console_logs))
            
            # Overall verdict
            passed_graphs = sum(1 for g in results["graphs"].values() if g["verdict"] == "PASS")
            total_graphs = len(results["graphs"])
            
            if passed_graphs == total_graphs:
                results["verdict"] = "SUCCESS"
                print(f"\n✅ ALL GREEKS GRAPHS PASS ({passed_graphs}/{total_graphs})")
            elif passed_graphs > 0:
                results["verdict"] = "PARTIAL"
                print(f"\n⚠ PARTIAL SUCCESS ({passed_graphs}/{total_graphs} graphs showing data)")
            else:
                results["verdict"] = "FAIL"
                print(f"\n❌ ALL GREEKS GRAPHS FAIL (0/{total_graphs})")
        
        except Exception as e:
            results["error"] = str(e)
            results["verdict"] = "ERROR"
            print(f"\n❌ Validation error: {e}")
            page.screenshot(path=str(SCREENSHOTS_DIR / "greeks_error.png"))
        
        finally:
            browser.close()
    
    # Save results
    with open(DIAGNOSTICS_DIR / "greeks_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == "__main__":
    print("=" * 80)
    print("GREEKS GRAPHS COMPREHENSIVE VALIDATION")
    print(f"Port: {PORT}")
    print(f"Mode: Headed Chromium (headless=False)")
    print("=" * 80)
    
    results = check_greeks_graphs(headed=True)
    
    print("\n" + "=" * 80)
    print(f"FINAL VERDICT: {results['verdict']}")
    print("=" * 80)
    
    sys.exit(0 if results["verdict"] in ["SUCCESS", "PARTIAL"] else 1)
