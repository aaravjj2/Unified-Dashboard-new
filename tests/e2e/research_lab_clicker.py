#!/usr/bin/env python3
"""E2E clicker test for Research Lab subtabs using Playwright (non-headless).

This script launches Chromium (non-headless), navigates to the dashboard at
`http://localhost:8050` by default (override via `DASHBOARD_URL`) and clicks
Research Lab subtabs, taking element-level screenshots of important buttons.

Usage:
  python tests/e2e/research_lab_clicker.py

Note: requires Playwright Python package and installed browsers. To install:
  pip install playwright
  playwright install chromium
"""
import sys
print("DEBUG: Script started", file=sys.stderr)
from playwright.sync_api import sync_playwright
import os
import time
from pathlib import Path

print("DEBUG: Imports complete", file=sys.stderr)

URL = os.getenv('DASHBOARD_URL', 'http://localhost:8050')
OUT_DIR = Path('reports/research_lab_fix/artifacts/e2e_snapshots')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def snapshot_element(page, selector, out_name):
    el = page.query_selector(selector)
    if not el:
        print(f"Selector not found: {selector}")
        return False
    path = OUT_DIR / out_name
    el.screenshot(path=str(path))
    print(f"Wrote snapshot: {path}")
    return True


def main():
    print(f"Opening dashboard at {URL} (Chromium, non-headless)")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        page.set_default_timeout(15000)

        # Subscribe to console/network events
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"BROWSER ERROR: {exc}"))
        page.on("requestfailed", lambda req: print(f"NETWORK FAIL: {req.url} - {req.failure}"))
        
        try:
            page.goto(URL)
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"Failed to load dashboard: {e}")
            browser.close()
            return

        # 1. Navigate to Research Lab
        print("Step 1: Navigating to Research Lab tab...")
        try:
            # Try clicking the top-level tab. Adjust selector if needed based on actual layout.
            # Assuming standard Dash Bootstrap Components Tabs, usually 'a.nav-link' with text.
            page.click("a.nav-link:has-text('Research Lab')", timeout=5000)
            time.sleep(1) # Animation wait
        except Exception as e:
            print(f"Could not click 'Research Lab' tab (might be already active or different selector): {e}")

        # Wait for the main container of Research Lab
        try:
            page.wait_for_selector('#research-lab-tabs', state='visible', timeout=10000)
            snapshot_element(page, 'body', '01_research_lab_loaded.png')
            print("✓ Research Lab loaded")
        except Exception as e:
            print("Timed out waiting for #research-lab-tabs:", e)
            browser.close()
            return

        # 2. Test "Load Demo Brief" Button
        print("Step 2: Testing 'Load Demo Brief'...")
        try:
            # Check if list is empty initially or not, but we'll just click load
            page.click('#rl-load-demo-btn')
            
            # Check for error alert
            time.sleep(1)
            if page.is_visible('#rl-alert'):
                alert_class = page.get_attribute('#rl-alert', 'class') or ''
                if "danger" in alert_class:
                     print(f"ALERT VISIBLE: {page.inner_text('#rl-alert')}")
                     snapshot_element(page, '#rl-alert', '02_error_alert.png')

            # Wait for a brief card to appear in the list
            page.wait_for_selector('.card-title:has-text("Demo Research Brief")', timeout=5000)
            snapshot_element(page, '#rl-brief-list', '02_demo_brief_loaded.png')
            print("✓ Demo brief loaded and visible")
        except Exception as e:
            print(f"Failed 'Load Demo Brief' test: {e}")
            snapshot_element(page, 'body', '02_fail_state.png')

        # 3. Test "Create New Brief" Modal
        print("Step 3: Testing 'Create New Brief' modal...")
        try:
            page.click('#rl-brief-create-btn')
            page.wait_for_selector('#rl-brief-modal', state='visible', timeout=3000)
            snapshot_element(page, '#rl-brief-modal .modal-content', '03_create_modal_open.png')
            
            # Fill form
            page.fill('#rl-brief-title-input', 'E2E Test Brief')
            page.fill('#rl-brief-summary-input', 'Created via Playwright')
            page.fill('#rl-brief-tags-input', 'e2e, test, automation')
            
            # Save
            page.click('#rl-brief-save-btn')
            # Wait for modal to close
            page.wait_for_selector('#rl-brief-modal', state='hidden', timeout=3000)
            
            # Verify new brief in list
            page.wait_for_selector('.card-title:has-text("E2E Test Brief")', timeout=5000)
            snapshot_element(page, '#rl-brief-list', '04_new_brief_created.png')
            print("✓ New brief created and visible")
        except Exception as e:
            print(f"Failed 'Create New Brief' test: {e}")
            snapshot_element(page, 'body', '04_fail_state.png')

        # 4. Test Subtab Navigation & Content
        print("Step 4: Testing Subtabs...")
        subtabs = ['Market Scan', 'Factor Analysis', 'Strategy Backtest']
        for tab_name in subtabs:
            try:
                print(f"  - Clicking '{tab_name}'...")
                page.click(f"#research-lab-tabs a.nav-link:has-text('{tab_name}')")
                time.sleep(0.5) # Wait for render
                
                # Take snapshot of the content area
                safe_name = tab_name.lower().replace(' ', '_')
                snapshot_element(page, '#research-lab-content', f'05_subtab_{safe_name}.png')
                
                # Specific interactions per tab
                if tab_name == 'Market Scan':
                    # Run the scan
                    if page.is_visible('#market-scan-run-button'):
                        page.click('#market-scan-run-button')
                        # Just snapshot after click to see if anything happened (mock might be fast)
                        time.sleep(0.5)
                        snapshot_element(page, '#research-lab-content', '06_market_scan_run.png')
            except Exception as e:
                print(f"  x Failed subtab '{tab_name}': {e}")

        # 5. Test Analysis Buttons (Screen/Backtest) on a selected brief
        print("Step 5: Testing Analysis Buttons...")
        try:
            # Select the Demo Brief first
            page.click('.card-title:has-text("Demo Research Brief")')
            time.sleep(0.5)
            
            # Check if detail panel updated
            if page.is_visible('h4:has-text("Demo Research Brief")'):
                print("✓ Brief selected")
                snapshot_element(page, '#rl-detail-panel', '07_brief_detail_view.png')
                
                # Run Screen
                print("  - Running Screen...")
                page.click('#rl-screen-run-btn')
                # Wait for results (look for a table or specific result class)
                # Assuming components.render_screen_results produces a table or div
                page.wait_for_selector('#rl-analysis-results table', timeout=10000) 
                snapshot_element(page, '#rl-analysis-results', '08_screen_results.png')
                print("✓ Screen results visible")
                
                # Run Backtest
                print("  - Running Backtest...")
                page.click('#rl-backtest-run-btn')
                # Wait for results
                page.wait_for_selector('#rl-analysis-results .card', timeout=15000) # Assuming backtest returns a card/graph
                snapshot_element(page, '#rl-analysis-results', '09_backtest_results.png')
                print("✓ Backtest results visible")
                
            else:
                print("x Brief selection failed (detail panel didn't update)")
                
        except Exception as e:
            print(f"Failed Analysis test: {e}")

        print('E2E test sequence complete.')
        browser.close()

if __name__ == '__main__':
    print("DEBUG: Calling main()", file=sys.stderr)
    main()
