"""
Market Trends Diagnostic Script
=================================
Comprehensive diagnosis of DOM rendering and callback behavior for Market Trends tab.
Tests for missing news-container and other critical elements.
"""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

# Configuration
BASE_URL = "http://localhost:8050"
OUTPUT_DIR = Path("/mnt/c/Aarav/fin_env/unified-dashboard/market_trends_snapshots")
OUTPUT_DIR.mkdir(exist_ok=True)

def save_snapshot(page, name, iteration=0):
    """Save HTML, screenshot, and element states"""
    prefix = f"iter{iteration}_{name}"
    
    # Save full HTML
    html_path = OUTPUT_DIR / f"{prefix}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(page.content())
    
    # Save screenshot
    screenshot_path = OUTPUT_DIR / f"{prefix}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    
    return html_path, screenshot_path

def check_element_presence(page, selector, description):
    """Check if element exists and return details"""
    try:
        element = page.locator(selector)
        count = element.count()
        
        if count == 0:
            return {
                "selector": selector,
                "description": description,
                "exists": False,
                "count": 0,
                "visible": False,
                "content_length": 0
            }
        
        is_visible = element.first.is_visible()
        content = ""
        try:
            content = element.first.inner_text() if is_visible else ""
        except:
            content = ""
        
        return {
            "selector": selector,
            "description": description,
            "exists": True,
            "count": count,
            "visible": is_visible,
            "content_length": len(content),
            "content_preview": content[:200] if content else ""
        }
    except Exception as e:
        return {
            "selector": selector,
            "description": description,
            "exists": False,
            "error": str(e)
        }

def diagnose_market_trends(iteration=1):
    """Run full diagnostic cycle"""
    
    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC ITERATION {iteration}")
    print(f"{'='*80}\n")
    
    results = {
        "iteration": iteration,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phases": {}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # PHASE 1: Initial page load (Home tab active)
        print("PHASE 1: Initial page load...")
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(3)
        
        html_path, screenshot_path = save_snapshot(page, "01_initial_load", iteration)
        
        critical_elements_initial = [
            ("#dashboard-tabs", "Main tab container"),
            ("#news-container", "News container (should be MISSING on Home tab)"),
            ("#results-area", "Results area"),
            ("#backtest-results", "Backtest results container"),
            ("#debug-log-container", "Debug log container"),
            ("#analysis-summary", "Analysis summary container"),
        ]
        
        phase1_results = []
        for selector, desc in critical_elements_initial:
            result = check_element_presence(page, selector, desc)
            phase1_results.append(result)
            status = "✓ FOUND" if result.get("exists") else "✗ MISSING"
            visible = "VISIBLE" if result.get("visible") else "HIDDEN"
            print(f"  {status} ({visible}): {desc} [{selector}]")
        
        results["phases"]["phase1_initial_load"] = {
            "html_snapshot": str(html_path),
            "screenshot": str(screenshot_path),
            "elements": phase1_results
        }
        
        # PHASE 2: Click Market Trends tab
        print("\nPHASE 2: Activating Market Trends tab...")
        
        # Find and click Market Trends tab
        market_trends_tab = page.locator('a:has-text("Market Trends")')
        if market_trends_tab.count() == 0:
            # Try alternative selector
            market_trends_tab = page.locator('[data-value="market_trends"]')
        
        if market_trends_tab.count() > 0:
            print(f"  Found {market_trends_tab.count()} Market Trends tab element(s)")
            market_trends_tab.first.click()
            print("  Clicked Market Trends tab")
            time.sleep(5)  # Wait for callback execution
        else:
            print("  ✗ ERROR: Could not find Market Trends tab to click!")
            results["phases"]["phase2_tab_activation"] = {"error": "Tab not found"}
            browser.close()
            return results
        
        html_path, screenshot_path = save_snapshot(page, "02_after_tab_click", iteration)
        
        # Check elements after tab activation
        critical_elements_active = [
            ("#news-container", "News container (MUST be present after activation)"),
            ("#results-area", "Results area"),
            ("#backtest-results", "Backtest results container"),
            ("#debug-log-container", "Debug log container"),
            ("#analysis-summary", "Analysis summary container"),
            ("#run-btn", "Run Analysis button"),
            ("#reload-model", "Reload Model button"),
            ("#refresh-cached", "Refresh Cached button"),
            ("#backtest-btn", "Backtest button"),
        ]
        
        phase2_results = []
        for selector, desc in critical_elements_active:
            result = check_element_presence(page, selector, desc)
            phase2_results.append(result)
            status = "✓ FOUND" if result.get("exists") else "✗ MISSING"
            visible = "VISIBLE" if result.get("visible") else "HIDDEN"
            content_info = f"({result.get('content_length', 0)} chars)" if result.get("exists") else ""
            print(f"  {status} ({visible}) {content_info}: {desc} [{selector}]")
        
        results["phases"]["phase2_tab_activation"] = {
            "html_snapshot": str(html_path),
            "screenshot": str(screenshot_path),
            "elements": phase2_results
        }
        
        # PHASE 3: Search for news-container in full HTML
        print("\nPHASE 3: Searching full HTML for news-container...")
        
        full_html = page.content()
        news_container_count = full_html.count('id="news-container"')
        news_panel_count = full_html.count('data-testid="news-panel"')
        
        print(f"  news-container ID occurrences: {news_container_count}")
        print(f"  news-panel testid occurrences: {news_panel_count}")
        
        # Search for Market Trends tab content section
        market_trends_section_present = 'id="market_trends"' in full_html or 'market_trends-content' in full_html
        print(f"  Market Trends content section present: {market_trends_section_present}")
        
        results["phases"]["phase3_html_search"] = {
            "news_container_count": news_container_count,
            "news_panel_count": news_panel_count,
            "market_trends_section_present": market_trends_section_present
        }
        
        # PHASE 4: Check callback execution via network logs
        print("\nPHASE 4: Checking for callback execution...")
        
        # Check for _dash-update-component requests
        page.goto(BASE_URL)
        time.sleep(2)
        
        # Set up request logging
        requests_log = []
        
        def log_request(request):
            if "_dash-update-component" in request.url or "_dash-dependencies" in request.url:
                requests_log.append({
                    "url": request.url,
                    "method": request.method,
                    "timestamp": time.time()
                })
        
        page.on("request", log_request)
        
        # Click tab again and monitor
        market_trends_tab = page.locator('a:has-text("Market Trends")')
        if market_trends_tab.count() > 0:
            market_trends_tab.first.click()
            time.sleep(5)
        
        print(f"  Captured {len(requests_log)} Dash-related requests")
        for req in requests_log:
            print(f"    - {req['method']} {req['url'][:100]}")
        
        results["phases"]["phase4_callback_monitoring"] = {
            "dash_requests": len(requests_log),
            "requests_log": requests_log
        }
        
        # PHASE 5: Final state check
        print("\nPHASE 5: Final state verification...")
        
        html_path, screenshot_path = save_snapshot(page, "03_final_state", iteration)
        
        final_check_results = []
        for selector, desc in critical_elements_active:
            result = check_element_presence(page, selector, desc)
            final_check_results.append(result)
        
        results["phases"]["phase5_final_state"] = {
            "html_snapshot": str(html_path),
            "screenshot": str(screenshot_path),
            "elements": final_check_results
        }
        
        browser.close()
    
    # Save results JSON
    results_path = OUTPUT_DIR / f"iter{iteration}_diagnostic_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {results_path}")
    
    return results

