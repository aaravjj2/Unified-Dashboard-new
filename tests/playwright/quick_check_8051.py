#!/usr/bin/env python3
"""Quick check of dashboard on port 8051 to verify Command Center and Research Lab."""

import sys
from playwright.sync_api import sync_playwright

def quick_check():
    print("\n" + "=" * 60)
    print("🔍 QUICK CHECK: Dashboard on Port 8051")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1920, "height": 1080}).new_page()
        
        try:
            # Navigate to dashboard
            page.goto("http://localhost:8051", wait_until="networkidle", timeout=30000)
            
            # Check Command Center
            print("\n📍 Command Center Check:")
            
            # Look for new features
            section_headers = page.locator("h5:has-text('Portfolio'), h5:has-text('Market'), h5:has-text('Watchlist'), h5:has-text('Analytics')")
            print(f"  Section headers found: {section_headers.count()}")
            
            quick_stats = page.locator("#home-portfolio-value-quick, #home-pnl-quick, #home-market-status-quick")
            print(f"  Quick stats bar elements: {quick_stats.count()}")
            
            title = page.locator("h3:has-text('Command Center')")
            print(f"  'Command Center' title found: {title.count() > 0}")
            
            # Check Research Lab
            print("\n📍 Research Lab Check:")
            
            # Click Research Lab tab
            research_tab = page.locator("a:has-text('Research Lab'), button:has-text('Research Lab'), .nav-link:has-text('Research Lab')")
            if research_tab.count() > 0:
                research_tab.first.click()
                page.wait_for_timeout(2000)
                
                # Check for NEW subtabs (7 tabs from research_lab_pkg)
                new_subtabs = page.locator(".nav-link:has-text('Research Scan'), .nav-link:has-text('Factor'), .nav-link:has-text('Screen Builder'), .nav-link:has-text('RAG Chat')")
                
                # Check for LEGACY subtabs
                legacy_subtabs = page.locator(".nav-link:has-text('Overview'), .nav-link:has-text('SEC Filings'), .nav-link:has-text('Screener')")
                
                if new_subtabs.count() >= 2:
                    print(f"  ✅ NEW Research Lab package detected! ({new_subtabs.count()} new subtabs)")
                elif legacy_subtabs.count() >= 2:
                    print(f"  ⚠️ LEGACY Research Lab detected ({legacy_subtabs.count()} legacy subtabs)")
                    print("     → Run with USE_NEW_RESEARCH_LAB=1 to enable new package")
                else:
                    print(f"  ❓ Unknown Research Lab version")
            else:
                print("  ❌ Research Lab tab not found")
            
            # Summary
            print("\n" + "=" * 60)
            print("📊 SUMMARY")
            print("=" * 60)
            
            cc_improved = section_headers.count() >= 3 or quick_stats.count() >= 2
            print(f"  Command Center UI improvements: {'✅ Applied' if cc_improved else '⚠️ Not detected'}")
            
            browser.close()
            return 0
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            browser.close()
            return 1

if __name__ == "__main__":
    sys.exit(quick_check())
