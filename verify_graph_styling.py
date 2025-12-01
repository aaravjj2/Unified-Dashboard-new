#!/usr/bin/env python3
"""Verify that graphs remain in dark mode while UI is in light mode."""

import time
import os

def main():
    from playwright.sync_api import sync_playwright
    
    # Create screenshot directory
    screenshot_dir = "/home/aarav/Unified-Dashboard/test_artifacts/graph_styling_verification"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Non-headless for visual verification
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("Opening dashboard...")
        page.goto("http://localhost:8050", wait_until="networkidle", timeout=60000)
        time.sleep(3)
        
        # Take screenshot of initial view
        page.screenshot(path=f"{screenshot_dir}/01_initial_view.png", full_page=False)
        print(f"Screenshot saved: 01_initial_view.png")
        
        # Navigate through tabs that have graphs
        tabs_with_graphs = [
            ("Market Forecast", "market-forecast-tab"),
            ("Strategy Lab", "strategy-lab-tab"),
            ("Portfolio", "portfolio-tab"),
            ("Options Lab", "options-lab-tab"),
            ("Volatility Lab", "volatility-lab-tab"),
            ("Swing Trade", "swing-tab"),
        ]
        
        for tab_name, tab_id in tabs_with_graphs:
            try:
                print(f"\nNavigating to {tab_name}...")
                
                # Try different selectors
                selectors = [
                    f"[id='{tab_id}']",
                    f"[data-tab='{tab_id}']",
                    f"a:has-text('{tab_name}')",
                    f".nav-link:has-text('{tab_name}')",
                    f"button:has-text('{tab_name}')",
                ]
                
                clicked = False
                for selector in selectors:
                    try:
                        elem = page.locator(selector).first
                        if elem.is_visible(timeout=2000):
                            elem.click()
                            clicked = True
                            break
                    except:
                        continue
                
                if clicked:
                    time.sleep(2)  # Wait for content to load
                    
                    # Take screenshot
                    safe_name = tab_name.lower().replace(" ", "_")
                    page.screenshot(path=f"{screenshot_dir}/{safe_name}_tab.png", full_page=False)
                    print(f"Screenshot saved: {safe_name}_tab.png")
                    
                    # Check for graph elements
                    graphs = page.locator(".dash-graph, .js-plotly-plot").all()
                    print(f"  Found {len(graphs)} graph(s) in {tab_name}")
                else:
                    print(f"  Could not find tab: {tab_name}")
                    
            except Exception as e:
                print(f"  Error with {tab_name}: {e}")
        
        # Keep browser open for manual inspection
        print("\n" + "="*60)
        print("Browser is open for manual verification.")
        print("Check that:")
        print("  1. UI elements (cards, tables, text) are in LIGHT mode")
        print("  2. Graphs and charts are in DARK mode")
        print("="*60)
        
        input("\nPress Enter to close browser...")
        browser.close()
        
        print(f"\nAll screenshots saved to: {screenshot_dir}")

if __name__ == "__main__":
    main()