def analyze_consistency(all_results):
    """Analyze consistency across multiple iterations"""
    
    print(f"\n{'='*80}")
    print("CONSISTENCY ANALYSIS")
    print(f"{'='*80}\n")
    
    # Check if news-container was found in any iteration
    news_container_found_iterations = []
    
    for result in all_results:
        iteration = result["iteration"]
        phase2 = result["phases"].get("phase2_tab_activation", {})
        elements = phase2.get("elements", [])
        
        for elem in elements:
            if elem["selector"] == "#news-container" and elem.get("exists"):
                news_container_found_iterations.append(iteration)
                break
    
    if news_container_found_iterations:
        print(f"✓ news-container FOUND in iterations: {news_container_found_iterations}")
    else:
        print(f"✗ news-container NOT FOUND in any iteration")
    
    # Check consistency of other elements
    element_consistency = {}
    
    for result in all_results:
        phase2 = result["phases"].get("phase2_tab_activation", {})
        elements = phase2.get("elements", [])
        
        for elem in elements:
            selector = elem["selector"]
            exists = elem.get("exists", False)
            
            if selector not in element_consistency:
                element_consistency[selector] = []
            element_consistency[selector].append(exists)
    
    print("\nElement consistency across iterations:")
    for selector, exists_list in element_consistency.items():
        consistency = "CONSISTENT" if len(set(exists_list)) == 1 else "INCONSISTENT"
        found_count = sum(exists_list)
        total_count = len(exists_list)
        print(f"  {selector}: {found_count}/{total_count} found - {consistency}")
    
    return {
        "news_container_found_iterations": news_container_found_iterations,
        "element_consistency": element_consistency
    }

if __name__ == "__main__":
    print("Market Trends Diagnostic Tool")
    print("="*80)
    
    # Run 3 iterations
    all_results = []
    for i in range(1, 4):
        results = diagnose_market_trends(iteration=i)
        all_results.append(results)
        
        if i < 3:
            print("\n⏳ Waiting 5 seconds before next iteration...\n")
            time.sleep(5)
    
    # Analyze consistency
    consistency_analysis = analyze_consistency(all_results)
    
    # Save final analysis
    final_report_path = OUTPUT_DIR / "consistency_analysis.json"
    with open(final_report_path, 'w') as f:
        json.dump(consistency_analysis, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC COMPLETE")
    print(f"{'='*80}")
    print(f"Snapshots saved to: {OUTPUT_DIR}")
    print(f"Consistency report: {final_report_path}")
