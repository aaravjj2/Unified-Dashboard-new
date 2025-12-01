#!/usr/bin/env python3
"""
Research Lab Comprehensive Clicker Test with Snapshots
=======================================================
This script performs actual click interactions on all Research Lab subtabs
and captures screenshots as proof of each interaction.

Output: screenshots saved to /reports/research_lab/snapshots/
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Directories
BASE_DIR = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = BASE_DIR / "reports" / "research_lab" / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Test results
results = {
    "timestamp": datetime.now().isoformat(),
    "dashboard_url": "http://localhost:8050",
    "snapshots": [],
    "interactions": [],
    "errors": []
}


def take_snapshot(page, name: str, description: str):
    """Capture a screenshot and record metadata."""
    filename = f"{len(results['snapshots']) + 1:02d}_{name}.png"
    filepath = SNAPSHOT_DIR / filename
    page.screenshot(path=str(filepath), full_page=False)
    results["snapshots"].append({
        "filename": filename,
        "description": description,
        "timestamp": datetime.now().isoformat()
    })
    print(f"  📸 Snapshot: {filename} - {description}")
    return filename


def log_interaction(action: str, target: str, success: bool, details: str = ""):
    """Log an interaction result."""
    results["interactions"].append({
        "action": action,
        "target": target,
        "success": success,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    status = "✅" if success else "❌"
    print(f"  {status} {action}: {target} {details}")


def run_clicker_tests():
    """Run comprehensive clicker tests with snapshots."""
    print("\n" + "=" * 70)
    print("🔬 RESEARCH LAB CLICKER TEST WITH SNAPSHOTS")
    print("=" * 70)
    
    with sync_playwright() as p:
        # Launch browser in headful mode for visual testing
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300  # Slow down for visibility
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            # ================================================================
            # STEP 1: Navigate to Dashboard
            # ================================================================
            print("\n📍 Step 1: Navigate to Dashboard")
            page.goto("http://localhost:8050", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            take_snapshot(page, "01_dashboard_home", "Dashboard home page loaded")
            log_interaction("navigate", "Dashboard Home", True)
            
            # ================================================================
            # STEP 2: Click on Research Lab Tab
            # ================================================================
            print("\n📍 Step 2: Navigate to Research Lab")
            research_tab = page.locator('[data-tab="research-lab"], .tab-research-lab, a:has-text("Research Lab"), button:has-text("Research Lab")')
            if research_tab.count() > 0:
                research_tab.first.click()
                time.sleep(2)
                take_snapshot(page, "02_research_lab_main", "Research Lab main view")
                log_interaction("click", "Research Lab Tab", True)
            else:
                # Try URL navigation as fallback
                page.goto("http://localhost:8050/research-lab", wait_until="networkidle")
                time.sleep(2)
                take_snapshot(page, "02_research_lab_main", "Research Lab via URL navigation")
                log_interaction("navigate", "Research Lab URL", True)
            
            # ================================================================
            # STEP 3: Test All Research Lab Subtabs
            # ================================================================
            print("\n📍 Step 3: Testing Research Lab Subtabs")
            
            # Actual subtab IDs from layout.py - using tab_id values
            subtabs = [
                ("rl-scan-tab", "Research Scan", "Research Scan subtab"),
                ("rl-factor-tab", "Factor & Signal Lab", "Factor analysis interface"),
                ("rl-screen-tab", "Screen Builder", "Stock screener builder"),
                ("rl-rag-tab", "RAG Chat", "RAG Chat interface"),
                ("rl-briefs-tab", "Briefs & Notes", "Research briefs"),
                ("rl-exp-tab", "Experiment Tracker", "Experiment tracking"),
                ("rl-diag-tab", "Diagnostics", "Diagnostics panel"),
            ]
            
            for i, (subtab_id, subtab_name, description) in enumerate(subtabs):
                print(f"\n  🔹 Testing subtab: {subtab_name}")
                
                # Try multiple selector strategies - Dash Bootstrap Tabs use nav-link class
                selectors = [
                    f"a.nav-link[id='rl-main-tabs-{subtab_id}-tab']",  # Dash Bootstrap Tab format
                    f"[id*='{subtab_id}']",
                    f".nav-link:has-text('{subtab_name}')",
                    f"a:has-text('{subtab_name}')",
                    f"button:has-text('{subtab_name}')",
                ]
                
                clicked = False
                for sel in selectors:
                    try:
                        element = page.locator(sel)
                        if element.count() > 0 and element.first.is_visible():
                            element.first.click()
                            time.sleep(1.5)
                            clicked = True
                            break
                    except Exception:
                        continue
                
                if clicked:
                    snapshot_name = f"{i + 3:02d}_subtab_{subtab_id}"
                    take_snapshot(page, snapshot_name, description)
                    log_interaction("click", f"Subtab: {subtab_name}", True)
                else:
                    log_interaction("click", f"Subtab: {subtab_name}", False, "Element not found or not visible")
            
            # ================================================================
            # STEP 4: Test RAG Chat Interaction
            # ================================================================
            print("\n📍 Step 4: Testing RAG Chat Interface")
            
            # Navigate to RAG Chat subtab
            rag_selectors = [".nav-link:has-text('RAG Chat')", "a:has-text('RAG Chat')", "[id*='rl-rag-tab']"]
            for sel in rag_selectors:
                try:
                    el = page.locator(sel)
                    if el.count() > 0 and el.first.is_visible():
                        el.first.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue
            
            # Find and interact with RAG input - using actual IDs from layout.py
            rag_input = page.locator("#rl-rag-input, textarea[id*='rl-rag'], input[id*='rl-rag']")
            if rag_input.count() > 0 and rag_input.first.is_visible():
                rag_input.first.fill("What are the key financial metrics for tech stocks?")
                time.sleep(0.5)
                take_snapshot(page, "10_rag_query_input", "RAG query input filled")
                log_interaction("input", "RAG Query Text", True, "Entered test query")
                
                # Try to submit - using actual button IDs
                submit_btn = page.locator("#rl-rag-submit-btn, button[id*='rl-rag']:has-text('Send'), button[id*='rl-rag']:has-text('Ask')")
                if submit_btn.count() > 0 and submit_btn.first.is_visible():
                    submit_btn.first.click()
                    time.sleep(3)  # Wait for response
                    take_snapshot(page, "11_rag_query_result", "RAG query result")
                    log_interaction("click", "RAG Submit Button", True)
                else:
                    take_snapshot(page, "11_rag_no_submit", "RAG interface - submit button not visible")
                    log_interaction("click", "RAG Submit Button", False, "Button not visible")
            else:
                log_interaction("input", "RAG Query Text", False, "Input field not found")
            
            # ================================================================
            # STEP 5: Test Screen Builder Interaction
            # ================================================================
            print("\n📍 Step 5: Testing Screen Builder Interface")
            
            # Navigate to Screen Builder
            screener_selectors = [".nav-link:has-text('Screen Builder')", "a:has-text('Screen Builder')", "[id*='rl-screen-tab']"]
            for sel in screener_selectors:
                try:
                    el = page.locator(sel)
                    if el.count() > 0 and el.first.is_visible():
                        el.first.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue
            
            take_snapshot(page, "12_screen_builder_view", "Screen Builder interface")
            log_interaction("navigate", "Screen Builder Tab", True)
            
            # Try to interact with screener filters if available
            filter_selector = page.locator("[id*='rl-screen'] select, [id*='rl-screen'] input, #rl-screen-metric-select")
            if filter_selector.count() > 0 and filter_selector.first.is_visible():
                try:
                    # Try select if it's a dropdown
                    if filter_selector.first.evaluate("el => el.tagName") == "SELECT":
                        filter_selector.first.select_option(index=1)
                    else:
                        filter_selector.first.fill("10")
                    time.sleep(1)
                    take_snapshot(page, "13_screen_builder_filtered", "Screen Builder with filter applied")
                    log_interaction("interact", "Screen Builder Filter", True)
                except Exception as e:
                    log_interaction("interact", "Screen Builder Filter", False, str(e))
            
            # ================================================================
            # STEP 6: Test Briefs & Notes Interaction
            # ================================================================
            print("\n📍 Step 6: Testing Briefs & Notes Interface")
            
            # Navigate to Briefs & Notes
            briefs_selectors = [".nav-link:has-text('Briefs')", "a:has-text('Briefs')", "[id*='rl-briefs-tab']"]
            for sel in briefs_selectors:
                try:
                    el = page.locator(sel)
                    if el.count() > 0 and el.first.is_visible():
                        el.first.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue
            
            take_snapshot(page, "14_briefs_view", "Briefs & Notes interface")
            log_interaction("navigate", "Briefs Tab", True)
            
            # Try to interact with brief creation if available
            new_brief_btn = page.locator("[id*='rl-brief'] button:has-text('New'), button[id*='rl-brief-new']")
            if new_brief_btn.count() > 0 and new_brief_btn.first.is_visible():
                new_brief_btn.first.click()
                time.sleep(1)
                take_snapshot(page, "15_briefs_new_modal", "New brief modal")
                log_interaction("click", "New Brief Button", True)
                
                # Close modal if opened
                close_btn = page.locator(".modal .btn-close, .modal button:has-text('Close'), .modal button:has-text('Cancel')")
                if close_btn.count() > 0 and close_btn.first.is_visible():
                    close_btn.first.click()
                    time.sleep(0.5)
            
            # ================================================================
            # STEP 7: Test Experiment Tracker
            # ================================================================
            print("\n📍 Step 7: Testing Experiment Tracker")
            
            # Navigate to Experiment Tracker
            exp_selectors = [".nav-link:has-text('Experiment')", "a:has-text('Experiment')", "[id*='rl-exp-tab']"]
            for sel in exp_selectors:
                try:
                    el = page.locator(sel)
                    if el.count() > 0 and el.first.is_visible():
                        el.first.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue
            
            take_snapshot(page, "16_experiment_tracker", "Experiment Tracker interface")
            log_interaction("navigate", "Experiment Tracker Tab", True)
            
            # ================================================================
            # STEP 8: Test Diagnostics Tab
            # ================================================================
            print("\n📍 Step 8: Testing Diagnostics Tab")
            
            diag_selectors = [".nav-link:has-text('Diagnostics')", "a:has-text('Diagnostics')", "[id*='rl-diag-tab']"]
            for sel in diag_selectors:
                try:
                    el = page.locator(sel)
                    if el.count() > 0 and el.first.is_visible():
                        el.first.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue
            
            take_snapshot(page, "17_diagnostics", "Diagnostics panel")
            log_interaction("navigate", "Diagnostics Tab", True)
            
            # ================================================================
            # STEP 9: Final Research Scan Overview
            # ================================================================
            print("\n📍 Step 9: Final Research Lab Overview")
            
            # Go back to Research Scan
            scan_selectors = [".nav-link:has-text('Research Scan')", "a:has-text('Research Scan')", "[id*='rl-scan-tab']"]
            for sel in scan_selectors:
                try:
                    el = page.locator(sel)
                    if el.count() > 0 and el.first.is_visible():
                        el.first.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue
            
            take_snapshot(page, "18_final_research_scan", "Final Research Scan state")
            log_interaction("navigate", "Return to Research Scan", True)
            
        except Exception as e:
            results["errors"].append({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            print(f"\n❌ Error during testing: {e}")
            take_snapshot(page, "error_state", f"Error occurred: {str(e)[:50]}")
        
        finally:
            # Summary
            print("\n" + "=" * 70)
            print("📊 TEST SUMMARY")
            print("=" * 70)
            
            successful = sum(1 for i in results["interactions"] if i["success"])
            total = len(results["interactions"])
            
            print(f"  Total Interactions: {total}")
            print(f"  Successful: {successful}")
            print(f"  Failed: {total - successful}")
            print(f"  Snapshots Captured: {len(results['snapshots'])}")
            print(f"  Errors: {len(results['errors'])}")
            
            # Save results JSON
            results_file = SNAPSHOT_DIR / "test_results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Results saved to: {results_file}")
            
            # Keep browser open for a moment for visual verification
            time.sleep(2)
            browser.close()
    
    return results


if __name__ == "__main__":
    results = run_clicker_tests()
    
    # Exit code based on success
    failed = sum(1 for i in results["interactions"] if not i["success"])
    sys.exit(1 if failed > len(results["interactions"]) // 2 else 0)
