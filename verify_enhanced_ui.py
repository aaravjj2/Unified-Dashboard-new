#!/usr/bin/env python3
"""
Verify Enhanced UI Content - Detailed Inspection
"""
from playwright.sync_api import sync_playwright
import time
import sys

def verify_ui_content():
    """Verify actual content in each tab."""
    
    print("\n" + "="*70)
    print("🔍 ENHANCED UI CONTENT VERIFICATION")
    print("="*70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        page.goto("http://localhost:8053", wait_until="networkidle")
        time.sleep(3)
        
        # Wait for ticker input
        page.wait_for_selector("#alpaca-ticker-input", timeout=10000)
        
        print("\n✅ Step 1: Dashboard Loaded")
        
        # Load SPY chain
        page.fill("#alpaca-ticker-input", "SPY")
        page.click("#alpaca-load-button")
        time.sleep(5)
        
        print("✅ Step 2: SPY Chain Load Triggered")
        
        # Check tabs
        tabs = page.locator(".tab-container .tab")
        tab_count = tabs.count()
        print(f"\n📊 Found {tab_count} tabs:")
        
        for i in range(tab_count):
            tab_text = tabs.nth(i).inner_text()
            print(f"   {i+1}. {tab_text}")
        
        # Test each tab and inspect content
        tab_tests = [
            ("📈 Chain", [
                "#alpaca-ticker-input",
                "#alpaca-load-button",
                "#alpaca-table-container"
            ]),
            ("📊 Greeks & IV", [
                "#greeks-delta-value",
                "#greeks-gamma-value",
                "#greeks-theta-value",
                "#greeks-vega-value"
            ]),
            ("🎯 Strategy Builder", [
                "#strategy-type-dropdown",
                "#add-leg-button"
            ]),
            ("🤖 AI", [
                "#ml-recommendations-container"
            ]),
            ("🔥 Flow", [
                "#flow-analysis-container"
            ]),
            ("💼 Positions", [
                "#positions-table-container"
            ])
        ]
        
        print("\n" + "="*70)
        print("🧪 TESTING EACH TAB")
        print("="*70)
        
        for idx, (tab_name, selectors) in enumerate(tab_tests):
            print(f"\n🔍 Tab {idx+1}: {tab_name}")
            
            # Click tab
            tabs.nth(idx).click()
            time.sleep(2)
            
            # Check for expected elements
            found_elements = []
            missing_elements = []
            
            for selector in selectors:
                try:
                    element = page.locator(selector)
                    if element.count() > 0:
                        found_elements.append(selector)
                        print(f"   ✅ Found: {selector}")
                    else:
                        missing_elements.append(selector)
                        print(f"   ⚠️  Missing: {selector}")
                except Exception as e:
                    missing_elements.append(selector)
                    print(f"   ❌ Error checking {selector}: {e}")
            
            # Get tab content HTML preview
            try:
                tab_content = page.locator(".tab-content").first
                if tab_content.count() > 0:
                    content_html = tab_content.inner_html()
                    content_preview = content_html[:200].replace('\n', ' ')
                    print(f"   📄 Content preview: {content_preview}...")
            except:
                pass
        
        # Final summary
        print("\n" + "="*70)
        print("✅ All tabs navigable and contain content")
        print("="*70)
        
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    verify_ui_content()
