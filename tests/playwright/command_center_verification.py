#!/usr/bin/env python3
"""
Command Center UI/UX Verification Test
=======================================
Tests the improved Command Center with snapshots as proof.
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# Directories
BASE_DIR = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = BASE_DIR / "reports" / "command_center" / "verification"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

results = {
    "timestamp": datetime.now().isoformat(),
    "dashboard_url": "http://localhost:8050",
    "snapshots": [],
    "improvements_verified": [],
    "interactions": []
}


def take_snapshot(page, name: str, description: str):
    """Capture a screenshot."""
    filename = f"{len(results['snapshots']) + 1:02d}_{name}.png"
    filepath = SNAPSHOT_DIR / filename
    page.screenshot(path=str(filepath), full_page=True)
    results["snapshots"].append({
        "filename": filename,
        "description": description,
        "timestamp": datetime.now().isoformat()
    })
    print(f"  📸 Snapshot: {filename}")
    return filename


def verify_improvements():
    """Verify Command Center UI/UX improvements."""
    print("\n" + "=" * 70)
    print("🎯 COMMAND CENTER UI/UX VERIFICATION")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=100)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # Navigate to dashboard
            print("\n📍 Step 1: Navigate to Dashboard")
            page.goto("http://localhost:8050", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            take_snapshot(page, "01_command_center_improved", "Improved Command Center layout")
            
            # Verify Quick Stats Bar
            print("\n📍 Step 2: Verify Quick Stats Bar")
            quick_stats = page.locator("#home-portfolio-value-quick, #home-pnl-quick, #home-market-status-quick")
            if quick_stats.count() >= 3:
                results["improvements_verified"].append({
                    "feature": "Quick Stats Bar",
                    "status": "verified",
                    "details": "All quick stats elements present"
                })
                print("  ✅ Quick Stats Bar: VERIFIED")
            else:
                results["improvements_verified"].append({
                    "feature": "Quick Stats Bar",
                    "status": "partial",
                    "details": f"Found {quick_stats.count()} of 3 expected elements"
                })
                print(f"  ⚠️ Quick Stats Bar: Partial ({quick_stats.count()}/3)")
            
            # Verify Section Headers
            print("\n📍 Step 3: Verify Section Headers")
            section_headers = page.locator("h5:has-text('Portfolio'), h5:has-text('Market'), h5:has-text('Watchlist'), h5:has-text('Analytics')")
            header_count = section_headers.count()
            if header_count >= 3:
                results["improvements_verified"].append({
                    "feature": "Section Headers",
                    "status": "verified",
                    "details": f"Found {header_count} section headers"
                })
                print(f"  ✅ Section Headers: VERIFIED ({header_count} found)")
            else:
                print(f"  ⚠️ Section Headers: {header_count} found")
            
            # Verify AI Morning Briefing
            print("\n📍 Step 4: Verify AI Morning Briefing")
            briefing = page.locator("#morning-briefing-content, :has-text('Morning Briefing')")
            if briefing.count() > 0:
                results["improvements_verified"].append({
                    "feature": "AI Morning Briefing",
                    "status": "verified",
                    "details": "Briefing widget present"
                })
                print("  ✅ AI Morning Briefing: VERIFIED")
            
            # Scroll to see all sections
            print("\n📍 Step 5: Capture Full Page Sections")
            page.evaluate("window.scrollTo(0, 500)")
            time.sleep(1)
            take_snapshot(page, "02_portfolio_actions", "Portfolio & Actions section")
            
            page.evaluate("window.scrollTo(0, 1200)")
            time.sleep(1)
            take_snapshot(page, "03_market_data", "Market Data section")
            
            page.evaluate("window.scrollTo(0, 2000)")
            time.sleep(1)
            take_snapshot(page, "04_watchlist_trading", "Watchlist & Trading section")
            
            page.evaluate("window.scrollTo(0, 2800)")
            time.sleep(1)
            take_snapshot(page, "05_analytics_insights", "Analytics & Insights section")
            
            # Test Action Center tabs
            print("\n📍 Step 6: Test Action Center Interactions")
            
            # Click Alerts tab
            alerts_tab = page.locator("a:has-text('Alerts'), button:has-text('Alerts')")
            if alerts_tab.count() > 0:
                alerts_tab.first.click()
                time.sleep(0.5)
                results["interactions"].append({"action": "click", "target": "Alerts Tab", "success": True})
                print("  ✅ Alerts tab clicked")
            
            # Click Tasks tab
            tasks_tab = page.locator("a:has-text('Tasks'), button:has-text('Tasks')")
            if tasks_tab.count() > 0:
                tasks_tab.first.click()
                time.sleep(0.5)
                results["interactions"].append({"action": "click", "target": "Tasks Tab", "success": True})
                print("  ✅ Tasks tab clicked")
            
            # Click Actions tab
            actions_tab = page.locator("a:has-text('Actions'), button:has-text('Actions')")
            if actions_tab.count() > 0:
                actions_tab.first.click()
                time.sleep(0.5)
                take_snapshot(page, "06_action_center_actions", "Action Center - Actions tab")
                results["interactions"].append({"action": "click", "target": "Actions Tab", "success": True})
                print("  ✅ Actions tab clicked")
            
            # Test Scan Market button
            print("\n📍 Step 7: Test Quick Action Buttons")
            scan_btn = page.locator("#home-scan-market, button:has-text('Scan Market')")
            if scan_btn.count() > 0 and scan_btn.first.is_visible():
                scan_btn.first.click()
                time.sleep(1)
                results["interactions"].append({"action": "click", "target": "Scan Market", "success": True})
                print("  ✅ Scan Market button clicked")
                take_snapshot(page, "07_scan_market_triggered", "Scan Market action triggered")
            
            # Return to top
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            take_snapshot(page, "08_final_state", "Final Command Center state")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            take_snapshot(page, "error_state", f"Error: {str(e)[:50]}")
        
        finally:
            # Summary
            print("\n" + "=" * 70)
            print("📊 VERIFICATION SUMMARY")
            print("=" * 70)
            
            print(f"  Snapshots captured: {len(results['snapshots'])}")
            print(f"  Improvements verified: {len(results['improvements_verified'])}")
            print(f"  Interactions tested: {len(results['interactions'])}")
            
            for imp in results["improvements_verified"]:
                status = "✅" if imp["status"] == "verified" else "⚠️"
                print(f"  {status} {imp['feature']}: {imp['status']}")
            
            # Save results
            results_file = SNAPSHOT_DIR / "verification_results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Results saved to: {results_file}")
            
            time.sleep(2)
            browser.close()
    
    return results


if __name__ == "__main__":
    results = verify_improvements()
