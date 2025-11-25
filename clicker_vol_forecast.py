"""
Clicker Automation - Market Forecast & Volatility Lab UX Cycle

This script automates clicking through:
1. Market Forecast tab
2. All 8 Volatility Lab subtabs

Captures:
- Screenshot per step (screenshots/UX_cycle_*.png)
- Timestamps for each interaction
- Layout delays (time to render > 2s logged)

Usage:
    python clicker_vol_forecast.py
"""

import time
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Configuration
import os
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8050')
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

LOG_FILE = SCREENSHOT_DIR / "clicker_execution_log.json"

# Timing thresholds
MAX_LOAD_TIME = 5.0  # seconds - warn if tab takes longer
EXPECTED_LOAD_TIME = 3.0  # seconds - target

# Tabs and subtabs to visit
TABS_TO_VISIT = [
        {
        'name': 'Market Forecast',
        'tab_id': '#tab-market_forecast',
        'wait_selector': '#mf-run-btn',  # Wait for the Run button element
        'screenshot_name': 'UX_cycle_01_market_forecast'
    },
    {
        'name': 'Volatility Lab',
        'tab_id': '#tab-volatility_lab',
        'wait_selector': '#vl-tabs',
        'screenshot_name': 'UX_cycle_02_volatility_lab_main',
        'subtabs': [
            {'name': 'Historical HV', 'subtab_selector': 'button[data-value="hv"]', 'screenshot': 'UX_cycle_03_vol_hv'},
            {'name': 'IV Surface', 'subtab_selector': 'button[data-value="iv"]', 'screenshot': 'UX_cycle_04_vol_iv'},
            {'name': 'Correlation', 'subtab_selector': 'button[data-value="corr"]', 'screenshot': 'UX_cycle_05_vol_corr'},
            {'name': 'Factor Analytics', 'subtab_selector': 'button[data-value="factors"]', 'screenshot': 'UX_cycle_06_vol_factors'},
            {'name': 'Advanced Charts', 'subtab_selector': 'button[data-value="charts"]', 'screenshot': 'UX_cycle_07_vol_charts'},
            {'name': 'Metrics Table', 'subtab_selector': 'button[data-value="metrics"]', 'screenshot': 'UX_cycle_08_vol_metrics'},
            {'name': 'Custom Scenarios', 'subtab_selector': 'button[data-value="scenarios"]', 'screenshot': 'UX_cycle_09_vol_scenarios'},
            {'name': 'Alerts', 'subtab_selector': 'button[data-value="alerts"]', 'screenshot': 'UX_cycle_10_vol_alerts'},
        ]
    }
]


