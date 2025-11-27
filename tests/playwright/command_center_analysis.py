#!/usr/bin/env python3
"""
Command Center UI/UX Analysis with Snapshots
==============================================
Captures the current state and analyzes usability issues.
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
SNAPSHOT_DIR = BASE_DIR / "reports" / "command_center" / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

results = {
    "timestamp": datetime.now().isoformat(),
    "dashboard_url": "http://localhost:8050",
    "snapshots": [],
    "ui_analysis": {},
    "ux_issues": [],
    "recommendations": []
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


def analyze_command_center():
    """Analyze Command Center UI/UX."""
    print("\n" + "=" * 70)
    print("🎯 COMMAND CENTER UI/UX ANALYSIS")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # Navigate to dashboard
            print("\n📍 Step 1: Navigate to Dashboard")
            page.goto("http://localhost:8050", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            take_snapshot(page, "01_dashboard_home", "Dashboard home page")
            
            # Navigate to Command Center
            print("\n📍 Step 2: Navigate to Command Center")
            cc_selectors = [
                "a:has-text('Command Center')",
                "button:has-text('Command Center')",
                ".nav-link:has-text('Command Center')",
                "[data-tab='command-center']"
            ]
            
            clicked = False
            for sel in cc_selectors:
                try:
                    el = page.locator(sel)
                    if el.count() > 0 and el.first.is_visible():
                        el.first.click()
                        time.sleep(2)
                        clicked = True
                        break
                except Exception:
                    continue
            
            if clicked:
                take_snapshot(page, "02_command_center_initial", "Command Center initial state")
                print("  ✅ Navigated to Command Center")
            else:
                print("  ⚠️ Command Center tab not found, trying URL navigation")
                page.goto("http://localhost:8050/command-center", wait_until="networkidle")
                time.sleep(2)
                take_snapshot(page, "02_command_center_url", "Command Center via URL")
            
            # Analyze visible components
            print("\n📍 Step 3: Analyzing UI Components")
            
            # Check header
            header = page.locator("#cc-header, h2:has-text('Command Center')")
            results["ui_analysis"]["header_visible"] = header.count() > 0 and header.first.is_visible() if header.count() > 0 else False
            
            # Check cards
            cards = page.locator(".card")
            results["ui_analysis"]["card_count"] = cards.count()
            print(f"  📦 Cards found: {cards.count()}")
            
            # Check buttons
            buttons = page.locator("button")
            results["ui_analysis"]["button_count"] = buttons.count()
            print(f"  🔘 Buttons found: {buttons.count()}")
            
            # Check for loading states
            loading_elements = page.locator(":has-text('Loading'), :has-text('loading')")
            results["ui_analysis"]["loading_states"] = loading_elements.count()
            print(f"  ⏳ Loading states: {loading_elements.count()}")
            
            # Check for "unavailable" messages
            unavailable = page.locator(":has-text('unavailable'), :has-text('Unavailable')")
            results["ui_analysis"]["unavailable_states"] = unavailable.count()
            print(f"  ❌ Unavailable states: {unavailable.count()}")
            
            # Test button interactions
            print("\n📍 Step 4: Testing Button Interactions")
            
            # Test Run Smoke Tests button
            smoke_btn = page.locator("#cc-run-smoke-btn")
            if smoke_btn.count() > 0 and smoke_btn.first.is_visible():
                smoke_btn.first.click()
                time.sleep(2)
                take_snapshot(page, "03_smoke_test_clicked", "After smoke test button click")
                print("  ✅ Smoke Tests button clicked")
            
            # Test Refresh button
            refresh_btn = page.locator("#cc-refresh-btn")
            if refresh_btn.count() > 0 and refresh_btn.first.is_visible():
                refresh_btn.first.click()
                time.sleep(2)
                take_snapshot(page, "04_refresh_clicked", "After refresh button click")
                print("  ✅ Refresh button clicked")
            
            # Test chat interaction
            print("\n📍 Step 5: Testing Chat Widget")
            chat_input = page.locator("#cc-chat-input")
            if chat_input.count() > 0 and chat_input.first.is_visible():
                chat_input.first.fill("What is my portfolio value?")
                time.sleep(0.5)
                
                chat_send = page.locator("#cc-chat-send")
                if chat_send.count() > 0:
                    chat_send.first.click()
                    time.sleep(3)
                    take_snapshot(page, "05_chat_response", "Chat widget response")
                    print("  ✅ Chat interaction tested")
            
            # Scroll to bottom for full view
            print("\n📍 Step 6: Full Page Analysis")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            take_snapshot(page, "06_full_page_bottom", "Command Center bottom section")
            
            # Scroll back to top
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)
            take_snapshot(page, "07_final_state", "Final Command Center state")
            
            # Identify UX issues based on analysis
            print("\n📍 Step 7: Identifying UX Issues")
            
            # Issue 1: Check for proper spacing
            if results["ui_analysis"]["card_count"] > 4:
                results["ux_issues"].append({
                    "severity": "medium",
                    "issue": "Dense card layout may cause visual overload",
                    "recommendation": "Consider grouping related cards or using tabs"
                })
            
            # Issue 2: Loading states
            if results["ui_analysis"]["loading_states"] > 2:
                results["ux_issues"].append({
                    "severity": "high",
                    "issue": "Multiple loading states visible - indicates slow data loading",
                    "recommendation": "Implement skeleton loaders or lazy loading"
                })
            
            # Issue 3: Unavailable services
            if results["ui_analysis"]["unavailable_states"] > 0:
                results["ux_issues"].append({
                    "severity": "high",
                    "issue": "Services shown as unavailable",
                    "recommendation": "Add graceful fallbacks or remove unavailable features"
                })
            
            # Standard recommendations
            results["recommendations"] = [
                "Add visual hierarchy with section headers",
                "Implement drag-and-drop widget reordering",
                "Add collapsible sections for less-used features",
                "Improve color contrast for status indicators",
                "Add keyboard shortcuts for common actions",
                "Implement real-time data streaming indicators",
                "Add quick action buttons for common workflows"
            ]
            
            for issue in results["ux_issues"]:
                print(f"  ⚠️ [{issue['severity'].upper()}] {issue['issue']}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            take_snapshot(page, "error_state", f"Error occurred: {str(e)[:50]}")
        
        finally:
            # Save results
            print("\n" + "=" * 70)
            print("📊 ANALYSIS SUMMARY")
            print("=" * 70)
            
            print(f"  Snapshots captured: {len(results['snapshots'])}")
            print(f"  UI components analyzed: {len(results['ui_analysis'])}")
            print(f"  UX issues found: {len(results['ux_issues'])}")
            print(f"  Recommendations: {len(results['recommendations'])}")
            
            # Save JSON
            results_file = SNAPSHOT_DIR / "analysis_results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Results saved to: {results_file}")
            
            time.sleep(2)
            browser.close()
    
    return results


if __name__ == "__main__":
    results = analyze_command_center()
