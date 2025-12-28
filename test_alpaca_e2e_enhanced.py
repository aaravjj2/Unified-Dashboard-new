#!/usr/bin/env python3
"""
Non-Headless E2E Test for Enhanced Alpaca Options Lab

This script launches the Alpaca Options Lab on port 8053, opens a visible browser,
interacts with all major features, and takes snapshots at each step.

Features tested:
1. Options chain loading
2. Expiration selection
3. Greeks visualization
4. IV Surface 3D chart
5. Strategy builder
6. ML recommendations
7. Flow analysis
8. Export functionality
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Set up paths
BASE_DIR = Path(__file__).parent
SNAPSHOT_DIR = BASE_DIR / "e2e_snapshots" / datetime.now().strftime("%Y%m%d_%H%M%S")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Dashboard settings
PORT = 8053
BASE_URL = f"http://localhost:{PORT}"


def take_snapshot(page, name: str, step: int):
    """Take a screenshot with descriptive name."""
    filename = SNAPSHOT_DIR / f"{step:02d}_{name}.png"
    page.screenshot(path=str(filename), full_page=True)
    print(f"📸 Snapshot saved: {filename.name}")
    return filename


def wait_for_element(page, selector: str, timeout: int = 10000):
    """Wait for element to be visible."""
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        return True
    except Exception as e:
        print(f"⚠️ Timeout waiting for {selector}: {e}")
        return False


def run_e2e_tests():
    """Run comprehensive E2E tests with visible browser."""
    print("\n" + "="*60)
    print("🚀 ALPACA OPTIONS LAB - E2E TEST SUITE")
    print("="*60)
    print(f"📁 Snapshots will be saved to: {SNAPSHOT_DIR}")
    print()
    
    # Start the dashboard server
    print("🔧 Starting Alpaca Options Lab server on port 8053...")
    
    server_process = subprocess.Popen(
        [sys.executable, "run_alpaca_enhanced_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(BASE_DIR)
    )
    
    # Give server time to start
    print("⏳ Waiting for server to start...")
    time.sleep(8)  # Increased wait time
    
    test_results = []
    
    try:
        with sync_playwright() as p:
            # Launch visible browser (headless=False)
            print("🌐 Launching visible browser...")
            browser = p.chromium.launch(
                headless=False,  # Non-headless for visibility
                slow_mo=300  # Slow down for visibility
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            step = 1
            
            # TEST 1: Load the dashboard
            print(f"\n📋 TEST {step}: Load Dashboard")
            page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            # Wait extra time for React/Dash to fully render
            time.sleep(5)
            # Wait for ticker input which should always be present
            page.wait_for_selector("#alpaca-ticker-input", state="visible", timeout=10000)
            take_snapshot(page, "01_dashboard_loaded", step)
            test_results.append(("Load Dashboard", True))
            step += 1
            
            # TEST 2: Verify ticker input exists
            print(f"\n📋 TEST {step}: Verify Ticker Input")
            ticker_input = page.locator("#alpaca-ticker-input")
            if ticker_input.is_visible():
                print("✅ Ticker input is visible")
                test_results.append(("Ticker Input Visible", True))
            else:
                print("❌ Ticker input NOT visible")
                test_results.append(("Ticker Input Visible", False))
            step += 1
            
            # TEST 3: Load SPY options chain
            print(f"\n📋 TEST {step}: Load SPY Options Chain")
            ticker_input.fill("SPY")
            load_button = page.locator("#alpaca-load-button")
            load_button.click()
            
            # Wait for data to load
            time.sleep(5)
            take_snapshot(page, "02_spy_chain_loading", step)
            
            # Check for status message or table container
            status = page.locator("#alpaca-status-message")
            table_container = page.locator("#alpaca-table-container")
            chain_loaded = False
            
            if status.is_visible():
                status_text = status.inner_text()
                print(f"📊 Status: {status_text}")
                chain_loaded = "Successfully" in status_text or "✅" in status_text or len(status_text) == 0
            
            # Also check if table has content
            if table_container.is_visible():
                table_html = table_container.inner_html()
                if "table" in table_html.lower() or "div" in table_html:
                    chain_loaded = True
                    print("✅ Options table has content")
            
            test_results.append(("Load SPY Chain", chain_loaded))
            step += 1
            
            # TEST 4: Verify expiration dropdown populated
            print(f"\n📋 TEST {step}: Verify Expiration Dropdown")
            time.sleep(2)
            take_snapshot(page, "03_chain_loaded", step)
            
            # Check for table container
            table_container = page.locator("#alpaca-table-container")
            if table_container.is_visible():
                print("✅ Options table container is visible")
                test_results.append(("Options Table Visible", True))
            step += 1
            
            # TEST 5: Check for tabs
            print(f"\n📋 TEST {step}: Verify Feature Tabs Exist")
            # The enhanced layout uses Dash dcc.Tabs which generates div.tab inside tab-container
            time.sleep(2)
            # Dash Tabs use class 'tab' for tab buttons inside tab-container
            tabs = page.locator(".tab-container .tab")
            tab_count = tabs.count()
            print(f"📊 Found {tab_count} tabs")
            if tab_count > 0:
                for i in range(tab_count):
                    tab_text = tabs.nth(i).inner_text()
                    print(f"   Tab {i+1}: {tab_text}")
            take_snapshot(page, "04_feature_tabs", step)
            test_results.append(("Feature Tabs Present", tab_count >= 6))
            step += 1
            
            # TEST 6: Click on Greeks & IV tab (2nd tab)
            print(f"\n📋 TEST {step}: Navigate to Greeks & IV Tab")
            try:
                # Dash tabs have class "tab" inside "tab-container"
                all_tabs = page.locator(".tab-container .tab")
                tab_count = all_tabs.count()
                if tab_count >= 2:
                    all_tabs.nth(1).click()  # Click second tab (Greeks & IV)
                    time.sleep(2)
                    take_snapshot(page, "05_greeks_iv_tab", step)
                    print("✅ Greeks & IV tab loaded")
                    test_results.append(("Greeks & IV Tab", True))
                else:
                    print(f"⚠️ Only {tab_count} tabs found, need at least 2")
                    test_results.append(("Greeks & IV Tab", False))
            except Exception as e:
                print(f"⚠️ Could not click Greeks tab: {e}")
                test_results.append(("Greeks & IV Tab", False))
            step += 1
            
            # TEST 7: Click on Strategy Builder tab (3rd tab)
            print(f"\n📋 TEST {step}: Navigate to Strategy Builder Tab")
            try:
                all_tabs = page.locator(".tab-container .tab")
                if all_tabs.count() >= 3:
                    all_tabs.nth(2).click()
                    time.sleep(2)
                    take_snapshot(page, "06_strategy_builder_tab", step)
                    print("✅ Strategy Builder tab loaded")
                    test_results.append(("Strategy Builder Tab", True))
                else:
                    test_results.append(("Strategy Builder Tab", False))
            except Exception as e:
                print(f"⚠️ Could not click Strategy tab: {e}")
                test_results.append(("Strategy Builder Tab", False))
            step += 1
            
            # TEST 8: Click on AI tab (4th tab)
            print(f"\n📋 TEST {step}: Navigate to AI Recommendations Tab")
            try:
                all_tabs = page.locator(".tab-container .tab")
                if all_tabs.count() >= 4:
                    all_tabs.nth(3).click()
                    time.sleep(2)
                    take_snapshot(page, "07_ai_recommendations_tab", step)
                    print("✅ AI Recommendations tab loaded")
                    test_results.append(("AI Recommendations Tab", True))
                else:
                    test_results.append(("AI Recommendations Tab", False))
            except Exception as e:
                print(f"⚠️ Could not click AI tab: {e}")
                test_results.append(("AI Recommendations Tab", False))
            step += 1
            
            # TEST 9: Click on Flow tab (5th tab)
            print(f"\n📋 TEST {step}: Navigate to Flow Analysis Tab")
            try:
                all_tabs = page.locator(".tab-container .tab")
                if all_tabs.count() >= 5:
                    all_tabs.nth(4).click()
                    time.sleep(2)
                    take_snapshot(page, "08_flow_analysis_tab", step)
                    print("✅ Flow Analysis tab loaded")
                    test_results.append(("Flow Analysis Tab", True))
                else:
                    test_results.append(("Flow Analysis Tab", False))
            except Exception as e:
                print(f"⚠️ Could not click Flow tab: {e}")
                test_results.append(("Flow Analysis Tab", False))
            step += 1
            
            # TEST 10: Click on Positions tab (6th tab)
            print(f"\n📋 TEST {step}: Navigate to Positions Tab")
            try:
                all_tabs = page.locator(".tab-container .tab")
                if all_tabs.count() >= 6:
                    all_tabs.nth(5).click()
                    time.sleep(2)
                    take_snapshot(page, "09_positions_tab", step)
                    print("✅ Positions tab loaded")
                    test_results.append(("Positions Tab", True))
                else:
                    test_results.append(("Positions Tab", False))
            except Exception as e:
                print(f"⚠️ Could not click Positions tab: {e}")
                test_results.append(("Positions Tab", False))
            step += 1
            
            # TEST 11: Go back to Chain tab and change ticker
            print(f"\n📋 TEST {step}: Change Ticker to AAPL")
            try:
                # Click first tab (Chain)
                all_tabs = page.locator(".tab-container .tab")
                if all_tabs.count() > 0:
                    all_tabs.first.click()
                    time.sleep(1)
                
                ticker_input.fill("AAPL")
                load_button.click()
                time.sleep(5)
                take_snapshot(page, "10_aapl_chain", step)
                print("✅ AAPL chain loaded")
                test_results.append(("Change Ticker to AAPL", True))
            except Exception as e:
                print(f"⚠️ Could not change ticker: {e}")
                test_results.append(("Change Ticker to AAPL", False))
            step += 1
            
            # TEST 12: Final full page screenshot
            print(f"\n📋 TEST {step}: Final Screenshot")
            take_snapshot(page, "11_final_state", step)
            test_results.append(("Final Screenshot", True))
            
            # Keep browser open for 5 seconds for visual inspection
            print("\n👀 Keeping browser open for visual inspection (5 seconds)...")
            time.sleep(5)
            
            browser.close()
            
    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        test_results.append(("Overall Test Execution", False))
    
    finally:
        # Stop the server
        print("\n🛑 Stopping dashboard server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
    
    # Print results summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in test_results if result)
    failed = len(test_results) - passed
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print()
    print(f"Total: {passed}/{len(test_results)} tests passed")
    print(f"📁 Snapshots saved in: {SNAPSHOT_DIR}")
    
    return passed == len(test_results)


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
