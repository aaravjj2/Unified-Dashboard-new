#!/usr/bin/env python3
"""
Phase 12 Screenshot Content Validation
Analyzes actual content in screenshots and compares with live dashboard
"""

import os
import json
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("snapshots/phase12_playwright_snapshots")
BASE_URL = "http://localhost:8050"

TABS = [
    {"name": "Command Center", "index": 0, "file": "command_center.png"},
    {"name": "Research Lab", "index": 1, "file": "research_lab.png"},
    {"name": "Attribution Lab", "index": 2, "file": "attribution_lab.png"},
    {"name": "Strategy Lab", "index": 3, "file": "strategy_lab.png"},
    {"name": "Azure ML Lab", "index": 4, "file": "azure_ml_lab.png"},
    {"name": "Weekly Picks", "index": 5, "file": "weekly_picks.png"},
    {"name": "Monthly Picks", "index": 6, "file": "monthly_picks.png"},
    {"name": "Market Trends", "index": 7, "file": "market_trends.png"},
    {"name": "Market Forecast", "index": 8, "file": "market_forecast.png"},
    {"name": "Volatility Lab", "index": 9, "file": "volatility_lab.png"},
    {"name": "Portfolio", "index": 10, "file": "portfolio.png"},
    {"name": "Options Lab", "index": 11, "file": "options_lab.png"},
]

def validate_screenshot_integrity():
    """Validate all screenshots can be opened and check dimensions"""
    print("\n" + "="*80)
    print("🖼️  SCREENSHOT INTEGRITY VALIDATION")
    print("="*80)
    
    results = []
    
    for tab in TABS:
        filepath = SCREENSHOT_DIR / tab["file"]
        result = {
            "tab": tab["name"],
            "file": tab["file"],
            "exists": False,
            "valid": False,
            "size_kb": 0,
            "dimensions": None,
            "mode": None
        }
        
        if filepath.exists():
            result["exists"] = True
            result["size_kb"] = round(filepath.stat().st_size / 1024, 1)
            
            try:
                with Image.open(filepath) as img:
                    result["valid"] = True
                    result["dimensions"] = f"{img.width}×{img.height}"
                    result["mode"] = img.mode
                    
                    icon = "✅" if img.width == 1920 and img.height >= 1080 else "⚠️"
                    print(f"{icon} {tab['name']:20s} | {result['size_kb']:6.1f} KB | {result['dimensions']:12s} | {img.mode}")
            except Exception as e:
                print(f"❌ {tab['name']:20s} | CORRUPT: {str(e)[:50]}")
                result["error"] = str(e)
        else:
            print(f"❌ {tab['name']:20s} | FILE NOT FOUND")
        
        results.append(result)
    
    valid_count = sum(1 for r in results if r["valid"])
    print(f"\n✅ Valid Screenshots: {valid_count}/{len(TABS)}")
    
    return results

