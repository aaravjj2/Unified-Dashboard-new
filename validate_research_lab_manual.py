#!/usr/bin/env python3
"""
Quick Research Lab Validation Script
====================================

Manually checks if all Research Lab subtabs are accessible
and have their input elements properly defined.
"""

import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8050"

def validate_research_lab():
    """Validate Research Lab subtabs."""
    print("🔬 Research Lab Validation Script")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible browser
        page = browser.new_page()
        
        # Navigate to dashboard
        print("\n1️⃣ Loading dashboard...")
        page.goto(BASE_URL, timeout=60000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        print("   ✅ Dashboard loaded")
        
        # Open Research Lab
        print("\n2️⃣ Opening Research Lab...")
        research_tab = page.locator("text=🔬 Research Lab").first
        if research_tab.count() == 0:
            print("   ❌ Research Lab tab not found!")
            browser.close()
            return False
        
        research_tab.click()
        page.wait_for_timeout(2000)
        print("   ✅ Research Lab opened")
        
        # Check each subtab
        subtabs = [
            {
                "name": "Market Scan",
                "label": "📊 Market Scan",
                "tab_id": "market-scan",
                "test_input": "#market-scan-tickers",
            },
            {
                "name": "Factor Analysis",
                "label": "📈 Factor Analysis",
                "tab_id": "factor-analysis",
                "test_input": "#factor-analysis-ticker",
            },
            {
                "name": "Correlation Explorer",
                "label": "🔗 Correlation Explorer",
                "tab_id": "correlation-explorer",
                "test_input": "#correlation-tickers",
            },
            {
                "name": "Strategy Backtest",
                "label": "⚙️ Strategy Backtest",
                "tab_id": "strategy-backtest",
                "test_input": "#backtest-ticker",
            },
            {
                "name": "Research Notes",
                "label": "📝 Research Notes",
                "tab_id": "research-notes",
                "test_input": "#research-notes-editor",
            },
        ]
        
        results = []
        
        for i, subtab in enumerate(subtabs, 1):
            print(f"\n{i}️⃣ Checking {subtab['name']}...")
            
            # Click subtab
            tab_locator = page.locator(f"text={subtab['label']}").first
            if tab_locator.count() == 0:
                print(f"   ❌ {subtab['name']} tab not found")
                results.append(("FAIL", subtab['name'], "Tab not found"))
                continue
            
            tab_locator.click()
            page.wait_for_timeout(1500)
            print(f"   ✅ {subtab['name']} tab clicked")
            
            # Check for test input
            input_locator = page.locator(subtab['test_input']).first
            if input_locator.count() == 0:
                print(f"   ⚠️ Input {subtab['test_input']} not found")
                results.append(("WARN", subtab['name'], f"Input {subtab['test_input']} not found"))
            else:
                # Check if visible
                try:
                    is_visible = input_locator.is_visible()
                    if is_visible:
                        print(f"   ✅ Input {subtab['test_input']} is visible")
                        results.append(("PASS", subtab['name'], "All checks passed"))
                    else:
                        print(f"   ⚠️ Input {subtab['test_input']} exists but NOT visible")
                        results.append(("WARN", subtab['name'], f"Input exists but hidden"))
                except Exception as e:
                    print(f"   ❌ Error checking visibility: {e}")
                    results.append(("FAIL", subtab['name'], str(e)))
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in results if r[0] == "PASS")
        warned = sum(1 for r in results if r[0] == "WARN")
        failed = sum(1 for r in results if r[0] == "FAIL")
        
        for status, name, detail in results:
            icon = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
            print(f"{icon} {name:25s} {status:6s} - {detail}")
        
        print(f"\nTotal: {passed} passed, {warned} warnings, {failed} failed")
        
        # Keep browser open for manual inspection
        print("\n👀 Browser will stay open for 30 seconds for manual inspection...")
        print("   Press Ctrl+C to close immediately")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n   Closing browser...")
        
        browser.close()
        
        return failed == 0

if __name__ == "__main__":
    try:
        success = validate_research_lab()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