def run_clicker_automation():
    """Execute clicker automation with Playwright"""
    
    print("=" * 80)
    print("CLICKER AUTOMATION - MARKET FORECAST & VOLATILITY LAB")
    print("=" * 80)
    print(f"\nTarget URL: {BASE_URL}")
    print(f"Screenshots: {SCREENSHOT_DIR}/")
    print(f"Log file: {LOG_FILE}\n")
    
    execution_log = {
        'start_time': datetime.now().isoformat(),
        'base_url': BASE_URL,
        'steps': [],
        'warnings': [],
        'summary': {}
    }
    
    total_screenshots = 0
    total_warnings = 0
    
    with sync_playwright() as p:
        print("🌐 Launching browser...")
        browser = p.chromium.launch(headless=False)  # Set to True for headless
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Navigate to dashboard
        print(f"📂 Loading {BASE_URL}...")
        start_nav = time.time()
        page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        nav_time = time.time() - start_nav
        
        print(f"✅ Dashboard loaded in {nav_time:.2f}s\n")
        
        execution_log['steps'].append({
            'step': 0,
            'action': 'Initial page load',
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': round(nav_time, 3)
        })
        
        step_counter = 1
        
        # Iterate through tabs
        for tab in TABS_TO_VISIT:
            print(f"\n{'='*60}")
            print(f"TAB: {tab['name']}")
            print(f"{'='*60}")
            
            # Click main tab
            print(f"🖱️  Clicking tab: {tab['tab_id']}")
            start_click = time.time()
            
            try:
                page.click(tab['tab_id'], timeout=10000)
                
                # Wait for content to load
                if 'wait_selector' in tab:
                    page.wait_for_selector(tab['wait_selector'], timeout=10000)
                
                click_time = time.time() - start_click
                
                # Check for layout delay
                if click_time > EXPECTED_LOAD_TIME:
                    warning = f"⚠️  {tab['name']} took {click_time:.2f}s to load (expected < {EXPECTED_LOAD_TIME}s)"
                    print(warning)
                    execution_log['warnings'].append(warning)
                    total_warnings += 1
                else:
                    print(f"✅ Loaded in {click_time:.2f}s")
                
                # Take screenshot
                screenshot_path = SCREENSHOT_DIR / f"{tab['screenshot_name']}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                total_screenshots += 1
                print(f"📸 Screenshot: {screenshot_path.name}")
                
                execution_log['steps'].append({
                    'step': step_counter,
                    'action': f"Click tab: {tab['name']}",
                    'selector': tab['tab_id'],
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': round(click_time, 3),
                    'screenshot': str(screenshot_path.name)
                })
                
                step_counter += 1
                time.sleep(0.5)  # Brief pause for stability
                
            except Exception as e:
                error_msg = f"❌ Failed to click {tab['name']}: {e}"
                print(error_msg)
                execution_log['warnings'].append(error_msg)
                total_warnings += 1
                continue
            
            # Handle subtabs (for Volatility Lab)
            if 'subtabs' in tab:
                print(f"\n  Visiting {len(tab['subtabs'])} subtabs...")
                
                for subtab in tab['subtabs']:
                    print(f"\n  🖱️  Subtab: {subtab['name']}")
                    start_subtab = time.time()
                    
                    try:
                        # Click subtab
                        page.click(subtab['subtab_selector'], timeout=10000)
                        time.sleep(1)  # Wait for render
                        
                        subtab_time = time.time() - start_subtab
                        
                        if subtab_time > EXPECTED_LOAD_TIME:
                            warning = f"  ⚠️  {subtab['name']} took {subtab_time:.2f}s (expected < {EXPECTED_LOAD_TIME}s)"
                            print(warning)
                            execution_log['warnings'].append(warning)
                            total_warnings += 1
                        else:
                            print(f"  ✅ Loaded in {subtab_time:.2f}s")
                        
                        # Take screenshot
                        screenshot_path = SCREENSHOT_DIR / f"{subtab['screenshot']}.png"
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        total_screenshots += 1
                        print(f"  📸 Screenshot: {screenshot_path.name}")
                        
                        execution_log['steps'].append({
                            'step': step_counter,
                            'action': f"Click subtab: {subtab['name']}",
                            'selector': subtab['subtab_selector'],
                            'timestamp': datetime.now().isoformat(),
                            'duration_seconds': round(subtab_time, 3),
                            'screenshot': str(screenshot_path.name)
                        })
                        
                        step_counter += 1
                        
                    except Exception as e:
                        error_msg = f"  ❌ Failed to click {subtab['name']}: {e}"
                        print(error_msg)
                        execution_log['warnings'].append(error_msg)
                        total_warnings += 1
                        continue
        
        print(f"\n{'='*60}")
        print("CLOSING BROWSER")
        print(f"{'='*60}")
        browser.close()
    
    # Finalize log
    execution_log['end_time'] = datetime.now().isoformat()
    execution_log['summary'] = {
        'total_steps': step_counter - 1,
        'total_screenshots': total_screenshots,
        'total_warnings': total_warnings,
        'expected_screenshots': 1 + 1 + 8,  # Initial + Market Forecast + 8 Vol subtabs
        'screenshot_completeness': f"{total_screenshots}/{1 + 1 + 8}"
    }
    
    # Save log
    with open(LOG_FILE, 'w') as f:
        json.dump(execution_log, f, indent=2)
    
    print(f"\n✅ Execution log saved to: {LOG_FILE}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total steps: {step_counter - 1}")
    print(f"Screenshots captured: {total_screenshots}")
    print(f"Expected screenshots: {1 + 1 + 8}")
    print(f"Warnings: {total_warnings}")
    
    if total_warnings > 0:
        print(f"\n⚠️  Warnings detected:")
        for warning in execution_log['warnings']:
            print(f"   - {warning}")
    
    return execution_log


if __name__ == "__main__":
    try:
        log = run_clicker_automation()
        
        # Exit code based on success
        expected_screenshots = 1 + 1 + 8  # Initial + Market Forecast + 8 Vol subtabs
        if log['summary']['total_screenshots'] == expected_screenshots:
            print("\n✅ All screenshots captured successfully")
            exit(0)
        else:
            print(f"\n⚠️  Only {log['summary']['total_screenshots']}/{expected_screenshots} screenshots captured")
            exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        exit(2)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(3)