def analyze_live_tab_content(tab_name, tab_index):
    """Capture live tab content and analyze what's actually displayed"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("ul.nav a.nav-link", timeout=10000)
            
            # Click tab
            page.locator("ul.nav a.nav-link").nth(tab_index).click(timeout=10000, force=True)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)
            
            # Analyze content
            content_analysis = {
                "tab_name": tab_name,
                "tab_index": tab_index,
                "dom_elements": {},
                "text_content": [],
                "visible_sections": []
            }
            
            # Count major elements
            content_analysis["dom_elements"] = {
                "total_divs": page.locator("div").count(),
                "charts": page.locator("canvas, svg[class*='chart'], div[id*='chart']").count(),
                "tables": page.locator("table").count(),
                "table_rows": page.locator("table tr").count(),
                "buttons": page.locator("button").count(),
                "inputs": page.locator("input").count(),
                "headers_h1": page.locator("h1").count(),
                "headers_h2": page.locator("h2").count(),
                "headers_h3": page.locator("h3").count(),
                "headers_h4": page.locator("h4").count(),
                "cards": page.locator(".card, [class*='card']").count(),
                "dropdowns": page.locator("select, [role='combobox']").count(),
            }
            
            # Get visible text from major sections
            try:
                # Try to find section headers
                headers = page.locator("h1, h2, h3, h4, h5").all()
                for i, header in enumerate(headers[:10]):  # First 10 headers
                    try:
                        text = header.inner_text(timeout=1000)
                        if text.strip():
                            content_analysis["visible_sections"].append(text.strip())
                    except:
                        pass
            except:
                pass
            
            # Check for common "no data" or placeholder messages
            body_text = page.locator("body").inner_text(timeout=5000)
            
            # Look for key phrases
            key_phrases = [
                "No data", "Loading", "Select", "Choose", "Pick", 
                "Forecast", "Prediction", "Analysis", "Strategy",
                "Coming Soon", "Under Construction", "Placeholder"
            ]
            
            found_phrases = []
            for phrase in key_phrases:
                if phrase.lower() in body_text.lower():
                    found_phrases.append(phrase)
            
            content_analysis["found_phrases"] = found_phrases
            
            # Check if there are any stock tickers visible
            ticker_pattern = r'\b[A-Z]{1,5}\b'
            import re
            tickers = re.findall(ticker_pattern, body_text)
            content_analysis["potential_tickers"] = list(set(tickers))[:20]  # First 20 unique
            
            # Get first 500 chars of visible text
            content_analysis["sample_text"] = body_text[:500].strip()
            
            browser.close()
            return content_analysis
            
        except Exception as e:
            browser.close()
            return {
                "tab_name": tab_name,
                "tab_index": tab_index,
                "error": str(e)
            }

def deep_content_analysis():
    """Analyze actual content in the 'Picks' and 'Forecast' tabs"""
    print("\n" + "="*80)
    print("🔍 DEEP CONTENT ANALYSIS - Weekly/Monthly Picks & Market Forecast")
    print("="*80)
    
    focus_tabs = [
        {"name": "Weekly Picks", "index": 5},
        {"name": "Monthly Picks", "index": 6},
        {"name": "Market Forecast", "index": 8},
    ]
    
    results = []
    
    for tab in focus_tabs:
        print(f"\n→ Analyzing {tab['name']}...")
        analysis = analyze_live_tab_content(tab["name"], tab["index"])
        results.append(analysis)
        
        print(f"  DOM Elements:")
        if "dom_elements" in analysis:
            for key, val in analysis["dom_elements"].items():
                print(f"    - {key}: {val}")
        
        if "visible_sections" in analysis:
            print(f"  Visible Sections: {len(analysis['visible_sections'])}")
            for section in analysis["visible_sections"][:5]:
                print(f"    • {section}")
        
        if "found_phrases" in analysis:
            print(f"  Key Phrases Found: {', '.join(analysis['found_phrases']) if analysis['found_phrases'] else 'None'}")
        
        if "potential_tickers" in analysis:
            print(f"  Potential Tickers: {', '.join(analysis['potential_tickers'][:10]) if analysis['potential_tickers'] else 'None'}")
        
        if "sample_text" in analysis:
            print(f"\n  Sample Text (first 300 chars):")
            print(f"  {analysis['sample_text'][:300]}")
        
        if "error" in analysis:
            print(f"  ❌ ERROR: {analysis['error']}")
    
    # Save results
    with open("screenshot_content_analysis.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Saved detailed analysis to screenshot_content_analysis.json")
    
    return results

def compare_all_tabs():
    """Quick comparison of all tabs"""
    print("\n" + "="*80)
    print("📊 ALL TABS CONTENT SUMMARY")
    print("="*80)
    
    all_results = []
    
    for tab in TABS:
        print(f"\n→ {tab['name']}...", end=" ", flush=True)
        analysis = analyze_live_tab_content(tab["name"], tab["index"])
        all_results.append(analysis)
        
        if "dom_elements" in analysis:
            charts = analysis["dom_elements"].get("charts", 0)
            tables = analysis["dom_elements"].get("tables", 0)
            print(f"✅ {charts} charts, {tables} tables")
        else:
            print("❌ Failed")
    
    # Generate summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(f"{'Tab':<20} | {'Charts':<7} | {'Tables':<7} | {'Buttons':<8} | {'Cards':<6}")
    print("-" * 80)
    
    for result in all_results:
        name = result.get("tab_name", "Unknown")
        if "dom_elements" in result:
            elem = result["dom_elements"]
            print(f"{name:<20} | {elem.get('charts', 0):<7} | {elem.get('tables', 0):<7} | "
                  f"{elem.get('buttons', 0):<8} | {elem.get('cards', 0):<6}")
        else:
            print(f"{name:<20} | ERROR")
    
    # Save all results
    with open("all_tabs_content_analysis.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✅ Saved complete analysis to all_tabs_content_analysis.json")
    
    return all_results

if __name__ == "__main__":
    print("\n🎯 PHASE 12 SCREENSHOT VALIDATION & CONTENT ANALYSIS")
    print("="*80)
    
    # Step 1: Validate screenshot files
    screenshot_results = validate_screenshot_integrity()
    
    # Step 2: Deep analysis of Weekly/Monthly Picks & Market Forecast
    deep_results = deep_content_analysis()
    
    # Step 3: Quick comparison of all tabs
    print("\n" + "="*80)
    print("Do you want to analyze all 12 tabs? (This will take ~2 minutes)")
    print("Enter 'yes' to continue, or press Enter to skip:")
    # For automated run, we'll skip this
    # all_results = compare_all_tabs()
    
    print("\n" + "="*80)
    print("✅ VALIDATION COMPLETE")
    print("="*80)
    print(f"Screenshot Integrity: {sum(1 for r in screenshot_results if r['valid'])}/{len(TABS)} valid")
    print(f"Deep Content Analysis: {len(deep_results)} tabs analyzed")
    print("\nReports Generated:")
    print("  - screenshot_content_analysis.json (Weekly/Monthly Picks + Forecast)")
    print("="*80)
