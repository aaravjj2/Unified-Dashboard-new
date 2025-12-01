#!/usr/bin/env python3
"""
Analyze Options Lab actual visible content and errors
"""

import os
import time
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://127.0.0.1:8051"
SCREENSHOT_DIR = "/tmp/options_lab_analysis"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

SUBTABS = [
    ("options-chain-tab", "Chain Viewer"),
    ("options-greeks-tab", "Greeks Calculator"), 
    ("options-vol-tab", "IV Surface"),
    ("options-flow-tab", "Flow Scanner"),
    ("options-iv-tab", "IV Analysis"),
    ("options-strategy-tab", "Strategy Builder"),
    ("options-manual-tab", "Manual Trade"),
    ("options-portfolio-tab", "Portfolio Greeks"),
    ("options-screener-tab", "Screener"),
    ("options-ai-tab", "AI Recommendations"),
    ("options-earnings-tab", "Earnings Calendar"),
    ("options-backtest-tab", "Backtester"),
]

def analyze_subtabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=" * 70)
        print("OPTIONS LAB CONTENT ANALYSIS")
        print("=" * 70)
        
        # Load dashboard
        page.goto(DASHBOARD_URL, timeout=60000)
        time.sleep(5)
        
        # Navigate to Options Lab
        page.locator("#tab-options_lab").click()
        time.sleep(2)
        
        # Load mock data
        page.locator("#options-mock-btn").click()
        time.sleep(3)
        print("✓ Mock data loaded\n")
        
        issues = []
        
        for tab_id, tab_name in SUBTABS:
            print(f"\n{'='*60}")
            print(f"ANALYZING: {tab_name}")
            print("="*60)
            
            try:
                page.locator(f"#{tab_id}").click()
                time.sleep(2)
                
                # Get visible text content
                visible_text = page.locator("body").inner_text()
                
                # Check for specific issues
                tab_issues = []
                
                # 1. Check for "webhook not configured"
                if "webhook not configured" in visible_text.lower():
                    tab_issues.append("webhook not configured")
                    
                # 2. Check for error messages
                if "error" in visible_text.lower() and "no error" not in visible_text.lower():
                    # Find actual error text
                    error_elements = page.locator(".alert-danger, .text-danger").all()
                    for el in error_elements:
                        try:
                            txt = el.inner_text()[:100]
                            if txt.strip():
                                tab_issues.append(f"Error: {txt}")
                        except:
                            pass
                
                # 3. Check for "exception" or "traceback"  
                if "exception" in visible_text.lower() or "traceback" in visible_text.lower():
                    tab_issues.append("Exception/Traceback detected")
                
                # 4. Check for empty results placeholders
                if "will be displayed here" in visible_text:
                    tab_issues.append("Placeholder text still showing")
                    
                # 5. Check for "--" values that should have data
                dash_elements = page.locator("h4:text('--')").count()
                if dash_elements > 3:
                    tab_issues.append(f"{dash_elements} empty value indicators (--)")
                
                # Take screenshot
                page.screenshot(path=f"{SCREENSHOT_DIR}/{tab_id}.png")
                
                if tab_issues:
                    print(f"  ⚠️ ISSUES FOUND:")
                    for issue in tab_issues:
                        print(f"     - {issue}")
                    issues.append((tab_name, tab_issues))
                else:
                    print(f"  ✓ No obvious issues")
                    
            except Exception as e:
                print(f"  ✗ Error analyzing: {e}")
                issues.append((tab_name, [f"Analysis error: {e}"]))
        
        # Summary
        print("\n\n" + "=" * 70)
        print("ANALYSIS SUMMARY")
        print("=" * 70)
        
        if issues:
            print(f"\n⚠️ {len(issues)} subtabs have issues:\n")
            for tab_name, tab_issues in issues:
                print(f"  {tab_name}:")
                for issue in tab_issues:
                    print(f"    - {issue}")
        else:
            print("\n✓ All subtabs look good!")
        
        print(f"\nScreenshots: {SCREENSHOT_DIR}")
        
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    analyze_subtabs()
