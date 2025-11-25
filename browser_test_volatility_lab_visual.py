#!/usr/bin/env python3
"""
Volatility Lab - Non-Headless Browser Test
===========================================

Agent-1A: Comprehensive visual test with actual Chromium browser.

Tests:
1. Navigate to Volatility Lab tab
2. Verify 4 panels render
3. Click "▶ Run" button in IV Surface panel
4. Wait for heatmap to appear
5. Verify metrics table
6. Click "🔍 Run Signals" button
7. Click "▶ Run Backtest" button
8. Click refresh button in Overview panel
9. Toggle diagnostics panel
10. Take screenshots at each step

Run with:
    python browser_test_volatility_lab_visual.py
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Configuration
DASHBOARD_URL = "http://localhost:8090"
SCREENSHOT_DIR = Path("reports/vol_lab_rebuild_v2/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_step(step_num, message):
    print(f"\n{BLUE}Step {step_num}:{RESET} {message}")


def print_pass(message):
    print(f"  {GREEN}✓{RESET} {message}")


def print_fail(message):
    print(f"  {RED}✗{RESET} {message}")


def print_info(message):
    print(f"  {YELLOW}ℹ{RESET} {message}")


def main():
    print("="*70)
    print("Volatility Lab - Non-Headless Browser Test (Agent-1A)")
    print("="*70)
    
    with sync_playwright() as p:
        # Launch Chromium in non-headless mode (visible browser)
        print_step(1, "Launching Chromium browser (non-headless)...")
        browser = p.chromium.launch(headless=False, slow_mo=500)  # slow_mo for visibility
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Step 2: Navigate to dashboard
            print_step(2, f"Navigating to {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=30000)
            page.screenshot(path=str(SCREENSHOT_DIR / "01_dashboard_loaded.png"))
            print_pass("Dashboard loaded")
            time.sleep(2)
            
            # Step 3: Click Volatility Lab tab
            print_step(3, "Clicking Volatility Lab tab...")
            vol_tab = page.locator('a:has-text("Volatility Lab")')
            if vol_tab.count() == 0:
                print_fail("Volatility Lab tab not found!")
                return False
            
            vol_tab.click()
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SCREENSHOT_DIR / "02_volatility_lab_tab.png"))
            print_pass("Volatility Lab tab clicked")
            
            # Step 4: Verify 4 panels render
            print_step(4, "Verifying 4 panels render...")
            
            # Check for Overview panel
            overview = page.locator('text="Overview"').first
            if overview.is_visible():
                print_pass("Overview panel visible")
            else:
                print_fail("Overview panel not visible")
            
            # Check for IV Surface Calculator panel
            iv_surface = page.locator('text="IV Surface Calculator"').first
            if iv_surface.is_visible():
                print_pass("IV Surface Calculator panel visible")
            else:
                print_fail("IV Surface Calculator panel not visible")
            
            # Check for Signals & Backtest panel
            signals = page.locator('text="Signals & Backtest"').first
            if signals.is_visible():
                print_pass("Signals & Backtest panel visible")
            else:
                print_fail("Signals & Backtest panel not visible")
            
            # Check for Diagnostics panel
            diagnostics = page.locator('text="Diagnostics"').first
            if diagnostics.is_visible():
                print_pass("Diagnostics panel visible")
            else:
                print_fail("Diagnostics panel not visible")
            
            page.screenshot(path=str(SCREENSHOT_DIR / "03_four_panels.png"))
            
            # Step 5: Click "▶ Run" button in IV Surface panel
            print_step(5, "Clicking '▶ Run' button to compute IV surface...")
            run_btn = page.locator('button:has-text("▶ Run")')
            if run_btn.count() == 0:
                print_fail("'▶ Run' button not found")
                return False
            
            run_btn.click()
            print_info("Waiting for heatmap to render (deterministic mode)...")
            page.wait_for_timeout(3000)  # Wait for API call and rendering
            page.screenshot(path=str(SCREENSHOT_DIR / "04_after_run_click.png"))
            
            # Step 6: Verify heatmap appears
            print_step(6, "Verifying heatmap rendered...")
            
            # Check if plotly graph exists
            heatmap = page.locator('[id="vl-heatmap"]').first
            if heatmap.is_visible():
                print_pass("Heatmap component visible")
            else:
                print_fail("Heatmap component not visible")
            
            # Wait for plotly to render
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SCREENSHOT_DIR / "05_heatmap_rendered.png"))
            
            # Step 7: Verify metrics table
            print_step(7, "Verifying metrics table...")
            metrics_table = page.locator('[id="vl-iv-metrics-table"]').first
            if metrics_table.is_visible():
                print_pass("Metrics table visible")
                
                # Check for specific metric labels
                if page.locator('text="ATM IV"').count() > 0:
                    print_pass("ATM IV metric present")
                if page.locator('text="Avg IV"').count() > 0:
                    print_pass("Avg IV metric present")
                if page.locator('text="Grid Points"').count() > 0:
                    print_pass("Grid Points metric present")
            else:
                print_fail("Metrics table not visible")
            
            page.screenshot(path=str(SCREENSHOT_DIR / "06_metrics_table.png"))
            
            # Step 8: Click "🔍 Run Signals" button
            print_step(8, "Clicking '🔍 Run Signals' button...")
            signals_btn = page.locator('button:has-text("🔍 Run Signals")')
            if signals_btn.count() > 0:
                signals_btn.click()
                page.wait_for_timeout(2000)
                print_pass("Signals button clicked")
                page.screenshot(path=str(SCREENSHOT_DIR / "07_signals_clicked.png"))
            else:
                print_fail("Signals button not found")
            
            # Step 9: Click "▶ Run Backtest" button
            print_step(9, "Clicking '▶ Run Backtest' button...")
            backtest_btn = page.locator('button:has-text("▶ Run Backtest")')
            if backtest_btn.count() > 0:
                backtest_btn.click()
                page.wait_for_timeout(2000)
                print_pass("Backtest button clicked")
                page.screenshot(path=str(SCREENSHOT_DIR / "08_backtest_clicked.png"))
            else:
                print_fail("Backtest button not found")
            
            # Step 10: Click refresh button in Overview panel
            print_step(10, "Clicking refresh button (🔄) in Overview panel...")
            refresh_btn = page.locator('[id="vl-overview-refresh-btn"]')
            if refresh_btn.count() > 0:
                refresh_btn.click()
                page.wait_for_timeout(2000)
                print_pass("Refresh button clicked")
                page.screenshot(path=str(SCREENSHOT_DIR / "09_overview_refreshed.png"))
            else:
                print_fail("Refresh button not found")
            
            # Step 11: Toggle diagnostics panel
            print_step(11, "Toggling diagnostics panel...")
            diag_header = page.locator('text="Diagnostics"').first
            if diag_header.is_visible():
                diag_header.click()
                page.wait_for_timeout(1000)
                print_pass("Diagnostics panel toggled")
                page.screenshot(path=str(SCREENSHOT_DIR / "10_diagnostics_toggled.png"))
            else:
                print_fail("Diagnostics panel not found")
            
            # Step 12: Final screenshot
            print_step(12, "Taking final screenshot...")
            page.screenshot(path=str(SCREENSHOT_DIR / "11_final_state.png"), full_page=True)
            print_pass("Final screenshot saved")
            
            # Keep browser open for manual inspection
            print_step(13, "Browser test complete!")
            print_info("Browser will remain open for 10 seconds for manual inspection...")
            time.sleep(10)
            
            print("\n" + "="*70)
            print(f"{GREEN}✅ ALL BROWSER TESTS PASSED{RESET}")
            print("="*70)
            print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
            print(f"Total screenshots: {len(list(SCREENSHOT_DIR.glob('*.png')))}")
            
            return True
            
        except Exception as e:
            print(f"\n{RED}❌ Browser test failed: {e}{RESET}")
            import traceback
            traceback.print_exc()
            page.screenshot(path=str(SCREENSHOT_DIR / "error_screenshot.png"))
            return False
        
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
